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
import time

import fluidsynth
import mido


# Python curses does not define curses.COLOR_GRAY, even though it appears to be
# number 8 by default
COLOR_GRAY = 8

# Color pair numbers
INSTRUMENT_PAIRS = [1, 2, 3, 4, 5, 6]
PAIR_AXIS = 7

SHARP_KEYS = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#']
FLAT_KEYS = ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb']

SHARP_NAMES = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
]

FLAT_NAMES = [
    'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'
]


class Note:
    def __init__(self, number, duration=1, velocity=127, instrument=0):
        self.number = number
        self.duration = duration
        self.velocity = velocity
        self.instrument = instrument

    @property
    def semitone(self):
        return self.number % 12

    @property
    def name(self):
        return self.name_in_key('C')

    def name_in_key(self, key):
        if key in SHARP_KEYS:
            return SHARP_NAMES[self.semitone]
        else:
            return FLAT_NAMES[self.semitone]

    @property
    def octave(self):
        return self.number // 12 - 1

    def __repr__(self):
        return self.name + str(self.octave)


def draw_axis(window, x_offset, y_offset):
    height = window.getmaxyx()[0]
    for y, note in enumerate(range(y_offset, y_offset + height)):
        window.addstr(height - y - 1,
                      x_offset,
                      str(Note(note)),
                      curses.color_pair(PAIR_AXIS))


def draw_notes(window, beats, x_offset, y_offset):
    height = window.getmaxyx()[0]
    x = 4
    for notes in beats:
        for note in notes:
            string = str(note.name).ljust(note.duration)
            if len(string) > note.duration:
                string = ' ' * note.duration
            window.addstr(height - (note.number - y_offset) - 1,
                          x + x_offset,
                          string,
                          curses.color_pair(INSTRUMENT_PAIRS[note.instrument]))
        x += 2


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
    curses.init_pair(PAIR_AXIS, COLOR_GRAY, -1)

    # Stores the notes played on each beat of the song
    beats = [[Note(60, duration=4), Note(67, duration=2), Note(76, duration=1)]]

    x_offset = 0
    y_offset = 60 - stdscr.getmaxyx()[0] // 2

    needs_input = True
    input_code = None

    # Loop until user the exits
    while True:
        draw_axis(stdscr, x_offset, y_offset)
        draw_notes(stdscr, beats, x_offset, y_offset)

        stdscr.refresh()

        try:
            input_code = stdscr.getch()
            # Block for input if auto mode is enabled
            while needs_input and input_code == curses.ERR:
                input_code = stdscr.getch()
        except KeyboardInterrupt:
            sys.exit(0)

        stdscr.erase()

        if curses.ascii.isalnum(input_code):
            input_char = chr(input_code)
        else:
            input_char = ''

        # Quit
        if input_char == 'q' or\
                input_code == curses.ascii.ESC or\
                input_code == curses.ascii.EOT:
            sys.exit(0)


if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser(
            description='A MIDI sequencer for the terminal')
    parser.add_argument(
            'soundfont',
            type=argparse.FileType('r'),
            help='the SF2 soundfont file to use (required for playback)')
    # ARGS is global
    ARGS = parser.parse_args()

    curses.wrapper(main)
