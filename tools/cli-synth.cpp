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
		case 'q': return "C4";
		case '2': return "C#4";
		case 'w': return "D4";
		case '3': return "D#4";
		case 'e': return "E4";
		case 'r': return "F4";
		case '5': return "F#4";
		case 't': return "G4";
		case '6': return "G#4";
		case 'y': return "A4";
		case '7': return "A#4";
		case 'u': return "B4";
		case 'i': return "C5";
		case '9': return "C#5";
		case 'o': return "D5";
		case '0': return "D#5";
		case 'p': return "E5";
		case ' ': return "--";
		default: return "C3";
	}
}

void printNotes(vector<int> notes, int currentNote) {
	clear();
	printw("Type notes and press Enter when done\n");
	for (int i = 0; i < notes.size(); i++) {
		if (i == currentNote) {
			attron(A_BOLD);
		}
		printw("%s\n", chToNote(notes[i]));
		attroff(A_BOLD);
	}
	refresh();
}

int main(int argc, char** argv) {
	Options options;
	options.define("o|output-file=s", "Output filename (stdout if none)");
	options.define("i|instrument=i:0", "General MIDI instrument number");
	options.define("x|hex=b", "Hex byte-code output");
	options.process(argc, argv);

	// Curses demo from https://tldp.org/HOWTO/NCURSES-Programming-HOWTO/init.html
	initscr();
	cbreak();
	keypad(stdscr, TRUE);
	noecho();

	//int ch[noteCount];
	vector<int> notes;
	int ch;
	int currentNote = 0;
	do {
		ch= getch();
		switch (ch) {
			case KEY_UP:
				currentNote = max(0, currentNote - 1);
				break;
			case KEY_DOWN:
				currentNote = min((int) notes.size(), currentNote + 1);
				break;
			case KEY_DC:
				if (currentNote < notes.size()) {
					notes.erase(notes.begin() + currentNote);
					break;
				}
				// If on the last note, handle like a backspace
			case KEY_BACKSPACE:
				if (notes.size() > 0) {
					notes.pop_back();
					currentNote = min(currentNote, (int) notes.size());
				}
				break;
			case '\n':
				break;
			default:
				if (currentNote == notes.size()) {
					notes.push_back(ch);
				} else {
					notes[currentNote] = ch;
				}
				currentNote++;
				break;
		}
		printNotes(notes, currentNote);
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
	int channel = 0;
	int instr = options.getInteger("instrument");
	midifile.addTimbre(track, 0, channel, instr);

	int tpq = midifile.getTPQ();
	int prevKey = 0;
	for (int i = 0; i < notes.size(); i++) {
		if (notes[i] == ' ') {
			continue;
		}
		int key = chToPitch(notes[i]);

		int starttick = int(i / 4.0 * tpq);
		if (prevKey != 0) {
			midifile.addNoteOff(track, starttick, channel, prevKey);
		}
		midifile.addNoteOn (track, starttick, channel, key, 100);
		if (i == notes.size() - 1) {
			midifile.addNoteOff(track, starttick + int(4.0 * tpq), channel, key);
		}
		prevKey = key;
		// FIXME there may be some weirdness if the last note is a rest
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
