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
from bisect import bisect_left, bisect_right, insort
import curses
import curses.ascii
from enum import Enum
from math import inf
import os
import os.path
import sys
from threading import Event, Thread
from time import sleep
from traceback import format_exc

from fluidsynth import Synth
from mido import (bpm2tempo, Message, MetaMessage, MidiFile, MidiTrack,
                  tempo2bpm)

###############################################################################
# CONSTANTS
###############################################################################

# On some systems, color 8 is gray, but this is not fully standardized
COLOR_GRAY = 8

# Color pair numbers
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

# Music-related constants
TOTAL_NOTES = 127
NOTES_PER_OCTAVE = 12
DEFAULT_OCTAVE = 4

MAX_VELOCITY = 127
DEFAULT_VELOCITY = MAX_VELOCITY  # 64 is recommended, but seems quiet

TOTAL_INSTRUMENTS = 127  # Drums replace gunshot as instrument 128
DEFAULT_CHANNEL = 0
DEFAULT_BANK = 0

DRUM_CHANNEL = 9
DRUM_TRACK = 127  # Can't use 128 as MIDI only supports 127 tracks
DRUM_BANK = 128
DRUM_INSTRUMENT = 0
DRUM_OFFSET = 35

ESCDELAY = 25

# Default files
DEFAULT_FILE = 'untitled.mid'
DEFAULT_SOUNDFONT = '/usr/share/soundfonts/default.sf2'
CRASH_FILE = 'crash.log'

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
SCALE_CHROMATIC = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

SCALE_NAME_MAP = {
    'major': SCALE_MAJOR,
    'major_pentatonic': SCALE_MAJOR_PENTATONIC,
    'minor': SCALE_MINOR_NATURAL,
    'natural_minor': SCALE_MINOR_NATURAL,
    'harmonic_minor': SCALE_MINOR_HARMONIC,
    'minor_pentatonic': SCALE_MAJOR_PENTATONIC,
    'blues': SCALE_BLUES,
    'chromatic': SCALE_CHROMATIC,
}

# Adapted from:
# https://en.wikipedia.org/wiki/General_MIDI#Program_change_events
INSTRUMENT_NAMES = [
    'Grand Piano',
    'Bright Grand Piano',
    'Electric Grand Piano',
    'Honky-tonk Piano',
    'Electric Piano 1',
    'Electric Piano 2',
    'Harpsichord',
    'Clavinet',
    'Celesta',
    'Glockenspiel',
    'Music Box',
    'Vibraphone',
    'Marimba',
    'Xylophone',
    'Tubular Bells',
    'Dulcimer',
    'Drawbar Organ',
    'Percussive Organ',
    'Rock Organ',
    'Church Organ',
    'Reed Organ',
    'Accordion',
    'Harmonica',
    'Tango Accordion',
    'Nylon Guitar',
    'Steel Guitar',
    'Jazz Guitar',
    'Clean Guitar',
    'Muted Guitar',
    'Overdrive Guitar',
    'Distortion Guitar',
    'Guitar Harmonics',
    'Acoustic Bass',
    'Finger Bass',
    'Pick Bass',
    'Fretless Bass',
    'Slap Bass 1',
    'Slap Bass 2',
    'Synth Bass 1',
    'Synth Bass 2',
    'Violin',
    'Viola',
    'Cello',
    'Contrabass',
    'Tremolo Strings',
    'Pizzicato Strings',
    'Orchestral Harp',
    'Timpani',
    'String Ensemble 1',
    'String Ensemble 2',
    'Synth Strings 1',
    'Synth Strings 2',
    'Choir Aahs',
    'Voice Oohs',
    'Synth Voice',
    'Orchestra Hit',
    'Trumpet',
    'Trombone',
    'Tuba',
    'Muted Trumpet',
    'French Horn',
    'Brass Section',
    'Synth Brass 1',
    'Synth Brass 2',
    'Soprano Sax',
    'Alto Sax',
    'Tenor Sax',
    'Baritone Sax',
    'Oboe',
    'English Horn',
    'Bassoon',
    'Clarinet',
    'Piccolo',
    'Flute',
    'Recorder',
    'Pan Flute',
    'Blown bottle',
    'Shakuhachi',
    'Whistle',
    'Ocarina',
    'Square Lead',
    'Sawtooth Lead',
    'Calliope Lead',
    'Chiff Lead',
    'Charang Lead',
    'Space Voice Lead',
    'Fifths Lead',
    'Bass and Lead',
    'Fantasia Pad',
    'Warm Pad',
    'Polysynth Pad',
    'Choir Pad',
    'Bowed Pad',
    'Metallic Pad',
    'Halo Pad',
    'Sweep Pad',
    'Rain FX',
    'Soundtrack FX',
    'Crystal FX',
    'Atmosphere FX',
    'Brightness FX',
    'Goblins FX',
    'Echoes FX',
    'Sci-Fi FX',
    'Sitar',
    'Banjo',
    'Shamisen',
    'Koto',
    'Kalimba',
    'Bag pipe',
    'Fiddle',
    'Shanai',
    'Tinkle Bell',
    'Agogo',
    'Steel Drums',
    'Woodblock',
    'Taiko Drum',
    'Melodic Tom',
    'Synth Drum',
    'Reverse Cymbal',
    'Guitar Fret Noise',
    'Breath Noise',
    'Seashore',
    'Bird Tweet',
    'Telephone Ring',
    'Helicopter',
    'Applause',
    'Gunshot',
]

# Adapted from:
# https://en.wikipedia.org/wiki/General_MIDI#Percussion
# Offset by DRUM_OFFSET
DRUM_NAMES = [
    'Acoustic Bass Drum',
    'Electric Bass Drum',
    'Side Stick',
    'Acoustic Snare',
    'Hand Clap',
    'Electric Snare',
    'Low Floor Tom',
    'Closed Hi-hat',
    'High Floor Tom',
    'Pedal Hi-hat',
    'Low Tom',
    'Open Hi-hat',
    'Low-Mid Tom',
    'Hi-Mid Tom',
    'Crash Cymbal 1',
    'High Tom',
    'Ride Cymbal 1',
    'Chinese Cymbal',
    'Ride Bell',
    'Tambourine',
    'Splash Cymbal',
    'Cowbell',
    'Crash Cymbal 2',
    'Vibraslap',
    'Ride Cymbal 2',
    'High Bongo',
    'Low Bongo',
    'Mute High Conga',
    'Open High Conga',
    'Low Conga',
    'High Timbale',
    'Low Timbale',
    'High Agogo',
    'Low Agogo',
    'Cabasa',
    'Maracas',
    'Short Whistle',
    'Long Whistle',
    'Short Guiro',
    'Long Guiro',
    'Claves',
    'High Woodblock',
    'Low Woodblock',
    'Mute Cuica',
    'Open Cuica',
    'Mute Triangle',
    'Open Triangle',
]


class Action(Enum):
    PAN_LEFT = 'pan left'
    PAN_LEFT_SHORT = 'pan left (short)'
    PAN_RIGHT = 'pan right'
    PAN_RIGHT_SHORT = 'pan right (short)'
    PAN_UP = 'pan up'
    PAN_UP_SHORT = 'pan up (short)'
    PAN_DOWN = 'pan down'
    PAN_DOWN_SHORT = 'pan down (short)'
    EDIT_LEFT = 'move the editing cursor one step forward'
    EDIT_RIGHT = 'move the editing cursor one step backward'
    EDIT_UP = 'move the editing cursor one octave higher'
    EDIT_DOWN = 'move the editing cursor one octave lower'
    JUMP_LEFT = 'jump to beginning of song'
    JUMP_RIGHT = 'jump to end of song'
    JUMP_UP = 'jump to highest note'
    JUMP_DOWN = 'jump to lowest note'
    MODE_NORMAL = 'enter normal mode, or deselect notes in normal mode'
    MODE_INSERT = 'enter insert mode'
    MODE_INSERT_STEP = 'enter insert mode, advance one step'
    MODE_INSERT_START = 'enter insert mode, jump to the beginning of the song'
    MODE_INSERT_END = 'enter insert mode, jump to the end of the song'
    DELETE_NOTE = 'delete the selected note'
    DELETE_NOTE_BACK = 'delete the selected note and step back'
    DELETE_CHORD = 'delete the selected chord'
    TIME_NOTE_DEC = 'decrease the start time of the selected note'
    TIME_NOTE_INC = 'increase the start time of the selected note'
    TIME_CHORD_DEC = 'decrease the start time of the selected chord'
    TIME_CHORD_INC = 'increase the start time of the selected chord'
    DURATION_NOTE_DEC = 'decrease the duration of the selected note'
    DURATION_NOTE_INC = 'increase the duration of the selected note'
    DURATION_CHORD_DEC = 'decrease the duration of the selected chord'
    DURATION_CHORD_INC = 'increase the duration of the selected chord'
    VELOCITY_NOTE_DEC = 'decrease the velocity of the selected note'
    VELOCITY_NOTE_INC = 'increase the velocity of the selected note'
    VELOCITY_CHORD_DEC = 'decrease the velocity of the selected chord'
    VELOCITY_CHORD_INC = 'increase the velocity of the selected chord'
    TRACK_DEC = 'switch to the previous track'
    TRACK_INC = 'switch to the next track'
    INSTRUMENT_DEC = 'use the previous instrument on this channel'
    INSTRUMENT_INC = 'use the next instrument on this channel'
    PLAYBACK_TOGGLE = 'toggle playback (play/pause)'
    PLAYBACK_RESTART = 'restart playback from the beginning of the song'
    WRITE_MIDI = 'export song as a MIDI file'
    QUIT_HELP = 'does not quit; use Ctrl+C to exit MusiCLI'


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

KEYMAP = {
    ord('h'): Action.PAN_LEFT,
    ord('H'): Action.PAN_LEFT_SHORT,
    ord('l'): Action.PAN_RIGHT,
    ord('L'): Action.PAN_RIGHT_SHORT,
    ord('k'): Action.PAN_UP,
    ord('K'): Action.PAN_UP_SHORT,
    ord('j'): Action.PAN_DOWN,
    ord('J'): Action.PAN_DOWN_SHORT,
    curses.KEY_LEFT: Action.EDIT_LEFT,
    curses.KEY_RIGHT: Action.EDIT_RIGHT,
    curses.KEY_UP: Action.EDIT_UP,
    curses.KEY_DOWN: Action.EDIT_DOWN,
    ord('0'): Action.JUMP_LEFT,
    ord('^'): Action.JUMP_LEFT,
    ord('$'): Action.JUMP_RIGHT,
    curses.KEY_PPAGE: Action.JUMP_UP,
    curses.KEY_NPAGE: Action.JUMP_DOWN,
    curses.KEY_HOME: Action.JUMP_LEFT,
    curses.KEY_END: Action.JUMP_RIGHT,
    curses.ascii.ESC: Action.MODE_NORMAL,
    ord('i'): Action.MODE_INSERT,
    ord('a'): Action.MODE_INSERT_STEP,
    ord('I'): Action.MODE_INSERT_START,
    ord('A'): Action.MODE_INSERT_END,
    curses.KEY_IC: Action.MODE_INSERT,
    ord('x'): Action.DELETE_NOTE,
    ord('d'): Action.DELETE_CHORD,
    curses.KEY_DC: Action.DELETE_NOTE,
    curses.KEY_BACKSPACE: Action.DELETE_NOTE_BACK,
    ord(','): Action.TIME_NOTE_DEC,
    ord('.'): Action.TIME_NOTE_INC,
    ord('<'): Action.TIME_CHORD_DEC,
    ord('>'): Action.TIME_CHORD_INC,
    ord('['): Action.DURATION_NOTE_DEC,
    ord(']'): Action.DURATION_NOTE_INC,
    ord('{'): Action.DURATION_CHORD_DEC,
    ord('}'): Action.DURATION_CHORD_INC,
    ord(';'): Action.VELOCITY_NOTE_DEC,
    ord('\''): Action.VELOCITY_NOTE_INC,
    ord(':'): Action.VELOCITY_CHORD_DEC,
    ord('"'): Action.VELOCITY_CHORD_INC,
    ord('-'): Action.TRACK_DEC,
    ord('='): Action.TRACK_INC,
    ord('_'): Action.INSTRUMENT_DEC,
    ord('+'): Action.INSTRUMENT_INC,
    ord(' '): Action.PLAYBACK_TOGGLE,
    curses.ascii.LF: Action.PLAYBACK_RESTART,
    ord('w'): Action.WRITE_MIDI,
    ord('q'): Action.QUIT_HELP,
}

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
SHIFT_NUMBERS = tuple('!@#$%^&*()')

# Global thread events
play_playback = Event()
restart_playback = Event()
kill_threads = Event()

# Globals
SONG = None
SYNTH = None
SOUNDFONT = None
PLAYHEAD = 0
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
        self.tracks = []

    @property
    def notes_by_track(self):
        return notes_by_track(self.notes)

    @property
    def start(self):
        return self[0].start if len(self.notes) > 0 else 0

    @property
    def end(self):
        return self[-1].end if len(self.notes) > 0 else 0

    def add_note(self, note, pair=True):
        index = bisect_left(self.notes, note)
        if (0 <= index < len(self) and
                self[index] == note and
                (not pair or self[index].pair == note.pair)):
            raise ValueError('Note {note} is already in the song')
        self.notes.insert(index, note)
        if pair:
            if note.pair is None:
                raise ValueError('Note {note} is unpaired')
            insort(self.notes, note.pair)

    def remove_note(self, note, pair=True, lookup=False):
        # Get the song note rather than the given note, since externally
        # created notes may have different pairs
        if lookup:
            note = self[self.notes.index(note)]
        self.notes.remove(note)
        if pair:
            if note.pair is None:
                raise ValueError('Note {song_note} is unpaired')
            self.notes.remove(note.pair)

    def move_note(self, note, time):
        self.remove_note(note)
        note.move(time)
        self.add_note(note)

    def set_duration(self, note, duration):
        self.remove_note(note)
        note.set_duration(duration)
        self.add_note(note)

    def get_index(self, time, track=None, on=False):
        index = bisect_left(self, DummyNote(time))
        if time < self[index].time:
            return -1
        if time > self[index].time:
            return len(self)
        while (index < len(self) and
               self[index].time == time and
               ((track is not None and self[index].track is not track) or
                (on and not self[index].on))):
            index += 1
        return index

    def get_previous_index(self, time, track=None, on=False):
        index = bisect_left(self, DummyNote(time))
        if time < self[index].time:
            return -1
        index -= 1
        while (index >= 0 and
               ((track is not None and self[index].track is not track) or
                (on and not self[index].on))):
            index -= 1
        return index

    def get_next_index(self, time, track=None, on=False, inclusive=True):
        if inclusive:
            index = bisect_left(self, DummyNote(time))
        else:
            index = bisect_right(self, DummyNote(time))
        if index < len(self) and time > self[index].time:
            return len(self)
        while (index < len(self) and
               ((track is not None and self[index].track is not track) or
                (on and not self[index].on))):
            index += 1
        return index

    def get_note(self, time, track=None, on=False):
        index = self.get_index(time, track, on)
        return self[index] if 0 <= index < len(self) else None

    def get_previous_note(self, time, track=None, on=False):
        index = self.get_previous_index(time, track, on)
        return self[index] if index >= 0 else None

    def get_next_note(self, time, track=None, on=False, inclusive=True):
        index = self.get_next_index(time, track, on, inclusive)
        return self[index] if index < len(self) else None

    def get_chord(self, time, track=None):
        index = self.get_index(time, track, on=True)
        if not 0 <= index < len(self):
            return []
        chord_time = self[index].time
        chord = [self[index]]
        index += 1
        while (index < len(self) and
               self[index].time == chord_time):
            if (self[index].on and
                    (track is None or self[index].track is track)):
                chord.append(self[index])
            index += 1
        return chord

    def get_previous_chord(self, time, track=None):
        index = self.get_previous_index(time, track, on=True)
        if index < 0:
            return []
        chord_time = self[index].time
        chord = [self[index]]
        index -= 1
        while index >= 0 and self[index].time == chord_time:
            if (self[index].on and
                    (track is None or self[index].track is track)):
                chord.append(self[index])
            index -= 1
        return chord

    def get_next_chord(self, time, track=None, inclusive=True):
        index = self.get_next_index(time, track, on=True, inclusive=inclusive)
        if index >= len(self):
            return []
        chord_time = self[index].time
        chord = [self[index]]
        index += 1
        while index < len(self) and self[index].time == chord_time:
            if (self[index].on and
                    (track is None or self[index].track is track)):
                chord.append(self[index])
            index += 1
        return chord

    def get_notes_in_track(self, track):
        notes = []
        for note in self.notes:
            if note.track is track:
                notes.append(note)
        return notes

    def has_channel(self, channel):
        for track in self.tracks:
            if track.channel == channel:
                return True
        return False

    def get_track(self, channel, create=True, synth=None):
        for track in self.tracks:
            if track.channel == channel:
                return track
        if create:
            track = Track(channel)
            track.set_instrument(ARGS.default_instrument, synth)
            self.tracks.append(track)
            return track
        return None

    def __len__(self):
        return len(self.notes)

    def __getitem__(self, key):
        return self.notes[key]

    def __contains__(self, item):
        return item in self.notes


class Track:
    def __init__(self, channel):
        self.channel = channel
        self.instrument = None

    @property
    def is_drum(self):
        return self.channel == DRUM_CHANNEL

    @property
    def instrument_name(self):
        if self.is_drum:
            return 'Drums'
        return INSTRUMENT_NAMES[self.instrument]

    @property
    def color_pair(self):
        if self.channel == DRUM_CHANNEL:
            return PAIR_DRUM
        return INSTRUMENT_PAIRS[self.instrument % len(INSTRUMENT_PAIRS)]

    def set_instrument(self, instrument, synth=None):
        self.instrument = instrument
        if synth is not None:
            if self.is_drum:
                synth.program_select(self.channel,
                                     SOUNDFONT,
                                     DRUM_BANK,
                                     instrument)
            else:
                synth.program_select(self.channel,
                                     SOUNDFONT,
                                     DEFAULT_BANK,
                                     instrument)

    def __hash__(self):
        return hash(self.channel)


class Note:
    def __init__(self,
                 on,
                 number,
                 time,
                 track,
                 velocity=DEFAULT_VELOCITY,
                 duration=None):
        if time < 0:
            raise ValueError(f'Time must be non-negative; was {time}')

        self.on = on
        self.number = number
        self.time = time
        self.velocity = velocity
        self.track = track

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

        self.pair = Note(on=not self.on,
                         number=self.number,
                         time=time,
                         velocity=self.velocity,
                         track=self.track)
        self.pair.pair = self

    @property
    def on_pair(self):
        return self if self.on else self.pair

    @property
    def off_pair(self):
        return self.pair if self.on else self

    @property
    def start(self):
        return self.on_pair.time

    @property
    def end(self):
        return self.off_pair.time

    @property
    def duration(self):
        return self.off_pair.time - self.on_pair.time

    @property
    def semitone(self):
        return self.number % NOTES_PER_OCTAVE

    @property
    def octave(self):
        return self.number // NOTES_PER_OCTAVE - 1

    @property
    def name(self):
        return self.name_in_key(None, octave=False)

    @property
    def full_name(self):
        return self.name_in_key(None, octave=True)

    def name_in_key(self, key, octave=False):
        if self.is_drum:
            return str(self.number)
        return number_to_name(self.number, key, octave=octave)

    @property
    def channel(self):
        return self.track.channel

    @property
    def is_drum(self):
        return self.track.is_drum

    @property
    def instrument(self):
        return self.track.instrument

    @property
    def instrument_name(self):
        if self.is_drum:
            return DRUM_NAMES[self.number - DRUM_OFFSET]
        return self.track.instrument_name

    @property
    def color_pair(self):
        return self.track.color_pair

    def move(self, time):
        if self.pair is not None:
            if self.on:
                self.pair.time = time + self.duration
            else:
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
            self.off_pair.time = self.on_pair.time + duration

    def set_velocity(self, velocity):
        if not 0 <= velocity < MAX_VELOCITY:
            raise ValueError('Velocity must be in the range '
                             f'0-{MAX_VELOCITY}; was {velocity}')

        self.velocity = velocity
        if self.pair is not None:
            self.pair.velocity = velocity

    def play(self, synth):
        if self.on:
            synth.noteon(self.channel, self.number, self.velocity)
        else:
            synth.noteoff(self.channel, self.number)

    def stop(self, synth):
        synth.noteoff(self.channel, self.number)

    def __str__(self):
        return f'{self.full_name} ({self.instrument_name} @ {self.velocity})'

    def __repr__(self):
        # TODO make a better __repr__
        return str(self)

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time

    def __eq__(self, other):
        return (isinstance(other, Note) and
                self.on == other.on and
                self.number == other.number and
                self.time == other.time and
                self.channel == other.channel)


def notes_by_track(notes):
    tracks = {}
    for note in notes:
        if note.track not in tracks:
            tracks[note.track] = []
        tracks[note.track].append(note)
    return tracks


def notes_to_messages(notes):
    messages = []
    last_time = 0
    for note in notes:
        delta = note.time - last_time
        message_type = 'note_on' if note.on else 'note_off'
        message = Message(message_type,
                          note=note.number,
                          velocity=note.velocity,
                          time=delta,
                          channel=note.channel)
        messages.append(message)
        last_time = note.time
    return messages


def import_midi(infile_path, synth):
    infile = MidiFile(infile_path)
    ARGS.ticks_per_beat = infile.ticks_per_beat

    song = Song()
    notes = []
    active_notes = []
    tempo_set = False
    for track in infile.tracks:
        time = 0
        for message in track:
            time += message.time
            if message.type == 'note_on':
                active_notes.append(Note(on=True,
                                         number=message.note,
                                         time=time,
                                         velocity=message.velocity,
                                         track=song.get_track(message.channel,
                                                              create=True,
                                                              synth=synth)))
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
            # Use the first set_tempo message as the song tempo
            elif message.type == 'set_tempo':
                if not tempo_set:
                    ARGS.beats_per_minute = tempo2bpm(message.tempo)
                    tempo_set = True
            # Update channel instrument with each program_change message
            elif message.type == 'program_change':
                song.get_track(message.channel).set_instrument(message.program,
                                                               synth)
    song.notes = sorted(notes)
    return song


def export_midi(song, filename):
    outfile = MidiFile(ticks_per_beat=ARGS.ticks_per_beat)

    tempo_set = False
    for track, notes in song.notes_by_track.items():
        midi_track = MidiTrack()
        if not tempo_set:
            midi_track.append(MetaMessage('set_tempo',
                                          tempo=bpm2tempo(
                                                ARGS.beats_per_minute)))
            tempo_set = True
        midi_track.append(Message('program_change',
                                  program=track.instrument,
                                  channel=track.channel))
        for message in notes_to_messages(notes):
            midi_track.append(message)
        outfile.tracks.append(midi_track)

    outfile.save(filename)


def init_synth():
    synth = Synth()
    synth.start()
    global SOUNDFONT
    SOUNDFONT = synth.sfload(ARGS.soundfont)
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
                next_note.play(synth)
                note_index += 1
                if note_index < len(SONG):
                    next_note = SONG[note_index]


def play_notes(synth, notes):
    if synth is not None:
        for note in notes:
            note.play(synth)


def stop_notes(synth, notes):
    if synth is not None:
        for note in notes:
            note.stop(synth)


def format_velocity(velocity):
    return f'Velocity: {velocity}'


def format_track(index, track):
    return f'Track {index + 1}: {track.instrument_name}'


class Interface:
    def __init__(self):
        if ARGS.import_file and os.path.exists(ARGS.import_file):
            self.song = import_midi(ARGS.import_file, SYNTH)
        else:
            self.song = Song()
            new_track = Track(0)
            self.song.tracks.append(new_track)
            new_track.set_instrument(ARGS.default_instrument, SYNTH)

        global SONG
        SONG = self.song

        self.octave = DEFAULT_OCTAVE
        self.key_name = ARGS.key
        self.scale_name = ARGS.scale

        self.time = 0
        self.duration = beats_to_ticks(1)
        self.velocity = DEFAULT_VELOCITY
        self.track_index = 0

        self.insert = False
        self.last_note = None
        self.last_chord = []

        self.window = None
        self.x_sidebar_offset = -6
        self.min_x_offset = self.x_sidebar_offset
        self.min_y_offset = -2
        self.max_y_offset = TOTAL_NOTES
        self.x_offset = self.min_x_offset
        self.y_offset = self.min_y_offset

    @property
    def width(self):
        return self.window.getmaxyx()[1]

    @property
    def height(self):
        return self.window.getmaxyx()[0]

    @property
    def key(self):
        return NAME_TO_NUMBER[self.key_name]

    @property
    def scale(self):
        return SCALE_NAME_MAP[ARGS.scale]

    @property
    def track(self):
        return self.song.tracks[self.track_index]

    @property
    def filename(self):
        return ARGS.file if ARGS.file else DEFAULT_FILE

    def init_window(self, window):
        self.window = window
        self.max_y_offset = TOTAL_NOTES - self.height
        self.y_offset = ((DEFAULT_OCTAVE + 1) * NOTES_PER_OCTAVE -
                         self.height // 2)

    def draw_line(self, x, string, attr, start_y=1):
        if 0 <= x and x + len(string) < self.width:
            for y in range(start_y, self.height):
                self.window.addstr(y, x, string, attr)

    def draw_scale_dots(self):
        string = '·' if ARGS.unicode else '.'
        attr = curses.color_pair(PAIR_LINE)
        for y, note in enumerate(range(self.y_offset,
                                       self.y_offset + self.height - 1)):
            semitone = note % NOTES_PER_OCTAVE
            if semitone in [(number + self.key) % NOTES_PER_OCTAVE
                            for number in self.scale]:
                for x in range(-self.x_offset % 4, self.width - 1, 4):
                    self.window.addstr(self.height - y - 1, x, string, attr)

    def draw_measures(self):
        units_per_measure = ARGS.units_per_beat * ARGS.beats_per_measure
        string = '▏' if ARGS.unicode else '|'
        attr = curses.color_pair(PAIR_LINE)
        for x in range(-self.x_offset % units_per_measure,
                       self.width - 1,
                       units_per_measure):
            self.draw_line(x, string, attr, start_y=0)
            measure_number = (x + self.x_offset) // units_per_measure + 1
            self.window.addstr(0, x, str(measure_number), attr)

    def draw_cursor(self):
        self.draw_line(ticks_to_units(self.time) - self.x_offset,
                       '▏' if ARGS.unicode else '|',
                       curses.color_pair(0))

    def draw_playhead(self):
        if SYNTH is not None:
            self.draw_line(PLAYHEAD - self.x_offset,
                           ' ',
                           curses.color_pair(PAIR_PLAYHEAD))

    def draw_notes(self):
        time = units_to_ticks(self.x_offset)
        index = self.song.get_next_index(time)
        string = '▏' if ARGS.unicode else '['
        for note in self.song.notes[index:]:
            start_x = ticks_to_units(note.start) - self.x_offset
            end_x = ticks_to_units(note.end) - self.x_offset
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
            else:
                color_pair = note.color_pair
            attr = curses.color_pair(color_pair)

            for x in range(max(start_x, 0), min(end_x, self.width - 1)):
                self.window.addstr(y, x, ' ', attr)

            if 0 <= start_x < self.width - 1:
                self.window.addstr(y, start_x, string, attr)

            note_width = end_x - start_x
            if note_width >= 4 and (0 <= start_x + 1 and
                                    start_x + len(note.name) < self.width - 1):
                self.window.addstr(y, start_x + 1, note.name, attr)

    def draw_sidebar(self):
        pair_note = curses.color_pair(PAIR_SIDEBAR_NOTE)
        pair_key = curses.color_pair(PAIR_SIDEBAR_KEY)
        for y, number in enumerate(range(self.y_offset,
                                         self.y_offset + self.height)):
            note_name = number_to_name(number)
            insert_key = number - self.octave * NOTES_PER_OCTAVE
            self.window.addstr(self.height - y - 1,
                               0,
                               note_name.ljust(4).rjust(6),
                               pair_note)
            if 0 <= insert_key < len(INSERT_KEYLIST):
                self.window.addstr(self.height - y - 1,
                                   0,
                                   INSERT_KEYLIST[insert_key],
                                   pair_key)

    def draw_status_item(self, x, string, attr):
        self.window.addstr(self.height - 2,
                           x,
                           string[:self.width - x - 1],
                           attr)
        return x + len(string)

    def draw_status_bar(self):
        self.window.addstr(self.height - 1,
                           0,
                           MESSAGE.ljust(self.width - 1)[:self.width - 1],
                           curses.color_pair(0))

        mode_text = f' {"INSERT" if self.insert else "NORMAL"} '
        filename_text = f' {self.filename} '
        key_scale_text = f' {self.key} {self.scale_name.replace("_", " ")} '
        play_measure = units_to_beats(PLAYHEAD) // ARGS.beats_per_measure + 1
        edit_measure = ticks_to_beats(self.time) // ARGS.beats_per_measure + 1
        end_measure = (ticks_to_beats(self.song.end) //
                       ARGS.beats_per_measure +
                       1)
        play_text = (f' P{play_measure}/{end_measure} ')
        edit_text = (f' E{edit_measure}/{end_measure} ')
        attr = curses.color_pair(PAIR_STATUS_INSERT if self.insert else
                                 PAIR_STATUS_NORMAL)
        x = 0
        x = self.draw_status_item(x, mode_text, attr | curses.A_BOLD)
        if x >= self.width:
            return

        x = self.draw_status_item(x,
                                  filename_text,
                                  attr | curses.A_REVERSE | curses.A_BOLD)
        if x >= self.width:
            return

        filler_width = (self.width -
                        len(mode_text) -
                        len(filename_text) -
                        len(key_scale_text) -
                        len(play_text) -
                        len(edit_text) - 1)
        if filler_width > 0:
            x = self.draw_status_item(x,
                                      ' ' * filler_width,
                                      attr | curses.A_REVERSE)

        x = self.draw_status_item(x,
                                  key_scale_text,
                                  attr | curses.A_REVERSE)
        if x >= self.width:
            return

        x = self.draw_status_item(x, play_text, attr | curses.A_BOLD)
        if x >= self.width:
            return

        x = self.draw_status_item(x, edit_text, attr | curses.A_BOLD)

    def draw(self):
        self.draw_scale_dots()
        self.draw_measures()
        self.draw_cursor()
        self.draw_playhead()
        self.draw_notes()
        self.draw_sidebar()
        self.draw_status_bar()

    def set_x_offset(self, x_offset):
        self.x_offset = max(x_offset, self.min_x_offset)

    def set_y_offset(self, y_offset):
        self.y_offset = min(max(y_offset,
                                self.min_y_offset),
                            self.max_y_offset)

    def snap_to_time(self, time=None, center=True):
        if time is None:
            time = self.time
        units_per_measure = ARGS.units_per_beat * ARGS.beats_per_measure
        time_units = ticks_to_units(time)
        if (time_units < self.x_offset or
                time_units >= self.x_offset + self.width):
            new_offset = time_units
            if center:
                new_offset -= self.width // 2
            self.set_x_offset(new_offset -
                              new_offset % units_per_measure +
                              self.x_sidebar_offset)

    def format_notes(self, notes):
        if len(notes) == 1:
            return str(notes[0])
        string = ''
        for note in sorted(notes, key=lambda x: x.number):
            string += note.name_in_key(self.key, octave=True) + ' '
        return string

    def insert_note(self, number, chord=False):
        global MESSAGE

        if not play_playback.is_set():
            stop_notes(SYNTH, self.last_chord)

        if self.last_note is not None and not chord:
            self.time += self.duration
            if self.insert:
                self.snap_to_time()
            self.last_chord = []

        number += self.octave * NOTES_PER_OCTAVE
        note = Note(on=True,
                    number=number,
                    time=self.time,
                    duration=self.duration,
                    velocity=self.velocity,
                    track=self.track)

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

        MESSAGE = self.format_notes(self.last_chord)

        if not play_playback.is_set():
            play_notes(SYNTH, self.last_chord)

    def move_cursor(self, left):
        global MESSAGE

        if left:
            nearest_chord = self.song.get_previous_chord(self.time,
                                                         self.track)
            if len(nearest_chord) > 0:
                nearest_time = nearest_chord[0].start
                end_time = max([note.end for note in nearest_chord])
            else:
                nearest_time = 0
                end_time = 0
            if (self.last_note is not None and
                    end_time >= self.last_note.start):
                self.time = nearest_time
            else:
                self.time = max(self.time - self.duration, nearest_time, 0)

        else:
            chord_time = self.time
            inclusive = self.last_note is None
            nearest_chord = self.song.get_next_chord(chord_time,
                                                     self.track,
                                                     inclusive=inclusive)
            if len(nearest_chord) > 0:
                nearest_time = nearest_chord[0].start
            else:
                nearest_time = inf

            if (self.last_note is not None and
                    nearest_time <= self.last_note.end):
                self.time = nearest_time
            else:
                self.time = min(self.time + self.duration, nearest_time)

        if len(nearest_chord) > 0 and self.time == nearest_time:
            self.last_chord = nearest_chord
            self.last_note = nearest_chord[0]
            self.duration = self.last_note.duration

        self.snap_to_time()

        MESSAGE = self.format_notes(self.last_chord)

    def set_octave(self, increase):
        if increase:
            self.octave = min(self.octave + 1,
                              TOTAL_NOTES // NOTES_PER_OCTAVE - 1)
        else:
            self.octave = max(self.octave - 1, 0)
        self.set_y_offset((self.octave + 1) * NOTES_PER_OCTAVE -
                          self.height // 2)

    def set_time(self, increase, chord):
        if not chord:
            if increase:
                new_start = self.last_note.start + units_to_ticks(1)
            else:
                new_start = max(self.last_note.start -
                                units_to_ticks(1),
                                0)
            self.song.move_note(self.last_note, new_start)
            self.time = self.last_note.start
            self.last_chord = [self.last_note]
        else:
            if increase:
                new_start = self.last_note.start + units_to_ticks(1)
            else:
                new_start = max(self.last_note.start -
                                units_to_ticks(1),
                                0)
            for note in self.last_chord:
                self.song.move_note(note, new_start)
            self.time = self.last_note.end

        self.snap_to_time()

    def set_duration(self, increase, chord):
        if self.last_note is not None:
            if not chord:
                if increase:
                    self.song.set_duration(self.last_note,
                                           self.last_note.duration +
                                           units_to_ticks(1))
                else:
                    self.song.set_duration(self.last_note,
                                           max(self.last_note.duration -
                                               units_to_ticks(1),
                                               units_to_ticks(1)))
            else:
                if increase:
                    for note in self.last_chord:
                        self.song.set_duration(note,
                                               note.duration +
                                               units_to_ticks(1))
                else:
                    for note in self.last_chord:
                        self.song.set_duration(note, max(note.duration -
                                                         units_to_ticks(1),
                                                         units_to_ticks(1)))

            # Update duration and time for next insertion
            self.duration = self.last_note.duration
        else:
            if increase:
                self.duration += units_to_ticks(1)
            else:
                self.duration = max(self.duration - units_to_ticks(1),
                                    units_to_ticks(1))

    def set_velocity(self, increase, chord):
        global MESSAGE

        if increase:
            self.velocity = min(self.velocity + 1, MAX_VELOCITY)
        else:
            self.velocity = max(self.velocity - 1, 0)

        MESSAGE = format_velocity(self.velocity)

        if not chord:
            if self.last_note is not None:
                self.last_note.set_velocity(self.velocity)
        else:
            for note in self.last_chord:
                note.set_velocity(self.velocity)

    def set_track(self, increase):
        global MESSAGE

        if increase:
            self.track_index += 1
        else:
            self.track_index -= 1
        self.track_index %= len(self.song.tracks)

        MESSAGE = format_track(self.track_index, self.track)

    def set_instrument(self, increase):
        global MESSAGE

        stop_notes(SYNTH, self.last_chord)

        instrument = self.song.tracks[self.track_index].instrument
        if increase:
            instrument += 1
        else:
            instrument -= 1
        instrument %= TOTAL_INSTRUMENTS

        self.track.set_instrument(instrument, SYNTH)

        MESSAGE = format_track(self.track_index, self.track)

        play_notes(SYNTH, self.last_chord)

    def delete(self, back):
        if self.last_note is not None:
            stop_notes(SYNTH, [self.last_note])
            if not back:
                self.time += self.last_note.duration
            last_duration = self.last_note.duration
            self.song.remove_note(self.last_note)
            self.last_chord.remove(self.last_note)
            self.last_note = None
            if back:
                self.last_chord = self.song.get_previous_chord(self.time,
                                                               self.track)
                if len(self.last_chord) > 0:
                    self.last_note = self.last_chord[0]
                    self.time = self.last_note.time
                else:
                    self.time -= last_duration
        elif back:
            # TODO move to the previous chord like KEY_LEFT
            # Consider deleting the entire chord with backspace
            self.time = max(self.time - self.duration, 0)

    def toggle_playback(self):
        if SYNTH is not None:
            if play_playback.is_set():
                play_playback.clear()
                curses.cbreak()
            else:
                stop_notes(SYNTH, self.last_chord)
                play_playback.set()
                curses.halfdelay(1)

    def restart_playback(self):
        if SYNTH is not None:
            stop_notes(SYNTH, self.last_chord)
            restart_playback.set()
            play_playback.set()
            curses.halfdelay(1)

    def deselect(self):
        self.last_note = None
        self.last_chord = []

    def escape(self):
        global MESSAGE

        if not self.insert:
            if self.last_note is None:
                MESSAGE = 'Press Ctrl+C to exit MusiCLI'
            else:
                self.deselect()
        else:
            stop_notes(SYNTH, self.last_chord)
            self.insert = False

    def handle_action(self, action):
        global MESSAGE

        # Pan view
        x_pan = ARGS.units_per_beat * ARGS.beats_per_measure
        x_pan_short = ARGS.units_per_beat
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
            self.set_y_offset(self.y_offset - y_pan)
        elif action == Action.PAN_UP_SHORT:
            self.set_y_offset(self.y_offset - y_pan_short)
        elif action == Action.PAN_DOWN:
            self.set_y_offset(self.y_offset + y_pan)
        elif action == Action.PAN_DOWN_SHORT:
            self.set_y_offset(self.y_offset + y_pan_short)
        elif action == Action.EDIT_LEFT:
            self.move_cursor(left=True)
        elif action == Action.EDIT_RIGHT:
            self.move_cursor(left=False)
        elif action == Action.EDIT_UP:
            self.set_octave(increase=False)
        elif action == Action.EDIT_DOWN:
            self.set_octave(increase=True)
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
        elif action == Action.DELETE_NOTE:
            self.delete(back=False)
        elif action == Action.DELETE_CHORD:
            self.delete(back=False)
        elif action == Action.DELETE_NOTE_BACK:
            self.delete(back=True)
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
        elif action == Action.PLAYBACK_TOGGLE:
            self.toggle_playback()
        elif action == Action.PLAYBACK_RESTART:
            self.restart_playback()
        elif action == Action.WRITE_MIDI:
            export_midi(self.song, self.filename)
            MESSAGE = f'Wrote MIDI to {self.filename}'
        elif action == Action.QUIT_HELP:
            MESSAGE = 'Press Ctrl+C to exit MusiCLI'

    def handle_input(self, input_code):
        global MESSAGE

        # Reset message on next actual keypress
        if input_code != curses.ERR:
            MESSAGE = ''

        if self.insert:
            if curses.ascii.isprint(input_code):
                input_char = chr(input_code)
                number = INSERT_KEYMAP.get(input_char.lower())
                chord = input_char.isupper() or not input_char.isalnum()
                if number is not None:
                    self.insert_note(number, chord)
                    return True
                if input_char.isalnum() or input_char in SHIFT_NUMBERS:
                    MESSAGE = "Key '{input_char}' does not map to a note"
                    return False
        action = KEYMAP.get(input_code)
        if action is not None:
            return self.handle_action(action)
        return False

    def main(self, window):
        self.init_window(window)

        # Loop until user the exits
        while True:
            if not self.insert and play_playback.is_set():
                self.snap_to_time(units_to_ticks(PLAYHEAD), center=False)

            self.draw()
            self.window.refresh()
            input_code = self.window.getch()
            self.window.erase()
            self.handle_input(input_code)


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
        Interface().main(stdscr)
    except Exception:
        with open(CRASH_FILE, 'w') as crash_file:
            crash_file.write(format_exc())
    finally:
        curses.cbreak()
        play_playback.set()
        kill_threads.set()
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

    SYNTH = init_synth() if ARGS.soundfont else None

    os.environ.setdefault('ESCDELAY', str(ESCDELAY))

    curses.wrapper(wrapper)
