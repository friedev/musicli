import argparse
from argparse import (
    ArgumentParser,
    ArgumentTypeError,
    BooleanOptionalAction,
    FileType,
)
import curses
import curses.ascii
import os
import os.path
import sys
from threading import Thread
from traceback import format_exc
from typing import Optional

from .interface import Interface, ERROR_FLUIDSYNTH, ERROR_MIDO, KEYMAP
from .song import (
    Song,
    COMMON_NAMES,
    DEFAULT_BEATS_PER_MEASURE,
    DEFAULT_COLS_PER_BEAT,
    DEFAULT_KEY,
    DEFAULT_SCALE_NAME,
    DEFAULT_TICKS_PER_BEAT,
    IMPORT_MIDO,
    NAME_TO_NUMBER,
    SCALES,
)
from .player import Player, IMPORT_FLUIDSYNTH, PLAY_EVENT, KILL_EVENT

# Default files
DEFAULT_FILE = "untitled.mid"
DEFAULT_SOUNDFONT = "/usr/share/soundfonts/default.sf2"
CRASH_FILE = "crash.log"

ESCDELAY = 25

CURSES_KEY_NAMES: dict[int, str] = {
    curses.KEY_LEFT: "Left",
    curses.KEY_RIGHT: "Right",
    curses.KEY_UP: "Up",
    curses.KEY_DOWN: "Down",
    curses.KEY_PPAGE: "Page Up",
    curses.KEY_NPAGE: "Page Down",
    curses.KEY_HOME: "Home",
    curses.KEY_END: "End",
    curses.KEY_IC: "Insert",
    curses.KEY_DC: "Delete",
    curses.KEY_BACKSPACE: "Backspace",
    curses.ascii.TAB: "Tab",
    curses.ascii.LF: "Enter",
    curses.ascii.ESC: "Escape",
}

ARGS: argparse.Namespace
PLAYER: Optional[Player] = None


def wrapper(stdscr: curses.window) -> None:
    # Hide curses cursor
    curses.curs_set(0)

    # Allow using default terminal colors (-1 = default color)
    curses.use_default_colors()

    if ARGS.import_file and os.path.exists(ARGS.import_file):
        midi_file = ARGS.import_file
    else:
        midi_file = None

    song = Song(
        midi_file=midi_file,
        player=PLAYER,
        ticks_per_beat=ARGS.ticks_per_beat,
        cols_per_beat=ARGS.cols_per_beat,
        beats_per_measure=ARGS.beats_per_measure,
        key=NAME_TO_NUMBER[ARGS.key],
        scale_name=ARGS.scale,
    )

    if PLAYER is not None:
        playback_thread = Thread(
            target=PLAYER.try_play_song, args=[song, CRASH_FILE]
        )
        playback_thread.start()
    else:
        playback_thread = None

    status = 0
    try:
        interface = Interface(stdscr, song, PLAYER, ARGS.file, ARGS.unicode)
        interface.main()
    except Exception:
        status = 1
        with open(CRASH_FILE, "w") as crash_file:
            crash_file.write(format_exc())
    finally:
        curses.cbreak()
        PLAY_EVENT.set()
        KILL_EVENT.set()
        if playback_thread is not None:
            playback_thread.join()
        if PLAYER is not None:
            PLAYER.synth.delete()
        sys.exit(status)


def print_keymap() -> None:
    print("MusiCLI Keybindings:")
    for key, action in KEYMAP.items():
        key_name = CURSES_KEY_NAMES.get(key)
        if key_name is None:
            key_name = chr(key)
        print(f"\t{key_name}: {action.value}")
    print()
    print("NOTE: All alphanumeric keys map to notes in insert mode.")
    print("Refer to the left sidebar in the editor to see this mapping.")


def positive_int(value) -> int:
    int_value = int(value)
    if int_value <= 0:
        raise ArgumentTypeError(f"must be a positive integer; was {int_value}")
    return int_value


def short_int(value) -> int:
    int_value = int(value)
    if not 0 <= int_value < 128:
        raise ArgumentTypeError(
            "must be an integer from 0-127; was " f"{int_value}"
        )
    return int_value


def optional_file(value):
    if os.path.isdir(value):
        raise ArgumentTypeError(f"file cannot be a directory; was {value}")
    if os.path.exists(value):
        with open(value, "r") as file:
            if not file.readable():
                raise ArgumentTypeError(f"cannot read {value}")
    return value


def main() -> None:
    global CRASH_FILE

    # Parse arguments
    parser = ArgumentParser(description="TUI MIDI sequencer")
    parser.add_argument(
        "-H",
        "--keymap",
        action="store_true",
        help="show the list of keybindings and exit",
    )
    parser.add_argument(
        "file",
        type=optional_file,
        nargs="?",
        help=f"MIDI file to read from and write to (default: {DEFAULT_FILE})",
    )
    parser.add_argument(
        "-i",
        "--import",
        dest="import_file",
        type=FileType("r"),
        help=(
            "MIDI file to read from, instead of the file specified by the "
            '"file" argument'
        ),
    )
    parser.add_argument(
        "-f",
        "--soundfont",
        type=FileType("r"),
        help=(
            "SF2 soundfont file to use for playback (default: "
            f"{DEFAULT_SOUNDFONT})"
        ),
    )
    parser.add_argument(
        "--ticks-per-beat",
        type=positive_int,
        help=(
            "MIDI ticks per beat (default: read from file, if any, else "
            f"{DEFAULT_TICKS_PER_BEAT})"
        ),
    )
    parser.add_argument(
        "--cols-per-beat",
        type=positive_int,
        default=DEFAULT_COLS_PER_BEAT,
        help=(
            "the number of terminal columns per beat to display in the editor "
            f"(default: {DEFAULT_COLS_PER_BEAT})"
        ),
    )
    parser.add_argument(
        "--beats-per-measure",
        type=positive_int,
        default=DEFAULT_BEATS_PER_MEASURE,
        help=(
            "the number of beats per measure to display in the editor "
            f"(default: {DEFAULT_BEATS_PER_MEASURE})"
        ),
    )
    parser.add_argument(
        "--key",
        type=str,
        choices=NAME_TO_NUMBER.keys(),
        default=COMMON_NAMES[DEFAULT_KEY],
        help=(
            "the key signature to display in the editor (default: "
            f"{COMMON_NAMES[DEFAULT_KEY]})"
        ),
    )
    parser.add_argument(
        "--scale",
        choices=SCALES.keys(),
        default=DEFAULT_SCALE_NAME,
        help=(
            "the scale to display in the editor (default: "
            f"{DEFAULT_SCALE_NAME})"
        ),
    )
    parser.add_argument(
        "--unicode",
        dest="unicode",
        action=BooleanOptionalAction,
        help=(
            "enable/disable drawing with unicode characters (default: "
            "enabled)"
        ),
    )
    parser.set_defaults(unicode=True)
    parser.add_argument(
        "--crash-file",
        type=FileType("w"),
        help=(
            "file to write debugging info to in the event of a crash; set to "
            f"/dev/null to disable the crash file (default: {CRASH_FILE})"
        ),
    )

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
        print("Try running:")
        print("pip3 install mido")
        sys.exit(1)

    if IMPORT_FLUIDSYNTH:
        if ARGS.soundfont:
            ARGS.soundfont = ARGS.soundfont.name
        elif os.path.isfile(DEFAULT_SOUNDFONT):
            with open(DEFAULT_SOUNDFONT, "r") as default_soundfont:
                if default_soundfont.readable():
                    ARGS.soundfont = DEFAULT_SOUNDFONT
    elif ARGS.soundfont:
        print(ERROR_FLUIDSYNTH)
        print()
        print("Make sure FluidSynth itself is installed:")
        print("https://www.fluidsynth.org/download/")
        print("Then try running:")
        print("pip3 install pyfluidsynth")
        sys.exit(1)

    if ARGS.soundfont is not None and IMPORT_FLUIDSYNTH:
        global PLAYER
        PLAYER = Player(ARGS.soundfont)

    if ARGS.crash_file is not None:
        CRASH_FILE = ARGS.crash_file

    os.environ.setdefault("ESCDELAY", str(ESCDELAY))

    curses.wrapper(wrapper)
