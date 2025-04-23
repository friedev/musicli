# MusiCLI

MusiCLI (pronounced "musically") is a MIDI sequencer that runs entirely in the terminal.

## Features

Implemented:

- Piano roll interface
- Basic modal editing
- Importing and exporting MIDI files
- Live playback via SF2 soundfonts
- Multiple tracks and instruments

Not yet implemented:

- Support for all MIDI messages (some MIDI files may play back as expected)
- MIDI input/output ports
- Mouse support
- Real-time input recording
- Detection of non-General MIDI soundfonts

## Setup

Dependencies:

- Python 3
- curses
- [mido](https://github.com/mido/mido) (optional; required for MIDI import/export)
- [FluidSynth](https://fluidsynth.org) (optional; required for playback)
- [pyFluidSynth](https://github.com/nwhitehead/pyfluidsynth) (optional; required for playback)

To install FluidSynth on your device, see [Getting FluidSynth](https://www.fluidsynth.org/download/).

Then, you can install MusiCLI from PyPI:

```sh
pip install musicli-sequencer
```

For live playback, you will need a soundfont in SF2 format.
Only General MIDI soundfonts are explicitly supported, but others may work.
I recommend the MuseScore General Soundfont, which can be freely downloaded from the [MuseScore handbook](https://musescore.org/en/handbook/3/soundfonts-and-sfz-files) along with other soundfonts.

## Usage

To run MusiCLI:

```sh
musicli file.mid --soundfont=soundfont.sf2
```

Providing a MIDI file to open is optional.
Providing an existing MIDI file will import it, while providing a nonexistent file will cause it to be created upon saving.
You may also provide no file; if you choose to save later, it will be saved as `untitled.mid`.

If you wish to import a MIDI file, but save changes to another file, use the `--import` or `-i` option:

```sh
musicli file_to_export.mid --import=file_to_import.mid --soundfont=soundfont.sf2
```

Providing a soundfont with `--soundfont` or `-f` is also optional, but live playback will be unavailable unless you do.
If no soundfont is provided, MusiCLI will look for one at `/usr/share/soundfonts/default.sf2`, which is FluidSynth's default location.

Much more song-specific information can be customized via other command line arguments.
View a full list by running:

```sh
musicli --help
```

### Keybindings

**For a full list of editor keybindings, run:**

```sh
musicli --keymap
```

### Interface

MusiCLI provides a piano roll interface that should be familiar to users of modern DAWs.

Each line represents a different pitch, labeled with its note name on the left of the UI.
Further left is the key you can type to enter that note while in insert mode (more on that later).
The dots on some rows correspond to the notes in the current key and scale you are using.
By default, this is C Major, but you can change it with the `--key` and `--scale` arguments.

Each character column represents a subdivision of a beat.
By default, this is a 16th note, but this can be customized with the `--cols-per-beat` argument.
Each beat is marked with a dot, and each measure is marked with a line.
The length of each measure can be customized with `--beats-per-measure` flag.

Each note is represented by a colored rectangle that occupies one pitch but may span multiple beats.
Longer notes are labeled with their note name for convenience.
The last note entered is highlighted in white, and the notes in the last chord entered are highlighted in gray (if available, otherwise white as well).
The color of the note represents which MIDI track it is on.
Notes may overlap, including notes from different tracks.
Currently, instruments cannot be changed while in the editor, but better support for instruments (including drums) is planned with a high priority.

The thin white vertical line is the cursor, which shows where you are currently editing notes.
The thicker white vertical line is the playhead, which is where playback is currently playing or stopped.

The editor scrolls infinitely horizontally, and a limited amount vertically, encompassing the full range of MIDI notes.

### Editing

MusiCLI is a modal editor, like vi, which means that the editor has different modes in which keys do different actions.

The default mode is normal mode, which allows you to navigate freely and use more special commands.

You can enter insert mode by pressing `i`.
Insert mode allows you to insert notes into your song directly by typing them on the keyboard.
You may always return to normal mode by pressing Escape.

In insert mode, the keys are laid out like two rows of a piano, with the `z` and `a` rows forming the lower set of white and black keys respectively, and the `q` and number rows forming the higher octave set.
This is a feature available in DAWs that support keyboard input, such as [LMMS](https://lmms.io), and is intended to be at least marginally familiar to pianists.
For quick reference, the keys that correspond to each note are listed to the left of them on the left sidebar.

To change where you are editing, use the arrow keys.
Left and right will change the beat you are entering, and up and down will change the octave range.
In normal mode, you can pan around without changing where you're editing by using the vi keys `hjkl`.
Pressing Shift along with the vi keys will cause you to pan a shorter distance.

Many operations will affect the last note or chord you inserted.
These notes are highlighted in white and gray respectively.

## Troubleshooting

> The color gray isn't showing up and every note in the selected chord is white.

Your terminal probably does not have gray as color 8.
You may be able to change this in your terminal's color scheme settings.

Terminals known to support gray include [Alacritty](https://alacritty.org) and [foot](https://codeberg.org/dnkl/foot).
Terminals known not to support gray include [cool-retro-term](https://github.com/Swordfish90/cool-retro-term).
[pywal](https://github.com/dylanaraps/pywal) is also compatible.

> MusiCLI just crashed.
> What do I do?

A `crash.log` file should have been generated (or a different file if you set the `--crash-file` option).
If not, there may be some output directly in the terminal.
In any case, please submit an issue on GitHub with the contents of the file or the error messages in the terminal, and a description of what you were doing right before the crash happened.
This will help get the issue resolved as soon as possible!

If MusiCLI didn't crash, but playback stopped working and you got a bunch of text appearing in weird places on the screen, the FluidSynth thread probably crashed.
Currently, getting the error messages out of a failure like this are challenging, so just try to copy/paste or screenshot what you can of the error messages that appeared on screen.

## Contributing

Before submitting a patch, run [Black](https://black.readthedocs.io) to format your code.
Strongly consider running other linters as well, such as [pylint](https://pylint.org), [flake8](https://flake8.pycqa.org), and [mypy](https://www.mypy-lang.org).
