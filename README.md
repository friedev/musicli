# MusiCLI

MusiCLI (pronounced "musically") is a simple, tracker-like, MIDI sequencer that runs entirely in the terminal, developed by Aaron Friesen and David Ryan for [CornHacks 2021](https://cornhacks.com).

MusiCLI is built upon great [Midifile](https://midifile.sapp.org) library by Craig Sapp.

## Dependencies

- gcc
- GNU Make
- Midifile
- ncurses
- FluidSynth (optional) - for playing MIDI files from within the editor

## Compiling

To compile MusiCLI, first install all required dependencies, except Midifile, which comes bundled with the repo (as recommended in the Midifile README). Then, clone the repo and run `make`.

If you want to use FluidSynth for live playback, you will also need a Soundfont in SF2 format (for some free Soundfonts, see the [MuseScore handbook](https://musescore.org/en/handbook/3/soundfonts-and-sfz-files)).

## Usage

To run MusiCLI from the root directory of the repo, run `./bin/musicli`.

### Command Line Arguments

```
-o, --output=[file]     Output filename              (default: export.mid)
-c, --channels=[int]    Number of MIDI channels      (default: 10)
-s, --soundfont=[file]  Soundfont to use             (default: `/usr/share/soundfonts/default.sf2` (FluidSynth default))
-l, --linenumbers       Enable line numbers          (default: false)
-m, --measure=[int]     Number of beats per measure  (default: 4)
```

For a full list of command line arguments, run `./bin/musicli -h` (or any other invalid flag), or refer to `main()` in `tools/musicli.cpp`.

### Editor

The MusiCLI editor is organized into rows and columns.

Each row represents a beat, or a subdivision of a beat. By default, each row corresponds to a 16th note. Rows highlighted in white or yellow represent quarter notes. Rows highlighted in yellow represent the first beat of a measure.

Each column represents a channel. By default, the channels are in groups of 4, and each group corresponds to an instrument. This allows you to have an instrument play multiple notes at the same time (i.e. chords). Currently, the 10th column is reserved for drums.

Each cell represents a note. Dashes represent the absence of a note (a rest), while a note name, such as `C4`, indicates the presence of that note. A cell in a drum channel corresponds to a drum hit, with different drums instead of different note pitches. These drums are indicated with a text label; for the meanings of each label, refer to `chToDrumNote()` in `tools/musicli.cpp`.

For now, notes are sustained until the next note is played or until the song ends. For this reason, it is recommended to use instruments whose sounds decay naturally over time, such as a piano or guitar, or whose sounds are intended to be sustained as part of a background chord.

### Keybindings

In MusiCLI, the keys of the keyboard correspond to the keys of a piano. If you have used DAWs or other music software that accepts keyboard input, you are probably already familiar with this concept. The rows starting `qwe` and `zxc` correspond to the white keys of piano, with `q` being `C4` and `z` being `C3`. The number row and the row starting with `asd` correspond to the black keys of a piano, with `2` being `C#4` and `s` being `C#3`. For the full mapping of keys to notes, see `chToNote()` in `tools/musicli.cpp`.

Note that all the following keybindings are capitalized. If you wish to emulate a modal editor, you can press caps lock and all your inputs will be interpreted as commands rather than notes.

```
Arrows/HJKL: Move the selection
      Space: Insert a rest
          I: Insert an empty row, shifting the current row and lower rows down
     Delete: Delete the current row across ALL channels, shifting lower rows up
  Backspace: Delete the previous across ALL channels, shifting the current row and lower rows up
          E: Export the song to the output file (set with -o)
          P: Play the song without leaving the editor (requires FluidSynth and a Soundfont)
          Q: Exit MusiCLI
```

For more detailed keybinding information, refer to `main()` in `tools/musicli.cpp`.

## Contributing

MusiCLI is a small project initially developed during a hackathon, so be warned that it is not fully polished and documented yet. Nonetheless, if you are interested in submitting PRs, we will be happy to review them!

If you want to submit a PR, please follow these guidelines:

- Run the editor to check for bugs.
- Copy the license notice from `tools/musicli.cpp` into any new C or C++ files you create.
- Avoid introducing any new compiler warnings if at all possible.

If you want to contribute but aren't sure what to work on, you can find a list of tasks in `TODO.md`.
