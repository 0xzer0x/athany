<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/0xzer0x/athany">
    <img src="images/athany_icon.ico" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">Athany</h3>

  <p align="center">
    a python application to remind you of your purpose
    <br />
    <br />
    <a href="https://github.com/0xzer0x/athany/releases/latest"><img src="https://img.shields.io/github/v/release/0xzer0x/athany"></a>
    <a href="https://www.codefactor.io/repository/github/0xzer0x/athany/overview/master"><img src="https://www.codefactor.io/repository/github/0xzer0x/athany/badge/master" alt="CodeFactor" /></a>
    <br />
    <a href="https://github.com/0xzer0x/athany#usage">View Demo</a>
    ·
    <a href="https://github.com/0xzer0x/athany/issues">Report Bug</a>
    ·
    <a href="https://github.com/0xzer0x/athany/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
        <li><a href="#build-from-source">Building from source</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

## About The Project

[![Athany Screen Shot][banner]][latest-release]

### قال تعالى: {وَمَا خَلَقْتُ ٱلْجِنَّ وَٱلْإِنسَ إِلَّا لِيَعْبُدُونِ (٥٦) مَآ أُرِيدُ مِنْهُم مِّن رِّزْقٍۢ وَمَآ أُرِيدُ أَن يُطْعِمُونِ (٥٧) إِنَّ ٱللَّهَ هُوَ ٱلرَّزَّاقُ ذُو ٱلْقُوَّةِ ٱلْمَتِينُ (٥٨)} \[الذاريات]

Athany is a lightweight python program for windows and linux that calculates the times for the five mandatory muslim prayers, tells you the time remaining until the next prayer, and plays the athan sound when the prayer time comes.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

- [![python][python]][python-url]
- [![pysimplegui][psg]][psg-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

## Getting Started

Install the [latest stable version][latest-release] using the windows setup provided in the release, If you want the latest code version up and running follow these simple steps.

### Prerequisites

- Python >= 3.9

- [Fonts][fonts-download-url] used in application.

- `python-tk` Tkinter package (Linux users only)

- `libappindicator-gtk3` & [appindicator shell extension][gnome-appindicator-ext] if you're using Gnome (Linux users only)

### Installation

1. Install dependencies (Linux users only)

   ```sh
   sudo apt-get install -y python3-tk python3-dev libappindicator3-1 libappindicator3-dev
   ```

2. Clone the repo

   ```sh
   git clone https://github.com/0xzer0x/athany.git
   ```

3. Install python packages

   ```sh
   cd athany
   pip install -r requirements.txt
   ```

4. Run the application
   ```sh
   python main.py
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<a name="build-from-source"></a>

### Building from source

**Replace the single-quotes with double-quotes if you're using windows and : with ;**

- After the installation steps, execute the following commands. You will find the built application folder in the _dist_ directory

```sh
    pip install pyinstaller
    pyinstaller --noconfirm --onedir --windowed --icon 'images/athany_icon.ico' --add-data 'src/Data:src/Data' --name 'athany' main.py
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>
<!-- USAGE EXAMPLES -->

## Usage

![choose-location][choose-location]

On first launch, the choose-location window will prompt you for a valid location. you can either type your location manually or use the automatically fetched location (note: your location is fetched using your public IP, so it may not be totally accurate)

![main-window][main-window]

the settings window can be accessed through the bottom left button

![settings-window-general-tab][settings-window-general-tab]

the general settings tab has the main app settings (mute athan, saving location, theme, change language, change/download athan sound)

![settings-window-custom-athan-tab][settings-window-custom-athan-tab]

the custom athan tab allows you to choose a local audio file (.wav, .mp3) to play instead of the offered athans

![settings-window-offset-tab][settings-window-offset-tab]

the offset tab allows you to adjust prayer times by adding/subtracting minutes from the default calculated time

![advanced-settings-tab][advanced-settings-tab]

the advanced settings tab allows you to use a different calculation method or set the calculation parameters manually. It also shows you the default method used in your country

[check out other screenshots](https://github.com/0xzer0x/athany/tree/master/images)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->

## Roadmap

- [x] Add advanced settings tab
  - [x] change calculation method
  - [x] use custom fajr & isha angles
- [ ] Add translations
- [ ] make an Android version using `kivy` library

See the [open issues](https://github.com/0xzer0x/athany/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->

## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->

## Contact

Fursan team - y.essam2256@nu.edu.eg

Project Link: [https://github.com/0xzer0x/athany](https://github.com/0xzer0x/athany)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->

## Acknowledgments

- [AlAdhan API](https://aladhan.com/prayer-times-api)
- [adhanpy library](https://github.com/alphahm/adhanpy)
- [hijri-converter library](https://hijri-converter.readthedocs.io/en/stable/index.html)
- [Muezzin](https://github.com/DBChoco/Muezzin)
- [Athan audios source](https://www.assabile.com/adhan-call-prayer)
- [This README template](https://github.com/othneildrew/Best-README-Template)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[latest-release]: https://github.com/0xzer0x/athany/releases/latest
[python]: https://img.shields.io/badge/Python-yellowgreen?style=for-the-badge&logo=Python&logoColor=white
[psg]: https://img.shields.io/badge/PySimpleGUI-blue?style=for-the-badge&logo=Python&logoColor=white
[python-url]: https://python.org
[psg-url]: https://pysimplegui.org
[banner]: images/banner.jpg
[choose-location]: images/choose-location-121-en.png
[main-window]: images/main-window-121-en.png
[settings-window-general-tab]: images/general-settings-121-en.png
[settings-window-custom-athan-tab]: images/custom-athan-121-en.png
[settings-window-offset-tab]: images/offset-tab-121-en.png
[advanced-settings-tab]: images/advanced-settings-121-en.png
[gnome-appindicator-ext]: https://extensions.gnome.org/extension/615/appindicator-support/
[fonts-download-url]: https://github.com/0xzer0x/athany/releases/download/1.0.0-stable/fonts.zip
