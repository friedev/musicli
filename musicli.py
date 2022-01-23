#!/usr/bin/env python3
# PyMusiCLI - A MIDI sequencer for the terminal
# Copyright (C) 2021 Aaron Friesen
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

import argparse
import curses
import curses.ascii
import sys
from time import sleep

from fluidsynth import Synth
from mido import bpm2tempo, Message, MidiFile, MidiTrack


# Python curses does not define curses.COLOR_GRAY, even though it appears to be
# number 8 by default
COLOR_GRAY = 8

# Color pair numbers
INSTRUMENT_PAIRS = list(range(1, 8))
PAIR_AXIS = len(INSTRUMENT_PAIRS) + 1
PAIR_LINE = len(INSTRUMENT_PAIRS) + 2

SHARP_KEYS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#']
FLAT_KEYS = ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb']

SHARP_NAMES = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
]

FLAT_NAMES = [
    'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'
]

SCALE_MAJOR = [0, 2, 4, 5, 7, 9, 11]
SCALE_MINOR = [0, 2, 3, 5, 7, 8, 10]
SCALE_BLUES = [0, 3, 5, 6, 7, 10]


def is_chr(char):
    '''
    Can the given character be cast to a chr?
    '''
    try:
        chr(char)
        return True
    except ValueError:
        return False

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


class Note:
    def __init__(self,
                 number,
                 start,
                 duration,
                 velocity=127,
                 instrument=0):
        self.number = number
        self.start = start
        self.duration = duration
        self.velocity = velocity
        self.instrument = instrument

    @property
    def end(self):
        return self.start + self.duration

    @property
    def semitone(self):
        return self.number % 12

    @property
    def name(self):
        return self.name_in_key('C')

    @property
    def on_event(self):
        return NoteEvent(on=True,
                         number=self.number,
                         time=self.start,
                         velocity=self.velocity,
                         instrument=self.instrument)

    @property
    def off_event(self):
        return NoteEvent(on=False,
                         number=self.number,
                         time=self.start + self.duration,
                         velocity=self.velocity,
                         instrument=self.instrument)

    def name_in_key(self, key):
        if key in SHARP_KEYS:
            return SHARP_NAMES[self.semitone]
        return FLAT_NAMES[self.semitone]

    @property
    def octave(self):
        return self.number // 12 - 1

    def __repr__(self):
        return self.name + str(self.octave)

    def __lt__(self, other):
        return self.start < other.start

    def __gt__(self, other):
        return self.start > other.start


class NoteEvent:
    def __init__(self,
                 on,
                 number,
                 time,
                 velocity=127,
                 instrument=0):
        self.on = on
        self.number = number
        self.time = time
        self.velocity = velocity
        self.instrument = instrument

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time


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
                    notes.append(note)
                    notes_on.remove(note)
    return notes


def import_midi(infile_path):
    infile = MidiFile(infile_path)
    ARGS.ticks_per_beat = infile.ticks_per_beat

    notes = []
    for i, track in enumerate(infile.tracks):
        notes += messages_to_notes(track, i)
    return notes


def export_midi(notes):
    outfile = MidiFile(ticks_per_beat=ARGS.ticks_per_beat)

    track = MidiTrack()
    outfile.tracks.append(track)

    track.append(Message('program_change', program=12))
    track.append(Message('set_tempo', tempo=bpm2tempo(ARGS.beats_per_minute)))

    for message in notes_to_messages(notes):
        track.append(message)

    outfile.save('test.mid')


def init_synth():
    synth = Synth()
    synth.start()
    soundfont = synth.sfload(ARGS.soundfont.name)
    synth.program_select(0, soundfont, 0, 0)
    return synth


def start_playback(messages, synth):
    for message in messages:
        sleep(message.time / ARGS.ticks_per_beat / ARGS.beats_per_minute * 60.0)
        if message.type == 'note_on':
            synth.noteon(0, message.note, message.velocity)
        elif message.type == 'note_off':
            synth.noteoff(0, message.note)


def draw_lines(window, x_offset, y_offset):
    height, width = window.getmaxyx()
    for y, note in enumerate(range(y_offset, y_offset + height)):
        semitone = note % 12
        if semitone in SCALE_MAJOR:
            for x in range(4 - x_offset % 4, width - 1, 4):
                window.addstr(height - y - 1,
                              x,
                              '·',
                              curses.color_pair(PAIR_LINE))


def draw_axis(window, y_offset):
    height = window.getmaxyx()[0]
    for y, note in enumerate(range(y_offset, y_offset + height)):
        window.addstr(height - y - 1,
                      0,
                      str(Note(note, 0, 0)).ljust(4),
                      curses.color_pair(PAIR_AXIS))


def draw_notes(window, notes, x_offset, y_offset):
    height, width = window.getmaxyx()
    for note in notes:
        y = height - (note.number - y_offset) - 1
        if y < 0 or y >= height:
            continue

        start_x = ticks_to_units(note.start) - x_offset
        end_x = ticks_to_units(note.end) - x_offset
        if end_x < 0 or start_x >= width - 1:
            continue

        color_pair = INSTRUMENT_PAIRS[note.instrument % len(INSTRUMENT_PAIRS)]

        for x in range(max(0, start_x), min(width - 1, end_x)):
            window.addstr(y,
                          x,
                          ' ',
                          curses.color_pair(color_pair))

        if 0 <= start_x < width - 1:
            window.addstr(y,
                          start_x,
                          '▏',
                          curses.color_pair(color_pair))


def exit_curses(synth):
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
    curses.init_pair(PAIR_AXIS, COLOR_GRAY, curses.COLOR_BLACK)
    curses.init_pair(PAIR_LINE, COLOR_GRAY, -1)

    notes = import_midi(ARGS.infile.name) if ARGS.infile else []

#   notes = [
#       Note(60, start=units_to_ticks(0),  duration=units_to_ticks(2)),
#       Note(62, start=units_to_ticks(2),  duration=units_to_ticks(2)),
#       Note(64, start=units_to_ticks(4),  duration=units_to_ticks(2)),
#       Note(62, start=units_to_ticks(6),  duration=units_to_ticks(2)),
#       Note(60, start=units_to_ticks(8),  duration=units_to_ticks(1)),
#       Note(62, start=units_to_ticks(9),  duration=units_to_ticks(1)),
#       Note(64, start=units_to_ticks(10), duration=units_to_ticks(1)),
#       Note(65, start=units_to_ticks(11), duration=units_to_ticks(1)),
#       Note(60, start=units_to_ticks(12), duration=units_to_ticks(8)),
#       Note(64, start=units_to_ticks(12), duration=units_to_ticks(8)),
#       Note(67, start=units_to_ticks(12), duration=units_to_ticks(8)),
#   ]

    min_x_offset = 4
    min_y_offset = 0
    max_y_offset = 127 - stdscr.getmaxyx()[0]
    x_offset = 4
    y_offset = 60 - stdscr.getmaxyx()[0] // 2

    needs_input = True
    input_code = None

    # Loop until user the exits
    while True:
        draw_lines(stdscr, x_offset, y_offset)
        draw_notes(stdscr, notes, x_offset, y_offset)
        draw_axis(stdscr, y_offset)

        stdscr.refresh()

        try:
            input_code = stdscr.getch()
            # Block for input if auto mode is enabled
            while needs_input and input_code == curses.ERR:
                input_code = stdscr.getch()
        except KeyboardInterrupt:
            exit_curses(SYNTH)

        stdscr.erase()

        if is_chr(input_code):
            input_char = chr(input_code)
        else:
            input_char = ''

        # Pan view
        if input_char == 'h':
            x_offset = max(x_offset - 1, min_x_offset)
        elif input_char == 'l':
            x_offset += 1
        elif input_char == 'j':
            y_offset = max(y_offset - 1, min_y_offset)
        elif input_char == 'k':
            y_offset = min(y_offset + 1, max_y_offset)

        # Export to MIDI
        elif input_char == 'w':
            export_midi(notes)

        elif input_char == ' ':
            start_playback(notes_to_messages(notes), SYNTH)

        # Quit
        elif input_char == 'q' or\
                input_code == curses.ascii.ESC or\
                input_code == curses.ascii.EOT:
            exit_curses(SYNTH)


if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser(
            description='A MIDI sequencer for the terminal')
    parser.add_argument(
            '-s', '--soundfont',
            type=argparse.FileType('r'),
            help='SF2 soundfont file to use for playback')
    parser.add_argument(
            '-i', '--infile',
            type=argparse.FileType('r'),
            help='MIDI file to read as input')
    parser.add_argument(
            '--ticks-per-beat',
            type=int,
            default=480,
            help='MIDI ticks per beat (quarter note)')
    parser.add_argument(
            '--units-per-beat',
            type=int,
            default=4,
            help='the number of subdivisions per beat to display in MusiCLI')
    parser.add_argument(
            '--beats-per-minute',
            type=int,
            default=120,
            help='the tempo of the song in beats per minute (BPM)')

    # Globals
    ARGS = parser.parse_args()
    SYNTH = init_synth() if ARGS.soundfont else None

    curses.wrapper(main)
