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
	switch (tolower(ch)) {
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
		default: return 48; // C3
	}
}

char* chToNote(int ch) {
	// 12 notes per octave
	switch (tolower(ch)) {
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
		default: return "C3";
	}
}

void printNotes(vector<int> notes[], int currentNote, int channels, int currentChannel) {
	clear();
	printw("Type notes and press Enter when done\n");
	for (int i = 0; i < notes[0].size(); i++) {
		for (int channel = 0; channel < channels; channel++) {
			if (i == currentNote && channel == currentChannel) {
				attron(A_BOLD);
			}
			printw("%s", chToNote(notes[channel][i]));
			attroff(A_BOLD);
			if (channel < channels - 1) {
				printw(" | ");
			}
		}
		printw("\n");
	}
	refresh();
}

int main(int argc, char** argv) {
	Options options;
	options.define("o|output-file=s", "Output filename (stdout if none)");
	options.define("i|instrument=i:0", "General MIDI instrument number");
	options.define("x|hex=b", "Hex byte-code output");
	options.process(argc, argv);

	initscr();
	cbreak();
	keypad(stdscr, TRUE);
	noecho();

	int channels = 4;
	vector<int> notes[channels];
	int channel = 0;
	int currentNote = 0;
	int ch;
	do {
		// TODO allow inserting notes, possibly with Shift+(Note)
		ch = getch();
		switch (ch) {
			case 'h':
			case KEY_LEFT:
				channel = max(0, channel - 1);
				break;
			case 'l':
			case KEY_RIGHT:
				channel = min(channels - 1, channel + 1);
				break;
			case 'k':
			case KEY_UP:
				currentNote = max(0, currentNote - 1);
				break;
			case 'j':
			case KEY_DOWN:
				currentNote = min((int) notes[channel].size(), currentNote + 1);
				break;
			case KEY_DC:
				if (currentNote < notes[channel].size()) {
					notes[channel].erase(notes[channel].begin() + currentNote);
					break;
				}
				// If on the last note, handle like a backspace
			case KEY_BACKSPACE:
				if (notes[channel].size() > 0) {
					notes[channel].pop_back();
					currentNote = min(currentNote, (int) notes[channel].size());
				}
				break;
			case '\n':
				break;
			default:
				if (currentNote == notes[channel].size()) {
					for (int c = 0; c < channels; c++) {
						notes[c].push_back(' ');
					}
				}
				notes[channel][currentNote] = ch;
				currentNote++;
				break;
		}
		printNotes(notes, currentNote, channels, channel);
	} while (ch != '\n');

	endwin();

	/*
	// Keeping original random code for reference on variable ranges
	random_device rd;
	mt19937 mt(rd());
	uniform_int_distribution<int> starttime(0, 100);
	uniform_int_distribution<int> duration(1, 8);
	uniform_int_distribution<int> pitch(36, 84);
	uniform_int_distribution<int> velocity(40, 100);
	*/

	MidiFile midifile;
	int track = 0;
	channel = 0;
	int instr = options.getInteger("instrument");
	midifile.addTimbre(track, 0, channel, instr);

	int tpq = midifile.getTPQ();
	int prevKey = 0;
	for (int channel = 0; channel < channels; channel++) {
		for (int i = 0; i < notes[channel].size(); i++) {
			int starttick = int(i / 4.0 * tpq);

			if (notes[channel][i] == ' ') {
				if (i == notes[channel].size() - 1 && prevKey != 0) {
					midifile.addNoteOff(track, starttick, channel, prevKey);
				}
				continue;
			}
			int key = chToPitch(notes[channel][i]);

			if (prevKey != 0) {
				midifile.addNoteOff(track, starttick, channel, prevKey);
			}
			midifile.addNoteOn (track, starttick, channel, key, 100);
			if (i == notes[channel].size() - 1) {
				midifile.addNoteOff(track, starttick + int(4.0 * tpq), channel, key);
			}
			prevKey = key;
		}
	}

	// Need to sort tracks since added events are appended to track in random tick order.
	midifile.sortTracks();
	string filename = options.getString("output-file");
	if (filename.empty()) {
		if (options.getBoolean("hex")) {
			midifile.writeHex(cout);
		} else {
			cout << midifile;
		}
	} else {
		midifile.write(filename);
	}

	return 0;
}
