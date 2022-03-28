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

from .interface import Interface, ERROR_FLUIDSYNTH, ERROR_MIDO, KEYMAP
from .song import (Song,
                   COMMON_NAMES,
                   DEFAULT_BEATS_PER_MEASURE,
                   DEFAULT_COLS_PER_BEAT,
                   DEFAULT_KEY,
                   IMPORT_MIDO,
                   NAME_TO_NUMBER,
                   SCALES)
from .player import Player, IMPORT_FLUIDSYNTH, PLAY_EVENT, KILL_EVENT

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
    curses.ascii.TAB: 'Tab',
    curses.ascii.LF: 'Enter',
    curses.ascii.ESC: 'Escape',
}

ARGS = None
PLAYER = None


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
                player=PLAYER,
                ticks_per_beat=ARGS.ticks_per_beat,
                cols_per_beat=ARGS.cols_per_beat,
                beats_per_measure=ARGS.beats_per_measure,
                key=NAME_TO_NUMBER[ARGS.key],
                scale_name=ARGS.scale)

    if PLAYER is not None:
        playback_thread = Thread(target=PLAYER.play_song, args=[song])
        playback_thread.start()
    else:
        playback_thread = None

    try:
        Interface(song, PLAYER, ARGS.file, ARGS.unicode).main(stdscr)
    except Exception:
        with open(CRASH_FILE, 'w') as crash_file:
            crash_file.write(format_exc())
    finally:
        curses.cbreak()
        PLAY_EVENT.set()
        KILL_EVENT.set()
        if playback_thread is not None:
            playback_thread.join()
        if PLAYER is not None:
            PLAYER.synth.delete()
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


def main():
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
            '--key',
            type=str,
            choices=NAME_TO_NUMBER.keys(),
            default=COMMON_NAMES[DEFAULT_KEY],
            help='the key of the song to display in MusiCLI')
    parser.add_argument(
            '--scale',
            choices=SCALES.keys(),
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

    global ARGS
    ARGS = parser.parse_args()

    if ARGS.keymap:
        print_keymap()
        sys.exit(0)

    if IMPORT_MIDO:
        if ARGS.import_file:
            ARGS.import_file = ARGS.import_file.name
        elif ARGS.file:
            ARGS.import_file = ARGS.file
        if ARGS.file is None:
            ARGS.file = DEFAULT_FILE
    elif ARGS.file or ARGS.import_file:
        print(ERROR_MIDO)
        print()
        print('Try running:')
        print('pip3 install mido')
        sys.exit(1)

    if IMPORT_FLUIDSYNTH:
        if ARGS.soundfont:
            ARGS.soundfont = ARGS.soundfont.name
        elif os.path.isfile(DEFAULT_SOUNDFONT):
            with open(DEFAULT_SOUNDFONT, 'r') as default_soundfont:
                if default_soundfont.readable():
                    ARGS.soundfont = DEFAULT_SOUNDFONT
    elif ARGS.soundfont:
        print(ERROR_FLUIDSYNTH)
        print()
        print('Make sure FluidSynth itself is installed:')
        print('https://www.fluidsynth.org/download/')
        print('Then try running:')
        print('pip3 install pyfluidsynth')
        sys.exit(1)

    if ARGS.soundfont is not None and IMPORT_FLUIDSYNTH:
        global PLAYER
        PLAYER = Player(ARGS.soundfont)

    os.environ.setdefault('ESCDELAY', str(ESCDELAY))

    curses.wrapper(wrapper)
