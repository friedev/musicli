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
from mido import bpm2tempo, Message, MetaMessage, MidiFile, MidiTrack


# On some systems, color 8 is gray, but this is not fully standardized
COLOR_GRAY = 8

# Color pair numbers
INSTRUMENT_PAIRS = list(range(1, 8))
PAIR_SIDEBAR_NOTE = len(INSTRUMENT_PAIRS) + 1
PAIR_SIDEBAR_KEY = len(INSTRUMENT_PAIRS) + 2
PAIR_LINE = len(INSTRUMENT_PAIRS) + 3
PAIR_PLAYHEAD = len(INSTRUMENT_PAIRS) + 4
PAIR_STATUS_NORMAL = len(INSTRUMENT_PAIRS) + 5
PAIR_STATUS_INSERT = len(INSTRUMENT_PAIRS) + 6
PAIR_LAST_NOTE = len(INSTRUMENT_PAIRS) + 7
PAIR_LAST_CHORD = len(INSTRUMENT_PAIRS) + 8

SHARP_KEYS = ('C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#')
FLAT_KEYS = ('F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb')

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
DEFAULT_OCTAVE = 4
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

playhead_position = 0
events = []


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


class DummyEvent:
    def __init__(self, time):
        self.time = time

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time


class NoteEvent:
    def __init__(self,
                 on,
                 number,
                 time,
                 duration=None,
                 velocity=MAX_VELOCITY,
                 instrument=0):
        if time < 0:
            raise ValueError(f'Time must be non-negative; was {time}')

        self.on = on
        self.number = number
        self.time = time
        self.velocity = velocity
        self.instrument = instrument

        if duration is not None:
            if duration < 0:
                raise ValueError('Duration must be non-negative; was '
                                 f'{duration}')

            pair_time = time + duration if on else time - duration
            self.pair = NoteEvent(not on,
                                  number,
                                  pair_time,
                                  velocity=velocity,
                                  instrument=instrument)
            self.pair.pair = self
        else:
            self.pair = None

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
        else:
            return self.time - self.pair.time

    @property
    def semitone(self):
        return self.number % 12

    @property
    def name(self):
        return self.name_in_key(ARGS.key)

    def name_in_key(self, key):
        if key in SHARP_KEYS:
            return SHARP_NAMES[self.semitone]
        return FLAT_NAMES[self.semitone]

    @property
    def octave(self):
        return self.number // 12 - 1

    def set_duration(self, duration):
        if duration < 0:
            raise ValueError(f'Duration must be non-negative; was {duration}')

        if self.on:
            self.pair.time = self.time + duration
        else:
            self.time = self.pair.time + duration

    def __repr__(self):
        return self.name + str(self.octave)

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time

    def __eq__(self, other):
        return (isinstance(other, NoteEvent) and
                self.on == other.on and
                self.number == other.number and
                self.time == other.time and
                self.instrument == other.instrument)


def notes_to_events(notes):
    events = []
    for note in notes:
        events.append(note.on_event)
        events.append(note.off_event)
    return sorted(events)


def events_to_messages(events):
    messages = []
    last_time = 0
    for event in events:
        delta = event.time - last_time
        message_type = 'note_on' if event.on else 'note_off'
        messages.append(Message(message_type,
                                note=event.number,
                                velocity=event.velocity,
                                time=delta))
        last_time = event.time
    return messages


def notes_to_messages(notes):
    return events_to_messages(notes_to_events(notes))


def messages_to_notes(messages, instrument=0):
    notes_on = []
    notes = []
    time = 0
    for message in messages:
        time += message.time
        if message.type == 'note_on':
            notes_on.append(Note(number=message.note,
                                 start=time,
                                 duration=0,
                                 velocity=message.velocity,
                                 instrument=instrument))
        elif message.type == 'note_off':
            for note in notes_on:
                if note.number == message.note:
                    note.duration = time - note.start
                    insort(notes, note)
                    notes_on.remove(note)
    return notes


def import_midi(infile_path):
    infile = MidiFile(infile_path)
    ARGS.ticks_per_beat = infile.ticks_per_beat

    notes = []
    for i, track in enumerate(infile.tracks):
        notes += messages_to_notes(track, i)
    return notes


def export_midi(notes, filename):
    outfile = MidiFile(ticks_per_beat=ARGS.ticks_per_beat)

    track = MidiTrack()
    outfile.tracks.append(track)

    track.append(Message('program_change', program=12))
    track.append(MetaMessage('set_tempo',
                             tempo=bpm2tempo(ARGS.beats_per_minute)))

    for message in notes_to_messages(notes):
        track.append(message)

    outfile.save(filename)


def init_synth():
    synth = Synth()
    synth.start()
    soundfont = synth.sfload(ARGS.soundfont.name)
    synth.program_select(0, soundfont, 0, 0)
    return synth


def start_playback(synth):
    global events
    global playhead_position
    while True:
        if restart_playback.is_set():
            restart_playback.clear()
            play_playback.clear()

        play_playback.wait()
        if kill_threads.is_set():
            sys.exit(0)

        time = 0
        event_index = 0
        playhead_position = 0
        next_unit_time = units_to_ticks(1)
        while event_index < len(events):
            next_event = events[event_index]
            delta = min(next_unit_time, next_event.time) - time
            sleep(delta /
                  ARGS.ticks_per_beat /
                  ARGS.beats_per_minute *
                  60.0)

            event_index = bisect_left(events, NoteEvent(False, 0, time))
            next_event = events[event_index]

            if time == next_unit_time:
                playhead_position += 1
                next_unit_time = units_to_ticks(1)

            play_playback.wait()
            if restart_playback.is_set():
                break
            if kill_threads.is_set():
                sys.exit(0)

            if time == next_event.time:
                if next_event.on:
                    synth.noteon(0, next_event.number, next_event.velocity)
                else:
                    synth.noteoff(0, next_event.number)
                event_index += 1


def play_notes(synth, notes):
    for note in notes:
        synth.noteon(0, note.number, note.velocity)


def stop_notes(synth, notes):
    for note in notes:
        synth.noteoff(0, note.number)


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
        window.addstr(0, x,
                      str((x + x_offset) // units_per_measure),
                      curses.color_pair(PAIR_LINE))


def draw_line(window, x, string, attr, start_y=1):
    height, width = window.getmaxyx()
    if 0 <= x and x + len(string) < width:
        for y in range(start_y, height):
            window.addstr(y, x, string, attr)


def draw_notes(window, notes, last_note, last_chord, x_offset, y_offset):
    height, width = window.getmaxyx()
    for note in notes:
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
            color_pair = INSTRUMENT_PAIRS[note.instrument %
                                          len(INSTRUMENT_PAIRS)]

        for x in range(max(0, start_x), min(width - 1, end_x)):
            window.addstr(y, x, ' ', curses.color_pair(color_pair))

        if 0 <= start_x < width - 1:
            window.addstr(y, start_x, '▏' if ARGS.unicode else '[',
                          curses.color_pair(color_pair))

        note_width = end_x - start_x
        if note_width >= 4 and (0 <= start_x + 1 and
                                start_x + len(note.name) < width - 1):
            window.addstr(y, start_x + 1, note.name,
                          curses.color_pair(color_pair))


def draw_sidebar(window, octave, y_offset):
    height, _ = window.getmaxyx()
    for y, number in enumerate(range(y_offset, y_offset + height)):
        note = Note(number, 0, 0)
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
    play = playhead_position
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


def exit_curses(synth, playback_thread):
    curses.cbreak()
    if playback_thread is not None:
        play_playback.set()
        kill_threads.set()
        playback_thread.join()
    if synth is not None:
        synth.delete()
    sys.exit(0)


def main(stdscr):
    '''
    Main render/input loop.
    '''
    # Hide curses cursor
    curses.curs_set(0)

    # Allow using default terminal colors (-1 = default color)
    curses.use_default_colors()

    # Initialize color pairs
    for pair in INSTRUMENT_PAIRS:
        curses.init_pair(pair, curses.COLOR_BLACK, pair)
    try:
        curses.init_pair(PAIR_SIDEBAR_NOTE, COLOR_GRAY, curses.COLOR_BLACK)
        curses.init_pair(PAIR_LINE, COLOR_GRAY, -1)
        curses.init_pair(PAIR_LAST_CHORD, curses.COLOR_BLACK, COLOR_GRAY)
    except ValueError:
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

    if ARGS.file and os.path.exists(ARGS.file):
        notes = import_midi(ARGS.file)
    else:
        notes = []

    global playhead_position
    playback_thread = None

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
    message = ''

    input_code = None

    # Loop until user the exits
    while True:
        height, width = stdscr.getmaxyx()
        if play_playback.is_set() and (playhead_position < x_offset or
                                       playhead_position >= x_offset + width):
            x_offset = max(playhead_position -
                           playhead_position % units_per_measure -
                           x_sidebar_offset,
                           min_x_offset)

        draw_scale_dots(stdscr, key, scale, x_offset, y_offset)
        draw_measures(stdscr, x_offset)
        cursor_x = time + (0 if last_note is None else duration) - x_offset
        draw_line(stdscr, cursor_x, '▏' if ARGS.unicode else '|',
                  curses.color_pair(0),)
        draw_line(stdscr, playhead_position - x_offset, ' ',
                  curses.color_pair(PAIR_PLAYHEAD))
        draw_notes(stdscr, notes, last_note, last_chord, x_offset, y_offset)
        draw_sidebar(stdscr, octave, y_offset)
        draw_status_bar(stdscr, insert, filename, time, message)

        stdscr.refresh()

        try:
            input_code = stdscr.getch()
        except KeyboardInterrupt:
            exit_curses(SYNTH, playback_thread)

        stdscr.erase()

        # Reset message on next actual keypress
        if input_code != curses.ERR:
            message = ''

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
                note = Note(number,
                            units_to_ticks(time),
                            units_to_ticks(duration))

                if note in notes:
                    notes.remove(note)
                    if note == last_note:
                        last_note = None
                    if note in last_chord:
                        last_chord.remove(note)
                else:
                    insort(notes, note)
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
                    last_note.duration =\
                        max(last_note.duration - units_to_ticks(1),
                            units_to_ticks(1))
                else:
                    duration = max(1, duration - 1)
            elif input_char == ']':
                if last_note is not None:
                    last_note.duration += units_to_ticks(1)
                else:
                    duration += 1

            # Change duration of last chord
            elif input_char == '{':
                for note in last_chord:
                    note.duration = max(note.duration - units_to_ticks(1),
                                        units_to_ticks(1))
                duration = max(1, duration - 1)
            elif input_char == '}':
                for note in last_chord:
                    note.duration += units_to_ticks(1)
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
                    notes.remove(last_note)
                    last_note.start = new_start
                    insort(notes, last_note)

                # Shift last chord
                else:
                    for note in last_chord:
                        notes.remove(note)
                        if input_char == '<':
                            note.start = max(note.start - units_to_ticks(1), 0)
                            time = max(0, time - 1)
                        else:
                            note.start += units_to_ticks(1)
                            time += 1
                        insort(notes, note)

                if time < x_offset or time >= x_offset + width:
                    new_offset = time - width // 2
                    x_offset = max(new_offset -
                                   new_offset % units_per_measure +
                                   x_sidebar_offset,
                                   min_x_offset)

        # Delete last note
        elif input_code in (curses.KEY_DC, curses.KEY_BACKSPACE):
            if last_note is not None:
                notes.remove(last_note)
                last_chord.remove(last_note)
                last_note = None

        # Enter insert mode
        elif input_char == 'i':
            insert = True
            if time < x_offset or time >= x_offset + width:
                new_offset = time - width // 2
                x_offset = max(new_offset - new_offset % units_per_measure +
                               x_sidebar_offset,
                               min_x_offset)

        # Leave insert mode
        elif input_char == '`' or input_code == curses.ascii.ESC:
            if not insert:
                message = 'Press Ctrl+C to exit MusiCLI'
            insert = False

        # Start/stop audio playback
        elif input_char == ' ' and SYNTH is not None:
            if playback_thread is None or not playback_thread.is_alive():
                stop_notes(SYNTH, last_chord)
                restart_playback.clear()
                play_playback.set()
                playback_thread = Thread(target=start_playback,
                                         args=(notes_to_messages(notes),
                                               SYNTH))
                playback_thread.start()
                curses.halfdelay(1)
            elif play_playback.is_set():
                play_playback.clear()
                curses.cbreak()
            else:
                stop_notes(SYNTH, last_chord)
                play_playback.set()
                curses.halfdelay(1)

        # Restart playback at the beginning
        elif input_code == curses.ascii.LF and SYNTH is not None:
            play_playback.set()
            restart_playback.set()
            curses.cbreak()

        # Export to MIDI
        elif input_char == 'w':
            export_midi(notes, filename)
            message = f'Wrote MIDI to {filename}'

        elif input_char == 'q':
            message = 'Press Ctrl+C to exit MusiCLI'


def positive_int(value):
    int_value = int(value)
    if int_value <= 0:
        raise ArgumentTypeError(f'must be a positive integer; was {int_value}')
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

    if ARGS.beats_per_minute <= 0:
        raise ArgumentTypeError('Beats per minute must be positive; was '
                                f'{ARGS.beats_per_minute}')

    curses.wrapper(main)
