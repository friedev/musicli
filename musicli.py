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


def main(stdscr):
    '''
    Main render/input loop.
    '''
    # Hide curses cursor
    curses.curs_set(0)

    # Allow using default terminal colors (-1 = default color)
    curses.use_default_colors()

    needs_input = True
    input_code = None

    # Loop until user the exits
    while True:
        stdscr.addstr(0, 0, 'hello')

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
