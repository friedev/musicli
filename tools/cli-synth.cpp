#include "MidiFile.h"
#include "Options.h"
#include <iostream>
#include <ncurses.h>
#include <stdio.h>
#include <ctype.h>
#include <vector>

using namespace std;
using namespace smf;

int chToPitch(int ch) {
	// 12 notes per octave
	switch (ch) {
		case 'z': return 48; // C3
		case 's': return 49; // C#3
		case 'x': return 50; // D3
		case 'd': return 51; // D#3
		case 'c': return 52; // E3
		case 'v': return 53; // F3
		case 'g': return 54; // F#3
		case 'b': return 55; // G3
		case 'h': return 56; // G#3
		case 'n': return 57; // A3
		case 'j': return 58; // A#3
		case 'm': return 59; // B3
		case 'q': return 60; // C4
		case '2': return 61; // C#4
		case 'w': return 62; // D4
		case '3': return 63; // D#4
		case 'e': return 64; // E4
		case 'r': return 65; // F4
		case '5': return 66; // F#4
		case 't': return 67; // G4
		case '6': return 68; // G#4
		case 'y': return 69; // A4
		case '7': return 70; // A#4
		case 'u': return 71; // B4
		case 'i': return 72; // C5
		case '9': return 73; // C#5
		case 'o': return 74; // D5
		case '0': return 75; // D#5
		case 'p': return 76; // E5
		default: return 0; // C0
	}
}

char* chToNote(int ch) {
	// 12 notes per octave
	switch (ch) {
		case 'z': return "C3 ";
		case 's': return "C#3";
		case 'x': return "D3 ";
		case 'd': return "D#3";
		case 'c': return "E3 ";
		case 'v': return "F3 ";
		case 'g': return "F#3";
		case 'b': return "G3 ";
		case 'h': return "G#3";
		case 'n': return "A3 ";
		case 'j': return "A#3";
		case 'm': return "B3 ";
		case 'q': return "C4 ";
		case '2': return "C#4";
		case 'w': return "D4 ";
		case '3': return "D#4";
		case 'e': return "E4 ";
		case 'r': return "F4 ";
		case '5': return "F#4";
		case 't': return "G4 ";
		case '6': return "G#4";
		case 'y': return "A4 ";
		case '7': return "A#4";
		case 'u': return "B4 ";
		case 'i': return "C5 ";
		case '9': return "C#5";
		case 'o': return "D5 ";
		case '0': return "D#5";
		case 'p': return "E5 ";
		case ' ': return "---";
		default: return "C0 ";
	}
}

int chToDrumPitch(int ch) {
	// Drums: https://soundprogramming.net/file-formats/general-midi-drum-note-numbers/
	switch (ch) {
		case 'q': return 36; // Bass Drum 1
		case 'w': return 38; // Snare Drum 1
		case 'e': return 43; // Low Tom 1
		case 'r': return 47; // Mid Tom 1
		case 't': return 50; // High Tom 1
		case 'y': return 42; // Closed Hi-hat
		case 'u': return 46; // Open Hi-hat
		case 'i': return 49; // Crash Cymbal 1
		case 'o': return 51; // Ride Cymbal 1
		case 'p': return 39; // Hand Clap
		default: return 0;
	}
}

char* chToDrumNote(int ch) {
	// Drums: https://soundprogramming.net/file-formats/general-midi-drum-note-numbers/
	switch (ch) {
		case 'q': return "BASS "; // Bass Drum 1
		case 'w': return "SNARE"; // Snare Drum 1
		case 'e': return "L TOM"; // Low Tom 1
		case 'r': return "M TOM"; // Mid Tom 1
		case 't': return "H TOM"; // High Tom 1
		case 'y': return "C HAT"; // Closed Hi-hat
		case 'u': return "O HAT"; // Open Hi-hat
		case 'i': return "C CYM"; // Crash Cymbal 1
		case 'o': return "R CYM"; // Ride Cymbal 1
		case 'p': return "CLAP "; // Hand Clap
		default: return "-----";
	}
}

void printNotes(vector<int> notes[], int currentNote, int channels, int currentChannel) {
	clear();
	int start = max(0, currentNote - getmaxy(stdscr) / 2);
	for (int i = start; i < start + getmaxy(stdscr); i++) {
		bool colorRow = has_colors() && i % 4 == 0;
		if (colorRow) {
			attron(COLOR_PAIR(1));
		}

		for (int channel = 0; channel < channels; channel++) {
			bool colorNote = i == currentNote && channel == currentChannel;
			if (colorNote) {
				attron(A_BOLD);
				if (has_colors()) {
					attron(COLOR_PAIR(2));
				}
			}

			char* output;
			if (channel == 9) {
				if (i < notes[channel].size()) {
					printw(" %s ", chToDrumNote(notes[channel][i]));
				} else {
					printw(" %s ", chToDrumNote(' '));
				}
			} else {
				if (i < notes[channel].size()) {
					printw(" %s ", chToNote(notes[channel][i]));
				} else {
					printw(" %s ", chToNote(' '));
				}
			}

			if (colorNote) {
				attroff(A_BOLD);
				if (has_colors()) {
					if (colorRow) {
						attron(COLOR_PAIR(1));
					} else {
						attroff(COLOR_PAIR(2));
					}
				}
			}

			if (colorRow && channel % 4 == 3 && has_colors()) {
				attroff(COLOR_PAIR(1));
			}

			if (channel < channels - 1) {
				printw("|");
			}

			if (colorRow && channel % 4 == 3 && has_colors()) {
				attron(COLOR_PAIR(1));
			}
		}
		printw("\n");

		if (colorRow) {
			attroff(COLOR_PAIR(1));
		}
	}
	refresh();
}

void exportMIDI(vector<int> notes[], int channels, Options& options, string filename, int (&instruments)[]) {
	MidiFile midifile;
	int tpq = midifile.getTPQ(); // Ticks per quarter note

	// INSTRUMENTS

	int track = midifile.addTrack();
	int prevKey = 0;
	for (int channel = 0; channel < 9; channel++) {
		int instrument = instruments[channel];
		midifile.addTimbre(track, 0, channel, instrument);
		for (int i = 0; i < notes[channel].size(); i++) {
			int startTick = int(i / 4.0 * tpq);

			if (notes[channel][i] == ' ') {
				if (i == notes[channel].size() - 1 && prevKey != 0) {
					midifile.addNoteOff(track, startTick + int(1.0 / 4.0 * tpq), channel, prevKey);
				}
				continue;
			}
			int key = chToPitch(notes[channel][i]);

			if (prevKey != 0) {
				midifile.addNoteOff(track, startTick, channel, prevKey);
			}
			midifile.addNoteOn(track, startTick, channel, key, 100);
			prevKey = key;
		}
	}

	// DRUMS

	vector<uchar> midievent; // temporary storage for MIDI events
	midievent.resize(3);     // set the size of the array to 3 bytes
	midievent[2] = 100;      // set the loudness to a constant value
	bool noteOn = false;
	int prevNote;
	int i = 0;
	int actionTime;
	track = midifile.addTrack();
	vector<int> drumNotes = notes[9];

	for (int i = 0; i < drumNotes.size(); i++) {
		if (noteOn) {
			// turn off previous note
			midievent[0] = 0x89;
			midievent[1] = prevNote;
			actionTime = int(i / 4.0 * tpq - 1);
			midifile.addEvent(track, actionTime, midievent);
		}
		// turn on current note
		midievent[0] = 0x99;
		midievent[1] = chToDrumPitch(drumNotes[i]);
		actionTime = int(i / 4.0 * tpq);
		midifile.addEvent(track, actionTime, midievent);
		noteOn = true;
		prevNote = chToDrumPitch(drumNotes[i]);
	}

	if (noteOn) {
		// turn off last note
		midievent[0] = 0x89;
		midievent[1] = prevNote;
		actionTime = int(i / 4 * tpq);
		midifile.addEvent(track, actionTime, midievent);
	}

	midifile.sortTracks();
	midifile.write(filename);
}

void playFile(string filename, string soundfont) {
	char command[100];
	sprintf(command, "fluidsynth -a alsa -m alsa_seq -liq %s %s 2>/dev/null", soundfont.c_str(), filename.c_str());
	system(command);
}

void playNote(int instrument, int key, string filename, string soundfont) {
	MidiFile midifile;
	int tpq = midifile.getTPQ();
	midifile.addTimbre(0, 0, 0, instrument);
	midifile.addNoteOn(0, 0, 0, key, 100);
	midifile.addNoteOff(0, int(1.0 * tpq), 0, key);
	midifile.write(filename);

	playFile(filename, soundfont);
}

int main(int argc, char** argv) {
	Options options;
	options.define("o|output=s:export.mid", "Output filename");
	options.define("i|instrument=i:0", "General MIDI instrument number");
	options.define("c|channels=i:10", "Number of MIDI channels");
	options.define("s|soundfont=s", "Soundfont to use");
	options.process(argc, argv);
	string filename = options.getString("output");
	string soundfont = options.getString("soundfont");

	// TODO read from arguments
	// Generic
	int instruments[] = {0, 0, 0, 0, 25, 25, 25, 25, 34, 34, 34, 34, 57, 57, 57, 57};
	// Rock
	//int instruments[] = {30, 30, 30, 30, 34, 34, 34, 34, 19, 19, 19, 19, 82, 82, 82, 82};
	// Electronic
	//int instruments[] = {81, 81, 81, 81, 82, 82, 82, 82, 39, 39, 39, 39, 91, 91, 91, 91};

	initscr();
	cbreak();
	keypad(stdscr, TRUE);
	noecho();

	if (has_colors()) {
		start_color();
		init_pair(1, COLOR_BLACK, COLOR_WHITE);
		init_pair(2, COLOR_YELLOW, COLOR_BLUE);
	}

	int channels = options.getInteger("channels");
	vector<int> notes[channels];
	for (int channel = 0; channel < channels; channel++) {
		notes[channel].push_back(' ');
	}

	int currentChannel = 0;
	int currentNote = 0;
	printNotes(notes, currentNote, channels, currentChannel);

	int ch;
	do {
		ch = getch();
		switch (ch) {
			case 'H':
			case KEY_LEFT:
				currentChannel = max(0, currentChannel - 1);
				break;
			case 'L':
			case KEY_RIGHT:
				currentChannel = min(channels - 1, currentChannel + 1);
				break;
			case 'K':
			case KEY_UP:
				currentNote = max(0, currentNote - 1);
				break;
			case 'J':
			case KEY_DOWN:
				if (currentNote == notes[currentChannel].size() - 1) {
					for (int c = 0; c < channels; c++) {
						notes[c].push_back(' ');
					}
				}
				currentNote = min((int) notes[currentChannel].size() - 1, currentNote + 1);
				break;
			case KEY_DC:
				if (currentNote < notes[currentChannel].size() - 2) {
					for (int c = 0; c < channels; c++) {
						notes[c].erase(notes[c].begin() + currentNote);
					}
					break;
				}
				// If on the last note, handle like a backspace
			case KEY_BACKSPACE:
				if (notes[currentChannel].size() > 1) {
					for (int c = 0; c < channels; c++) {
						notes[c].erase(notes[c].end() - 2);
					}
					currentNote = min(currentNote, (int) notes[currentChannel].size() - 1);
				} else if (notes[currentChannel].size() == 2) {
					for (int c = 0; c < currentChannel; c++) {
						notes[c][0] = ' ';
					}
				}
				break;
			case 'Q':
				// Do nothing
				break;
			case 'E':
				exportMIDI(notes, channels, options, filename, instruments);
				printw("Exported song to %s. Press any key to continue.", filename.c_str());
				getch();
				break;
			case 'P':
				exportMIDI(notes, channels, options, "tmp.mid", instruments);
				playFile("tmp.mid", soundfont);
				break;
			default:
				if ((currentChannel == 9 && chToDrumPitch(ch) == 0) || (currentChannel != 9 && chToPitch(ch) == 0)) {
					break;
				}
			case ' ':
				if (currentNote == notes[currentChannel].size() - 1) {
					for (int c = 0; c < channels; c++) {
						notes[c].push_back(' ');
					}
				}
				notes[currentChannel][currentNote] = ch;
				currentNote++;
				//playNote(0, chToPitch(ch), "soundfont.sf2", "tmp.mid");
		}
		printNotes(notes, currentNote, channels, currentChannel);
	} while (ch != 'Q');

	endwin();
	return 0;
}
