# Athany: a python application to remind you of your purpose

<br>

### قال تعالى: {وَمَا خَلَقْتُ الْجِنَّ وَالْإِنسَ إِلَّا لِيَعْبُدُونِ (56)} \[الذاريات]

<br>
 
#### Athany is a python program for windows and linux that fetches the times for the five mandatory muslim prayers, tells you the time remaining until the next prayer and plays the athan sound if the prayer time comes.
 
<br>
 
## Requirements
 
- Python3 (tested on python 3.10 & 3.11)

- `tk` tkinter package if you're on linux, install it using your package manager. If you can't find it, search how to install tkinter on your distro.

- `PySimpleGUI` python module

- `psgtray` python module

- `requests` python module

- `simpleaudio` python module

- **If you're not using windows**, the following modules are required to correctly display arabic text
  - `python-bidi`
  - `arabic-reshaper`

## Installation

1. Install tkinter (`python-tk` on debian-based, `tk` on arch-based) using your package manager if you're on Linux, you may need to install extra dependencies like alsa sound libraries and `libappindicator3-1`.

2. `git clone https://github.com/0xzer0x/athany-app` or download the code as zip from GitHub

3. Download the _Athans.zip_ file from [here](https://drive.google.com/file/d/183jhzs7cQzxY6IqeTadjKf3b7ZLqbUa7/view?usp=sharing), extract the audio files from the zip file into the **Data** directory/folder

4. Download & install required [Fonts](https://drive.google.com/file/d/15EewmO12DdEWfIdnbJJ9JeGXbBIvB2km/view?usp=sharing) for application. Copy fonts to /usr/share/fonts/ if you're using linux

5. Open a terminal, browse into the "athany-app" folder

6. run `pip install -r requirements.txt`

7. run `python athany.py`
