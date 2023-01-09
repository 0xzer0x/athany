<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/0xzer0x/athany-app">
    <img src="images/athany_icon.ico" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">Athany</h3>

  <p align="center">
    a python application to remind you of your purpose
    <br />
    <a href="https://github.com/0xzer0x/athany-app"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/0xzer0x/athany-app">View Demo</a>
    ·
    <a href="https://github.com/0xzer0x/athany-app/issues">Report Bug</a>
    ·
    <a href="https://github.com/0xzer0x/athany-app/issues">Request Feature</a>
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

[![Athany Screen Shot][product-screenshot]](https://github.com/0xzer0x/athany-app/releases/latest)

### قال تعالى: {وَمَا خَلَقْتُ ٱلْجِنَّ وَٱلْإِنسَ إِلَّا لِيَعْبُدُونِ (٥٦) مَآ أُرِيدُ مِنْهُم مِّن رِّزْقٍۢ وَمَآ أُرِيدُ أَن يُطْعِمُونِ (٥٧) إِنَّ ٱللَّهَ هُوَ ٱلرَّزَّاقُ ذُو ٱلْقُوَّةِ ٱلْمَتِينُ ٥٨)} \[الذاريات]

Athany is a lightweight python program for windows and linux that fetches the times for the five mandatory muslim prayers, tells you the time remaining until the next prayer, and plays the athan sound when the prayer time comes.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

- [![python][python]][python-url]
- [![pysimplegui][psg]][psg-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

- Python >= 3.9

- `python-tk` Tkinter package if you're on linux, install it using your package manager.

- [Fonts](https://github.com/0xzer0x/athany-app/releases/download/1.0.0-stable/fonts.zip) used for application.

### Installation

1. Install dependencies (Linux users only)

   ```sh
   sudo apt-get install -y python3-tk python3-dev libasound2-dev
   ```

2. Clone the repo

   ```sh
   git clone https://github.com/0xzer0x/athany-app.git
   ```

3. Install python packages

   ```sh
   cd athany-app
   pip install -r requirements.txt
   ```

4. Run the application
   ```sh
   python athany.py
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->

## Usage

![choose-location][choose-location]

On first launch, the choose-location window will prompt you for a valid location. you can either type your location manually or use the automatically fetched location (note: your location is fetched using your public IP, so it may not be totally accurate)

![main-window][main-window]

the settings window can be accessed through the bottom left button

![settings-window-app-tab][settings-window-app-tab]

the app settings tab has the main app settings (mute athan, saving location, theme, change/download athan sound)

![settings-window-offset-tab][settings-window-offset-tab]

the offset tab allows you to adjust prayer times by adding/subtracting minutes from the default calculated time

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->

## Roadmap

- [ ] make an Android version using `kivy` library

See the [open issues](https://github.com/0xzer0x/athany-app/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->

## License

Distributed under the GNU GPL v3. See `LICENSE.md` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->

## Contact

Fursan team - y.essam2256@nu.edu.eg

Project Link: [https://github.com/0xzer0x/athany-app](https://github.com/0xzer0x/athany-app)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->

## Acknowledgments

- [AlAdhan API](https://aladhan.com/prayer-times-api)
- [adhanpy library](https://github.com/alphahm/adhanpy)
- [hijri-converter library](https://hijri-converter.readthedocs.io/en/stable/index.html)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->

[python]: https://img.shields.io/badge/Python-yellowgreen?style=for-the-badge&logo=Python&logoColor=white
[psg]: https://img.shields.io/badge/PySimpleGUI-blue?style=for-the-badge&logo=Python&logoColor=white
[python-url]: https://python.org
[psg-url]: https://pysimplegui.org
[product-screenshot]: images/banner.jpg
[choose-location]: images/choose-location.png
[main-window]: images/main-window.png
[settings-window-app-tab]: images/settings-window.png
[settings-window-offset-tab]: images/settings-window-offset-tab.png
