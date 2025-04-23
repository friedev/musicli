# Changelog

### 2.1.0 (2025-04-22)

Features:

- Added support for multiple channels
- Added support for different MIDI instruments, with special support for drums
- Added support for importing and exporting meta messages
- Handle playback of the following meta messages:
	- `program_change`
	- `set_tempo`
	- `pitchwheel`
	- `control_change` (control 7 is interpreted as volume, per General MIDI standard)
- Added support for changing note velocities
- Automatically select chords under the cursor
- Identify selected chord and display on status bar
- Allow running the application with missing dependencies (the corresponding features will be disabled)

New key bindings:

- `0`: jump to beginning of song
- `^`: jump to beginning of song
- `$`: jump to end of song
- Page Up: jump to highest note
- Page Down: jump to lowest note
- Home: jump to beginning of song
- End: jump to end of song
- `a`: enter insert mode, advance one step
- `I`: enter insert mode, jump to the beginning of the song
- `A`: enter insert mode, jump to the end of the song
- `;`: decrease the velocity of the selected note
- `'`: increase the velocity of the selected note
- `:`: decrease the velocity of the selected chord
- `"`: increase the velocity of the selected chord
- `-`: switch to the previous track
- `=`: switch to the next track
- `_`: use the previous instrument on this channel
- `+`: use the next instrument on this channel
- `z`: toggle this channel between drums and regular instruments
- `f`: focus on the current track and hide others
- `t`: create a new track
- `T`: delete the current track
- `g`: restart playback from the editing cursor
- `G`: sync the cursor location to the playhead
- Tab: cycle through notes in the selected chord
- Backtick: deselect all notes (replacing duplicate keybind for "return to normal mode")
- Number: repeat the next action the given number of times

Improvements:

- Reduced delay after pressing escape to switch to normal mode
- Collapse status bar items to fit terminal width
- Fall back to system default soundfont at `/usr/share/soundfonts/default.sf2` (if available) when no soundfont is provided
- Hide playhead if playback is not possible (e.g. no soundfont was provided)
- Added "chromatic" scale
- Added "minor" scale (alias for "natural_minor")
- Replace underscores in scale name with spaces when displayed on the status bar

Fixes:

- Fixed a crash when attempting to change the selected note's start time when no note is selected
- Fixed a crash when a song is shortened such that the playhead is out of bounds
- Exit program when player thread crashes
- Fixed player not detecting changes to the song made while playback is ongoing
- Interpret `note_on` messages with 0 velocity as `note_off` messages
- Play notes with 0 duration

Packaging:

- Added flit config
- Published on PyPI

## 2.0.0 (2022-01-23)

MusiCLI has been rewritten from scratch in Python!
This rewrite was developed by Aaron Friesen for [CornHacks 2022](https://unlcornhacks.com), where it won third place overall.
The new version provides a piano roll interface, MIDI import and export via [mido](https://github.com/mido/mido), live non-blocking playback with [pyFluidSynth](https://github.com/nwhitehead/pyfluidsynth), and improved modal editing.

## 1.0.0 (2021-01-31)

Initial C++ version of MusiCLI, developed by Aaron Friesen and David Ryan for [CornHacks 2021](https://unlcornhacks.com).
It provides a tracker-like curses interface, MIDI export via [Midifile](https://midifile.sapp.org), and limited playback via [FluidSynth](https://fluidsynth.org).
