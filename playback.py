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

import sys
from threading import Event
from time import sleep

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
    def __init__(self, soundfont):
        self.synth = Synth()
        self.synth.start()
        self.soundfont = self.synth.sfload(soundfont)

        self.playhead = 0
        self.restart_time = 0

    @property
    def playing(self):
        return PLAY_EVENT.is_set()

    def stop_note(self, note):
        self.synth.noteoff(note.channel, note.number)

    def play_note(self, note):
        if note.on:
            self.synth.noteon(note.channel, note.number, note.net_velocity)
        else:
            self.stop_note(note)

    def set_instrument(self, channel, bank, instrument):
        self.synth.program_select(channel, self.soundfont, bank, instrument)

    def play_song(self, song):
        while True:
            if RESTART_EVENT.is_set():
                RESTART_EVENT.clear()

            PLAY_EVENT.wait()
            if KILL_EVENT.is_set():
                sys.exit(0)

            if len(song) == 0:
                PLAY_EVENT.clear()
                continue

            self.playhead = self.restart_time
            next_unit_time = (self.playhead -
                              (self.playhead % song.cols_to_ticks(1)) +
                              song.cols_to_ticks(1))
            note_index = song.get_next_index(self.playhead, inclusive=True)
            next_note = song[note_index]
            active_notes = []
            while note_index < len(song):
                delta = min(next_unit_time, next_note.time) - self.playhead
                sleep(delta / song.ticks_per_beat / song.bpm * 60.0)

                self.playhead += delta

                if self.playhead == next_unit_time:
                    next_unit_time += song.cols_to_ticks(1)
                    note_index = song.get_next_index(self.playhead)
                    next_note = song[note_index]

                if not PLAY_EVENT.is_set():
                    for note in active_notes:
                        self.stop_note(note)
                    PLAY_EVENT.wait()
                if RESTART_EVENT.is_set():
                    break
                if KILL_EVENT.is_set():
                    sys.exit(0)

                while (note_index < len(song) and
                       self.playhead == next_note.time):
                    if next_note.on:
                        active_notes.append(next_note)
                    elif next_note.pair in active_notes:
                        active_notes.remove(next_note.pair)
                    self.play_note(next_note)
                    note_index += 1
                    if note_index < len(song):
                        next_note = song[note_index]

            for note in active_notes:
                self.stop_note(note)
