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
import curses
import curses.ascii
import os
import os.path
import sys
from threading import Thread
from traceback import format_exc

from fluidsynth import Synth
from mido import bpm2tempo

from interface import Interface, KEYMAP
from song import (Song,
                  COMMON_NAMES,
                  DEFAULT_BEATS_PER_MEASURE,
                  DEFAULT_COLS_PER_BEAT,
                  DEFAULT_KEY,
                  DEFAULT_TEMPO,
                  DEFAULT_VELOCITY,
                  NAME_TO_NUMBER,
                  SCALE_NAME_MAP)
from playback import Player, PLAY_EVENT, KILL_EVENT

###############################################################################
# CONSTANTS
###############################################################################

# Default files
DEFAULT_FILE = 'untitled.mid'
DEFAULT_SOUNDFONT = '/usr/share/soundfonts/default.sf2'
CRASH_FILE = 'crash.log'

ESCDELAY = 25

CURSES_KEY_NAMES = {
    curses.KEY_LEFT: 'Left',
    curses.KEY_RIGHT: 'Right',
    curses.KEY_UP: 'Up',
    curses.KEY_DOWN: 'Down',
    curses.KEY_PPAGE: 'Page Up',
    curses.KEY_NPAGE: 'Page Down',
    curses.KEY_HOME: 'Home',
    curses.KEY_END: 'End',
    curses.KEY_IC: 'Insert',
    curses.KEY_DC: 'Delete',
    curses.KEY_BACKSPACE: 'Backspace',
    curses.ascii.LF: 'Enter',
    curses.ascii.ESC: 'Escape',
}


def wrapper(stdscr):
    # Hide curses cursor
    curses.curs_set(0)

    # Allow using default terminal colors (-1 = default color)
    curses.use_default_colors()

    if ARGS.import_file and os.path.exists(ARGS.import_file):
        midi_file = ARGS.import_file
    else:
        midi_file = None

    song = Song(midi_file=midi_file,
                synth=SYNTH,
                soundfont=SOUNDFONT,
                tempo=bpm2tempo(ARGS.bpm) if ARGS.bpm is not None else None,
                ticks_per_beat=ARGS.ticks_per_beat,
                cols_per_beat=ARGS.cols_per_beat,
                beats_per_measure=ARGS.beats_per_measure,
                key=NAME_TO_NUMBER[ARGS.key],
                scale_name=ARGS.scale)

    if SYNTH is not None:
        player = Player(SYNTH, SOUNDFONT)
        playback_thread = Thread(target=player.play_song, args=[song])
        playback_thread.start()
    else:
        player = None

    try:
        Interface(song, player, ARGS.file, ARGS.unicode).main(stdscr)
    except Exception:
        with open(CRASH_FILE, 'w') as crash_file:
            crash_file.write(format_exc())
    finally:
        curses.cbreak()
        PLAY_EVENT.set()
        KILL_EVENT.set()
        playback_thread.join()
        if SYNTH is not None:
            SYNTH.delete()
        sys.exit(0)


def print_keymap():
    print('MusiCLI Keybindings:')
    for key, action in KEYMAP.items():
        key_name = CURSES_KEY_NAMES.get(key)
        if key_name is None:
            key_name = chr(key)
        print(f'\t{key_name}: {action.value}')
    print()
    print('NOTE: All alphanumeric keys map to notes in insert mode.')
    print('Refer to the left sidebar in the editor to see this mapping.')


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
            '-H', '--keymap',
            action='store_true',
            help='show the list of keybindings and exit')
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
            help='MIDI ticks per beat (quarter note)')
    parser.add_argument(
            '--cols-per-beat',
            type=positive_int,
            default=DEFAULT_COLS_PER_BEAT,
            help='the number of subdivisions per beat to display in MusiCLI')
    parser.add_argument(
            '--beats-per-measure',
            type=positive_int,
            default=DEFAULT_BEATS_PER_MEASURE,
            help='the number of beats per measure to display in MusiCLI')
    parser.add_argument(
            '--bpm',
            type=positive_int,
            help='the tempo of the song in beats per minute (BPM)')
    parser.add_argument(
            '--key',
            type=str,
            choices=NAME_TO_NUMBER.keys(),
            default=COMMON_NAMES[DEFAULT_KEY],
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
    parser.add_argument(
            '--crash-file',
            type=FileType('w'),
            help='file to write debugging info to in the event of a crash; '
                 'set to /dev/null to disable the crash file')
    parser.set_defaults(unicode=True)

    ARGS = parser.parse_args()

    if ARGS.keymap:
        print_keymap()
        sys.exit(0)

    if ARGS.import_file:
        ARGS.import_file = ARGS.import_file.name
    elif ARGS.file:
        ARGS.import_file = ARGS.file

    if ARGS.soundfont:
        ARGS.soundfont = ARGS.soundfont.name
    elif os.path.isfile(DEFAULT_SOUNDFONT):
        with open(DEFAULT_SOUNDFONT, 'r') as default_soundfont:
            if default_soundfont.readable():
                ARGS.soundfont = DEFAULT_SOUNDFONT

    if ARGS.soundfont is not None:
        SYNTH = Synth()
        SYNTH.start()
        SOUNDFONT = SYNTH.sfload(ARGS.soundfont)

    os.environ.setdefault('ESCDELAY', str(ESCDELAY))

    curses.wrapper(wrapper)
