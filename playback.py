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

# Global thread events
PLAY_EVENT = Event()
RESTART_EVENT = Event()
KILL_EVENT = Event()


class Player:
    def __init__(self, synth, soundfont):
        self.synth = synth
        self.soundfont = soundfont
        self.playhead = 0

    @property
    def playing(self):
        return PLAY_EVENT.is_set()

    def stop_note(self, note):
        self.synth.noteoff(note.channel, note.number)

    def play_note(self, note):
        if note.on:
            self.synth.noteon(note.channel, note.number, note.velocity)
        else:
            self.stop_note(note)

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

            note_index = 0
            self.playhead = 0
            next_unit_time = song.cols_to_ticks(1)
            next_note = song[note_index]
            while note_index < len(song):
                delta = min(next_unit_time, next_note.time) - self.playhead
                sleep(delta /
                      song.ticks_per_beat /
                      song.bpm *
                      60.0)

                self.playhead += delta

                if self.playhead == next_unit_time:
                    next_unit_time += song.cols_to_ticks(1)
                    note_index = song.get_next_index(self.playhead)
                    next_note = song[note_index]

                PLAY_EVENT.wait()
                if RESTART_EVENT.is_set():
                    break
                if KILL_EVENT.is_set():
                    sys.exit(0)

                while (note_index < len(song) and
                       self.playhead == next_note.time):
                    self.play_note(next_note)
                    note_index += 1
                    if note_index < len(song):
                        next_note = song[note_index]
