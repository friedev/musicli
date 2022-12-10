from abc import ABC, abstractmethod
import curses
import curses.ascii
from enum import Enum
from dataclasses import dataclass
from math import inf
import sys
from typing import Optional, Union

from .player import Player, PLAY_EVENT, RESTART_EVENT, KILL_EVENT

from .song import (
    Note,
    Song,
    Track,
    number_to_name,
    CHORDS,
    COMMON_NAMES,
    DEFAULT_VELOCITY,
    DRUM_CHANNEL,
    DRUM_NAMES,
    DRUM_OFFSET,
    MAX_VELOCITY,
    NOTES_PER_OCTAVE,
    TOTAL_INSTRUMENTS,
    TOTAL_NOTES,
)


# On some systems, color 8 is gray, but this is not fully standardized
COLOR_GRAY = 8

INSTRUMENT_PAIRS = list(range(1, 7))
PAIR_DRUM = len(INSTRUMENT_PAIRS) + 1
PAIR_SIDEBAR_NOTE = len(INSTRUMENT_PAIRS) + 2
PAIR_SIDEBAR_KEY = len(INSTRUMENT_PAIRS) + 3
PAIR_LINE = len(INSTRUMENT_PAIRS) + 4
PAIR_PLAYHEAD = len(INSTRUMENT_PAIRS) + 5
PAIR_STATUS_NORMAL = len(INSTRUMENT_PAIRS) + 6
PAIR_STATUS_INSERT = len(INSTRUMENT_PAIRS) + 7
PAIR_LAST_NOTE = len(INSTRUMENT_PAIRS) + 8
PAIR_LAST_CHORD = len(INSTRUMENT_PAIRS) + 9
PAIR_HIGHLIGHT = len(INSTRUMENT_PAIRS) + 10

DEFAULT_OCTAVE = 4

ERROR_FLUIDSYNTH = (
    "fluidsynth could not be imported, so playback is unavailable"
)
ERROR_MIDO = "mido could not be imported, so MIDI import/export is unavailable"


class Action(Enum):
    PAN_LEFT = "pan left"
    PAN_LEFT_SHORT = "pan left (short)"
    PAN_RIGHT = "pan right"
    PAN_RIGHT_SHORT = "pan right (short)"
    PAN_UP = "pan up"
    PAN_UP_SHORT = "pan up (short)"
    PAN_DOWN = "pan down"
    PAN_DOWN_SHORT = "pan down (short)"
    EDIT_LEFT = "move the editing cursor one step forward"
    EDIT_RIGHT = "move the editing cursor one step backward"
    EDIT_UP = "move the editing cursor one octave higher"
    EDIT_DOWN = "move the editing cursor one octave lower"
    JUMP_LEFT = "jump to beginning of song"
    JUMP_RIGHT = "jump to end of song"
    JUMP_UP = "jump to highest note"
    JUMP_DOWN = "jump to lowest note"
    MODE_NORMAL = "enter normal mode, or deselect notes in normal mode"
    MODE_INSERT = "enter insert mode"
    MODE_INSERT_STEP = "enter insert mode, advance one step"
    MODE_INSERT_START = "enter insert mode, jump to the beginning of the song"
    MODE_INSERT_END = "enter insert mode, jump to the end of the song"
    DELETE_NOTE = "delete the selected note"
    DELETE_NOTE_BACK = "delete the selected note and step back"
    DELETE_CHORD = "delete the selected chord"
    DELETE_CHORD_BACK = "delete the selected chord and step back"
    TIME_NOTE_DEC = "decrease the start time of the selected note"
    TIME_NOTE_INC = "increase the start time of the selected note"
    TIME_CHORD_DEC = "decrease the start time of the selected chord"
    TIME_CHORD_INC = "increase the start time of the selected chord"
    DURATION_NOTE_DEC = "decrease the duration of the selected note"
    DURATION_NOTE_INC = "increase the duration of the selected note"
    DURATION_CHORD_DEC = "decrease the duration of the selected chord"
    DURATION_CHORD_INC = "increase the duration of the selected chord"
    VELOCITY_NOTE_DEC = "decrease the velocity of the selected note"
    VELOCITY_NOTE_INC = "increase the velocity of the selected note"
    VELOCITY_CHORD_DEC = "decrease the velocity of the selected chord"
    VELOCITY_CHORD_INC = "increase the velocity of the selected chord"
    TRACK_DEC = "switch to the previous track"
    TRACK_INC = "switch to the next track"
    INSTRUMENT_DEC = "use the previous instrument on this channel"
    INSTRUMENT_INC = "use the next instrument on this channel"
    DRUM_TOGGLE = "toggle this channel between drums and regular instruments"
    CYCLE_NOTES = "cycle through notes in the selected chord"
    DESELECT_NOTES = "deselect all notes"
    FOCUS_TOGGLE = "focus on the current track and hide others"
    TRACK_CREATE = "create a new track"
    TRACK_DELETE = "delete the current track"
    PLAYBACK_TOGGLE = "toggle playback (play/pause)"
    PLAYBACK_RESTART = "restart playback from the beginning of the song"
    PLAYBACK_CURSOR = "restart playback from the editing cursor"
    CURSOR_TO_PLAYHEAD = "sync the cursor location to the playhead"
    WRITE_MIDI = "export song as a MIDI file"
    QUIT_HELP = "does not quit; use Ctrl+C to exit MusiCLI"


KEYMAP: dict[int, Action] = {
    ord("h"): Action.PAN_LEFT,
    ord("H"): Action.PAN_LEFT_SHORT,
    ord("l"): Action.PAN_RIGHT,
    ord("L"): Action.PAN_RIGHT_SHORT,
    ord("k"): Action.PAN_UP,
    ord("K"): Action.PAN_UP_SHORT,
    ord("j"): Action.PAN_DOWN,
    ord("J"): Action.PAN_DOWN_SHORT,
    curses.KEY_LEFT: Action.EDIT_LEFT,
    curses.KEY_RIGHT: Action.EDIT_RIGHT,
    curses.KEY_UP: Action.EDIT_UP,
    curses.KEY_DOWN: Action.EDIT_DOWN,
    ord("0"): Action.JUMP_LEFT,
    ord("^"): Action.JUMP_LEFT,
    ord("$"): Action.JUMP_RIGHT,
    curses.KEY_PPAGE: Action.JUMP_UP,
    curses.KEY_NPAGE: Action.JUMP_DOWN,
    curses.KEY_HOME: Action.JUMP_LEFT,
    curses.KEY_END: Action.JUMP_RIGHT,
    curses.ascii.ESC: Action.MODE_NORMAL,
    ord("i"): Action.MODE_INSERT,
    ord("a"): Action.MODE_INSERT_STEP,
    ord("I"): Action.MODE_INSERT_START,
    ord("A"): Action.MODE_INSERT_END,
    curses.KEY_IC: Action.MODE_INSERT,
    ord("x"): Action.DELETE_NOTE,
    ord("X"): Action.DELETE_NOTE_BACK,
    ord("d"): Action.DELETE_CHORD,
    ord("D"): Action.DELETE_CHORD,
    curses.ascii.TAB: Action.CYCLE_NOTES,
    ord("`"): Action.DESELECT_NOTES,
    curses.KEY_DC: Action.DELETE_NOTE,
    curses.KEY_BACKSPACE: Action.DELETE_CHORD_BACK,
    ord(","): Action.TIME_NOTE_DEC,
    ord("."): Action.TIME_NOTE_INC,
    ord("<"): Action.TIME_CHORD_DEC,
    ord(">"): Action.TIME_CHORD_INC,
    ord("["): Action.DURATION_NOTE_DEC,
    ord("]"): Action.DURATION_NOTE_INC,
    ord("{"): Action.DURATION_CHORD_DEC,
    ord("}"): Action.DURATION_CHORD_INC,
    ord(";"): Action.VELOCITY_NOTE_DEC,
    ord("'"): Action.VELOCITY_NOTE_INC,
    ord(":"): Action.VELOCITY_CHORD_DEC,
    ord('"'): Action.VELOCITY_CHORD_INC,
    ord("-"): Action.TRACK_DEC,
    ord("="): Action.TRACK_INC,
    ord("_"): Action.INSTRUMENT_DEC,
    ord("+"): Action.INSTRUMENT_INC,
    ord("z"): Action.DRUM_TOGGLE,
    ord("Z"): Action.DRUM_TOGGLE,
    ord("f"): Action.FOCUS_TOGGLE,
    ord("F"): Action.FOCUS_TOGGLE,
    ord("t"): Action.TRACK_CREATE,
    ord("T"): Action.TRACK_DELETE,
    ord(" "): Action.PLAYBACK_TOGGLE,
    curses.ascii.LF: Action.PLAYBACK_RESTART,
    ord("g"): Action.PLAYBACK_CURSOR,
    ord("G"): Action.CURSOR_TO_PLAYHEAD,
    ord("w"): Action.WRITE_MIDI,
    ord("W"): Action.WRITE_MIDI,
    ord("q"): Action.QUIT_HELP,
    ord("Q"): Action.QUIT_HELP,
}

INSERT_KEYMAP: dict[str, int] = {
    "z": 0,  # C
    "s": 1,  # C#
    "x": 2,  # D
    "d": 3,  # D#
    "c": 4,  # E
    "v": 5,  # F
    "g": 6,  # F#
    "b": 7,  # G
    "h": 8,  # G#
    "n": 9,  # A
    "j": 10,  # A#
    "m": 11,  # B
    "q": 12,  # C
    "2": 13,  # C#
    "w": 14,  # D
    "3": 15,  # D#
    "e": 16,  # E
    "r": 17,  # F
    "5": 18,  # F#
    "t": 19,  # G
    "6": 20,  # G#
    "y": 21,  # A
    "7": 22,  # A#
    "u": 23,  # B
    "i": 24,  # C
    "9": 25,  # C#
    "o": 26,  # D
    "0": 27,  # D#
    "p": 28,  # E
}

SYMBOLS_TO_NUMBERS: dict[str, str] = {
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
}

INSERT_KEYLIST = tuple(INSERT_KEYMAP.keys())


def init_color_pairs() -> None:
    global COLOR_GRAY

    try:
        curses.init_pair(1, COLOR_GRAY, COLOR_GRAY)
    except ValueError:
        COLOR_GRAY = curses.COLOR_WHITE

    for pair in INSTRUMENT_PAIRS:
        curses.init_pair(pair, curses.COLOR_BLACK, pair)

    curses.init_pair(PAIR_DRUM, curses.COLOR_BLACK, COLOR_GRAY)
    curses.init_pair(PAIR_SIDEBAR_NOTE, COLOR_GRAY, curses.COLOR_BLACK)
    curses.init_pair(PAIR_SIDEBAR_KEY, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(PAIR_LINE, COLOR_GRAY, -1)
    curses.init_pair(PAIR_PLAYHEAD, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(PAIR_STATUS_NORMAL, curses.COLOR_BLACK, curses.COLOR_BLUE)
    curses.init_pair(PAIR_STATUS_INSERT, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(PAIR_LAST_NOTE, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(PAIR_LAST_CHORD, curses.COLOR_BLACK, COLOR_GRAY)
    curses.init_pair(PAIR_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_WHITE)


def format_velocity(velocity: int) -> str:
    return f"Velocity: {velocity}"


def format_track(index: int, track: Track) -> str:
    return f"Track {index + 1}: {track.instrument_name}"


def format_notes(notes: list[Note]) -> tuple[str, str]:
    if len(notes) == 1:
        return notes[0].full_name, str(notes[0])

    sorted_notes = sorted(notes)

    if not any(note.is_drum for note in notes):
        unique_notes = []
        semitones = set()
        for note in sorted_notes:
            if note.semitone not in semitones:
                unique_notes.append(note)
                semitones.add(note.semitone)

        numbers = [note.number for note in unique_notes]
        inversion = 0
        while inversion < len(numbers):
            intervals = [0]
            for number in numbers[1:]:
                intervals.append(
                    (number - intervals[-1] - numbers[0]) % NOTES_PER_OCTAVE
                )
            name_tuple = CHORDS.get(tuple(intervals))
            if name_tuple is not None:
                root = unique_notes[inversion].name
                short_name, long_name = name_tuple
                short_string = root + short_name
                long_string = root + " " + long_name
                if inversion > 0:
                    bass = unique_notes[0].name
                    short_string += f"/{bass}"
                    long_string += f" over {bass} (inversion {inversion})"
                return short_string, long_string
            numbers.append(numbers.pop(0) + NOTES_PER_OCTAVE)
            inversion += 1

    short_string = ""
    long_string = ""
    for note in sorted_notes:
        short_string += note.full_name + " "
        long_string += note.full_name + " "
    return short_string, long_string


class Block(ABC):
    short: bool

    @abstractmethod
    def __len__(self) -> int:
        pass

    @abstractmethod
    def __lt__(self, other) -> bool:
        pass

    @abstractmethod
    def __gt__(self, other) -> bool:
        pass


@dataclass
class FillerBlock(Block):
    attr: int = curses.A_NORMAL
    short: bool = False

    @property
    def priority(self) -> float:
        return inf

    def __len__(self) -> int:
        return 0

    def __lt__(self, other) -> bool:
        return False

    def __gt__(self, other) -> bool:
        return True


class StatusBlock(Block):
    def __init__(
        self,
        string: str,
        short_string: Optional[str] = None,
        attr: int = curses.A_NORMAL,
        priority: int = 0,
        pad: bool = True,
    ):
        if short_string is None:
            short_string = string
        if pad:
            self.string = " " + string + " "
            self.short_string = " " + short_string + " "
        else:
            self.string = string
            self.short_string = short_string
        self.priority = priority
        self.attr = attr
        self.short = False

    def __str__(self) -> str:
        return self.short_string if self.short else self.string

    def __len__(self) -> int:
        return len(str(self))

    def __lt__(self, other) -> bool:
        return self.priority < other.priority

    def __gt__(self, other) -> bool:
        return self.priority > other.priority


class Interface:
    window: curses.window
    song: Song
    player: Optional[Player]
    x_offset: int
    y_offset: int
    insert: bool
    time: int
    duration: int
    velocity: int
    track_index: int
    octave: int
    last_note: Optional[Note]
    last_chord: list[Note]
    message: str
    filename: Optional[str]
    unicode: bool
    highlight_track: bool
    focus_track: bool
    repeat_count: int

    def __init__(
        self,
        window: curses.window,
        song: Song,
        player: Optional[Player] = None,
        filename: Optional[str] = None,
        unicode: bool = True,
    ):
        self.window = window
        self.song = song
        self.player = player

        self.insert = False
        self.time = 0
        self.duration = self.song.beats_to_ticks(1)
        self.velocity = DEFAULT_VELOCITY
        self.track_index = 0
        self.octave = DEFAULT_OCTAVE
        self.last_note = None
        self.last_chord = []
        self.message = ""
        self.filename = filename
        self.unicode = unicode
        self.highlight_track = False
        self.focus_track = False
        self.repeat_count = 0

        self.x_offset = self.min_x_offset
        self.y_offset = (
            DEFAULT_OCTAVE + 1
        ) * NOTES_PER_OCTAVE - self.height // 2

        init_color_pairs()

    @property
    def width(self) -> int:
        return self.window.getmaxyx()[1]

    @property
    def height(self) -> int:
        return self.window.getmaxyx()[0]

    @property
    def x_sidebar_offset(self) -> int:
        return -9 if self.track.is_drum else -6

    @property
    def min_x_offset(self) -> int:
        return self.x_sidebar_offset

    @property
    def min_y_offset(self) -> int:
        return -2

    @property
    def max_y_offset(self) -> int:
        if self.window is not None:
            return TOTAL_NOTES - self.height
        return TOTAL_NOTES

    @property
    def key(self) -> str:
        return COMMON_NAMES[self.song.key]

    @property
    def track(self) -> Track:
        return self.song.tracks[self.track_index]

    @property
    def instrument(self) -> int:
        return self.track.instrument

    def draw_line(
        self, x: int, string: str, attr: int, start_y: int = 1
    ) -> None:
        if 0 <= x and x + len(string) < self.width:
            for y in range(start_y, self.height):
                self.window.addstr(y, x, string, attr)

    def draw_scale_dots(self) -> None:
        string = "·" if self.unicode else "."
        attr = curses.color_pair(PAIR_LINE)
        for y, note in enumerate(
            range(self.y_offset, self.y_offset + self.height - 1)
        ):
            semitone = note % NOTES_PER_OCTAVE
            if semitone in [
                (number + self.song.key) % NOTES_PER_OCTAVE
                for number in self.song.scale
            ]:
                for x in range(-self.x_offset % 4, self.width - 1, 4):
                    self.window.addstr(self.height - y - 1, x, string, attr)

    def draw_measures(self) -> None:
        cols_per_measure = self.song.cols_per_beat * self.song.beats_per_measure
        string = "▏" if self.unicode else "|"
        attr = curses.color_pair(PAIR_LINE)
        for x in range(
            -self.x_offset % cols_per_measure, self.width - 1, cols_per_measure
        ):
            self.draw_line(x, string, attr, start_y=0)
            measure_number = (x + self.x_offset) // cols_per_measure + 1
            self.window.addstr(0, x, str(measure_number), attr)

    def draw_cursor(self) -> None:
        self.draw_line(
            self.song.ticks_to_cols(self.time) - self.x_offset,
            "▏" if self.unicode else "|",
            curses.color_pair(0),
        )

    def draw_playhead(self) -> None:
        if self.player is not None:
            self.draw_line(
                self.song.ticks_to_cols(self.player.playhead) - self.x_offset,
                "▏" if self.unicode else "|",
                curses.color_pair(PAIR_PLAYHEAD),
            )

    def draw_notes(self) -> None:
        time = self.song.cols_to_ticks(self.x_offset)
        index = self.song.get_next_index(time)
        string = "▏" if self.unicode else "["
        for note in self.song.events[index:]:
            if not isinstance(note, Note):
                continue

            if self.focus_track and note.track is not self.track:
                continue

            start_x = self.song.ticks_to_cols(note.start) - self.x_offset
            end_x = self.song.ticks_to_cols(note.end) - self.x_offset
            if start_x >= self.width - 1:
                if note.on:
                    break
                continue

            y = self.height - (note.number - self.y_offset) - 1
            if not 0 < y < self.height:
                continue

            if not note.on and start_x >= 0:
                continue

            if note.on_pair is self.last_note:
                color_pair = PAIR_LAST_NOTE
            elif note.on_pair in self.last_chord:
                color_pair = PAIR_LAST_CHORD
            elif self.highlight_track and note.track is self.track:
                color_pair = PAIR_HIGHLIGHT
            else:
                if note.is_drum:
                    color_pair = PAIR_DRUM
                else:
                    color_pair = INSTRUMENT_PAIRS[
                        note.instrument % len(INSTRUMENT_PAIRS)
                    ]

            attr = curses.color_pair(color_pair)

            for x in range(max(start_x, 0), min(end_x, self.width - 1)):
                self.window.addstr(y, x, " ", attr)

            if 0 <= start_x < self.width - 1:
                self.window.addstr(y, start_x, string, attr)

            note_width = end_x - start_x
            if note_width >= 4 and 0 <= start_x + 1:
                string_width = min(self.width, end_x) - start_x - 2
                self.window.addstr(
                    y, start_x + 1, note.name[:string_width], attr
                )

    def draw_sidebar(self) -> None:
        pair_note = curses.color_pair(PAIR_SIDEBAR_NOTE)
        pair_key = curses.color_pair(PAIR_SIDEBAR_KEY)
        for y, number in enumerate(
            range(self.y_offset, self.y_offset + self.height)
        ):
            if self.track.is_drum:
                drum_number = number - DRUM_OFFSET
                if 0 <= drum_number < len(DRUM_NAMES):
                    note_name, _ = DRUM_NAMES[drum_number]
                else:
                    note_name = str(number)
            else:
                note_name = number_to_name(number)
            self.window.addstr(
                self.height - y - 1,
                0,
                "  " + note_name.ljust(-self.x_sidebar_offset - 2),
                pair_note,
            )

            insert_key = number - self.octave * NOTES_PER_OCTAVE
            if 0 <= insert_key < len(INSERT_KEYMAP):
                self.window.addstr(
                    self.height - y - 1,
                    0,
                    list(INSERT_KEYMAP.keys())[insert_key],
                    pair_key,
                )

    def draw_status_block(self, x: int, block, length: int) -> int:
        if isinstance(block, FillerBlock):
            filler_width = self.width - length - 1
            string = " " * filler_width
            new_x = x + max(filler_width, 0)
        else:
            string = str(block)[: self.width - x - 1]
            new_x = x + len(block)

        if len(string) > 0:
            self.window.addstr(self.height - 2, x, string, block.attr)
        return new_x

    def draw_status_bar(self) -> None:
        if len(self.message) == 0 and len(self.last_chord) > 0:
            short_notes, long_notes = format_notes(self.last_chord)
            self.message = (
                long_notes if len(long_notes) < self.width else short_notes
            )

        self.window.addstr(
            self.height - 1,
            0,
            self.message.ljust(self.width - 1)[: self.width - 1],
            curses.color_pair(0),
        )

        if self.repeat_count > 0:
            repeat_string = str(self.repeat_count)
            self.window.addstr(
                self.height - 1,
                max(self.width - len(repeat_string) - 1, 0),
                repeat_string[: self.width],
                curses.color_pair(0),
            )

        bar: list[Block] = []

        color = curses.color_pair(
            PAIR_STATUS_INSERT if self.insert else PAIR_STATUS_NORMAL
        )

        bar.append(
            StatusBlock(
                f'{"INSERT" if self.insert else "NORMAL"}',
                f'{"I" if self.insert else "N"}',
                attr=color | curses.A_BOLD,
                priority=2,
            )
        )

        if self.filename:
            filename_text = self.filename
            basename_text = filename_text[filename_text.rfind("/") + 1 :]
        else:
            filename_text = ""
            basename_text = ""
        bar.append(
            StatusBlock(
                filename_text,
                basename_text,
                attr=color | curses.A_BOLD | curses.A_REVERSE,
                priority=0,
            )
        )

        bar.append(FillerBlock(attr=color | curses.A_REVERSE))

        key_name = self.song.key_name
        scale_name = self.song.scale_name.replace("_", " ")
        bar.append(
            StatusBlock(
                f"{key_name} {scale_name}",
                key_name,
                attr=color | curses.A_REVERSE,
                priority=4,
            )
        )

        if self.focus_track:
            bar.append(
                StatusBlock(
                    "FOCUS", "F", attr=color | curses.A_BOLD, priority=3
                )
            )

        track_number_text = f"T{self.track_index + 1}/{len(self.song.tracks)}"
        bar.append(
            StatusBlock(
                f"{track_number_text}: " + self.track.instrument_name,
                track_number_text,
                attr=color | curses.A_NORMAL,
                priority=1,
            )
        )

        end_measure = (
            self.song.ticks_to_beats(self.song.end)
            // self.song.beats_per_measure
            + 1
        )
        if self.player is not None:
            play_measure = (
                self.song.ticks_to_beats(self.player.playhead)
                // self.song.beats_per_measure
                + 1
            )
            play_text = f"P{play_measure}/{end_measure}"
        else:
            play_text = ""
        bar.append(
            StatusBlock(play_text, attr=color | curses.A_BOLD, priority=5)
        )

        edit_measure = (
            self.song.ticks_to_beats(self.time) // self.song.beats_per_measure
            + 1
        )
        bar.append(
            StatusBlock(
                f"C{edit_measure}/{end_measure}",
                attr=color | curses.A_BOLD,
                priority=6,
            )
        )

        length = sum(len(block) for block in bar)
        if length >= self.width:
            priority_order = sorted(bar)
            for block in priority_order:
                length -= len(block)
                block.short = True
                length += len(block)
                if length < self.width:
                    break

        x = 0
        for block in bar:
            x = self.draw_status_block(x, block, length)
            if x >= self.width:
                return

    def draw(self) -> None:
        self.draw_scale_dots()
        self.draw_measures()
        self.draw_cursor()
        self.draw_playhead()
        self.draw_notes()
        self.draw_sidebar()
        self.draw_status_bar()

    def play_note(self, note: Optional[Note] = None) -> None:
        if note is None:
            note = self.last_note
        if (
            note is not None
            and self.player is not None
            and not self.player.playing
        ):
            self.player.play_note(note)

    def stop_note(self, note: Optional[Note] = None) -> None:
        if note is None:
            note = self.last_note
        if (
            note is not None
            and self.player is not None
            and not self.player.playing
        ):
            self.player.stop_note(note)

    def play_notes(self, notes: Optional[list[Note]] = None) -> None:
        if notes is None:
            notes = self.last_chord
        if self.player is not None and not self.player.playing:
            for note in notes:
                self.player.play_note(note)

    def stop_notes(self, notes: Optional[list[Note]] = None):
        if notes is None:
            notes = self.last_chord
        if self.player is not None and not self.player.playing:
            for note in notes:
                self.player.stop_note(note)

    def set_x_offset(self, x_offset: int) -> None:
        self.x_offset = max(x_offset, self.min_x_offset)

    def set_y_offset(self, y_offset: int) -> None:
        self.y_offset = min(max(y_offset, self.min_y_offset), self.max_y_offset)

    def snap_to_time(
        self, time: Optional[int] = None, center: bool = True
    ) -> None:
        if time is None:
            time = self.time
        cols_per_measure = self.song.cols_per_beat * self.song.beats_per_measure
        time_cols = self.song.ticks_to_cols(time)
        if time_cols < self.x_offset or time_cols >= self.x_offset + self.width:
            new_offset = time_cols
            if center:
                new_offset -= self.width // 2
            self.set_x_offset(
                new_offset
                - new_offset % cols_per_measure
                + self.x_sidebar_offset
            )

    def insert_note(self, number: int, chord: bool = False):
        if not PLAY_EVENT.is_set():
            self.stop_notes()

        if self.last_note is not None and not chord:
            self.time += self.duration
            if self.insert:
                self.snap_to_time()
            self.last_chord = []

        note = Note(
            on=True,
            number=number,
            time=self.time,
            duration=self.duration,
            velocity=self.velocity,
            track=self.track,
        )

        if note in self.song:
            self.song.remove_note(note, lookup=True)
            if note == self.last_note:
                self.last_note = None
            if note in self.last_chord:
                self.last_chord.remove(note)
        else:
            self.song.add_note(note)
            self.last_note = note
            self.last_chord.append(note)

        if not PLAY_EVENT.is_set():
            self.play_notes()

    def move_cursor(self, left: bool) -> None:
        nearest_time: Union[int, float]
        if left:
            nearest_chord = self.song.get_previous_chord(self.time, self.track)
            if len(nearest_chord) > 0:
                nearest_time = nearest_chord[0].start
                end_time = max(note.end for note in nearest_chord)
            else:
                nearest_time = 0
                end_time = 0

            if self.last_note is not None and end_time >= self.last_note.start:
                self.time = nearest_time
            else:
                self.time = max(self.time - self.duration, nearest_time, 0)
        else:
            inclusive = self.last_note is None
            nearest_chord = self.song.get_next_chord(
                self.time, self.track, inclusive=inclusive
            )
            if len(nearest_chord) > 0:
                nearest_time = nearest_chord[0].start
            else:
                nearest_time = inf

            if (
                self.last_note is not None
                and nearest_time <= self.last_note.end
            ):
                # Should not be inf
                assert isinstance(nearest_time, int)
                self.time = nearest_time
            else:
                # Should not be inf
                new_time = min(self.time + self.duration, nearest_time)
                assert isinstance(new_time, int)
                self.time = new_time

        if len(nearest_chord) > 0 and self.time == nearest_time:
            self.last_chord = nearest_chord
            self.last_note = nearest_chord[0]
            self.duration = self.last_note.duration

        self.snap_to_time()

    def set_octave(self, increase: bool) -> None:
        if increase:
            self.octave = min(
                self.octave + 1, TOTAL_NOTES // NOTES_PER_OCTAVE - 1
            )
        else:
            self.octave = max(self.octave - 1, 0)
        self.set_y_offset(
            (self.octave + 1) * NOTES_PER_OCTAVE - self.height // 2
        )

    def set_time(self, increase: bool, chord: bool) -> None:
        if self.last_note is None:
            return

        if not chord:
            if increase:
                new_start = self.last_note.start + self.song.cols_to_ticks(1)
            else:
                new_start = max(
                    self.last_note.start - self.song.cols_to_ticks(1), 0
                )
            self.song.move_note(self.last_note, new_start)
            self.time = self.last_note.start
            self.last_chord = [self.last_note]
        else:
            if increase:
                new_start = self.last_note.start + self.song.cols_to_ticks(1)
            else:
                new_start = max(
                    self.last_note.start - self.song.cols_to_ticks(1), 0
                )
            for note in self.last_chord:
                self.song.move_note(note, new_start)
            self.time = self.last_note.start

        self.snap_to_time()

    def set_duration(self, increase: bool, chord: bool) -> None:
        if self.last_note is not None:
            if not chord:
                if increase:
                    self.song.set_duration(
                        self.last_note,
                        self.last_note.duration + self.song.cols_to_ticks(1),
                    )
                else:
                    self.song.set_duration(
                        self.last_note,
                        max(
                            self.last_note.duration
                            - self.song.cols_to_ticks(1),
                            self.song.cols_to_ticks(1),
                        ),
                    )
            else:
                if increase:
                    for note in self.last_chord:
                        self.song.set_duration(
                            note, note.duration + self.song.cols_to_ticks(1)
                        )
                else:
                    for note in self.last_chord:
                        self.song.set_duration(
                            note,
                            max(
                                note.duration - self.song.cols_to_ticks(1),
                                self.song.cols_to_ticks(1),
                            ),
                        )

            # Update duration and time for next insertion
            self.duration = self.last_note.duration
        else:
            if increase:
                self.duration += self.song.cols_to_ticks(1)
            else:
                self.duration = max(
                    self.duration - self.song.cols_to_ticks(1),
                    self.song.cols_to_ticks(1),
                )

    def set_velocity(self, increase: bool, chord: bool) -> None:
        if increase:
            self.velocity = min(self.velocity + 1, MAX_VELOCITY - 1)
        else:
            self.velocity = max(self.velocity - 1, 0)

        self.message = format_velocity(self.velocity)

        if not chord:
            if self.last_note is not None:
                self.last_note.set_velocity(self.velocity)
        else:
            for note in self.last_chord:
                note.set_velocity(self.velocity)

    def set_track(self, increase: bool) -> None:
        old_x_sidebar_offset = self.x_sidebar_offset
        if increase:
            self.track_index += 1
        else:
            self.track_index -= 1
        self.track_index %= len(self.song.tracks)
        self.x_offset += self.x_sidebar_offset - old_x_sidebar_offset
        self.highlight_track = True

        self.message = format_track(self.track_index, self.track)

    def set_instrument(self, increase: bool) -> None:
        self.stop_notes()

        instrument = self.song.tracks[self.track_index].instrument
        if increase:
            instrument += 1
        else:
            instrument -= 1
        instrument %= TOTAL_INSTRUMENTS

        self.track.set_instrument(instrument, self.player)

        self.message = format_track(self.track_index, self.track)

        self.play_notes()

    def toggle_drum(self) -> None:
        self.stop_notes()

        old_x_sidebar_offset = self.x_sidebar_offset
        if self.track.is_drum:
            self.track.set_channel(self.song.get_open_channel(), self.player)
        else:
            for index, track in enumerate(self.song.tracks):
                if track.is_drum:
                    self.message = f"Track {index + 1} is already a drum track"
                    return
            self.track.set_channel(DRUM_CHANNEL, self.player)
        self.x_offset += self.x_sidebar_offset - old_x_sidebar_offset

        self.message = format_track(self.track_index, self.track)

    def delete(self, back: bool, chord: bool) -> None:
        if self.last_note is not None:
            if chord:
                self.stop_notes()
            else:
                self.stop_note(self.last_note)

            if chord:
                for note in self.last_chord:
                    self.song.remove_note(note)
                self.last_chord = []
                self.last_note = None
            else:
                note_to_remove = self.last_note
                if not self.cycle_notes():
                    self.last_note = None
                self.song.remove_note(note_to_remove)
                self.last_chord.remove(note_to_remove)

        if back:
            self.last_note = None
            self.last_chord = []
            self.move_cursor(left=True)

    def create_track(self) -> None:
        track = self.song.create_track(
            instrument=self.instrument, player=self.player
        )
        self.track_index = self.song.tracks.index(track)
        self.message = format_track(self.track_index, self.track)

    def delete_track(self) -> None:
        self.deselect()
        instrument = self.instrument
        self.song.delete_track(self.track)
        if len(self.song.tracks) == 0:
            self.song.create_track(instrument=instrument, player=self.player)
            self.track_index = 0
            self.message = f"Track {self.track_index + 1} cleared"
        else:
            self.track_index = max(self.track_index - 1, 0)
            self.message = format_track(self.track_index, self.track)
            self.highlight_track = True

    def toggle_playback(self) -> None:
        if self.player is None:
            self.message = ERROR_FLUIDSYNTH
            return

        if PLAY_EVENT.is_set():
            PLAY_EVENT.clear()
            curses.cbreak()
        else:
            self.stop_notes()
            PLAY_EVENT.set()
            curses.halfdelay(1)

    def restart_playback(self, restart_time: int = 0) -> None:
        if self.player is None:
            self.message = ERROR_FLUIDSYNTH
            return

        self.stop_notes()
        self.player.restart_time = restart_time
        RESTART_EVENT.set()
        PLAY_EVENT.set()
        curses.halfdelay(1)

    def cursor_to_playhead(self) -> None:
        if self.player is None:
            self.message = ERROR_FLUIDSYNTH
            return
        self.time = self.player.playhead
        self.snap_to_time()

    def export_midi(self) -> None:
        if self.filename is None:
            self.message = ERROR_MIDO
            return

        self.song.export_midi(self.filename)
        self.message = f"Wrote MIDI to {self.filename}"

    def cycle_notes(self) -> bool:
        if self.last_note is not None and len(self.last_chord) >= 2:
            index = self.last_chord.index(self.last_note)
            index += 1
            index %= len(self.last_chord)
            self.last_note = self.last_chord[index]
            return True
        return False

    def deselect(self) -> None:
        self.last_note = None
        self.last_chord = []

    def escape(self) -> None:
        if not self.insert:
            if self.last_note is None:
                self.message = "Press Ctrl+C to exit MusiCLI"
            else:
                self.deselect()
        else:
            self.stop_notes()
            self.insert = False

    def handle_action(self, action: Action) -> None:
        # Pan view
        x_pan = self.song.cols_per_beat * self.song.beats_per_measure
        x_pan_short = self.song.cols_per_beat
        y_pan = NOTES_PER_OCTAVE
        y_pan_short = 1
        if action == Action.PAN_LEFT:
            self.set_x_offset(self.x_offset - x_pan)
        elif action == Action.PAN_LEFT_SHORT:
            self.set_x_offset(self.x_offset - x_pan_short)
        elif action == Action.PAN_RIGHT:
            self.set_x_offset(self.x_offset + x_pan)
        elif action == Action.PAN_RIGHT_SHORT:
            self.set_x_offset(self.x_offset + x_pan_short)
        elif action == Action.PAN_UP:
            self.set_y_offset(self.y_offset + y_pan)
        elif action == Action.PAN_UP_SHORT:
            self.set_y_offset(self.y_offset + y_pan_short)
        elif action == Action.PAN_DOWN:
            self.set_y_offset(self.y_offset - y_pan)
        elif action == Action.PAN_DOWN_SHORT:
            self.set_y_offset(self.y_offset - y_pan_short)
        elif action == Action.EDIT_LEFT:
            self.move_cursor(left=True)
        elif action == Action.EDIT_RIGHT:
            self.move_cursor(left=False)
        elif action == Action.EDIT_UP:
            self.set_octave(increase=True)
        elif action == Action.EDIT_DOWN:
            self.set_octave(increase=False)
        elif action == Action.JUMP_LEFT:
            self.snap_to_time(0)
        elif action == Action.JUMP_RIGHT:
            self.snap_to_time(self.song.end)
        elif action == Action.JUMP_UP:
            self.y_offset = self.max_y_offset
        elif action == Action.JUMP_DOWN:
            self.y_offset = self.min_y_offset
        elif action == Action.MODE_NORMAL:
            self.escape()
        elif action == Action.MODE_INSERT:
            self.insert = True
        elif action == Action.MODE_INSERT_STEP:
            self.insert = True
            self.time += self.duration
            self.snap_to_time()
        elif action == Action.MODE_INSERT_START:
            self.insert = True
            self.time = 0
            self.snap_to_time()
        elif action == Action.MODE_INSERT_END:
            self.insert = True
            self.time = self.song.end
            self.snap_to_time()
        elif action == Action.CYCLE_NOTES:
            self.cycle_notes()
        elif action == Action.DESELECT_NOTES:
            self.deselect()
        elif action == Action.DELETE_NOTE:
            self.delete(back=False, chord=False)
        elif action == Action.DELETE_CHORD:
            self.delete(back=False, chord=True)
        elif action == Action.DELETE_NOTE_BACK:
            self.delete(back=True, chord=False)
        elif action == Action.DELETE_CHORD_BACK:
            self.delete(back=True, chord=True)
        elif action == Action.TIME_NOTE_DEC:
            self.set_time(increase=False, chord=False)
        elif action == Action.TIME_NOTE_INC:
            self.set_time(increase=True, chord=False)
        elif action == Action.TIME_CHORD_DEC:
            self.set_time(increase=False, chord=True)
        elif action == Action.TIME_CHORD_INC:
            self.set_time(increase=True, chord=True)
        elif action == Action.DURATION_NOTE_DEC:
            self.set_duration(increase=False, chord=False)
        elif action == Action.DURATION_NOTE_INC:
            self.set_duration(increase=True, chord=False)
        elif action == Action.DURATION_CHORD_DEC:
            self.set_duration(increase=False, chord=True)
        elif action == Action.DURATION_CHORD_INC:
            self.set_duration(increase=True, chord=True)
        elif action == Action.VELOCITY_NOTE_DEC:
            self.set_velocity(increase=False, chord=False)
        elif action == Action.VELOCITY_NOTE_INC:
            self.set_velocity(increase=True, chord=False)
        elif action == Action.VELOCITY_CHORD_DEC:
            self.set_velocity(increase=False, chord=True)
        elif action == Action.VELOCITY_CHORD_INC:
            self.set_velocity(increase=True, chord=True)
        elif action == Action.TRACK_DEC:
            self.set_track(increase=False)
        elif action == Action.TRACK_INC:
            self.set_track(increase=True)
        elif action == Action.INSTRUMENT_DEC:
            self.set_instrument(increase=False)
        elif action == Action.INSTRUMENT_INC:
            self.set_instrument(increase=True)
        elif action == Action.DRUM_TOGGLE:
            self.toggle_drum()
        elif action == Action.FOCUS_TOGGLE:
            self.focus_track = not self.focus_track
        elif action == Action.TRACK_CREATE:
            self.create_track()
        elif action == Action.TRACK_DELETE:
            self.delete_track()
        elif action == Action.PLAYBACK_TOGGLE:
            self.toggle_playback()
        elif action == Action.PLAYBACK_RESTART:
            self.restart_playback()
        elif action == Action.PLAYBACK_CURSOR:
            self.restart_playback(self.time)
        elif action == Action.CURSOR_TO_PLAYHEAD:
            self.cursor_to_playhead()
        elif action == Action.WRITE_MIDI:
            self.export_midi()
        elif action == Action.QUIT_HELP:
            self.message = "Press Ctrl+C to exit MusiCLI"

    def handle_input(self, input_code: int) -> bool:
        if input_code == curses.ERR:
            return False

        if curses.ascii.isprint(input_code):
            input_char = chr(input_code)
        else:
            input_char = ""

        # Reset temporary state upon an actual keypress
        self.message = ""
        self.highlight_track = False

        if self.insert:
            number = INSERT_KEYMAP.get(
                SYMBOLS_TO_NUMBERS.get(input_char, input_char.lower())
            )
            chord = input_char.isupper() or not input_char.isalnum()
            if number is not None:
                number += self.octave * NOTES_PER_OCTAVE
                if 0 <= number <= TOTAL_NOTES:
                    self.insert_note(number, chord)
                    return True
                self.message = f"Note {number} is out of range 0-127"
                return False
            if input_char.isalnum() or input_char in SYMBOLS_TO_NUMBERS:
                self.message = f'Key "{input_char}" does not map to a note'
                return False

        if input_char.isdigit() and (
            int(input_char) != 0 or self.repeat_count > 0
        ):
            self.repeat_count *= 10
            self.repeat_count += int(input_char)
            return True

        action = KEYMAP.get(input_code)

        if action is None:
            if len(input_char) > 0:
                self.message = f'Key "{input_char}" does not map to an action'
            else:
                self.message = "That key does not map to an action"
            return False

        if action is not None:
            for _ in range(max(self.repeat_count, 1)):
                self.handle_action(action)
            self.repeat_count = 0
            return True

        return False

    def main(self) -> None:
        # Loop until user the exits
        previous_playhead = 0
        redraw = True
        while True:
            if (
                self.player is not None
                and PLAY_EVENT.is_set()
                and not self.insert
            ):
                assert self.player is not None
                self.snap_to_time(self.player.playhead, center=False)

            if redraw:
                self.draw()
                self.window.refresh()

            input_code = self.window.getch()

            if KILL_EVENT.is_set():
                sys.exit(1)

            redraw = input_code != curses.ERR or (
                self.player is not None
                and PLAY_EVENT.is_set()
                and self.player.playhead != previous_playhead
            )

            if self.player is not None and PLAY_EVENT.is_set():
                previous_playhead = self.player.playhead

            if redraw:
                self.window.erase()

            self.handle_input(input_code)
