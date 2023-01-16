import os
import json
import sys
import datetime
from zoneinfo import ZoneInfo

import requests
import hijri_converter
import PySimpleGUI as sg
from pygame import mixer
from psgtray import SystemTray
from adhanpy.PrayerTimes import PrayerTimes
from adhanpy.calculation import CalculationMethod
if sys.platform != "win32":
    try:
        from bidi.algorithm import get_display
        import arabic_reshaper
        MISSING_ARABIC_MODULES = False
    except ImportError:
        MISSING_ARABIC_MODULES = True
        print("[DEBUG] Couldn't load Arabic text modules, Install arabic text modules to display text correctly")
else:  # library for system notifications on Windows
    import ctypes
    myappid = "athany notifications"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


def display_ar_text(text: str) -> str:
    """
    :param text: (str) arabic text to display correctly
    :return: (str) correctly formatted arabic string
    """
    if sys.platform != "win32" and not MISSING_ARABIC_MODULES:
        ar_txt = arabic_reshaper.reshape(text)
        bidi_txt = get_display(ar_txt)
        return bidi_txt
    else:
        return text


class Translator:
    """class that provides an interface for translation & layout adjustment"""

    def __init__(self, lang, trans_files_dir):
        self.lang = lang
        self.translation_dict = None
        self.bidirectional = False

        if lang == 'ar':
            self.bidirectional = True
        if lang != 'en':
            self.translation_dict = json.load(
                open(os.path.join(trans_files_dir, lang+'_trans.json'), 'r', encoding='utf-8'))

    # ------------------------------------- UI Translation methods ------------------------------- #

    def translate(self, sentence):
        """method to translate the given string in the language of the translator object
        :param str sentence: string to translate
        :return str: translated text correctly formatted
        """
        if not self.translation_dict:
            text = sentence
        else:
            text = display_ar_text(
                self.translation_dict[sentence]) if self.bidirectional else self.translation_dict[sentence]

        return text

    def adjust_layout_direction(self, layout):
        """method to correctly display given layout depending on the direction of language
        :param list[list] layout: PySimpleGUI layout in list format
        :return list[list]: layout in correct direction
        """
        if self.bidirectional:
            return [x[::-1] for x in layout]

        return layout


class Athany:
    """Python application to fetch prayer times, display them in a GUI and play adhan"""
    # ------------------------------------- Application Settings --------------------------------- #

    def __init__(self) -> None:
        self.DATA_DIR = os.path.join(os.path.dirname(
            os.path.abspath(__file__)),  "Data")
        self.ATHANS_DIR = os.path.join(self.DATA_DIR, "Athans")
        self.TRANSLATIONS_DIR = os.path.join(self.DATA_DIR, "Translations")

        self.settings = sg.UserSettings(
            filename="athany-config.json", path=self.DATA_DIR)
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

        if not self.settings["-mute-athan-"]:
            self.settings["-mute-athan-"] = False
        if not self.settings["-use-custom-athan-"]:
            self.settings["-use-custom-athan-"] = False
        if not self.settings["-custom-athan-"]:
            self.settings["-custom-athan-"] = "None"
        if not self.settings["-athan-sound-"] or \
                self.settings["-athan-sound-"] not in os.listdir(self.ATHANS_DIR):
            self.settings["-athan-sound-"] = "Default.wav"

        self.now = datetime.datetime.now()
        self.tomorrow = self.now+datetime.timedelta(days=1)
        self.translator = Translator(
            self.settings["-lang-"], self.TRANSLATIONS_DIR)
        self.available_themes = ["DarkAmber", "DarkBlack1", "DarkBlue13",
                                 "DarkBlue17", "DarkBrown", "DarkBrown2",
                                 "DarkBrown7", "DarkGreen7", "DarkGrey2",
                                 "DarkGrey5", "DarkGrey8", "DarkGrey10",
                                 "DarkGrey11", "DarkGrey13", "DarkPurple7",
                                 "DarkTeal10", "DarkTeal11"]
        self.api_endpoint = " http://api.aladhan.com/v1/timingsByCity"
        self.displayed_times = ["Fajr", "Sunrise",
                                "Dhuhr", "Asr", "Maghrib", "Isha"]
        self.calculation_methods = {
            1: CalculationMethod.KARACHI,
            2: CalculationMethod.NORTH_AMERICA,
            3: CalculationMethod.MUSLIM_WORLD_LEAGUE,
            4: CalculationMethod.UMM_AL_QURA,
            5: CalculationMethod.EGYPTIAN,
            9: CalculationMethod.KUWAIT,
            10: CalculationMethod.QATAR,
            11: CalculationMethod.SINGAPORE,
            12: CalculationMethod.UOIF,
            15: CalculationMethod.MOON_SIGHTING_COMMITTEE,
        }

        if sys.platform == "win32":
            self.GUI_FONT = ("Readex Pro", 11)
            self.HIJRI_DATE_FONT = ("Arabic Typesetting", 20)
        else:
            self.GUI_FONT = ("Droid Sans Arabic", 11)
            self.HIJRI_DATE_FONT = (self.GUI_FONT[0], 12)
        if self.translator.lang == 'ar':
            self.BUTTON_FONT = (self.GUI_FONT[0], 8)
            self.MONO_FONT = (self.GUI_FONT[0], 9)
        else:
            self.MONO_FONT = ("IBM Plex Mono", 10)
            self.BUTTON_FONT = ("Helvetica", 9)

        with open(os.path.join(self.DATA_DIR, "app_icon.dat"), mode="rb") as icon:
            self.APP_ICON = icon.read()
        with open(os.path.join(self.DATA_DIR, "settings.dat"), mode="rb") as icon:
            self.SETTINGS_ICON = icon.read()
        with open(os.path.join(self.DATA_DIR, "download.dat"), mode="rb") as down:
            self.DOWNLOAD_ICON_B64 = down.read()
        with open(os.path.join(self.DATA_DIR, "toggle_off.dat"), mode="rb") as toff:
            self.TOGGLE_OFF_B64 = toff.read()
        with open(os.path.join(self.DATA_DIR, "toggle_on.dat"), mode="rb") as ton:
            self.TOGGLE_ON_B64 = ton.read()
        with open(os.path.join(self.DATA_DIR, "available_adhans.txt"), encoding="utf-8") as adhans:
            self.AVAILABLE_ADHANS = adhans.read().strip().split("\n")

        sg.theme(self.settings["-theme-"])
        sg.set_global_icon(self.APP_ICON)
        self.chosen_theme = None
        self.location_api = None
        self.restart_app = False
        self.save_loc_check = False

        self.current_fard = None
        self.upcoming_prayer = None
        self.current_furood = None

        mixer.init()
        self.location_win_layout = self.translator.adjust_layout_direction([
            [
                sg.Text(self.translator.translate("Set your location"),
                        key="-LOC-TXT-", pad=(0, 5)),
                sg.Text(key="-LOCATION-NAME-", pad=(0, 5)),
                sg.Push()
            ],
            [
                sg.Text(self.translator.translate("City")),
                sg.Input(size=(15, 1), key="-CITY-", focus=True),
                sg.Text((self.translator.translate("Country"))),
                sg.Input(size=(15, 1), key="-COUNTRY-"),
                sg.Push(),
                sg.Checkbox(self.translator.translate(
                    "Save location"), key="-SAVE-LOC-CHECK-")
            ],
            [
                sg.Button(self.translator.translate("Ok"), size=(10, 1), key="-OK-",
                          font=self.BUTTON_FONT, bind_return_key=True),
                sg.Button(self.translator.translate("Use current location"),
                          key="-USE-CURRENT-LOCATION-", font=self.BUTTON_FONT),
                sg.Text(key="-AUTO-LOCATION-"),
                sg.Push(),
                sg.Button(self.translator.translate("Cancel"), size=(10, 1),
                          key="-CANCEL-", font=self.BUTTON_FONT)
            ]
        ])

        # self.calculation_data will either be a dict (api json response) or None
        self.calculation_data = self.choose_location_if_not_saved()

    # ------------------------------------- Main Application logic ------------------------------- #

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
    def get_hijri_date(date: datetime.datetime) -> str:
        """function to return arabic hijri date string to display in main window
        :param date: (datetime.datetime) date to get hijri date for
        :return: (str) Arabic string of current Hijri date
        """
        hijri_date = hijri_converter.Gregorian(date.year,
                                               date.month,
                                               date.day).to_hijri()
        unformatted_text = f"{hijri_date.day_name(language='ar')} {hijri_date.day} {hijri_date.month_name(language='ar')} {hijri_date.year}"
        return display_ar_text(text=unformatted_text)

    def yes_or_no_popup(self, text="An error occurred, Do you want to restart the application?"):
        """function to display a popup window & prompt the user to try again"""
        ans, _ = sg.Window("Confirm",
                           [[sg.T(self.translator.translate(text))],
                            [sg.Push(), sg.Button(self.translator.translate("Yes"), key="Yes", s=7), sg.Button(self.translator.translate("No"), key="No", s=7)]],
                           font=self.BUTTON_FONT,
                           keep_on_top=True, disable_close=True).read(close=True)
        if ans == "Yes":
            return True
        else:
            return False

    def download_athan(self, athan_filename: str) -> bool:
        """Function to download athans from app bucket
        :param athan_filename: (str) name of .wav file to download from bucket
        :return: (bool) True if the download completed successfully without errors, False otherwise
        """
        try:
            prog_win = None
            saved_file = os.path.join(self.ATHANS_DIR, athan_filename)
            with open(saved_file, "wb") as athan_file:
                file_data = requests.get("https://s3.us-east-1.amazonaws.com/athany-data/"+athan_filename,
                                         stream=True, timeout=10)
                file_size = int(file_data.headers.get("content-length"))

                progress_layout = self.translator.adjust_layout_direction([
                    [sg.Text(
                        self.translator.translate("Downloading"), pad=0),
                        sg.Text(f"{athan_filename} ({file_size//1024} KB)", pad=0)],
                    [sg.ProgressBar(max_value=file_size,
                                    size=(20, 10), expand_x=True, orientation="h", key="-PROGRESS-METER-")],
                    [sg.Push(), sg.Button(
                        self.translator.translate("Cancel"), key="-CANCEL-")]
                ])

                prog_win = sg.Window("Download athan", progress_layout,
                                     font=self.BUTTON_FONT, icon=self.DOWNLOAD_ICON_B64,
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
            mixer.music.load(self.settings["-custom-athan-"])
        else:
            current_athan_path = os.path.join(
                self.ATHANS_DIR, self.settings["-athan-sound-"])
            mixer.music.load(current_athan_path, "wav")

        mixer.music.play()
        return True

    def fetch_calculation_data(self, cit: str, count: str) -> dict:
        """check if location data (coords, timezone) for city+country exists and fetch it if not
        :param cit: (str) city to get data for
        :param count: (str) country to get data for
        :return: (dict) api response data as dictionary
        """
        json_month_file = os.path.join(
            self.DATA_DIR, f"{cit}-{count}.json")

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
        self.now = datetime.datetime.now(
            tz=ZoneInfo(self.settings["-location-"]["-timezone-"]))
        self.tomorrow = self.now+datetime.timedelta(days=1)

        coords = self.settings["-location-"]["-coordinates-"]
        self.current_furood = self.get_prayers_dict(coords, self.now)

        # Prayer times change after Isha athan to the times of the following day
        # this sets the current_fard & upcoming prayer times
        self.update_current_and_next_prayer()

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
                sg.Text(key="-LEFT-DECORATION-", font=self.GUI_FONT),
                sg.HorizontalSeparator(),
                sg.Text(key="-NEXT-PRAYER-"),
                sg.Text(self.translator.translate("in"), font=self.GUI_FONT),
                sg.Text(font=self.GUI_FONT, key="-TIME-D-"),
                sg.HorizontalSeparator(),
                sg.Text(key="-RIGHT-DECORATION-", font=self.GUI_FONT)
            ]
        ]

        for prayer, time in self.current_furood.items():  # append upcoming prayers to list
            # setting the main window layout with the inital prayer times
            self.init_layout.append(
                [
                    sg.Text(self.translator.translate(prayer), key=f"-{prayer.upper()}-",
                            font=self.GUI_FONT),
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
                sg.Button(self.translator.translate("Settings"), key="-SETTINGS-",
                          font=self.BUTTON_FONT),
                sg.Button(self.translator.translate("Stop athan"), key="-STOP-ATHAN-",
                          font=self.BUTTON_FONT),
                sg.Push(),
                sg.Text(self.translator.translate(
                    "current time"), font=self.MONO_FONT),
                sg.Text("~", font=("IBM Plex Mono", 10)),
                sg.Text(key="-CURRENT-TIME-", font=("IBM Plex Mono", 10))
            ]
        ]

        self.init_layout = self.init_layout[:1] + \
            self.translator.adjust_layout_direction(self.init_layout[1:])

        print("="*50)

    def get_prayers_dict(self, coordinates, date) -> dict:
        """function to get given date prayer times dictionary
        :param coordinates: (tuple[int,int]) a tuple containing the lat & long coordinates
        :param date: (datetime.datetime) the date to get the prayer times for
        :return: (dict) dictionary of prayer name-prayer datetime pairs
        """
        if not date:
            date = self.now
        method = self.calculation_methods.get(
            self.settings["-method-id-"], self.calculation_methods[4])
        pt_object = PrayerTimes(coordinates, date, method,
                                time_zone=ZoneInfo(self.settings["-location-"]["-timezone-"]))

        return {"Fajr": pt_object.fajr
                + datetime.timedelta(minutes=self.settings["-offset-"]["-Fajr-"]),
                "Sunrise": pt_object.sunrise
                + datetime.timedelta(minutes=self.settings["-offset-"]["-Sunrise-"]),
                "Dhuhr":  pt_object.dhuhr
                + datetime.timedelta(minutes=self.settings["-offset-"]["-Dhuhr-"]),
                "Asr": pt_object.asr
                + datetime.timedelta(minutes=self.settings["-offset-"]["-Asr-"]),
                "Maghrib": pt_object.maghrib
                + datetime.timedelta(minutes=self.settings["-offset-"]["-Maghrib-"]),
                "Isha": pt_object.isha
                + datetime.timedelta(minutes=self.settings["-offset-"]["-Isha-"])}

    def update_current_and_next_prayer(self):
        """function to set the current & next fard from the furood dict & update the dict used if Isha passed
        :return: (bool) whether Isha passed (i.e current furood times were changed) or no,
        in order for the main window to update the prayer times displayed
        """
        isha_passed = False
        self.tomorrow = self.now+datetime.timedelta(days=1)

        # If isha is the current fard, update the furood dict to set the fajr of tomorrow
        if self.now >= self.current_furood["Isha"]:
            self.current_fard = ("Isha", self.current_furood["Isha"])
            self.current_furood = self.get_prayers_dict(
                self.settings["-location-"]["-coordinates-"], self.tomorrow)
            self.upcoming_prayer = ("Fajr", self.current_furood["Fajr"])
            isha_passed = True

        elif self.now >= self.current_furood["Maghrib"]:
            self.current_fard = ("Maghrib", self.current_furood["Maghrib"])
            self.upcoming_prayer = ("Isha", self.current_furood["Isha"])

        elif self.now >= self.current_furood["Asr"]:
            self.current_fard = ("Asr", self.current_furood["Asr"])
            self.upcoming_prayer = ("Maghrib", self.current_furood["Maghrib"])

        elif self.now >= self.current_furood["Dhuhr"]:
            self.current_fard = ("Dhuhr", self.current_furood["Dhuhr"])
            self.upcoming_prayer = ("Asr", self.current_furood["Asr"])

        elif self.now >= self.current_furood["Sunrise"]:
            self.current_fard = ("Sunrise", self.current_furood["Sunrise"])
            self.upcoming_prayer = ("Dhuhr", self.current_furood["Dhuhr"])

        elif self.now >= self.current_furood["Fajr"]:
            self.current_fard = ("Fajr", self.current_furood["Fajr"])
            self.upcoming_prayer = ("Sunrise", self.current_furood["Sunrise"])

        else:
            self.current_fard = ("Isha", self.current_furood["Isha"])
            self.upcoming_prayer = ("Fajr", self.current_furood["Fajr"])

        return isha_passed

    # ----------------------------- Main Windows And SystemTray Functions ------------------------ #

    def choose_location_if_not_saved(self) -> dict:
        """function to get & set the user location
        :return: (dict) dictionary of the chosen location json data
        """
        if self.settings["-location-"].get("-coordinates-", None) is None:
            # If there are no saved settings, display the choose location window to set these values
            self.choose_location = sg.Window("Athany - set location",
                                             self.location_win_layout,
                                             font=self.GUI_FONT)

            self.choose_location.perform_long_operation(
                self.get_current_location, "-AUTOMATIC-LOCATION-THREAD-")
            while True:
                location_data = False
                event, values = self.choose_location.read()

                if event in (sg.WIN_CLOSED, "-CANCEL-"):
                    self.close_app_windows()
                    break

                elif event == "-AUTOMATIC-LOCATION-THREAD-":
                    self.location_api = values["-AUTOMATIC-LOCATION-THREAD-"]
                    self.choose_location["-AUTO-LOCATION-"].update(value=f"({self.location_api[0]}, {self.location_api[1]})" if not isinstance(
                        self.location_api, str) else f"({self.translator.translate('Internet connection required')})")
                else:
                    if event == "-OK-":
                        city = values["-CITY-"].strip().capitalize()
                        country = values["-COUNTRY-"].strip().capitalize()
                        if len(city+country) < 4:
                            continue
                        if len(country) == 2:
                            country = country.upper()

                        self.choose_location["-LOC-TXT-"].update(
                            value=self.translator.translate(
                                'Fetching location data for')
                        )
                        self.choose_location["-LOCATION-NAME-"].update(
                            value=f"({city}, {country})")
                        self.choose_location.refresh()

                        location_data = self.fetch_calculation_data(city,
                                                                    country)

                        if location_data is None:  # if invalid city/country dont continue
                            self.choose_location["-LOC-TXT-"].update(
                                value=self.translator.translate("Invalid city or country, enter a valid location"))
                            self.choose_location["-LOCATION-NAME-"].update(
                                value="")
                            self.choose_location["-CITY-"].update(
                                background_color="dark red")
                            self.choose_location["-COUNTRY-"].update(
                                background_color="dark red")
                            continue

                    elif event == "-USE-CURRENT-LOCATION-":
                        if not isinstance(self.location_api, tuple):
                            self.location_api = self.get_current_location()
                        if self.location_api == "RequestError":
                            self.choose_location["-LOC-TXT-"].update(
                                value=self.translator.translate("An error occurred, try entering location manually"))
                            self.choose_location["-LOCATION-NAME-"].update(
                                value="")
                            self.choose_location.refresh()

                        else:
                            city = self.location_api[0]
                            country = self.location_api[1]

                            self.choose_location["-LOC-TXT-"].update(
                                value=self.translator.translate(
                                    'Fetching location data for')
                            )
                            self.choose_location["-LOCATION-NAME-"].update(
                                value=f"({city}, {country})")
                            self.choose_location.refresh()

                            location_data = self.fetch_calculation_data(city,
                                                                        country)

                    if not location_data:
                        continue

                    if location_data == "RequestError":
                        self.choose_location["-LOC-TXT-"].update(
                            value="Internet connection required")
                    else:
                        self.settings["-location-"]["-city-"] = city
                        self.settings["-location-"]["-country-"] = country
                        self.settings["-location-"]["-coordinates-"] = (
                            location_data["latitude"],
                            location_data["longitude"]
                        )
                        self.settings["-location-"]["-timezone-"] = location_data["timezone"]
                        self.settings.save()
                        self.settings["-method-id-"] = location_data["method"]["id"]

                        self.save_loc_check = values["-SAVE-LOC-CHECK-"]

                        # close location choosing window
                        self.close_app_windows()

                        return location_data

        else:
            self.save_loc_check = True
            location_data = self.fetch_calculation_data(
                self.settings["-location-"]["-city-"],
                self.settings["-location-"]["-country-"])

            return location_data

    def start_system_tray(self, win: sg.Window) -> SystemTray:
        """starts the SystemTray object and instantiates it"s menu and tooltip
        :return: (psgtray.SystemTray) systemtray object for application
        """
        menu = ["", ["Show Window", "Hide Window", "---", "Stop athan",
                     "Settings", "Exit"]]
        tray = SystemTray(menu=menu, tooltip="Next Prayer",
                          window=win, icon=self.APP_ICON)
        tray.show_message(
            title="Athany", message="Choose 'Hide Window' or close the window to minimize application to system tray")
        return tray

    def display_main_window(self, init_main_layout):
        """Displays the main application window, keeps running until window is closed
        :param init_main_layout: (list) main application window layout
        """
        self.window = sg.Window("Athany: a python athan app",
                                init_main_layout,
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

        self.application_tray = self.start_system_tray(win=self.window)
        win2_active = False
        athan_playing = None
        while True:
            self.now = datetime.datetime.now(
                tz=ZoneInfo(self.settings["-location-"]["-timezone-"])).replace(microsecond=0)

            if self.now >= self.upcoming_prayer[1]:
                prayer_times_changed = self.update_current_and_next_prayer()

                if self.current_fard[0] != "Sunrise":
                    self.application_tray.show_message(
                        title="Athany 🕌", message=self.translator.translate(f"It's time for {self.current_fard[0]} prayer"))
                    # play athan sound from user athan sound settings (if athan sound not muted)
                    try:
                        if not self.settings["-mute-athan-"]:
                            athan_playing = self.play_current_athan()
                    except:
                        print(
                            "[DEBUG] Couldn't play athan audio, rechoose your athan in the app settings")

                for f in self.displayed_times:
                    self.window[f"-{f.upper()}-"].update(font=self.GUI_FONT,
                                                         text_color=sg.theme_text_color())
                    self.window[f"-{f.upper()}-TIME-"].update(font=self.GUI_FONT,
                                                              text_color=sg.theme_text_color())

                # If current_furood dict was changed,
                # then update the whole application with the next day prayers starting from Fajr
                if prayer_times_changed:
                    for prayer, time in self.current_furood.items():
                        self.window[f"-{prayer.upper()}-TIME-"].update(
                            value=time.strftime("%I:%M %p"))

            # get remaining time till next prayer
            time_d = self.upcoming_prayer[1] - self.now

            # Highlight current fard in main window
            if self.current_fard[0] == "Sunrise":
                self.window["-FAJR-"].update(
                    font=(self.GUI_FONT[0], self.GUI_FONT[1], "italic"), text_color='#cd8032')
                self.window["-FAJR-TIME-"].update(
                    font=(self.GUI_FONT[0], self.GUI_FONT[1], "italic"), text_color='#cd8032')
            else:
                self.window[f"-{self.current_fard[0].upper()}-"].update(
                    font=(self.GUI_FONT[0], self.GUI_FONT[1], "italic"), text_color='#cd8032')
                self.window[f"-{self.current_fard[0].upper()}-TIME-"].update(
                    font=(self.GUI_FONT[0], self.GUI_FONT[1], "italic"), text_color='#cd8032')

            # update the main window with the next prayer and remaining time
            self.window["-NEXT-PRAYER-"].update(
                value=self.translator.translate(self.upcoming_prayer[0]), font=(self.GUI_FONT[0], self.GUI_FONT[1], "bold"))
            self.window["-TIME-D-"].update(value=str(time_d))

            # update the current dates
            self.window["-CURRENT-TIME-"].update(
                value=self.now.strftime("%I:%M %p"))
            self.window["-TODAY-"].update(
                value=self.now.date().strftime("%a %d %b %y"))
            self.window["-TODAY_HIJRI-"].update(
                value=self.get_hijri_date(self.now))

            # update system tray tooltip also
            self.application_tray.set_tooltip(
                f"{self.upcoming_prayer[0]} in {time_d}")

            # main event reading
            event1, values1 = self.window.read(timeout=100)

            if event1 == self.application_tray.key:
                event1 = values1[event1]
                # Debugging
                print("[DEBUG] SystemTray event:", event1)

            # Event check and preform action
            if event1 in (sg.WIN_CLOSED, "-EXIT-", "Exit"):
                break

            if event1 in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "Hide Window"):
                self.window.hide()
                self.application_tray.show_icon()
                self.application_tray.show_message(title="Athany minimized to system tray",
                                                   message="To completely close the app, choose the 'Exit' button")

            elif event1 in ("Show Window", sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
                self.window.un_hide()
                self.window.bring_to_front()

            elif event1 in ("-STOP-ATHAN-", "Stop athan") and athan_playing:
                mixer.music.unload()

            # if clicked settings button,
            # open up the settings window and read values from it along with the main window
            elif event1 in ("-SETTINGS-", "Settings") and not win2_active:
                win2_active = True
                button_width = 10 if self.translator.lang == 'ar' else 6
                current_athan = "Custom" if self.settings["-use-custom-athan-"] else self.settings["-athan-sound-"][:-4].replace(
                    "_", " ")

                # tab 1 contains application settings
                app_settings_tab = self.translator.adjust_layout_direction([
                    [
                        sg.Col(
                            self.translator.adjust_layout_direction([[
                                sg.Text(self.translator.translate(
                                    "Mute athan"), pad=0),
                                sg.Push(),
                                sg.Button(image_data=self.TOGGLE_ON_B64 if self.settings["-mute-athan-"] else self.TOGGLE_OFF_B64,
                                          key="-TOGGLE-MUTE-", pad=(5, 0), button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                          border_width=0, metadata=self.settings["-mute-athan-"])
                            ],
                                [
                                sg.Text(self.translator.translate(
                                    "Save location"), pad=0),
                                sg.Text(
                                    f"({self.settings['-location-']['-city-']}, {self.settings['-location-']['-country-']})", pad=0),
                                sg.Push(),
                                sg.Button(image_data=self.TOGGLE_ON_B64 if self.save_loc_check else self.TOGGLE_OFF_B64,
                                          key="-TOGGLE-GRAPHIC-", button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                          border_width=0, pad=(5, 0), metadata=self.save_loc_check)
                            ]])
                        ),
                        sg.Col(
                            self.translator.adjust_layout_direction([[
                                sg.Text(self.translator.translate("Language")),
                                sg.Push(),
                                sg.Combo(enable_events=True, values=["ar", "en"], key="-DROPDOWN-LANG-",
                                         readonly=True, default_value=self.settings["-lang-"], font="Helvetica 9")
                            ],

                                [
                                sg.Text(self.translator.translate(
                                    "Current theme"), pad=(5, (10, 0))),
                                sg.Push(),
                                sg.Combo(enable_events=True, values=self.available_themes, key="-DROPDOWN-THEMES-",
                                         readonly=True, default_value=self.settings["-theme-"], font="Helvetica 9", pad=(5, (10, 0)))
                            ]])
                        )
                    ],
                    [
                        sg.Text(self.translator.translate("Current athan"), pad=(5, 5),
                                key="-DISPLAYED-MSG-"),
                        sg.Push(),
                        sg.Combo(disabled=self.settings["-use-custom-athan-"], enable_events=True,
                                 values=self.AVAILABLE_ADHANS, key="-DROPDOWN-ATHANS-",
                                 readonly=True, s=37, default_value=current_athan,
                                 font="Helvetica 9", pad=(10, 5))
                    ]
                ])

                # tab 2 contains prayer offset adjustments
                prayer_offset_tab = self.translator.adjust_layout_direction([
                    [
                        sg.Col(
                            self.translator.adjust_layout_direction([
                                [sg.Text(self.translator.translate("Fajr offset")),
                                 sg.Push(), sg.Spin(
                                 [sz for sz in range(-59, 60)], key="-FAJR-OFFSET-", initial_value=self.settings["-offset-"]["-Fajr-"])
                                 ],
                                [sg.Text(self.translator.translate("Sunrise offset")),
                                 sg.Push(), sg.Spin(
                                 [sz for sz in range(-59, 60)], key="-SUNRISE-OFFSET-", initial_value=self.settings["-offset-"]["-Sunrise-"])
                                 ],
                                [sg.Text(self.translator.translate("Dhuhr offset")),
                                 sg.Push(), sg.Spin(
                                 [sz for sz in range(-59, 60)], key="-DHUHR-OFFSET-", initial_value=self.settings["-offset-"]["-Dhuhr-"])
                                 ]
                            ])

                        ),
                        sg.Push(),
                        sg.Col(
                            self.translator.adjust_layout_direction([
                                [sg.Text(self.translator.translate("Asr offset")),
                                 sg.Push(), sg.Spin(
                                 [sz for sz in range(-59, 60)], key="-ASR-OFFSET-", initial_value=self.settings["-offset-"]["-Asr-"])
                                 ],
                                [sg.Text(self.translator.translate("Maghrib offset")),
                                 sg.Push(), sg.Spin(
                                 [sz for sz in range(-59, 60)], key="-MAGHRIB-OFFSET-", initial_value=self.settings["-offset-"]["-Maghrib-"])
                                 ],
                                [sg.Text(self.translator.translate("Isha offset")),
                                 sg.Push(), sg.Spin(
                                 [sz for sz in range(-59, 60)], key="-ISHA-OFFSET-", initial_value=self.settings["-offset-"]["-Isha-"])
                                 ]
                            ]
                            )
                        )
                    ]
                ])

                # tab 3 containing custom athan settings
                custom_athan_tab = self.translator.adjust_layout_direction([
                    [
                        sg.Text(self.translator.translate(
                            "Use custom athan"), pad=5),
                        sg.Push(),
                        sg.Button(image_data=self.TOGGLE_ON_B64 if self.settings["-use-custom-athan-"] else self.TOGGLE_OFF_B64,
                                  key="-TOGGLE-CUSTOM-ATHAN-", pad=(5, 0), button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                  border_width=0, metadata=self.settings["-use-custom-athan-"])
                    ],
                    [
                        sg.Text(os.path.basename(self.settings["-custom-athan-"]),
                                key="-CUSTOM-ATHAN-NAME-", font=(self.GUI_FONT[0], 10), s=50),
                    ],
                    [
                        sg.Push(),
                        sg.FileBrowse(button_text=self.translator.translate(
                            "Browse"), disabled=not self.settings["-use-custom-athan-"], target="-CUSTOM-ATHAN-NAME-",
                            file_types=(("WAVE audio", ".wav"), ("MP3 audio", ".mp3")), font=(self.GUI_FONT[0], 10), pad=(5, 5),
                            key="-CUSTOM-ATHAN-BROWSE-")
                    ],

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
                        ]])
                    ],
                    [
                        sg.Button(self.translator.translate("Restart"), key="-RESTART-",
                                  font=self.BUTTON_FONT, s=button_width, pad=(5, 15)),
                        sg.Button(self.translator.translate("Exit"), key="-EXIT-",
                                  font=self.BUTTON_FONT, button_color=(
                                      'black', '#651C32'),
                                  s=button_width, pad=(5, 15)),
                        sg.Push(),
                        sg.Button(self.translator.translate("Done"), key="-DONE-",
                                  font=self.BUTTON_FONT, s=button_width, pad=(5, 15))
                    ]
                ]

                settings_window = sg.Window("Athany - settings",
                                            settings_layout,
                                            icon=self.SETTINGS_ICON,
                                            font=self.GUI_FONT,
                                            enable_close_attempted_event=True,
                                            keep_on_top=True)

            # If 2nd window (settings window) is open, read values from it
            if win2_active:
                event2, values2 = settings_window.read(timeout=100)

                if event2 in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "-DONE-"):
                    win2_active = False
                    offset_changed = False
                    action_type = values2.get("-DONE-", None)
                    print("[DEBUG] Settings exit action:", action_type)
                    self.save_loc_check = settings_window["-TOGGLE-GRAPHIC-"].metadata
                    self.settings["-custom-athan-"] = settings_window["-CUSTOM-ATHAN-NAME-"].get()

                    for prayer in self.current_furood:
                        pt_offset = settings_window[f"-{prayer.upper()}-OFFSET-"].get()
                        if self.settings["-offset-"][f"-{prayer}-"] != pt_offset:
                            self.settings["-offset-"][f"-{prayer}-"] = pt_offset
                            self.settings.save()
                            offset_changed = True

                    settings_window.close()

                    if offset_changed:
                        self.restart_app = self.yes_or_no_popup(
                            "Prayer offsets were changed, do you want to restart application?")

                    if action_type == "-RESTART-" or self.restart_app:
                        mixer.music.unload()
                        self.restart_app = True
                        self.window.write_event_value("-EXIT-", None)

                    elif action_type == "-EXIT-":
                        self.window.write_event_value("-EXIT-", None)

                elif event2 in ("-EXIT-", "-RESTART-"):
                    settings_window.write_event_value(
                        "-DONE-", event2)

                elif event2 in "-TOGGLE-MUTE-":
                    settings_window["-TOGGLE-MUTE-"].metadata = not settings_window["-TOGGLE-MUTE-"].metadata
                    settings_window["-TOGGLE-MUTE-"].update(
                        image_data=self.TOGGLE_ON_B64 if settings_window["-TOGGLE-MUTE-"].metadata else self.TOGGLE_OFF_B64)

                    self.settings["-mute-athan-"] = settings_window["-TOGGLE-MUTE-"].metadata

                elif event2 == "-TOGGLE-CUSTOM-ATHAN-":
                    settings_window["-TOGGLE-CUSTOM-ATHAN-"].metadata = not settings_window["-TOGGLE-CUSTOM-ATHAN-"].metadata
                    settings_window["-TOGGLE-CUSTOM-ATHAN-"].update(
                        image_data=self.TOGGLE_ON_B64 if settings_window["-TOGGLE-CUSTOM-ATHAN-"].metadata else self.TOGGLE_OFF_B64)

                    self.settings["-use-custom-athan-"] = settings_window["-TOGGLE-CUSTOM-ATHAN-"].metadata

                    settings_window["-DROPDOWN-ATHANS-"].update(
                        disabled=self.settings["-use-custom-athan-"])
                    settings_window["-CUSTOM-ATHAN-BROWSE-"].update(
                        disabled=not self.settings["-use-custom-athan-"])

                    if self.settings["-use-custom-athan-"]:
                        settings_window["-DROPDOWN-ATHANS-"].update(
                            value="Custom")
                    else:
                        settings_window["-DROPDOWN-ATHANS-"].update(
                            value=self.settings["-athan-sound-"][:-4].replace("_", " "))

                elif event2 == "-TOGGLE-GRAPHIC-":
                    settings_window["-TOGGLE-GRAPHIC-"].metadata = not settings_window["-TOGGLE-GRAPHIC-"].metadata
                    settings_window["-TOGGLE-GRAPHIC-"].update(
                        image_data=self.TOGGLE_ON_B64 if settings_window["-TOGGLE-GRAPHIC-"].metadata else self.TOGGLE_OFF_B64)

                elif event2 == "-DROPDOWN-LANG-" and self.settings["-lang-"] != values2["-DROPDOWN-LANG-"]:
                    self.settings["-lang-"] = values2["-DROPDOWN-LANG-"]
                    self.restart_app = self.yes_or_no_popup(
                        "App language was changed, do you want to restart?")
                    if self.restart_app:
                        settings_window.write_event_value(
                            "-DONE-", "-RESTART-")

                elif event2 == "-DROPDOWN-THEMES-":
                    self.chosen_theme = values2["-DROPDOWN-THEMES-"]
                    if self.chosen_theme != self.settings["-theme-"]:
                        self.restart_app = self.yes_or_no_popup(
                            "Theme was changed, Do you want to restart application?")
                        if self.restart_app:
                            settings_window.write_event_value(
                                "-DONE-", "-RESTART-")

                elif event2 == "-DROPDOWN-ATHANS-":
                    # get a list of all athans currently in folder
                    # as user might have downloaded before
                    DOWNLOADED_ATHANS = os.listdir(self.ATHANS_DIR)
                    # convert option into filename
                    chosen_athan = f"{values2['-DROPDOWN-ATHANS-'].replace(' ', '_')}.wav"

                    if chosen_athan in DOWNLOADED_ATHANS:  # athan is already in Athans directory
                        self.settings["-athan-sound-"] = chosen_athan
                        athan_playing = self.play_current_athan()

                    else:  # athan is not on pc, will be downloaded from the internet
                        settings_window["-DONE-"].update(disabled=True)
                        settings_window["-RESTART-"].update(disabled=True)
                        settings_window["-EXIT-"].update(disabled=True)
                        settings_window["-DISPLAYED-MSG-"].update(
                            value=self.translator.translate("Establishing connection..."))
                        settings_window.refresh()

                        mixer.music.unload()

                        # run the download function to get athan from archive
                        downloaded = self.download_athan(chosen_athan)
                        if downloaded:  # if all went well, set as new athan and play audio
                            self.settings["-athan-sound-"] = chosen_athan
                            settings_window["-DISPLAYED-MSG-"].update(
                                value=self.translator.translate("Current athan"))
                            settings_window.refresh()

                            athan_playing = self.play_current_athan()

                        else:  # something messed up during download or no internet
                            settings_window["-DISPLAYED-MSG-"].update(
                                value=self.translator.translate("Current athan"))
                            settings_window["-DROPDOWN-ATHANS-"].update(
                                value=self.settings["-athan-sound-"][:-4].replace("_", " "))
                            self.application_tray.show_message(
                                title="Download Failed", message=f"Couldn't download athan file: {chosen_athan}")

                        settings_window["-DONE-"].update(disabled=False)
                        settings_window["-RESTART-"].update(disabled=False)
                        settings_window["-EXIT-"].update(disabled=False)
                    # Debugging
                    print("[DEBUG] Current athan:",
                          self.settings["-athan-sound-"])

        # close application on exit
        self.close_app_windows()

    def close_app_windows(self):
        """function to properly close all app windows before shutting down"""
        try:

            if self.choose_location:
                self.choose_location.close()
                del self.choose_location

        except AttributeError:
            pass

        try:

            if self.application_tray:
                self.application_tray.close()
                del self.application_tray

            if self.window:
                self.window.close()
                del self.window

        except AttributeError:
            pass

# ------------------------------------- Starts The GUI ------------------------------------- #


if __name__ == "__main__":
    RESTART_APP = True
    while RESTART_APP:

        app = Athany()
        if app.calculation_data:
            app.setup_inital_layout()
            # app.init_layout will be set by the previous line
            app.display_main_window(app.init_layout)

            # If user doesn't want to save settings, delete saved entries before closing
            if not app.save_loc_check:
                app.settings.delete_entry("-location-")

            if app.chosen_theme:  # if user changed theme in settings, save his choice
                app.settings["-theme-"] = app.chosen_theme

        RESTART_APP = app.restart_app
