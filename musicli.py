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
import fluidsynth
import mido
import sys
import time


class Note:
    def __init__(self, number, duration=1, velocity=127):
        self.number = number
        self.duration = duration
        self.velocity = velocity

    @property
    def semitone(self):
        return self.number % 12

    @property
    def name(self):
        return self.name_in_key('C')

    def name_in_key(self, key):
        sharp = key in ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#']
        semitone = self.semitone
        if semitone == 0:
            return 'C'
        elif semitone == 1:
            return 'C#' if sharp else 'Db'
        elif semitone == 2:
            return 'D'
        elif semitone == 3:
            return 'D#' if sharp else 'Eb'
        elif semitone == 4:
            return 'E'
        elif semitone == 5:
            return 'F'
        elif semitone == 6:
            return 'F#' if sharp else 'Gb'
        elif semitone == 7:
            return 'G'
        elif semitone == 8:
            return 'G#' if sharp else 'Ab'
        elif semitone == 9:
            return 'A'
        elif semitone == 10:
            return 'A#' if sharp else 'Bb'
        else:
            return 'B'

    @property
    def octave(self):
        return self.number // 12 - 1

    def __repr__(self):
        return self.name + str(self.octave)


def note_y(window, note):
    c4 = 60
    height = window.getmaxyx()[0]
    midpoint = height // 2
    return midpoint - (note.number - c4)


def draw_notes(window, beats):
    for x, notes in enumerate(beats):
        for note in notes:
            window.addstr(note_y(window, note), x * 2, str(note))


def main(stdscr):
    '''
    Main render/input loop.
    '''
    # Hide curses cursor
    curses.curs_set(0)

    # Allow using default terminal colors (-1 = default color)
    curses.use_default_colors()

    # Stores the notes played on each beat of the song
    beats = [[Note(60), Note(67), Note(76)]]

    needs_input = True
    input_code = None

    # Loop until user the exits
    while True:
        draw_notes(stdscr, beats)

        stdscr.refresh()

        try:
            input_code = stdscr.getch()
            # Block for input if auto mode is enabled
            while needs_input and input_code == curses.ERR:
                input_code = stdscr.getch()
        except KeyboardInterrupt:
            sys.exit(0)

        stdscr.erase()

        # Handle input

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
