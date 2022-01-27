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

from bisect import bisect_left, bisect_right, insort

from mido import (Message,
                  MetaMessage,
                  MidiFile,
                  MidiTrack,
                  tempo2bpm)
from mido.midifiles.midifiles import DEFAULT_TEMPO, DEFAULT_TICKS_PER_BEAT


TOTAL_NOTES = 127
NOTES_PER_OCTAVE = 12

MAX_VELOCITY = 127
DEFAULT_VELOCITY = MAX_VELOCITY  # 64 is recommended, but seems quiet

TOTAL_INSTRUMENTS = 128  # Drums replace gunshot as instrument 128
DEFAULT_CHANNEL = 0
DEFAULT_BANK = 0

DRUM_CHANNEL = 9
DRUM_BANK = 128
DRUM_INSTRUMENT = 0
DRUM_OFFSET = 35

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

DEFAULT_COLS_PER_BEAT = 4
DEFAULT_BEATS_PER_MEASURE = 4
DEFAULT_INSTRUMENT = 0
DEFAULT_KEY = 0
DEFAULT_SCALE_NAME = 'major'


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

    def set_instrument(self, instrument, synth=None, soundfont=None):
        self.instrument = instrument
        if synth is not None and soundfont is not None:
            if self.is_drum:
                synth.program_select(self.channel,
                                     soundfont,
                                     DRUM_BANK,
                                     instrument)
            else:
                synth.program_select(self.channel,
                                     soundfont,
                                     DEFAULT_BANK,
                                     instrument)

    def __str__(self):
        return f'Channel {self.channel}: {self.instrument_name}'

    def __repr__(self):
        return f'Track(channel={self.channel})'

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

    def __str__(self):
        return f'{self.full_name} ({self.instrument_name} @ {self.velocity})'

    def __repr__(self):
        return (f'Note(on={self.on}, '
                f'number={self.number}, '
                f'time={self.time}, '
                f'track={self.track}, '
                f'velocity={self.velocity}, '
                f'duration={self.duration})')

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


class DummyNote:
    def __init__(self, time):
        self.time = time

    def __lt__(self, other):
        return self.time < other.time

    def __gt__(self, other):
        return self.time > other.time

    def __repr__(self):
        return f'DummyNote(time={self.time})'


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


class Song:
    def __init__(self,
                 midi_file=None,
                 synth=None,
                 soundfont=None,
                 tempo=None,
                 ticks_per_beat=None,
                 cols_per_beat=DEFAULT_COLS_PER_BEAT,
                 beats_per_measure=DEFAULT_BEATS_PER_MEASURE,
                 key=DEFAULT_KEY,
                 scale_name=DEFAULT_SCALE_NAME):
        self.notes = []
        self.tracks = []
        self.tempo = tempo
        self.ticks_per_beat = ticks_per_beat

        if midi_file is not None:
            self.import_midi(midi_file, synth, soundfont)
        else:
            new_track = Track(0)
            new_track.set_instrument(DEFAULT_INSTRUMENT, synth, soundfont)
            self.tracks.append(new_track)

        if self.tempo is None:
            self.tempo = DEFAULT_TEMPO
        if self.ticks_per_beat is None:
            self.ticks_per_beat = DEFAULT_TICKS_PER_BEAT
        self.cols_per_beat = cols_per_beat
        self.beats_per_measure = beats_per_measure
        self.key = key
        self.scale_name = scale_name

    @property
    def bpm(self):
        return tempo2bpm(self.tempo)

    @property
    def key_name(self):
        return COMMON_NAMES[self.key]

    @property
    def scale(self):
        return SCALE_NAME_MAP[self.scale_name]

    @property
    def notes_by_track(self):
        return notes_by_track(self.notes)

    @property
    def start(self):
        return self[0].start if len(self.notes) > 0 else 0

    @property
    def end(self):
        return self[-1].end if len(self.notes) > 0 else 0

    def ticks_to_beats(self, ticks):
        return ticks // self.ticks_per_beat

    def beats_to_ticks(self, beats):
        return beats * self.ticks_per_beat

    def ticks_to_cols(self, ticks):
        return int(ticks / self.ticks_per_beat * self.cols_per_beat)

    def cols_to_ticks(self, cols):
        return int(cols / self.cols_per_beat * self.ticks_per_beat)

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

    def get_track(self, channel, create=True, synth=None, soundfont=None):
        for track in self.tracks:
            if track.channel == channel:
                return track
        if create:
            track = Track(channel)
            track.set_instrument(DEFAULT_INSTRUMENT, synth, soundfont)
            self.tracks.append(track)
            return track
        return None

    def import_midi(self, infile_path, synth=None, soundfont=None):
        infile = MidiFile(infile_path)
        self.ticks_per_beat = infile.ticks_per_beat

        notes = []
        active_notes = []
        for track in infile.tracks:
            time = 0
            for message in track:
                time += message.time
                if message.type == 'note_on':
                    active_notes.append(Note(on=True,
                                             number=message.note,
                                             time=time,
                                             velocity=message.velocity,
                                             track=self.get_track(
                                                 message.channel,
                                                 create=True,
                                                 synth=synth,
                                                 soundfont=soundfont)))
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
                elif message.type == 'program_change':
                    self.get_track(message.channel).set_instrument(
                            message.program,
                            synth,
                            soundfont)
                elif message.type == 'set_tempo':
                    if self.tempo is None:
                        self.tempo = message.tempo

        self.notes = sorted(notes)

    def export_midi(self, filename):
        outfile = MidiFile(ticks_per_beat=self.ticks_per_beat)

        tempo_set = False
        for track, notes in self.notes_by_track.items():
            midi_track = MidiTrack()
            if not tempo_set:
                midi_track.append(MetaMessage('set_tempo', tempo=self.tempo))
                tempo_set = True
            midi_track.append(Message('program_change',
                                      program=track.instrument,
                                      channel=track.channel))
            for message in notes_to_messages(notes):
                midi_track.append(message)
            outfile.tracks.append(midi_track)

        outfile.save(filename)

    def __len__(self):
        return len(self.notes)

    def __getitem__(self, key):
        return self.notes[key]

    def __contains__(self, item):
        return item in self.notes
