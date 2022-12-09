# Athany: a python application to remind you of your purpose

<br>

### قال تعالى: {وَمَا خَلَقْتُ الْجِنَّ وَالْإِنسَ إِلَّا لِيَعْبُدُونِ (56)} \[الذاريات]

<br>
 
#### [Athany](https://github.com/0xzer0x/athany-app/releases/latest) is a lightweight python program for windows and linux that fetches the times for the five mandatory muslim prayers, tells you the time remaining until the next prayer, and plays the athan sound when the prayer time comes.
 
<br>
 
## Requirements
 
- Python3 (tested on python 3.10 & 3.11)

- Internet connection is required **before the Isha prayer of the last day in each month** in order to fetch the new month calender, otherwise it operates offline

- `tk` tkinter package if you're on linux, install it using your package manager. If you can't find it, search how to install tkinter on your distro.

- `PySimpleGUI` python module

- `psgtray` python module

- `requests` python module

- `simpleaudio` python module

- **If you're not using windows**, the following modules are required to correctly display arabic text
  - `python-bidi`
  - `arabic-reshaper`

## Installation (for development)

1. Install tkinter (`python-tk` on debian-based, `tk` on arch-based) using your package manager if you're on Linux, you may need to install extra dependencies like alsa sound libraries and `libappindicator3-1`.

2. `git clone https://github.com/0xzer0x/athany-app` or download the code as zip from GitHub

3. Download the [Athans.zip](https://github.com/0xzer0x/athany-app/releases/download/1.0.0-stable/Athans.zip) file, extract the audio files from the zip file into the **Data/Athans** directory/folder

4. Download & install required [Fonts](https://github.com/0xzer0x/athany-app/releases/download/1.0.0-stable/fonts.zip) for application. Copy fonts to /usr/share/fonts/ if you're using linux

5. Open a terminal, browse into the "athany-app" folder

6. run `pip install -r requirements.txt`

7. run `python athany.py`
