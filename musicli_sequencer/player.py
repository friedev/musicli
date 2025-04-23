import sys
from threading import Event
from time import sleep
from traceback import format_exc

from mido import tempo2bpm

from .song import MessageEvent, Note, Song, DEFAULT_BPM

try:
    from fluidsynth import Synth

    IMPORT_FLUIDSYNTH = True
except ImportError:
    IMPORT_FLUIDSYNTH = False

# Global thread events
PLAY_EVENT = Event()
RESTART_EVENT = Event()
KILL_EVENT = Event()


class Player:
    synth: Synth
    soundfont: int
    playhead: int
    restart_time: int

    def __init__(self, soundfont: str):
        self.synth = Synth()
        self.synth.start()
        self.soundfont = self.synth.sfload(soundfont)

        self.playhead = 0
        self.restart_time = 0

    @property
    def playing(self) -> bool:
        return PLAY_EVENT.is_set()

    def stop_note(self, note: Note) -> None:
        self.synth.noteoff(note.channel, note.number)

    def play_note(self, note: Note) -> None:
        if note.on:
            self.synth.noteon(note.channel, note.number, note.velocity)
        else:
            self.stop_note(note)

    def set_instrument(self, channel: int, bank: int, instrument: int) -> None:
        self.synth.program_select(channel, self.soundfont, bank, instrument)

    def play_song(self, song: Song) -> None:
        while True:
            bpm = DEFAULT_BPM

            if RESTART_EVENT.is_set():
                RESTART_EVENT.clear()

            PLAY_EVENT.wait()
            if KILL_EVENT.is_set():
                sys.exit(0)

            if len(song) == 0:
                PLAY_EVENT.clear()
                continue

            song.dirty = False
            self.playhead = self.restart_time
            next_unit_time = (
                self.playhead
                - (self.playhead % song.cols_to_ticks(1))
                + song.cols_to_ticks(1)
            )
            event_index = song.get_next_index(self.playhead, inclusive=True)
            next_event = song[event_index]
            active_notes = []
            while event_index < len(song):
                delta = min(next_unit_time, next_event.time) - self.playhead
                sleep(delta / song.ticks_per_beat / bpm * 60.0)

                self.playhead += delta

                if self.playhead == next_unit_time:
                    next_unit_time += song.cols_to_ticks(1)

                if not PLAY_EVENT.is_set():
                    for note in active_notes:
                        self.stop_note(note)
                    PLAY_EVENT.wait()
                if RESTART_EVENT.is_set():
                    break
                if KILL_EVENT.is_set():
                    sys.exit(0)

                if song.dirty:
                    event_index = song.get_next_index(self.playhead)
                    if event_index >= len(song):
                        break
                    next_event = song[event_index]
                    song.dirty = False

                while (
                    event_index < len(song) and self.playhead == next_event.time
                ):
                    if isinstance(next_event, Note):
                        if next_event.on:
                            active_notes.append(next_event)
                        elif next_event.pair in active_notes:
                            active_notes.remove(next_event.pair)
                        self.play_note(next_event)
                    elif isinstance(next_event, MessageEvent):
                        if next_event.message.type == "pitchwheel":
                            self.synth.pitch_bend(
                                next_event.track.channel,
                                next_event.message.pitch,
                            )
                        elif next_event.message.type == "control_change":
                            self.synth.cc(
                                next_event.track.channel,
                                next_event.message.control,
                                next_event.message.value,
                            )
                        elif next_event.message.type == "set_tempo":
                            bpm = tempo2bpm(next_event.message.tempo)
                    event_index += 1
                    if event_index < len(song):
                        next_event = song[event_index]

            for note in active_notes:
                self.stop_note(note)

    def try_play_song(self, song, crash_file_path):
        try:
            self.play_song(song)
        except Exception:
            with open(crash_file_path, "w") as crash_file:
                crash_file.write(format_exc())
        finally:
            KILL_EVENT.set()
            sys.exit(1)
