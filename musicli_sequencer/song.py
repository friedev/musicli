from __future__ import annotations
from bisect import bisect_left, bisect_right, insort
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import Player

try:
    from mido import Message, MidiFile, MidiTrack

    IMPORT_MIDO = True
except ImportError:
    IMPORT_MIDO = False


TOTAL_NOTES = 127
NOTES_PER_OCTAVE = 12

MAX_VELOCITY = 127
DEFAULT_VELOCITY = MAX_VELOCITY  # 64 is recommended, but seems quiet

TOTAL_INSTRUMENTS = 128
DEFAULT_CHANNEL = 0
DEFAULT_BANK = 0

DRUM_CHANNEL = 9
DRUM_BANK = 128
DRUM_INSTRUMENT = 0
DRUM_OFFSET = 35

NAME_TO_NUMBER: dict[str, int] = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}

SHARP_KEYS: tuple[str, ...] = ("G", "D", "A", "E", "B", "F#", "C#")
FLAT_KEYS: tuple[str, ...] = ("F", "Bb", "Eb", "Ab", "Db", "Gb")

COMMON_NAMES: tuple[str, ...] = (
    "C",
    "C#",
    "D",
    "Eb",
    "E",
    "F",
    "F#",
    "G",
    "Ab",
    "A",
    "Bb",
    "B",
)

SHARP_NAMES: tuple[str, ...] = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)

FLAT_NAMES: tuple[str, ...] = (
    "C",
    "Db",
    "D",
    "Eb",
    "E",
    "F",
    "Gb",
    "G",
    "Ab",
    "A",
    "Bb",
    "B",
)

# Adapted from:
# https://en.wikipedia.org/wiki/List_of_musical_scales_and_modes
SCALES: dict[str, tuple[int, ...]] = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "major_pentatonic": (0, 2, 4, 7, 9),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
    "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
    "minor_pentatonic": (0, 3, 5, 7, 10),
    "blues": (0, 3, 5, 6, 7, 10),
    "chromatic": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
}

# Adapted from:
# https://en.wikipedia.org/wiki/Interval_(music)
# https://en.wikipedia.org/wiki/List_of_chords
# https://en.wikipedia.org/wiki/Chord_names_and_symbols_(popular_music)
# TODO add more obscure chords from the second link
CHORDS: dict[tuple[int, ...], tuple[str, str]] = {
    (0, 1): ("ii", "minor second"),
    (0, 2): ("II", "major second"),
    (0, 3): ("iii", "minor third"),
    (0, 4): ("III", "major third"),
    (0, 5): ("IV", "perfect fourth"),
    (0, 6): ("TT", "tritone"),
    (0, 7): ("V", "perfect fifth"),
    (0, 8): ("vi", "minor sixth"),
    (0, 9): ("VI", "major sixth"),
    (0, 10): ("vii", "minor seventh"),
    (0, 11): ("VII", "major seventh"),
    (0, 4, 3): ("maj", "major chord"),
    (0, 3, 4): ("min", "minor chord"),
    (0, 3, 3): ("dim", "diminished chord"),
    (0, 4, 4): ("aug", "augmented chord"),
    (0, 2, 5): ("sus2", "suspended second chord"),
    (0, 5, 2): ("sus4", "suspended fourth chord"),
    (0, 4, 3, 3): ("7", "dominant seventh chord"),
    (0, 4, 3, 4): ("maj7", "major seventh chord"),
    (0, 3, 4, 3): ("min7", "minor seventh chord"),
    (0, 3, 4, 4): ("minmaj7", "minor major seventh chord"),
    (0, 4, 3, 3, 3): ("9", "dominant ninth chord"),
    (0, 4, 3, 3, 4): ("7b9", "dominant minor ninth chord"),
    (0, 4, 3, 4, 4): ("maj9", "major ninth chord"),
    (0, 3, 4, 3, 4): ("min9", "minor ninth chord"),
}

# Adapted from:
# https://en.wikipedia.org/wiki/General_MIDI#Program_change_events
INSTRUMENT_NAMES: list[str] = [
    "Grand Piano",
    "Bright Grand Piano",
    "Electric Grand Piano",
    "Honky-tonk Piano",
    "Electric Piano 1",
    "Electric Piano 2",
    "Harpsichord",
    "Clavinet",
    "Celesta",
    "Glockenspiel",
    "Music Box",
    "Vibraphone",
    "Marimba",
    "Xylophone",
    "Tubular Bells",
    "Dulcimer",
    "Drawbar Organ",
    "Percussive Organ",
    "Rock Organ",
    "Church Organ",
    "Reed Organ",
    "Accordion",
    "Harmonica",
    "Tango Accordion",
    "Nylon Guitar",
    "Steel Guitar",
    "Jazz Guitar",
    "Clean Guitar",
    "Muted Guitar",
    "Overdrive Guitar",
    "Distortion Guitar",
    "Guitar Harmonics",
    "Acoustic Bass",
    "Finger Bass",
    "Pick Bass",
    "Fretless Bass",
    "Slap Bass 1",
    "Slap Bass 2",
    "Synth Bass 1",
    "Synth Bass 2",
    "Violin",
    "Viola",
    "Cello",
    "Contrabass",
    "Tremolo Strings",
    "Pizzicato Strings",
    "Orchestral Harp",
    "Timpani",
    "String Ensemble 1",
    "String Ensemble 2",
    "Synth Strings 1",
    "Synth Strings 2",
    "Choir Aahs",
    "Voice Oohs",
    "Synth Voice",
    "Orchestra Hit",
    "Trumpet",
    "Trombone",
    "Tuba",
    "Muted Trumpet",
    "French Horn",
    "Brass Section",
    "Synth Brass 1",
    "Synth Brass 2",
    "Soprano Sax",
    "Alto Sax",
    "Tenor Sax",
    "Baritone Sax",
    "Oboe",
    "English Horn",
    "Bassoon",
    "Clarinet",
    "Piccolo",
    "Flute",
    "Recorder",
    "Pan Flute",
    "Blown bottle",
    "Shakuhachi",
    "Whistle",
    "Ocarina",
    "Square Lead",
    "Sawtooth Lead",
    "Calliope Lead",
    "Chiff Lead",
    "Charang Lead",
    "Space Voice Lead",
    "Fifths Lead",
    "Bass and Lead",
    "Fantasia Pad",
    "Warm Pad",
    "Polysynth Pad",
    "Choir Pad",
    "Bowed Pad",
    "Metallic Pad",
    "Halo Pad",
    "Sweep Pad",
    "Rain FX",
    "Soundtrack FX",
    "Crystal FX",
    "Atmosphere FX",
    "Brightness FX",
    "Goblins FX",
    "Echoes FX",
    "Sci-Fi FX",
    "Sitar",
    "Banjo",
    "Shamisen",
    "Koto",
    "Kalimba",
    "Bag pipe",
    "Fiddle",
    "Shanai",
    "Tinkle Bell",
    "Agogo",
    "Steel Drums",
    "Woodblock",
    "Taiko Drum",
    "Melodic Tom",
    "Synth Drum",
    "Reverse Cymbal",
    "Guitar Fret Noise",
    "Breath Noise",
    "Seashore",
    "Bird Tweet",
    "Telephone Ring",
    "Helicopter",
    "Applause",
    "Gunshot",
]

# Adapted from:
# https://en.wikipedia.org/wiki/General_MIDI#Percussion
# Offset by DRUM_OFFSET
DRUM_NAMES: list[tuple[str, str]] = [
    ("ABass", "Acoustic Bass Drum"),
    ("EBass", "Electric Bass Drum"),
    ("SStick", "Side Stick"),
    ("ASnare", "Acoustic Snare"),
    ("Clap", "Hand Clap"),
    ("ESnare", "Electric Snare"),
    ("LFTom", "Low Floor Tom"),
    ("CHat", "Closed Hi-hat"),
    ("HFTom", "High Floor Tom"),
    ("PHat", "Pedal Hi-hat"),
    ("LTom", "Low Tom"),
    ("OHat", "Open Hi-hat"),
    ("LMTom", "Low-Mid Tom"),
    ("HMTom", "Hi-Mid Tom"),
    ("CCym1", "Crash Cymbal 1"),
    ("HTom", "High Tom"),
    ("RCym1", "Ride Cymbal 1"),
    ("CNCym", "Chinese Cymbal"),
    ("RBell", "Ride Bell"),
    ("Tamb", "Tambourine"),
    ("SCym", "Splash Cymbal"),
    ("CBell", "Cowbell"),
    ("CCym2", "Crash Cymbal 2"),
    ("VSlap", "Vibraslap"),
    ("RCym2", "Ride Cymbal 2"),
    ("HBongo", "High Bongo"),
    ("LBongo", "Low Bongo"),
    ("MConga", "Mute High Conga"),
    ("HConga", "Open High Conga"),
    ("LConga", "Low Conga"),
    ("HTimb", "High Timbale"),
    ("LTimb", "Low Timbale"),
    ("HAgogo", "High Agogo"),
    ("LAgogo", "Low Agogo"),
    ("Cabasa", "Cabasa"),
    ("Maraca", "Maracas"),
    ("SWhist", "Short Whistle"),
    ("LWhist", "Long Whistle"),
    ("SGuiro", "Short Guiro"),
    ("LGuiro", "Long Guiro"),
    ("Claves", "Claves"),
    ("HWood", "High Woodblock"),
    ("LWood", "Low Woodblock"),
    ("MCuica", "Mute Cuica"),
    ("OCuica", "Open Cuica"),
    ("MTri", "Mute Triangle"),
    ("OTri", "Open Triangle"),
]

DEFAULT_COLS_PER_BEAT = 4
# These correspond to mido's DEFAULT_TEMPO and DEFAULT_TICKS_PER_BEAT
# Manually specified to reduce dependency
DEFAULT_BPM = 120
DEFAULT_TICKS_PER_BEAT = 480
DEFAULT_BEATS_PER_MEASURE = 4
DEFAULT_INSTRUMENT = 0
DEFAULT_KEY = 0
DEFAULT_SCALE_NAME = "major"


def number_to_name(
    number: int, scale: Optional[str] = None, octave: bool = True
) -> str:
    semitone = number % NOTES_PER_OCTAVE
    if scale in SHARP_KEYS:
        letter = SHARP_NAMES[semitone]
    elif scale in FLAT_KEYS:
        letter = FLAT_NAMES[semitone]
    else:
        letter = COMMON_NAMES[semitone]
    if not octave:
        return letter
    octave_str = number // NOTES_PER_OCTAVE - 1
    return f"{letter}{octave_str}"


def name_to_number(name: str) -> int:
    number = NAME_TO_NUMBER.get(name[:2])
    if number is None:
        number = NAME_TO_NUMBER.get(name[:1])
        if number is None:
            raise ValueError(f"{name} is not a valid note name")
        octave = name[1:]
    else:
        octave = name[2:]

    if octave == "":
        return number
    try:
        return number + int(octave) * NOTES_PER_OCTAVE
    except ValueError as e:
        raise ValueError(f"{name} is not a valid note name") from e


class Track:
    channel: int
    instrument: int

    def __init__(self, channel, instrument):
        self.channel = channel
        self.instrument = instrument

    @property
    def is_drum(self) -> bool:
        return self.channel == DRUM_CHANNEL

    @property
    def bank(self) -> int:
        return DRUM_BANK if self.is_drum else DEFAULT_BANK

    @property
    def instrument_name(self) -> str:
        if self.is_drum:
            return "Drums"
        return INSTRUMENT_NAMES[self.instrument]

    def register(self, player: Player) -> None:
        player.set_instrument(self.channel, self.bank, self.instrument)

    def set_channel(self, channel: int, player: Optional[Player] = None):
        self.channel = channel
        if player is not None:
            self.register(player)

    def set_instrument(self, instrument: int, player: Optional[Player] = None):
        self.instrument = instrument
        if player is not None:
            self.register(player)

    def __str__(self) -> str:
        return f"Channel {self.channel}: {self.instrument_name}"

    def __repr__(self) -> str:
        return f"Track(channel={self.channel})"

    def __hash__(self) -> int:
        return hash(self.channel)


@dataclass(init=False)
class SongEvent:
    time: int
    track: Track

    def __init__(self, time: int, track: Track):
        if time < 0:
            raise ValueError(f"Time must be non-negative; was {time}")

        self.time = time
        self.track = track

    def __lt__(self, other) -> bool:
        return self.time < other.time

    def __gt__(self, other) -> bool:
        return self.time > other.time


@dataclass(init=False)
class BaseNote(SongEvent):
    time: int
    track: Track
    number: int

    def __init__(self, time: int, track: Track, number: int = 0):
        super().__init__(time, track)
        self.number = number

    def __lt__(self, other) -> bool:
        if isinstance(other, BaseNote) and self.time == other.time:
            return self.number < other.number
        return super().__lt__(other)

    def __gt__(self, other) -> bool:
        if isinstance(other, BaseNote) and self.time == other.time:
            return self.number > other.number
        return super().__gt__(other)

    def __repr__(self) -> str:
        return (
            f"BaseNote(time={self.time}, "
            f"track={self.track}, "
            f"number={self.number})"
        )


class Note(BaseNote):
    on: bool
    number: int
    time: int
    track: Track
    velocity: int
    pair: Optional[Note]

    def __init__(
        self,
        on: bool,
        number: int,
        time: int,
        track: Track,
        velocity: int = DEFAULT_VELOCITY,
        duration: Optional[int] = None,
    ):
        super().__init__(time, track, number)

        self.on = on
        self.velocity = velocity

        self.pair = None
        if duration is not None:
            if duration < 0:
                raise ValueError(
                    f"Duration must be non-negative; was {duration}"
                )
            self.make_pair(time + duration if on else time - duration)

    def make_pair(self, time: int) -> None:
        if time < 0:
            raise ValueError(f"Time must be non-negative; was {time}")

        if (self.on and time < self.time) or (not self.on and time > self.time):
            raise ValueError(
                "Note must not end before it starts; "
                f"times were {self.time} and {time}"
            )

        self.pair = Note(
            on=not self.on,
            number=self.number,
            time=time,
            velocity=self.velocity,
            track=self.track,
        )
        self.pair.pair = self

    @property
    def on_pair(self) -> Note:
        if self.pair is None:
            raise ValueError(f"{repr(self)} is not part of a pair")
        return self if self.on else self.pair

    @property
    def off_pair(self) -> Note:
        if self.pair is None:
            raise ValueError(f"{repr(self)} is not part of a pair")
        return self.pair if self.on else self

    @property
    def start(self) -> int:
        return self.on_pair.time

    @property
    def end(self) -> int:
        return self.off_pair.time

    @property
    def duration(self) -> int:
        return self.off_pair.time - self.on_pair.time

    @property
    def semitone(self) -> int:
        return self.number % NOTES_PER_OCTAVE

    @property
    def octave(self) -> int:
        return self.number // NOTES_PER_OCTAVE - 1

    @property
    def name(self) -> str:
        return self.name_in_key(None, octave=False)

    @property
    def full_name(self) -> str:
        return self.name_in_key(None, octave=True)

    def name_in_key(self, key: Optional[str], octave: bool = False) -> str:
        if self.is_drum:
            drum_number = self.number - DRUM_OFFSET
            if 0 <= drum_number < len(DRUM_NAMES):
                short_name, long_name = DRUM_NAMES[drum_number]
            else:
                short_name = str(self.number)
                long_name = short_name
            return long_name if octave else short_name
        return number_to_name(self.number, key, octave=octave)

    @property
    def channel(self) -> int:
        return self.track.channel

    @property
    def is_drum(self) -> bool:
        return self.track.is_drum

    @property
    def instrument(self) -> int:
        return self.track.instrument

    @property
    def instrument_name(self) -> str:
        if self.is_drum:
            _, drum_name = DRUM_NAMES[self.number - DRUM_OFFSET]
            return drum_name
        return self.track.instrument_name

    def move(self, time: int) -> None:
        if self.pair is not None:
            if self.on:
                self.pair.time = time + self.duration
            else:
                self.pair.time = time - self.duration
                if self.pair.time < 0:
                    raise ValueError(
                        f"New start time must be non-negative; was {time}"
                    )
        self.time = time

    def set_duration(self, duration: int) -> None:
        if duration < 0:
            raise ValueError(f"Duration must be non-negative; was {duration}")

        if self.pair is None:
            self.make_pair(
                self.time + duration if self.on else self.time - duration
            )
        else:
            self.off_pair.time = self.on_pair.time + duration

    def set_velocity(self, velocity: int) -> None:
        if not 0 <= velocity < MAX_VELOCITY:
            raise ValueError(
                "Velocity must be in the range "
                f"0-{MAX_VELOCITY}; was {velocity}"
            )

        self.velocity = velocity
        if self.pair is not None:
            self.pair.velocity = velocity

    def to_message(self, delta: int) -> Message:
        message_type = "note_on" if self.on else "note_off"
        return Message(
            message_type,
            note=self.number,
            velocity=self.velocity,
            time=delta,
            channel=self.channel,
        )

    def __str__(self) -> str:
        return f"{self.full_name} (Velocity: {self.velocity})"

    def __repr__(self) -> str:
        return (
            f"Note(on={self.on}, "
            f"number={self.number}, "
            f"time={self.time}, "
            f"track={repr(self.track)}, "
            f"velocity={self.velocity}, "
            f"duration={self.duration})"
        )

    def __eq__(self, other):
        return (
            isinstance(other, Note)
            and self.on == other.on
            and self.number == other.number
            and self.time == other.time
            and self.channel == other.channel
        )

    # Sorting off notes before on notes prevents an unintended staccato effect
    # where a note is played and then immediately stopped by the off event for
    # a note of the same pitch ending at the same time
    # (e.g. 2 back-to-back quarter notes of the same pitch)

    def __lt__(self, other):
        if (
            isinstance(other, Note)
            and self.time == other.time
            and self.number == other.number
        ):
            return not self.on and other.on
        return super().__lt__(other)

    def __gt__(self, other):
        if (
            isinstance(other, Note)
            and self.time == other.time
            and self.number == other.number
        ):
            return self.on and not other.on
        return super().__gt__(other)


class MessageEvent(SongEvent):
    def __init__(self, time, message, track=None):
        super().__init__(time, track)
        self.message = message

    def to_message(self, delta):
        self.message.time = delta
        if self.track is not None:
            self.message.channel = self.track.channel
        return self.message

    def __repr__(self):
        return (
            f"MessageEvent(time={self.time}, "
            f"message={self.message}, "
            f"track={self.track})"
        )


def events_by_track(events):
    tracks = {}
    for event in events:
        if event.track is not None:
            if event.track not in tracks:
                tracks[event.track] = []
            tracks[event.track].append(event)
    return tracks


def events_to_messages(events) -> Message:
    messages = []
    last_time = 0
    for event in events:
        delta = event.time - last_time
        if isinstance(event, (Note, MessageEvent)):
            messages.append(event.to_message(delta))
        last_time = event.time
    return messages


class Song:
    def __init__(
        self,
        midi_file: Optional[str] = None,
        player: Optional[Player] = None,
        ticks_per_beat: Optional[int] = None,
        cols_per_beat: int = DEFAULT_COLS_PER_BEAT,
        beats_per_measure: int = DEFAULT_BEATS_PER_MEASURE,
        key: int = DEFAULT_KEY,
        scale_name: str = DEFAULT_SCALE_NAME,
    ):
        self.events = []
        self.tracks = []

        if ticks_per_beat is None:
            self.ticks_per_beat = DEFAULT_TICKS_PER_BEAT
        else:
            self.ticks_per_beat = ticks_per_beat

        if midi_file is not None:
            self.import_midi(midi_file, player)
        else:
            self.create_track(player=player)

        self.cols_per_beat = cols_per_beat
        self.beats_per_measure = beats_per_measure
        self.key = key
        self.scale_name = scale_name

        self.dirty = True

    @property
    def key_name(self) -> str:
        return COMMON_NAMES[self.key]

    @property
    def scale(self) -> tuple[int, ...]:
        return SCALES[self.scale_name]

    @property
    def events_by_track(self) -> list[SongEvent]:
        return events_by_track(self.events)

    @property
    def start(self) -> int:
        return self[0].time if len(self.events) > 0 else 0

    @property
    def end(self) -> int:
        return self[-1].time if len(self.events) > 0 else 0

    def ticks_to_beats(self, ticks: int) -> int:
        return ticks // self.ticks_per_beat

    def beats_to_ticks(self, beats: int) -> int:
        return beats * self.ticks_per_beat

    def ticks_to_cols(self, ticks: int) -> int:
        return int(ticks / self.ticks_per_beat * self.cols_per_beat)

    def cols_to_ticks(self, cols: int) -> int:
        return int(cols / self.cols_per_beat * self.ticks_per_beat)

    def add_note(self, note: Note, pair: bool = True) -> None:
        index = bisect_left(self.events, note)
        if (
            0 <= index < len(self)
            and self[index] == note
            and (not pair or self[index].pair == note.pair)
        ):
            raise ValueError("Note {note} is already in the song")
        self.events.insert(index, note)
        if pair:
            if note.pair is None:
                raise ValueError("Note {note} is unpaired")
            insort(self.events, note.pair)
        self.dirty = True

    def remove_note(
        self, note: Note, pair: bool = True, lookup: bool = False
    ) -> None:
        # Get the song note rather than the given note, since externally
        # created notes may have different pairs
        if lookup:
            note = self[self.events.index(note)]
        self.events.remove(note)
        if pair:
            if note.pair is None:
                raise ValueError("Note {song_note} is unpaired")
            self.events.remove(note.pair)
        self.dirty = True

    def move_note(self, note: Note, time: int) -> None:
        self.remove_note(note)
        note.move(time)
        self.add_note(note)

    def set_duration(self, note: Note, duration: int) -> None:
        self.remove_note(note)
        note.set_duration(duration)
        self.add_note(note)

    def get_index(
        self,
        time: int,
        track: Optional[Track] = None,
        note: bool = False,
        on: bool = False,
    ) -> int:
        dummy_track = track if track is not None else self.tracks[0]
        dummy_note = BaseNote(time, dummy_track)
        index = bisect_left(self, dummy_note)  # type: ignore
        if not 0 <= index < len(self) or time != self[index].time:
            return len(self)
        while (
            index < len(self)
            and self[index].time == time
            and (
                (note and not isinstance(self[index], Note))
                or (track is not None and self[index].track is not track)
                or (
                    on
                    and not (isinstance(self[index], Note) and self[index].on)
                )
            )
        ):
            index += 1
        return index

    def get_previous_index(
        self,
        time: int,
        track: Optional[Track] = None,
        note: bool = False,
        on: bool = False,
    ) -> int:
        dummy_track = track if track is not None else self.tracks[0]
        dummy_note = BaseNote(time, dummy_track)
        index = bisect_left(self, dummy_note) - 1  # type: ignore
        if not 0 <= index < len(self) or time < self[index].time:
            return len(self)
        while index >= 0 and (
            (note and not isinstance(self[index], Note))
            or (track is not None and self[index].track is not track)
            or (on and not (isinstance(self[index], Note) and self[index].on))
        ):
            index -= 1
        return index

    def get_next_index(
        self,
        time: int,
        track: Optional[Track] = None,
        note: bool = False,
        on: bool = False,
        inclusive: bool = True,
    ) -> int:
        time = max(time, 0)
        dummy_track = track if track is not None else self.tracks[0]
        if inclusive:
            dummy_note = BaseNote(time, dummy_track)
            index = bisect_left(self, dummy_note)  # type: ignore
        else:
            dummy_note = BaseNote(time, dummy_track, number=TOTAL_NOTES)
            index = bisect_right(self, dummy_note)  # type: ignore
        if not 0 <= index < len(self) or time > self[index].time:
            return len(self)
        while index < len(self) and (
            (note and not isinstance(self[index], Note))
            or (track is not None and self[index].track is not track)
            or (on and not (isinstance(self[index], Note) and self[index].on))
        ):
            index += 1
        return index

    def get_note(
        self,
        time: int,
        track: Optional[Track] = None,
        on: bool = False,
    ) -> Optional[Note]:
        index = self.get_index(time, track, note=True, on=on)
        return self[index] if 0 <= index < len(self) else None

    def get_previous_note(
        self, time: int, track: Optional[Track] = None, on: bool = False
    ) -> Optional[Note]:
        index = self.get_previous_index(time, track, note=True, on=on)
        return self[index] if index >= 0 else None

    def get_next_note(
        self,
        time: int,
        track: Optional[Track] = None,
        on: bool = False,
        inclusive: bool = True,
    ) -> Optional[Note]:
        index = self.get_next_index(
            time,
            track,
            note=True,
            on=on,
            inclusive=inclusive,
        )
        return self[index] if index < len(self) else None

    def get_chord(self, time: int, track: Optional[Track] = None) -> list[Note]:
        index = self.get_index(time, track, on=True)
        if not 0 <= index < len(self):
            return []
        chord_time = self[index].time
        chord = [self[index]]
        index += 1
        while index < len(self) and self[index].time == chord_time:
            if (
                isinstance(self[index], Note)
                and self[index].on
                and (track is None or self[index].track is track)
            ):
                chord.append(self[index])
            index += 1
        return chord

    def get_previous_chord(
        self, time: int, track: Optional[Track] = None
    ) -> list[Note]:
        index = self.get_previous_index(time, track, on=True)
        if not 0 <= index < len(self):
            return []
        chord_time = self[index].time
        chord = [self[index]]
        index -= 1
        while index >= 0 and self[index].time == chord_time:
            if (
                isinstance(self[index], Note)
                and self[index].on
                and (track is None or self[index].track is track)
            ):
                chord.append(self[index])
            index -= 1
        return chord

    def get_next_chord(
        self, time: int, track: Optional[Track] = None, inclusive: bool = True
    ) -> list[Note]:
        index = self.get_next_index(time, track, on=True, inclusive=inclusive)
        if not 0 <= index < len(self):
            return []
        chord_time = self[index].time
        chord = [self[index]]
        index += 1
        while index < len(self) and self[index].time == chord_time:
            if (
                isinstance(self[index], Note)
                and self[index].on
                and (track is None or self[index].track is track)
            ):
                chord.append(self[index])
            index += 1
        return chord

    def get_events_in_track(self, track: Track, notes: bool = False):
        events = []
        for event in self.events:
            if event.track is track and (not notes or isinstance(event, Note)):
                events.append(event)
        return events

    def has_channel(self, channel: int) -> bool:
        for track in self.tracks:
            if track.channel == channel:
                return True
        return False

    def get_open_channel(self) -> int:
        channels = set()
        for track in self.tracks:
            channels.add(track.channel)
        channel = 0
        while channel in channels or channel == DRUM_CHANNEL:
            channel += 1
        return channel

    def create_track(
        self,
        channel: Optional[int] = None,
        instrument: int = DEFAULT_INSTRUMENT,
        player: Optional[Player] = None,
    ) -> Track:
        if channel is None:
            channel = self.get_open_channel()
        track = Track(channel, instrument)
        track.set_instrument(instrument, player)
        self.tracks.append(track)
        self.dirty = True
        return track

    def get_track(
        self,
        channel: int,
        create: bool = True,
        instrument: int = DEFAULT_INSTRUMENT,
        player: Optional[Player] = None,
    ) -> Optional[Track]:
        for track in self.tracks:
            if track.channel == channel:
                return track
        if create:
            return self.create_track(channel, instrument, player)
        return None

    def delete_track(self, track: Track) -> None:
        i = 0
        while i < len(self.events):
            if self[i].track is track:
                self.events.pop(i)
            else:
                i += 1
        self.tracks.remove(track)

    def import_midi(self, infile_path: str, player: Optional[Player] = None):
        if not IMPORT_MIDO:
            raise ValueError(
                "mido is required to import MIDI files (pip install mido)"
            )
        infile = MidiFile(infile_path)
        self.ticks_per_beat = infile.ticks_per_beat

        events: list[SongEvent] = []
        active_notes: list[Note] = []
        for track in infile.tracks:
            time = 0
            for message in track:
                time += message.time
                if message.type == "note_on" and message.velocity > 0:
                    track = self.get_track(
                        message.channel, create=True, player=player
                    )
                    assert track is not None
                    active_notes.append(
                        Note(
                            on=True,
                            number=message.note,
                            time=time,
                            velocity=message.velocity,
                            track=track,
                        )
                    )
                elif message.type == "note_off" or (
                    message.type == "note_on" and message.velocity == 0
                ):
                    for note in active_notes.copy():
                        if note.number == message.note:
                            duration = time - note.time
                            note.set_duration(duration)
                            events.append(note)
                            assert note.pair is not None
                            events.append(note.pair)
                            active_notes.remove(note)
                            break
                elif message.type == "program_change":
                    track = self.get_track(
                        message.channel, create=True, player=player
                    )
                    track.set_instrument(message.program, player)
                elif message.type in ("pitchwheel", "control_change"):
                    track = self.get_track(
                        message.channel, create=True, player=player
                    )
                    events.append(MessageEvent(time, message, track))
                elif message.type == "set_tempo":
                    events.append(MessageEvent(time, message))

        self.events = sorted(events)
        self.dirty = True

    def export_midi(self, filename):
        if not IMPORT_MIDO:
            raise ValueError(
                "mido is required to export MIDI files (pip install mido)"
            )

        outfile = MidiFile(ticks_per_beat=self.ticks_per_beat)

        for track, events in self.events_by_track.items():
            midi_track = MidiTrack()
            midi_track.append(
                Message(
                    "program_change",
                    channel=track.channel,
                    program=track.instrument,
                )
            )
            for message in events_to_messages(events):
                midi_track.append(message)
            outfile.tracks.append(midi_track)

        outfile.save(filename)

    def __len__(self):
        return len(self.events)

    def __getitem__(self, key):
        return self.events[key]

    def __contains__(self, item):
        return item in self.events
