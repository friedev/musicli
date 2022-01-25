#!/usr/bin/env python3
# MusiCLI - A MIDI sequencer for the terminal
# Copyright (C) 2022 Aaron Friesen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from argparse import ArgumentParser, ArgumentTypeError, FileType
from bisect import bisect_left, insort
import curses
import curses.ascii
import os
import os.path
import sys
from threading import Event, Thread
from time import sleep

from fluidsynth import Synth
from mido import (bpm2tempo, Message, MetaMessage, MidiFile, MidiTrack,
                  tempo2bpm)


# On some systems, color 8 is gray, but this is not fully standardized
COLOR_GRAY = 8

# Color pair numbers
INSTRUMENT_PAIRS = list(range(1, 7))
PAIR_DRUM = len(INSTRUMENT_PAIRS)
PAIR_SIDEBAR_NOTE = len(INSTRUMENT_PAIRS) + 1
PAIR_SIDEBAR_KEY = len(INSTRUMENT_PAIRS) + 2
PAIR_LINE = len(INSTRUMENT_PAIRS) + 3
PAIR_PLAYHEAD = len(INSTRUMENT_PAIRS) + 4
PAIR_STATUS_NORMAL = len(INSTRUMENT_PAIRS) + 5
PAIR_STATUS_INSERT = len(INSTRUMENT_PAIRS) + 6
PAIR_LAST_NOTE = len(INSTRUMENT_PAIRS) + 7
PAIR_LAST_CHORD = len(INSTRUMENT_PAIRS) + 8

SHARP_KEYS = ('G', 'D', 'A', 'E', 'B', 'F#', 'C#')
FLAT_KEYS = ('F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb')

COMMON_NAMES = (
    'C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'
)

SHARP_NAMES = (
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
)

FLAT_NAMES = (
    'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'
)

SCALE_MAJOR = [0, 2, 4, 5, 7, 9, 11]
SCALE_MAJOR_PENTATONIC = [0, 2, 4, 7, 9]
SCALE_MINOR_NATURAL = [0, 2, 3, 5, 7, 8, 10]
SCALE_MINOR_HARMONIC = [0, 2, 3, 5, 7, 8, 11]
SCALE_MINOR_PENTATONIC = [0, 3, 5, 7, 10]
SCALE_BLUES = [0, 3, 5, 6, 7, 10]

SCALE_NAME_MAP = {
    'major': SCALE_MAJOR,
    'major_pentatonic': SCALE_MAJOR_PENTATONIC,
    'natural_minor': SCALE_MINOR_NATURAL,
    'harmonic_minor': SCALE_MINOR_HARMONIC,
    'minor_pentatonic': SCALE_MAJOR_PENTATONIC,
    'blues': SCALE_BLUES,
}

TOTAL_NOTES = 127
NOTES_PER_OCTAVE = 12
MAX_VELOCITY = 127
DEFAULT_VELOCITY = MAX_VELOCITY  # 64 is recommended, but seems quiet
DEFAULT_OCTAVE = 4
TOTAL_INSTRUMENTS = 127  # Drums replace gunshot as instrument 128
DEFAULT_CHANNEL = 0
DEFAULT_BANK = 0
DRUM_CHANNEL = 9
DRUM_TRACK = 127  # Can't use 128 as MIDI only supports 127 tracks
DRUM_BANK = 128
DRUM_INSTRUMENT = 0
DEFAULT_FILE = 'untitled.mid'

INSERT_KEYMAP = {
    'z': 0,   # C
    's': 1,   # C#
    'x': 2,   # D
    'd': 3,   # D#
    'c': 4,   # E
    'v': 5,   # F
    'g': 6,   # F#
    'b': 7,   # G
    'h': 8,   # G#
    'n': 9,   # A
    'j': 10,  # A#
    'm': 11,  # B
    'q': 12,  # C
    '2': 13,  # C#
    'w': 14,  # D
    '3': 15,  # D#
    'e': 16,  # E
    'r': 17,  # F
    '5': 18,  # F#
    't': 19,  # G
    '6': 20,  # G#
    'y': 21,  # A
    '7': 22,  # A#
    'u': 23,  # B
    'i': 24,  # C
    '9': 25,  # C#
    'o': 26,  # D
    '0': 27,  # D#
    'p': 28,  # E
}

INSERT_KEYLIST = tuple('zsxdcvgbhnjmq2w3er5t6y7ui9o0p')

NAME_TO_NUMBER = {
    'C':  0,
    'C#': 1,
    'Db': 1,
    'D':  2,
    'D#': 3,
    'Eb': 3,
    'E':  4,
    'F':  5,
    'F#': 6,
    'Gb': 6,
    'G':  7,
    'G#': 8,
    'Ab': 8,
    'A':  9,
    'A#': 10,
    'Bb': 10,
    'B':  11,
}

play_playback = Event()
restart_playback = Event()
kill_threads = Event()

PLAYHEAD = 0
SONG = None
MESSAGE = ''


def number_to_name(number, scale=None, octave=True):
    semitone = number % NOTES_PER_OCTAVE
    if scale in SHARP_KEYS:
        letter = SHARP_NAMES[semitone]
    elif scale in FLAT_KEYS:
        letter = FLAT_NAMES[semitone]
    else:
        letter = COMMON_NAMES[semitone]
    if not octave:
        return letter
    octave = number // NOTES_PER_OCTAVE - 1
    return f'{letter}{octave}'


def name_to_number(name):
    number = NAME_TO_NUMBER.get(name[:2])
    if number is None:
        number = NAME_TO_NUMBER.get(name[:1])
        if number is None:
            raise ValueError(f'{name} is not a valid note name')
        octave = name[1:]
    else:
        octave = name[2:]

    if octave == '':
        return number
    try:
        return number + int(octave) * NOTES_PER_OCTAVE
    except ValueError as e:
        raise ValueError(f'{name} is not a valid note name') from e


def ticks_to_beats(ticks):
    return ticks // ARGS.ticks_per_beat


def beats_to_ticks(beats):
    return beats * ARGS.ticks_per_beat


def beats_to_units(beats):
    return beats * ARGS.units_per_beat


def units_to_beats(units):
    return units // ARGS.ticks_per_beat


def ticks_to_units(ticks):
    return int(ticks / ARGS.ticks_per_beat * ARGS.units_per_beat)


def units_to_ticks(units):
    return int(units / ARGS.units_per_beat * ARGS.ticks_per_beat)


class DummyNote:
    def __init__(self, time):
        self.time = time

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time


class Song:
    def __init__(self):
        self.notes = []

    def add(self, note, pair=True):
        if note in self:
            raise ValueError('Note {note} is already in this song')

        insort(self.notes, note)
        if pair:
            if note.pair is None:
                raise ValueError('Note {note} is unpaired')
            if note.pair in self:
                raise ValueError('Note {note.pair} is already in this song')
            insort(self.notes, note.pair)

    def remove(self, note, pair=True):
        self.notes.remove(note)
        if pair:
            if note.pair is None:
                raise ValueError('Note {note} is unpaired')
            self.notes.remove(note.pair)

    def move(self, note, time):
        self.remove(note)
        note.move(time)
        self.add(note)

    def get_next_index(self, time):
        return bisect_left(self.notes, DummyNote(time))

    def get_next_note(self, time):
        return self[self.get_next_index(time)]

    def __len__(self):
        return len(self.notes)

    def __getitem__(self, key):
        return self.notes[key]

    def __contains__(self, item):
        return item in self.notes


class Note:
    def __init__(self,
                 on,
                 number,
                 time,
                 duration=None,
                 velocity=DEFAULT_VELOCITY,
                 instrument=None,
                 channel=DEFAULT_CHANNEL):
        if time < 0:
            raise ValueError(f'Time must be non-negative; was {time}')

        self.on = on
        self.number = number
        self.time = time
        self.velocity = velocity
        self.instrument = (ARGS.default_instrument if instrument is None else
                           instrument)
        self.channel = channel

        self.pair = None
        if duration is not None:
            if duration <= 0:
                raise ValueError(f'Duration must be positive; was {duration}')
            self.make_pair(time + duration if on else time - duration)

    def make_pair(self, time):
        if time < 0:
            raise ValueError(f'Time must be non-negative; was {time}')

        if ((self.on and time <= self.time) or
                (not self.on and time >= self.time)):
            raise ValueError('Note must end strictly after it starts; '
                             f'times were {self.time} and {time}')

        self.pair = Note(not self.on,
                         self.number,
                         time,
                         velocity=self.velocity,
                         instrument=self.instrument,
                         channel=self.channel)
        self.pair.pair = self

    @property
    def start(self):
        return self.time if self.on else self.pair.time

    @property
    def end(self):
        return self.pair.time if self.on else self.time

    @property
    def duration(self):
        if self.on:
            return self.pair.time - self.time
        return self.time - self.pair.time

    @property
    def semitone(self):
        return self.number % 12

    @property
    def name(self):
        return number_to_name(self.number, octave=False)

    def name_in_key(self, key):
        return number_to_name(self.number, key, octave=False)

    @property
    def octave(self):
        return self.number // 12 - 1

    @property
    def is_drum(self):
        return self.channel == DRUM_CHANNEL

    @property
    def track(self):
        return DRUM_TRACK if self.is_drum else self.instrument

    @property
    def color_pair(self):
        if self.is_drum:
            return PAIR_DRUM
        return INSTRUMENT_PAIRS[self.instrument %
                                len(INSTRUMENT_PAIRS)]

    def play(self, synth):
        synth.noteon(self.track, self.number, self.velocity)

    def stop(self, synth):
        synth.noteoff(self.track, self.number)

    def move(self, time):
        if self.on:
            if self.pair is not None:
                self.pair.time = time + self.duration
        else:
            if self.pair is not None:
                self.pair.time = time - self.duration
                if self.pair.time < 0:
                    raise ValueError('New start time must be non-negative; '
                                     f'was {time}')
        self.time = time

    def set_duration(self, duration):
        if duration <= 0:
            raise ValueError(f'Duration must be positive; was {duration}')

        if self.pair is None:
            self.make_pair(self.time + duration if self.on else
                           self.time - duration)
        else:
            if self.on:
                self.pair.time = self.time + duration
            else:
                self.time = self.pair.time + duration

    def __str__(self):
        return self.name + str(self.octave)

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time

    def __eq__(self, other):
        return (isinstance(other, Note) and
                self.on == other.on and
                self.number == other.number and
                self.time == other.time and
                self.track == other.track)


def messages_to_notes(messages, instrument=None):
    if instrument is None:
        instrument = ARGS.default_instrument
    notes = []
    active_notes = []
    time = 0
    for message in messages:
        time += message.time
        if message.type == 'note_on':
            active_notes.append(Note(True,
                                     number=message.note,
                                     time=time,
                                     velocity=message.velocity,
                                     instrument=instrument,
                                     channel=message.channel))
        elif message.type == 'note_off':
            for note in active_notes:
                if note.number == message.note:
                    duration = time - note.time
                    if duration == 0:
                        active_notes.remove(note)
                    else:
                        note.set_duration(duration)
                        notes.append(note)
                        notes.append(note.pair)
                        active_notes.remove(note)
                        break
    return sorted(notes)


def notes_to_tracks(notes):
    tracks = {}
    last_times = {}
    for note in notes:
        if note.instrument not in tracks:
            tracks[note.instrument] = []
            last_times[note.instrument] = 0

        track = tracks[note.instrument]
        last_time = last_times[note.instrument]
        delta = note.time - last_time
        message_type = 'note_on' if note.on else 'note_off'
        message = Message(message_type,
                          note=note.number,
                          velocity=note.velocity,
                          time=delta,
                          channel=note.channel)

        track.append(message)
        last_times[note.instrument] = note.time
    return tracks


def import_midi(infile_path):
    infile = MidiFile(infile_path)
    ARGS.ticks_per_beat = infile.ticks_per_beat

    notes = []
    set_tempo = False
    for track in infile.tracks:
        instrument = 0

        # Use the first set_tempo message in any track as the song tempo
        # Use the first program_change message in this track as its instrument
        program_change = False
        for message in track:
            if not set_tempo and message.type == 'set_tempo':
                ARGS.beats_per_minute = tempo2bpm(message.tempo)
                set_tempo = True
            elif not program_change and message.type == 'program_change':
                instrument = message.program
                program_change = True
            if set_tempo and program_change:
                break

        notes += messages_to_notes(track, instrument)
    return sorted(notes)


def export_midi(notes, filename):
    outfile = MidiFile(ticks_per_beat=ARGS.ticks_per_beat)

    tracks = notes_to_tracks(notes)
    for instrument, messages in tracks.items():
        track = MidiTrack()
        track.append(Message('program_change', program=instrument,
                             channel=messages[0].channel))
        for message in messages:
            track.append(message)
        outfile.tracks.append(track)

    tempo_track = MidiTrack()
    tempo_track.append(MetaMessage('set_tempo',
                                   tempo=bpm2tempo(ARGS.beats_per_minute)))
    outfile.tracks.append(tempo_track)

    outfile.save(filename)


def init_synth():
    synth = Synth()
    synth.start()
    soundfont = synth.sfload(ARGS.soundfont.name)
    # For live playback, each track uses the instrument of the same number
    for i in range(TOTAL_INSTRUMENTS):
        synth.program_select(i, soundfont, DEFAULT_CHANNEL, i)
    synth.program_select(DRUM_TRACK, soundfont, DRUM_BANK, DRUM_INSTRUMENT)
    return synth


def start_playback(synth):
    global PLAYHEAD
    while True:
        if restart_playback.is_set():
            restart_playback.clear()

        play_playback.wait()
        if kill_threads.is_set():
            sys.exit(0)

        if len(SONG) == 0:
            play_playback.clear()
            continue

        time = 0
        note_index = 0
        PLAYHEAD = 0
        next_unit_time = units_to_ticks(1)
        next_note = SONG[note_index]
        while note_index < len(SONG):
            delta = min(next_unit_time, next_note.time) - time
            sleep(delta /
                  ARGS.ticks_per_beat /
                  ARGS.beats_per_minute *
                  60.0)

            time += delta

            if time == next_unit_time:
                PLAYHEAD += 1
                next_unit_time += units_to_ticks(1)
                note_index = SONG.get_next_index(time)
                next_note = SONG[note_index]

            play_playback.wait()
            if restart_playback.is_set():
                break
            if kill_threads.is_set():
                sys.exit(0)

            while note_index < len(SONG) and time == next_note.time:
                if next_note.on:
                    next_note.play(synth)
                else:
                    next_note.stop(synth)
                note_index += 1
                if note_index < len(SONG):
                    next_note = SONG[note_index]


def play_notes(synth, notes):
    for note in notes:
        if note.on:
            note.play(synth)


def stop_notes(synth, notes):
    for note in notes:
        note.stop(synth)


def draw_scale_dots(window, key, scale, x_offset, y_offset):
    height, width = window.getmaxyx()
    for y, note in enumerate(range(y_offset, y_offset + height - 1)):
        semitone = note % NOTES_PER_OCTAVE
        if semitone in [(number + key) % NOTES_PER_OCTAVE for number in scale]:
            for x in range(-x_offset % 4, width - 1, 4):
                window.addstr(height - y - 1, x, '·' if ARGS.unicode else '.',
                              curses.color_pair(PAIR_LINE))


def draw_measures(window, x_offset):
    _, width = window.getmaxyx()
    units_per_measure = ARGS.units_per_beat * ARGS.beats_per_measure
    for x in range(-x_offset % units_per_measure,
                   width - 1, units_per_measure):
        draw_line(window,
                  x,
                  '▏' if ARGS.unicode else '|',
                  curses.color_pair(PAIR_LINE),
                  start_y=0)

        # Measure number
        window.addstr(0, x,
                      str((x + x_offset) // units_per_measure + 1),
                      curses.color_pair(PAIR_LINE))


def draw_line(window, x, string, attr, start_y=1):
    height, width = window.getmaxyx()
    if 0 <= x and x + len(string) < width:
        for y in range(start_y, height):
            window.addstr(y, x, string, attr)


def draw_notes(window, notes, last_note, last_chord, x_offset, y_offset):
    # TODO only iterate over notes in view (assume list is sorted)
    height, width = window.getmaxyx()
    for note in notes:
        if not note.on:
            continue

        y = height - (note.number - y_offset) - 1
        if y <= 0 or y >= height:
            continue

        start_x = ticks_to_units(note.start) - x_offset
        end_x = ticks_to_units(note.end) - x_offset
        if end_x < 0 or start_x >= width - 1:
            continue

        if note is last_note:
            color_pair = PAIR_LAST_NOTE
        elif note in last_chord:
            color_pair = PAIR_LAST_CHORD
        else:
            color_pair = note.color_pair

        for x in range(max(0, start_x), min(width - 1, end_x)):
            window.addstr(y, x, ' ', curses.color_pair(color_pair))

        if 0 <= start_x < width - 1:
            window.addstr(y, start_x, '▏' if ARGS.unicode else '[',
                          curses.color_pair(color_pair))

        if note.is_drum:
            continue

        note_width = end_x - start_x
        if note_width >= 4 and (0 <= start_x + 1 and
                                start_x + len(note.name) < width - 1):
            window.addstr(y, start_x + 1, note.name,
                          curses.color_pair(color_pair))


def draw_sidebar(window, octave, y_offset):
    height, _ = window.getmaxyx()
    for y, number in enumerate(range(y_offset, y_offset + height)):
        note = number_to_name(number)
        insert_key = number - octave * NOTES_PER_OCTAVE
        window.addstr(height - y - 1,
                      0,
                      str(note).ljust(4).rjust(6),
                      curses.color_pair(PAIR_SIDEBAR_NOTE))
        if 0 <= insert_key < len(INSERT_KEYLIST):
            window.addstr(height - y - 1,
                          0,
                          INSERT_KEYLIST[insert_key],
                          curses.color_pair(PAIR_SIDEBAR_KEY))


def draw_status_bar(window, insert, filename, time, message):
    height, width = window.getmaxyx()

    window.addstr(height - 1,
                  0,
                  message.ljust(width - 1)[:width - 1],
                  curses.color_pair(0))

    mode_text = f' {"INSERT" if insert else "NORMAL"} '
    filename_text = f' {filename} '
    key_scale_text = f' {ARGS.key} {ARGS.scale} '
    play = PLAYHEAD
    play_text = (
            f' P{play // ARGS.units_per_beat // ARGS.beats_per_measure + 1}'
            f':{play // ARGS.units_per_beat % ARGS.beats_per_measure + 1} ')
    edit_text = (
            f' E{time // ARGS.units_per_beat // ARGS.beats_per_measure + 1}'
            f':{time // ARGS.units_per_beat % ARGS.beats_per_measure + 1} ')
    status_attr = curses.color_pair(PAIR_STATUS_INSERT if insert else
                                    PAIR_STATUS_NORMAL)
    x = 0
    window.addstr(height - 2,
                  x,
                  mode_text[:width - x - 1],
                  status_attr | curses.A_BOLD)
    x += len(mode_text)
    if x >= width:
        return

    window.addstr(height - 2,
                  x,
                  filename_text[:width - x - 1],
                  status_attr | curses.A_REVERSE | curses.A_BOLD)
    x += len(filename_text)
    if x >= width:
        return

    filler_width = (width -
                    len(mode_text) -
                    len(filename_text) -
                    len(key_scale_text) -
                    len(play_text) -
                    len(edit_text) - 1)
    if filler_width > 0:
        window.addstr(height - 2,
                      x,
                      ' ' * filler_width,
                      status_attr | curses.A_REVERSE)
        x += filler_width

    window.addstr(height - 2,
                  x,
                  key_scale_text[:width - x - 1],
                  status_attr | curses.A_REVERSE)
    x += len(key_scale_text)
    if x >= width:
        return

    window.addstr(height - 2,
                  x,
                  play_text[:width - x - 1],
                  status_attr | curses.A_BOLD)
    x += len(play_text)
    if x >= width:
        return

    window.addstr(height - 2,
                  x,
                  edit_text[:width - x - 1],
                  status_attr | curses.A_BOLD)
    x += len(edit_text)
    if x >= width:
        return


def main(stdscr):
    '''
    Main render/input loop.
    '''
    global SONG, MESSAGE
    SONG = Song()

    if ARGS.import_file and os.path.exists(ARGS.import_file):
        SONG.notes = import_midi(ARGS.import_file)

    height, width = stdscr.getmaxyx()
    units_per_measure = ARGS.units_per_beat * ARGS.beats_per_measure
    x_sidebar_offset = -6
    min_x_offset = x_sidebar_offset
    min_y_offset = 0
    max_y_offset = TOTAL_NOTES - height
    x_offset = min_x_offset
    y_offset = (DEFAULT_OCTAVE + 1) * NOTES_PER_OCTAVE - height // 2

    insert = False
    octave = DEFAULT_OCTAVE
    key = NAME_TO_NUMBER[ARGS.key]
    scale = SCALE_NAME_MAP[ARGS.scale]
    time = 0
    duration = ARGS.units_per_beat
    last_note = None
    last_chord = []
    filename = ARGS.file if ARGS.file else DEFAULT_FILE

    input_code = None

    # Loop until user the exits
    while True:
        height, width = stdscr.getmaxyx()
        if (not insert and
                play_playback.is_set() and
                (PLAYHEAD < x_offset or PLAYHEAD >= x_offset + width)):
            x_offset = max(PLAYHEAD -
                           PLAYHEAD % units_per_measure +
                           x_sidebar_offset,
                           min_x_offset)

        draw_scale_dots(stdscr, key, scale, x_offset, y_offset)
        draw_measures(stdscr, x_offset)
        cursor_x = time + (0 if last_note is None else duration) - x_offset
        draw_line(stdscr, cursor_x, '▏' if ARGS.unicode else '|',
                  curses.color_pair(0),)
        draw_line(stdscr, PLAYHEAD - x_offset, ' ',
                  curses.color_pair(PAIR_PLAYHEAD))
        draw_notes(stdscr, SONG.notes, last_note, last_chord, x_offset,
                   y_offset)
        draw_sidebar(stdscr, octave, y_offset)
        draw_status_bar(stdscr, insert, filename, time, MESSAGE)

        stdscr.refresh()

        # Get keyboard input
        # Don't handle KeyboardInterrupt here, because when the song is
        # playing, raw mode will not block on this check, so the
        # KeyboardInterrupt is likely to be generated during some other part of
        # the loop
        # Thus, handling it outside the method allows for more consistently
        # graceful shutdowns
        input_code = stdscr.getch()

        stdscr.erase()

        # Reset message on next actual keypress
        if input_code != curses.ERR:
            MESSAGE = ''

        if curses.ascii.isprint(input_code):
            input_char = chr(input_code)
        else:
            input_char = ''

        if insert:
            number = INSERT_KEYMAP.get(input_char.lower())
            if number is not None:
                if SYNTH is not None and not play_playback.is_set():
                    stop_notes(SYNTH, last_chord)

                if last_note is not None and not input_char.isupper():
                    time += duration
                    if insert and time > x_offset + width:
                        new_offset = time - width // 2
                        x_offset = max(new_offset -
                                       new_offset % units_per_measure +
                                       x_sidebar_offset,
                                       min_x_offset)
                    last_chord = []

                number += octave * NOTES_PER_OCTAVE
                note = Note(True,
                            number,
                            units_to_ticks(time),
                            units_to_ticks(duration))

                if note in SONG.notes:
                    SONG.remove(note)
                    if note == last_note:
                        last_note = None
                    if note in last_chord:
                        last_chord.remove(note)
                else:
                    SONG.add(note)
                    last_note = note
                    last_chord.append(note)

                if SYNTH is not None and not play_playback.is_set():
                    play_notes(SYNTH, last_chord)
                continue
        else:
            # Pan view
            if input_char.lower() in tuple('hl'):
                delta = (ARGS.units_per_beat if input_char.isupper() else
                         ARGS.units_per_beat * ARGS.beats_per_measure)
                if input_char.lower() == 'h':
                    x_offset = max(x_offset - delta, min_x_offset)
                else:
                    x_offset += delta
            if input_char.lower() in tuple('kj'):
                delta = 1 if input_char.isupper() else NOTES_PER_OCTAVE
                if input_char.lower() == 'j':
                    y_offset = max(y_offset - delta, min_y_offset)
                if input_char.lower() == 'k':
                    y_offset = min(y_offset + delta, max_y_offset)

            # Enter insert mode
            elif input_char in tuple('ia'):
                insert = True

                if input_char == 'a':
                    time += duration

                if time < x_offset or time >= x_offset + width:
                    new_offset = time - width // 2
                    x_offset = max(new_offset -
                                   new_offset % units_per_measure +
                                   x_sidebar_offset,
                                   min_x_offset)

            # Export to MIDI
            elif input_char == 'w':
                export_midi(SONG.notes, filename)
                MESSAGE = f'Wrote MIDI to {filename}'

            # Q doesn't quit
            # It'd be too easy to do on accident because it's C in insert mode
            # Instead, show a message saying how to exit
            elif input_char == 'q':
                MESSAGE = 'Press Ctrl+C to exit MusiCLI'

        # Move the editing cursor and octave
        if input_code in (curses.KEY_LEFT, curses.KEY_RIGHT):
            if input_code == curses.KEY_LEFT:
                time = max(time - duration, 0)
            elif input_code == curses.KEY_RIGHT:
                time += duration

            if time < x_offset or time >= x_offset + width:
                new_offset = time - width // 2
                x_offset = max(new_offset - new_offset % units_per_measure +
                               x_sidebar_offset,
                               min_x_offset)
        elif input_code == curses.KEY_UP:
            octave = min(octave + 1, TOTAL_NOTES // NOTES_PER_OCTAVE - 1)
            y_offset = min(((octave + 1) * NOTES_PER_OCTAVE) - height // 2,
                           max_y_offset)
        elif input_code == curses.KEY_DOWN:
            octave = max(octave - 1, 0)
            y_offset = max(((octave + 1) * NOTES_PER_OCTAVE) - height // 2,
                           min_y_offset)

        elif input_char in tuple('[]{}'):
            # Change duration of last note
            if input_char == '[':
                if last_note is not None:
                    last_note.set_duration(max(last_note.duration -
                                               units_to_ticks(1),
                                               units_to_ticks(1)))
                else:
                    duration = max(1, duration - 1)
            elif input_char == ']':
                if last_note is not None:
                    last_note.set_duration(last_note.duration +
                                           units_to_ticks(1))
                else:
                    duration += 1

            # Change duration of last chord
            elif input_char == '{':
                for note in last_chord:
                    note.set_duration(max(note.duration - units_to_ticks(1),
                                          units_to_ticks(1)))
                duration = max(1, duration - 1)
            elif input_char == '}':
                for note in last_chord:
                    note.set_duration(note.duration + units_to_ticks(1))
                duration += 1

            # Update duration and time for next insertion
            if last_note is not None:
                duration = ticks_to_units(last_note.duration)

        elif input_char in tuple(',.<>'):
            if last_note is not None:
                # Shift last note
                if input_char in tuple(',.'):
                    if input_char == ',':
                        new_start = max(last_note.start - units_to_ticks(1), 0)
                        time = max(0, time - 1)
                    else:
                        new_start = last_note.start + units_to_ticks(1)
                        time += 1
                    SONG.move(last_note, new_start)

                # Shift last chord
                else:
                    for note in last_chord:
                        if input_char == '<':
                            note.start = max(note.start - units_to_ticks(1), 0)
                            time = max(0, time - 1)
                        else:
                            note.start += units_to_ticks(1)
                            time += 1
                        SONG.move(note, new_start)

                if time < x_offset or time >= x_offset + width:
                    new_offset = time - width // 2
                    x_offset = max(new_offset -
                                   new_offset % units_per_measure +
                                   x_sidebar_offset,
                                   min_x_offset)

        # Delete last note
        elif input_code in (curses.KEY_DC, curses.KEY_BACKSPACE):
            if last_note is not None:
                SONG.remove(last_note)
                last_chord.remove(last_note)
                last_note = None

        # Leave insert mode or deselect notes
        elif input_code == curses.ascii.ESC:
            if not insert:
                if last_note is None:
                    MESSAGE = 'Press Ctrl+C to exit MusiCLI'
                else:
                    last_note = None
                    last_chord = []
            else:
                stop_notes(SYNTH, last_chord)
                insert = False

        # Start/stop audio playback
        elif input_char == ' ' and SYNTH is not None:
            if play_playback.is_set():
                play_playback.clear()
                curses.cbreak()
            else:
                stop_notes(SYNTH, last_chord)
                play_playback.set()
                curses.halfdelay(1)

        # Restart playback at the beginning
        elif input_code == curses.ascii.LF and SYNTH is not None:
            restart_playback.set()
            play_playback.set()
            curses.halfdelay(1)


def wrapper(stdscr):
    '''
    Wrapper method for curses. Hosts actual main method.
    '''
    # Hide curses cursor
    curses.curs_set(0)

    # Allow using default terminal colors (-1 = default color)
    curses.use_default_colors()

    # Initialize color pairs
    for pair in INSTRUMENT_PAIRS:
        curses.init_pair(pair, curses.COLOR_BLACK, pair)
    try:
        curses.init_pair(PAIR_DRUM, curses.COLOR_BLACK, COLOR_GRAY)
        curses.init_pair(PAIR_SIDEBAR_NOTE, COLOR_GRAY, curses.COLOR_BLACK)
        curses.init_pair(PAIR_LINE, COLOR_GRAY, -1)
        curses.init_pair(PAIR_LAST_CHORD, curses.COLOR_BLACK, COLOR_GRAY)
    except ValueError:
        curses.init_pair(PAIR_DRUM, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(PAIR_SIDEBAR_NOTE,
                         curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(PAIR_LINE, curses.COLOR_WHITE, -1)
        curses.init_pair(PAIR_LAST_CHORD,
                         curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(PAIR_SIDEBAR_KEY, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(PAIR_PLAYHEAD, -1, curses.COLOR_WHITE)
    curses.init_pair(PAIR_STATUS_NORMAL,
                     curses.COLOR_BLACK, curses.COLOR_BLUE)
    curses.init_pair(PAIR_STATUS_INSERT,
                     curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(PAIR_LAST_NOTE, curses.COLOR_BLACK, curses.COLOR_WHITE)

    playback_thread = Thread(target=start_playback, args=[SYNTH])
    playback_thread.start()

    try:
        main(stdscr)
    finally:
        curses.cbreak()
        play_playback.set()
        kill_threads.set()
        playback_thread.join()
        if SYNTH is not None:
            SYNTH.delete()
        sys.exit(0)


def positive_int(value):
    int_value = int(value)
    if int_value <= 0:
        raise ArgumentTypeError(f'must be a positive integer; was {int_value}')
    return int_value


def short_int(value):
    int_value = int(value)
    if not 0 <= int_value < 128:
        raise ArgumentTypeError('must be an integer from 0-127; was '
                                f'{int_value}')
    return int_value


def optional_file(value):
    if os.path.isdir(value):
        raise ArgumentTypeError(f'file cannot be a directory; was {value}')
    if os.path.exists(value):
        with open(value, 'r') as file:
            if not file.readable():
                raise ArgumentTypeError(f'cannot read {value}')
    return value


if __name__ == '__main__':
    # Parse arguments
    parser = ArgumentParser(
            description='A MIDI sequencer for the terminal')
    parser.add_argument(
            'file',
            type=optional_file,
            nargs='?',
            help='MIDI file to read input from and write output to')
    parser.add_argument(
            '-i', '--import',
            dest='import_file',
            type=FileType('r'),
            help='MIDI file to import from; overrides the file argument for '
                 'importing')
    parser.add_argument(
            '-f', '--soundfont',
            type=FileType('r'),
            help='SF2 soundfont file to use for playback')
    parser.add_argument(
            '--ticks-per-beat',
            type=positive_int,
            default=480,
            help='MIDI ticks per beat (quarter note)')
    parser.add_argument(
            '--units-per-beat',
            type=positive_int,
            default=4,
            help='the number of subdivisions per beat to display in MusiCLI')
    parser.add_argument(
            '--beats-per-measure',
            type=positive_int,
            default=4,
            help='the number of beats per measure to display in MusiCLI')
    parser.add_argument(
            '--beats-per-minute',
            type=positive_int,
            default=120,
            help='the tempo of the song in beats per minute (BPM)')
    parser.add_argument(
            '--key',
            type=str,
            choices=NAME_TO_NUMBER.keys(),
            default='C',
            help='the key of the song to display in MusiCLI')
    parser.add_argument(
            '--scale',
            choices=SCALE_NAME_MAP.keys(),
            default='major',
            help='the scale of the song to display in MusiCLI')
    parser.add_argument(
            '--default-velocity',
            type=short_int,
            default=MAX_VELOCITY,
            help='the default velocity to use for new notes')
    parser.add_argument(
            '--default-instrument',
            type=short_int,
            default=0,
            help='the default instrument to use for playback if no other '
                 'instrument is specified; given as a 0-indexed MIDI'
                 'instrument number')
    parser.add_argument(
            '-u', '--unicode',
            dest='unicode',
            action='store_true',
            help='enable unicode characters (default)')
    parser.add_argument(
            '-U', '--no-unicode',
            dest='unicode',
            action='store_false',
            help='disable unicode characters')
    parser.set_defaults(unicode=True)

    # Globals
    ARGS = parser.parse_args()
    SYNTH = init_synth() if ARGS.soundfont else None

    if ARGS.import_file:
        ARGS.import_file = ARGS.import_file.name
    if ARGS.file and not ARGS.import_file:
        ARGS.import_file = ARGS.file

    os.environ.setdefault('ESCDELAY', '25')

    curses.wrapper(wrapper)
