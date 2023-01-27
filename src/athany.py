import os
import json
import sys

import requests
import hijri_converter
from src.elements import sg, mixer
from src.elements import SettingsWindow, MainWindow, ChooseLocationWindow
from src.elements import TranslatedText, TranslatedButton
from src.modifiedpt import ModifiedPrayerTimes
from src.translator import Translator
if sys.platform == "win32":
    # library for system notifications on Windows
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "athany notifications")

DATA_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "Data")
ATHANS_DIR = os.path.join(DATA_DIR, "Athans")
TRANSLATIONS_DIR = os.path.join(DATA_DIR, "Translations")

with open(os.path.join(DATA_DIR, "app_icon.dat"), mode="rb") as icon:
    APP_ICON = icon.read()
with open(os.path.join(DATA_DIR, "settings.dat"), mode="rb") as icon:
    SETTINGS_ICON = icon.read()
with open(os.path.join(DATA_DIR, "download.dat"), mode="rb") as down:
    DOWNLOAD_ICON_B64 = down.read()
with open(os.path.join(DATA_DIR, "toggle_off.dat"), mode="rb") as toff:
    TOGGLE_OFF_B64 = toff.read()
with open(os.path.join(DATA_DIR, "toggle_on.dat"), mode="rb") as ton:
    TOGGLE_ON_B64 = ton.read()
with open(os.path.join(DATA_DIR, "available_athans.txt"), encoding="utf-8") as fd:
    AVAILABLE_ATHANS = fd.read().strip().split("\n")


class Athany:
    """Python application to fetch prayer times, display them in a GUI and play adhan"""
    # ------------------------- default app settings ------------------------- #

    def __init__(self) -> None:
        self.settings = sg.UserSettings(
            filename="athany-config.json", path=DATA_DIR)

        if not self.settings["-theme-"]:
            self.settings["-theme-"] = "DarkAmber"
        if not self.settings["-lang-"]:
            self.settings["-lang-"] = "en"

        if not self.settings["-location-"]:
            self.settings["-location-"] = dict()
        if not self.settings["-offset-"]:
            self.settings["-offset-"] = {"-Fajr-": 0, "-Sunrise-": 0,
                                         "-Dhuhr-": 0, "-Asr-": 0,
                                         "-Maghrib-": 0, "-Isha-": 0}
        if not self.settings["-custom-angles-"]:
            self.settings["-custom-angles-"] = [18, 18]

        if not self.settings["-mute-athan-"]:
            self.settings["-mute-athan-"] = False
        if not self.settings["-use-custom-athan-"]:
            self.settings["-use-custom-athan-"] = False
        if not self.settings["-custom-athan-"]:
            self.settings["-custom-athan-"] = "None"
        if not self.settings["-athan-sound-"] or \
                self.settings["-athan-sound-"] not in os.listdir(ATHANS_DIR):
            self.settings["-athan-sound-"] = "Abdul-Basit_(Takbeer_only).mp3"

        if sys.platform == "win32":
            self.GUI_FONT = ("Readex Pro", 11)
            self.HIJRI_DATE_FONT = ("Arabic Typesetting", 20)
            if self.settings["-lang-"] == 'ar':
                self.BUTTON_FONT = (self.GUI_FONT[0], 8)
                self.MONO_FONT = (self.GUI_FONT[0], 9)
                self.settings_button_width = 10
            else:
                self.MONO_FONT = ("IBM Plex Mono", 10)
                self.BUTTON_FONT = ("Helvetica", 9)
                self.settings_button_width = 6
        else:
            self.GUI_FONT = ("STC", 13)
            self.HIJRI_DATE_FONT = (self.GUI_FONT[0], 14)
            if self.settings["-lang-"] == 'ar':
                self.BUTTON_FONT = (self.GUI_FONT[0], 9)
                self.MONO_FONT = (self.GUI_FONT[0], 10)
                self.settings_button_width = 10
            else:
                self.MONO_FONT = ("IBM Plex Mono", 10)
                self.BUTTON_FONT = ("Helvetica", 9)
                self.settings_button_width = 6

        self.location_api = None
        self.restart_app, self.save_loc_check = False, False
        self.translator = Translator(self.settings["-lang-"], TRANSLATIONS_DIR)
        self.api_endpoint = " http://api.aladhan.com/v1/timingsByCity"
        self.displayed_times = ["Fajr", "Sunrise",
                                "Dhuhr", "Asr", "Maghrib", "Isha"]

        self.chosen_theme = None
        sg.set_global_icon(APP_ICON)
        sg.theme(self.settings["-theme-"])
        self.available_themes = ["DarkAmber", "DarkBlack1", "DarkBlue13",
                                 "DarkBlue17", "DarkBrown", "DarkBrown2",
                                 "DarkBrown7", "DarkGreen7", "DarkGrey2",
                                 "DarkGrey5", "DarkGrey8", "DarkGrey10",
                                 "DarkGrey11", "DarkGrey13", "DarkPurple7",
                                 "DarkTeal10", "DarkTeal11"]

        self.pt = None
        self.init_layout = None
        self.window = None

        # self.calculation_data will either be a dict (api json response) or None
        self.calculation_data = self.choose_location_if_not_saved()

    # ---------------------------- static methods ---------------------------- #

    @staticmethod
    def get_current_location() -> tuple[str, str]:
        """ function that gets the current city and country of the user IP\n
        :return: (Tuple[str, str]) tuple containing 2 strings of the city & country fetched
        """
        try:
            ipinfo_res = requests.get(
                "https://ipinfo.io/json", timeout=5)

            if ipinfo_res.status_code == 200:
                ipinfo_json = ipinfo_res.json()
                ret_val = (ipinfo_json["city"], ipinfo_json["country"])
            else:
                ipgeoloc_res = requests.get(
                    "https://api.ipgeolocation.io/ipgeo?apiKey=397b014528ba421cafcc5df4d00c9e9a", timeout=5)

                if ipgeoloc_res.status_code == 200:
                    ipgeoloc_json = ipgeoloc_res.json()
                    ret_val = (ipgeoloc_json["city"],
                               ipgeoloc_json["country_code2"])
                else:
                    raise requests.exceptions.ConnectionError

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            ret_val = "RequestError"

        return ret_val

    @staticmethod
    def get_hijri_date() -> str:
        """function to return arabic hijri date string to display in main window
        :return: (str) Arabic string of current Hijri date
        """
        hijri_date = hijri_converter.Gregorian.today().to_hijri()
        unformatted_text = f"{hijri_date.day_name(language='ar')} {hijri_date.day} {hijri_date.month_name(language='ar')} {hijri_date.year}"
        return Translator.display_ar_text(text=unformatted_text)

    # -------------------------- window generators -------------------------- #

    def generate_location_window(self):
        """method to generate the location window layout based on the app language

        :return PySimpleGUI.Window: choose location window object
        """
        layout = self.translator.adjust_layout_direction([
            [
                TranslatedText(self.translator, "Set your location",
                               key="-LOC-TXT-", pad=(0, 5)),
                sg.Text(key="-LOCATION-NAME-", pad=(0, 5)),
                sg.Push()
            ],
            [
                TranslatedText(self.translator, "City"),
                sg.Input(size=(15, 1), key="-CITY-", focus=True),
                TranslatedText(self.translator, "Country"),
                sg.Input(size=(15, 1), key="-COUNTRY-"),
                sg.Push(),
                sg.Checkbox(self.translator.translate(
                    "Save location"), key="-SAVE-LOC-CHECK-")
            ],
            [
                TranslatedButton(self.translator, "Ok", size=(10, 1), key="-OK-",
                                 font=self.BUTTON_FONT, bind_return_key=True),
                TranslatedButton(self.translator, "Use current location",
                                 key="-USE-CURRENT-LOCATION-", font=self.BUTTON_FONT),
                sg.Text(key="-AUTO-LOCATION-"),
                sg.Push(),
                TranslatedButton(self.translator, "Cancel", size=(10, 1),
                                 key="-CANCEL-", font=self.BUTTON_FONT)
            ]
        ])

        return ChooseLocationWindow(self,
                                    title="Athany - set location",
                                    layout=layout,
                                    font=self.GUI_FONT)

    def generate_settings_window(self):
        """method to generate the settings window layout based on app language

        :return SettingsWindow: settings window object
        """
        current_athan = "Custom" if self.settings["-use-custom-athan-"] \
            else self.settings["-athan-sound-"][:-4].replace("_", " ")

        method = self.pt.calculation_methods.get(
            self.settings["-used-method-"], self.pt.calculation_methods[4])[1]

        # tab 1 contains application settings
        app_settings_tab = self.translator.adjust_layout_direction([
            [
                sg.Col(
                    self.translator.adjust_layout_direction([[
                        TranslatedText(self.translator,
                                       "Mute athan", pad=0),
                        sg.Push(),
                        sg.Button(image_data=TOGGLE_ON_B64 if self.settings["-mute-athan-"] else TOGGLE_OFF_B64,
                                  key="-TOGGLE-MUTE-", pad=(5, 0), button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                  border_width=0, metadata=self.settings["-mute-athan-"])
                    ],
                        [
                        TranslatedText(self.translator,
                                       "Save location", pad=0),
                        sg.Text(
                            f"({self.settings['-location-']['-city-']}, {self.settings['-location-']['-country-']})", pad=0),
                        sg.Push(),
                        sg.Button(image_data=TOGGLE_ON_B64 if self.save_loc_check else TOGGLE_OFF_B64,
                                  key="-TOGGLE-SAVE-LOCATION-", button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                  border_width=0, pad=(5, 0), metadata=self.save_loc_check)
                    ]]), expand_x=True),
                sg.Col(
                    self.translator.adjust_layout_direction([[
                        TranslatedText(self.translator, "Language"),
                        sg.Push(),
                        sg.Combo(enable_events=True, values=["ar", "en"], key="-DROPDOWN-LANG-",
                                 readonly=True, default_value=self.settings["-lang-"], font="Helvetica 9")
                    ],

                        [
                        TranslatedText(self.translator,
                                       "Current theme", pad=(5, (10, 0))),
                        sg.Push(),
                        sg.Combo(enable_events=True, values=self.available_themes, key="-DROPDOWN-THEMES-",
                                 readonly=True, default_value=self.settings["-theme-"], font="Helvetica 9", pad=(5, (10, 0)))
                    ]]), expand_x=True)
            ],
            [
                TranslatedText(self.translator, "Current athan", pad=(5, 5),
                               key="-DISPLAYED-MSG-"),
                sg.Push(),
                sg.Combo(disabled=self.settings["-use-custom-athan-"], enable_events=True,
                         values=AVAILABLE_ATHANS, key="-DROPDOWN-ATHANS-",
                         readonly=True, s=37, default_value=current_athan,
                         font="Helvetica 9", pad=(10, 5))
            ]
        ])

        # tab 2 contains prayer offset adjustments
        prayer_offset_tab = self.translator.adjust_layout_direction([
            [
                sg.Col(
                    self.translator.adjust_layout_direction([
                        [TranslatedText(self.translator, "Fajr offset"),
                         sg.Push(), sg.Spin(
                         [sz for sz in range(-59, 60)], initial_value=self.settings["-offset-"]["-Fajr-"],
                         key="-FAJR-OFFSET-", readonly=True, text_color="black")
                         ],
                        [TranslatedText(self.translator, "Sunrise offset"),
                         sg.Push(), sg.Spin(
                         [sz for sz in range(-59, 60)], initial_value=self.settings["-offset-"]["-Sunrise-"],
                         key="-SUNRISE-OFFSET-", readonly=True, text_color="black")
                         ],
                        [TranslatedText(self.translator, "Dhuhr offset"),
                         sg.Push(), sg.Spin(
                         [sz for sz in range(-59, 60)], initial_value=self.settings["-offset-"]["-Dhuhr-"],
                         key="-DHUHR-OFFSET-", readonly=True, text_color="black")
                         ]
                    ]), expand_x=True),
                sg.Col(
                    self.translator.adjust_layout_direction([
                        [TranslatedText(self.translator, "Asr offset"),
                         sg.Push(), sg.Spin(
                         [sz for sz in range(-59, 60)], initial_value=self.settings["-offset-"]["-Asr-"],
                         key="-ASR-OFFSET-", readonly=True, text_color="black")
                         ],
                        [TranslatedText(self.translator, "Maghrib offset"),
                         sg.Push(), sg.Spin(
                         [sz for sz in range(-59, 60)], initial_value=self.settings["-offset-"]["-Maghrib-"],
                         key="-MAGHRIB-OFFSET-", readonly=True, text_color="black")
                         ],
                        [TranslatedText(self.translator, "Isha offset"),
                         sg.Push(), sg.Spin(
                         [sz for sz in range(-59, 60)], initial_value=self.settings["-offset-"]["-Isha-"],
                         key="-ISHA-OFFSET-", readonly=True, text_color="black")
                         ]
                    ]
                    ), expand_x=True)
            ],
            [
                sg.Push(),
                TranslatedButton(self.translator, "Reset",
                                 key="-RESET-OFFSET-", font=self.BUTTON_FONT)
            ]
        ])

        # tab 3 containing custom athan settings
        custom_athan_tab = self.translator.adjust_layout_direction([
            [
                TranslatedText(self.translator,
                               "Use custom athan sound", pad=5),
                sg.Push(),
                sg.Button(image_data=TOGGLE_ON_B64 if self.settings["-use-custom-athan-"] else TOGGLE_OFF_B64,
                          key="-TOGGLE-CUSTOM-ATHAN-", pad=(5, 0), button_color=(sg.theme_background_color(), sg.theme_background_color()),
                          border_width=0, metadata=self.settings["-use-custom-athan-"])
            ],
            [
                sg.InputText(self.settings["-custom-athan-"], readonly=True,
                             text_color=sg.theme_text_color(),
                             disabled_readonly_background_color=sg.theme_background_color(),
                             key="-CUSTOM-ATHAN-NAME-", font=(self.GUI_FONT[0], 10), expand_x=True),
            ],
            [
                sg.Push(),
                sg.FileBrowse(button_text=self.translator.translate(
                    "Browse"), disabled=not self.settings["-use-custom-athan-"], target="-CUSTOM-ATHAN-NAME-",
                    file_types=(("WAVE audio", ".wav"), ("MP3 audio", ".mp3")), font=(self.GUI_FONT[0], 10), pad=(5, 5),
                    key="-CUSTOM-ATHAN-BROWSE-")
            ],

        ])

        # tab 4 is for advanced calculation settings
        advanced_settings_tab = self.translator.adjust_layout_direction([
            [
                TranslatedText(self.translator,
                               "Calculation method", pad=(5, 10)),
                sg.Push(),
                sg.Combo(default_value=method, readonly=True, s=37,
                         values=[x[1]
                                 for x in self.pt.calculation_methods.values()],
                         key="-DROPDOWN-METHODS-", enable_events=True, pad=(5, 10), font="Helvetica 10")
            ],
            [
                TranslatedText(self.translator, "Fajr angle"),
                sg.Input(key="-FAJR-ANGLE-IN-", s=7, disabled=self.settings["-used-method-"] != 99,
                         default_text=self.settings["-custom-angles-"][0], disabled_readonly_text_color="grey",
                         disabled_readonly_background_color=sg.theme_background_color(), font="Helvetica 10"),
                TranslatedText(self.translator, "Isha angle"),
                sg.Input(key="-ISHA-ANGLE-IN-", s=7, disabled=self.settings["-used-method-"] != 99,
                         default_text=self.settings["-custom-angles-"][1], disabled_readonly_text_color="grey",
                         disabled_readonly_background_color=sg.theme_background_color(), font="Helvetica 10"),
                sg.Push(),
                TranslatedButton(self.translator, "Set custom angles",
                                 key="-SET-CUSTOM-ANGLES-", font=self.BUTTON_FONT, disabled=self.settings["-used-method-"] != 99)
            ],
            [
                TranslatedText(self.translator,
                               "Default method"),
                sg.Push(),
                TranslatedText(self.translator,
                               self.pt.calculation_methods[self.settings["-default-method-"]][1]),
            ]
        ])

        settings_layout = [
            [
                sg.TabGroup([[
                            sg.Tab(self.translator.translate(
                                "general settings"), app_settings_tab),
                            sg.Tab(self.translator.translate(
                                "custom athan"), custom_athan_tab),
                            sg.Tab(self.translator.translate(
                                "prayer times offset (min)"), prayer_offset_tab),
                            sg.Tab(self.translator.translate(
                                "advanced settings"), advanced_settings_tab)
                            ]])
            ],
            [
                TranslatedButton(self.translator, "Restart", key="-RESTART-",
                                 font=self.BUTTON_FONT, s=self.settings_button_width, pad=(5, 15)),
                TranslatedButton(self.translator, "Exit", key="-EXIT-",
                                 font=self.BUTTON_FONT,
                                 button_color=('black', '#651C32'),
                                 s=self.settings_button_width, pad=(5, 15)),
                sg.Push(),
                TranslatedButton(self.translator, "Done", key="-DONE-",
                                 font=self.BUTTON_FONT, s=self.settings_button_width, pad=(5, 15))
            ]
        ]

        return SettingsWindow(self, title="Athany - settings",
                              layout=settings_layout,
                              icon=SETTINGS_ICON,
                              font=self.GUI_FONT,
                              enable_close_attempted_event=True,
                              keep_on_top=True)

    def yes_or_no_popup(self, text="Do you want to restart the application?"):
        """function to display a popup window & prompt the user to try again"""
        ans, _ = sg.Window("Confirm",
                           [[TranslatedText(self.translator, text)],
                            [sg.Push(), TranslatedButton(self.translator, "Yes", key="Yes", s=7), TranslatedButton(self.translator, "No", key="No", s=7)]],
                           font=self.BUTTON_FONT,
                           keep_on_top=True, disable_close=True).read(close=True)
        if ans == "Yes":
            return True
        else:
            return False

    # ------------------------ athan-related methods ------------------------ #

    def download_athan(self, athan_filename: str) -> bool:
        """Function to download athans from app bucket
        :param athan_filename: (str) name of .wav file to download from bucket
        :return: (bool) True if the download completed successfully without errors, False otherwise
        """
        try:
            prog_win = None
            saved_file = os.path.join(ATHANS_DIR, athan_filename)
            with open(saved_file, "wb") as athan_file:
                file_data = requests.get("https://s3.us-east-1.amazonaws.com/athany-data/mp3/"+athan_filename,
                                         stream=True, timeout=10)
                file_size = int(file_data.headers.get("content-length"))

                progress_layout = self.translator.adjust_layout_direction([
                    [TranslatedText(self.translator, "Downloading", pad=0),
                        sg.Text(f"{athan_filename} ({file_size//1024} KB)", pad=0)],
                    [sg.ProgressBar(max_value=file_size,
                                    size=(20, 10), expand_x=True, orientation="h", key="-PROGRESS-METER-")],
                    [sg.Push(),
                     TranslatedButton(self.translator, "Cancel", key="-CANCEL-")]
                ])

                prog_win = sg.Window("Download athan", progress_layout,
                                     font=self.BUTTON_FONT, icon=DOWNLOAD_ICON_B64,
                                     keep_on_top=True, enable_close_attempted_event=True)

                dl = 0
                for chunk in file_data.iter_content(chunk_size=4096):
                    dl += len(chunk)
                    athan_file.write(chunk)

                    prog_e = prog_win.read(timeout=10)[0]
                    prog_win.make_modal()
                    if prog_e in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "-CANCEL-"):
                        file_data.close()
                        raise requests.exceptions.ConnectionError

                    prog_win["-PROGRESS-METER-"].update(current_count=dl)

                prog_win.close()
                del prog_win

            return True
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL):
            if prog_win:
                prog_win.close()
                del prog_win

            os.remove(saved_file)
            return False

    def play_current_athan(self):
        """ fetches current settings for athan and plays the corresponding athan
        :return: (bool) boolean value to represent whether an audio is playing or not
        """
        mixer.music.unload()

        if self.settings["-use-custom-athan-"]:
            current_athan_path = self.settings["-custom-athan-"]
        else:
            current_athan_path = os.path.join(
                ATHANS_DIR, self.settings["-athan-sound-"])

        mixer.music.load(current_athan_path, current_athan_path[-3:])
        mixer.music.play()
        return True

    # --------------------------- helper methods ---------------------------- #

    def fetch_calculation_data(self, cit: str, count: str) -> dict:
        """check if location data (coords, timezone) for city+country exists and fetch it if not
        :param cit: (str) city to get data for
        :param count: (str) country to get data for
        :return: (dict) api response data as dictionary
        """
        json_month_file = os.path.join(
            DATA_DIR, f"{cit}-{count}.json")

        if not os.path.exists(json_month_file):
            try:
                res = requests.get(
                    self.api_endpoint+f"?city={cit}&country={count}", timeout=5)
            except (requests.Timeout, requests.ConnectionError):
                return "RequestError"

            if res.status_code != 200:  # if invalid city or country, return None instead of filename
                return None

            with open(json_month_file, mode="w", encoding="utf-8") as f:
                json.dump(res.json()["data"]["meta"], f)

        with open(json_month_file, encoding="utf-8") as location_metadata:
            data = json.load(location_metadata)

        return data

    def setup_inital_layout(self):
        """sets the prayer times window layout and
        the inital upcoming prayers on application startup
        """
        self.pt = ModifiedPrayerTimes(self)
        # Prayer times change after Isha athan to the times of the following day
        # this sets the current_fard & upcoming_prayer times
        self.pt.update_current_and_next_prayer()

        print(" DEBUG ".center(50, "="))

        self.init_layout = [
            [
                sg.Text(key="-TODAY-",
                        font=(self.GUI_FONT[0], self.GUI_FONT[1], "bold")),
                sg.Push(),
                sg.Text(sg.SYMBOL_CIRCLE, font="Arial 6"),
                sg.Push(),
                sg.Text(key="-TODAY_HIJRI-", font=self.HIJRI_DATE_FONT)
            ],
            [
                sg.Text(key="-LEFT-DECORATION-"),
                sg.HorizontalSeparator(),
                TranslatedText(self.translator, key="-NEXT-PRAYER-",
                               font=(self.GUI_FONT[0], self.GUI_FONT[1], "bold")),
                TranslatedText(self.translator, "in", font=self.GUI_FONT),
                sg.Text(font=self.GUI_FONT, key="-TIME-D-"),
                sg.HorizontalSeparator(),
                sg.Text(key="-RIGHT-DECORATION-")
            ]
        ]

        for prayer, time in self.pt.current_furood.items():
            # setting the main window layout with the inital prayer times
            self.init_layout.append(
                [
                    TranslatedText(self.translator, prayer,
                                   key=f"-{prayer.upper()}-", font=self.GUI_FONT),
                    sg.Push(),
                    sg.Text(time.strftime('%I:%M %p'), key=f"-{prayer.upper()}-TIME-",
                            font=self.GUI_FONT)
                ]
            )

            print(prayer, time)  # Debugging

        # the rest of the main window layout
        self.init_layout += [
            [sg.HorizontalSeparator(color="black")],
            [
                TranslatedButton(self.translator, "Settings", key="-SETTINGS-",
                                 font=self.BUTTON_FONT),
                TranslatedButton(self.translator, "Stop athan", key="-STOP-ATHAN-",
                                 font=self.BUTTON_FONT),
                sg.Push(),
                TranslatedText(self.translator, "current time",
                               font=self.MONO_FONT),
                sg.Text("~", font=("IBM Plex Mono", 10)),
                sg.Text(key="-CURRENT-TIME-", font=("IBM Plex Mono", 10))
            ]
        ]

        self.init_layout = self.init_layout[:1] + \
            self.translator.adjust_layout_direction(self.init_layout[1:])

        print("="*50)

    def choose_location_if_not_saved(self) -> dict:
        """function to get & set the user location
        :return: (dict) dictionary of the chosen location json data
        """
        if self.settings["-location-"].get("-coordinates-", None) is None:
            # If there are no saved settings, display the choose location window to set these values
            self.choose_location = self.generate_location_window()
            location_data = self.choose_location.run_event_loop()

        else:
            self.save_loc_check = True
            location_data = self.fetch_calculation_data(
                self.settings["-location-"]["-city-"],
                self.settings["-location-"]["-country-"])

        return location_data

    # ---------------------- startup & shutdown methods ---------------------- #

    def display_main_window(self, init_main_layout):
        """Displays the main application window, keeps running until window is closed
        :param init_main_layout: (list) main application window layout
        """
        mixer.init(frequency=16000)
        self.window = MainWindow(self,
                                 title="Athany: a python athan app",
                                 layout=init_main_layout,
                                 enable_close_attempted_event=True,
                                 finalize=True)

        if self.translator.bidirectional:
            self.window["-RIGHT-DECORATION-"].update(
                value=sg.SYMBOL_LEFT_ARROWHEAD)
            self.window["-LEFT-DECORATION-"].update(
                value=sg.SYMBOL_RIGHT_ARROWHEAD)
        else:
            self.window["-LEFT-DECORATION-"].update(
                value=sg.SYMBOL_LEFT_ARROWHEAD)
            self.window["-RIGHT-DECORATION-"].update(
                value=sg.SYMBOL_RIGHT_ARROWHEAD)

        self.window.start_system_tray()
        self.window.highlight_current_fard_in_ui()
        self.window.run_event_loop()

        # when the event loop ends, close the application
        self.close_app_windows()

    def close_app_windows(self):
        """function to properly close all app windows before shutting down"""
        try:
            self.choose_location.close()
            del self.choose_location
        except AttributeError:
            pass

        try:
            self.window.close()
            del self.window
        except AttributeError:
            pass
