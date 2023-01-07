import os
import json
import sys
import datetime
import requests
import simpleaudio
import PySimpleGUI as sg
from psgtray import SystemTray
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


def yes_or_no_popup(text="An error occurred, Do you want to restart the application?"):
    """function to display an error window & prompt the user to try again"""
    ans, _ = sg.Window("Confirm", [[sg.T(text)],
                                   [sg.Push(), sg.Yes(s=10), sg.No(s=10)]], keep_on_top=True, disable_close=True).read(close=True)
    if ans == "Yes":
        return True
    else:
        return False


class Athany:
    """Python application to fetch prayer times, display them in a GUI and play adhan"""
    # ------------------------------------- Application Settings --------------------------------- #

    def __init__(self) -> None:
        self.DATA_DIR = os.path.join(os.path.dirname(
            os.path.abspath(__file__)),  "Data")
        self.ATHANS_DIR = os.path.join(self.DATA_DIR, "Athans")

        if not os.path.exists(self.DATA_DIR):
            os.mkdir(self.DATA_DIR)
        if not os.path.exists(self.ATHANS_DIR):
            os.mkdir(self.ATHANS_DIR)

        self.settings = sg.UserSettings(
            filename="athany-config.json", path=self.DATA_DIR)
        if not self.settings["-theme-"]:
            self.settings["-theme-"] = "DarkAmber"
        if not self.settings["-mute-athan-"]:
            self.settings["-mute-athan-"] = False
        if not self.settings["-last-time-down-12-mons-"]:
            self.settings["-last-time-down-12-mons-"] = dict()
        if not self.settings["-athan-sound-"] or \
                self.settings["-athan-sound-"] not in os.listdir(self.ATHANS_DIR):
            self.settings["-athan-sound-"] = "Default.wav"

        self.UPCOMING_PRAYERS = []
        self.save_loc_check = False
        self.available_themes = ["DarkAmber", "DarkBlack1", "DarkBlue13", "DarkBlue17", "DarkBrown", "DarkBrown2", "DarkBrown7", "DarkGreen7",
                                 "DarkGrey2", "DarkGrey5", "DarkGrey8", "DarkGrey10", "DarkGrey11", "DarkGrey13", "DarkPurple7", "DarkTeal10", "DarkTeal11"]
        self.API_ENDPOINT = "https://api.aladhan.com/v1/calendarByCity"
        self.FUROOD_NAMES = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
        with open(os.path.join(self.DATA_DIR, "available_adhans.txt"), encoding="utf-8") as adhans:
            self.AVAILABLE_ADHANS = adhans.read().strip().split("\n")

        if sys.platform == "win32":
            self.ARABIC_FONT = "Arabic\ Typesetting 20"
            self.MONO_FONT = "consolas 10"
        else:
            self.ARABIC_FONT = "Segoe\ UI 12"
            self.MONO_FONT = "Hack 9"
        self.GUI_FONT = "Segoe\ UI 11"
        self.BUTTON_FONT = "Helvetica 9"

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

        sg.theme(self.settings["-theme-"])
        sg.set_global_icon(self.APP_ICON)

        self.restart_app = False
        self.location_api = None
        self.chosen_theme = None
        self.current_fard = None
        self.end_of_month_hijri = None
        self.download_thread_active = False
        self.location_win_layout = [
            [
                sg.Text("Set your location", size=(50, 1), key="-LOC-TXT-")
            ],
            [
                sg.Text("City"),
                sg.Input(size=(15, 1), key="-CITY-", focus=True),
                sg.Text("Country"),
                sg.Input(size=(15, 1), key="-COUNTRY-"),
                sg.Push(),
                sg.Checkbox("Save settings", key="-SAVE-LOC-CHECK-")
            ],
            [
                sg.Button("Ok", size=(10, 1), key="-OK-",
                          font=self.BUTTON_FONT, bind_return_key=True),
                sg.Button("Use current location",
                          key="-USE-CURRENT-LOCATION-", font=self.BUTTON_FONT),
                sg.Text(key="-AUTO-LOCATION-"),
                sg.Push(),
                sg.Button("Cancel", size=(10, 1),
                          key="-CANCEL-", font=self.BUTTON_FONT)
            ]
        ]

        self.now = datetime.datetime.now()
        self.tomorrow = self.now+datetime.timedelta(days=1)

        # self.current_m_data will either be a dict (api json response) or None
        self.current_m_data = self.choose_location_if_not_saved()

    # ------------------------------------- Main Application logic ------------------------------- #

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

                progress_layout = [
                    [sg.Text(
                        f"Downloading {athan_filename} ({file_size//1024} KB)...")],
                    [sg.ProgressBar(max_value=file_size,
                                    size=(20, 10), expand_x=True, orientation="h", key="-PROGRESS-METER-")],
                    [sg.Push(), sg.Button("Cancel")]
                ]

                prog_win = sg.Window("Download athan",
                                     progress_layout, keep_on_top=True, icon=self.DOWNLOAD_ICON_B64, enable_close_attempted_event=True)

                dl = 0
                for chunk in file_data.iter_content(chunk_size=4096):
                    dl += len(chunk)
                    athan_file.write(chunk)

                    prog_e = prog_win.read(timeout=10)[0]
                    prog_win.make_modal()
                    if prog_e in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "Cancel"):
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

    def play_current_athan(self) -> simpleaudio.PlayObject:
        """ fetches current settings for athan and plays the corresponding athan
        :return: (simpleaudio.PlayObject) play object to control playback of athan
        """
        current_athan_path = os.path.join(
            self.ATHANS_DIR, self.settings["-athan-sound-"])
        wave_obj = simpleaudio.WaveObject.from_wave_file(current_athan_path)
        play_obj = wave_obj.play()
        return play_obj

    def download_12_months(self):
        """function that downloads api data for the next 12 months"""
        if not self.download_thread_active:
            self.download_thread_active = True
            download_year = self.now.year
            for mon_d in range(1, 13):
                download_mon = (mon_d + self.now.month) % 12
                if download_mon == 0:
                    download_mon = 12
                elif download_mon <= self.now.month:
                    download_year = self.now.year+1
                downloaded = False
                while not downloaded:
                    downloaded = not isinstance(self.fetch_calendar_data(self.settings["-city-"],
                                                                         self.settings["-country-"],
                                                                         download_mon,
                                                                         download_year), str)

            self.settings["-last-time-down-12-mons-"][f"{self.settings['-city-']}-{self.settings['-country-']}"] = f"{self.now.month}-{self.now.year}"
            self.settings.save()
            self.download_thread_active = False

    def get_current_location(self) -> tuple[str, str]:
        """ function that gets the current city and country of the user IP\n
        :return: (Tuple[str, str]) tuple containing 2 strings of the city & country fetched
        """
        try:
            ipinfo_res = requests.get(
                "https://ipinfo.io/json", timeout=10)

            if ipinfo_res.status_code == 200:
                ipinfo_json = ipinfo_res.json()
                ret_val = (ipinfo_json["city"], ipinfo_json["country"])
            else:
                ipgeoloc_res = requests.get(
                    "https://api.ipgeolocation.io/ipgeo?apiKey=397b014528ba421cafcc5df4d00c9e9a", timeout=10)

                if ipgeoloc_res.status_code == 200:
                    ipgeoloc_json = ipgeoloc_res.json()
                    ret_val = (ipgeoloc_json["city"],
                               ipgeoloc_json["country_code2"])
                else:
                    raise requests.exceptions.ConnectionError

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            ret_val = "RequestError"

        return ret_val

    def fetch_calendar_data(self, cit: str, count: str, month: str, year: str) -> dict:
        """check if calendar data for the city+country+month+year exists and fetch it if not
        :param cit: (str) city to get data for
        :param count: (str) country to get data for
        :param month: (str) month to get times for
        :param year: (str) year to get times for
        :return: (dict) api response json data dictionary
        """
        json_month_file = os.path.join(
            self.DATA_DIR, f"{year}-{month}-{cit}-{count}.json")

        if not os.path.exists(json_month_file):
            try:
                res = requests.get(
                    self.API_ENDPOINT+f"?city={cit}&country={count}&month={month}&year={year}", timeout=20)
            except (requests.Timeout, requests.ConnectionError):
                return "RequestError"

            if res.status_code != 200:  # if invalid city or country, return None instead of filename
                return None

            with open(json_month_file, mode="w", encoding="utf-8") as f:
                f.write(res.text)

        with open(json_month_file, encoding="utf-8") as month_prayers:
            month_data = json.load(month_prayers)

        return month_data

    def get_hijri_date_from_json(self, date: datetime.datetime, api_res) -> str:
        """function to return arabic hijri date string to display in main window
        :param date: (datetime.datetime) date to get hijri date for
        :param api_res: (dict) api response to extract hijri date from
        :return: (str) Arabic string of current Hijri date
        """
        hijri_date = api_res["data"][date.day - 1]["date"]["hijri"]
        text = f"{hijri_date['weekday']['ar']} {hijri_date['day']} {hijri_date['month']['ar']} {hijri_date['year']}"
        return display_ar_text(text=text)

    def set_main_layout_and_tomorrow_prayers(self, api_res: dict) -> tuple[list, dict]:
        """sets the prayer times window layout and
        the inital upcoming prayers on application startup
        :param api_res: (dict) - adhan api month json response as a dictionary
        """
        self.now = datetime.datetime.now()
        self.tomorrow = self.now+datetime.timedelta(days=1)
        current_times = api_res["data"][self.now.day-1]["timings"]

        isha_passed = False
        # Check if Isha passed as to get the following day timings
        # Prayer times change after Isha athan to the times of the following day
        # if self.now is after current Isha time
        if self.now > datetime.datetime(self.now.year, self.now.month, self.now.day, hour=int(current_times["Isha"][:2]), minute=int(current_times["Isha"][3:5])):
            # replace all prayer times with the next day prayers
            # SPECIAL CASE: if today is the last day in the month, fetch new month calendar
            if self.tomorrow.day < self.now.day:
                self.end_of_month_hijri = self.get_hijri_date_from_json(
                    self.now, api_res=api_res)

                api_res = self.fetch_calendar_data(
                    self.settings["-city-"],
                    self.settings["-country-"],
                    self.tomorrow.month,
                    self.tomorrow.year)

                while api_res == "RequestError":
                    keep_trying = yes_or_no_popup(
                        "Couldn't fetch new month data, try again?")
                    if not keep_trying:
                        sys.exit()
                    else:
                        api_res = self.fetch_calendar_data(
                            self.settings["-city-"],
                            self.settings["-country-"],
                            self.tomorrow.month,
                            self.tomorrow.year)

                current_times = api_res["data"][self.tomorrow.day - 1]["timings"]
                # remove last month data after setting up the new month json file
                os.remove(os.path.join(
                    self.DATA_DIR, f"{self.now.year}-{self.now.month}-{self.settings['-city-']}-{self.settings['-country-']}.json"
                )
                )
            else:
                current_times = api_res["data"][self.now.day]["timings"]

            isha_passed = True

        self.current_m_data = api_res
        # loop through all prayer times to convert timing to datetime objects
        for prayer_name, time_str in current_times.items():
            # to adjust the day, month, year of the prayer datetime object
            date = self.tomorrow if isha_passed else self.now

            # time_str is in the format "05:24 (EET)"
            current_times[prayer_name] = datetime.datetime(
                date.year,
                date.month,
                date.day,
                hour=int(time_str[:2]),
                minute=int(time_str[3:5])
            )

        print(" DEBUG ".center(50, "="))

        self.init_layout = [
            [
                sg.Text(key="-TODAY-", font=self.GUI_FONT+" bold"),
                sg.Push(),
                sg.Text(sg.SYMBOL_CIRCLE, font="Segoe\ UI 6"),
                sg.Push(),
                sg.Text(key="-TODAY_HIJRI-", font=self.ARABIC_FONT)
            ],
            [
                sg.Text(sg.SYMBOL_LEFT_ARROWHEAD, font=self.GUI_FONT),
                sg.HorizontalSeparator(),
                sg.Text(key="-NEXT-PRAYER-"),
                sg.Text("in", font=self.GUI_FONT),
                sg.Text(font=self.GUI_FONT, key="-TIME-D-"),
                sg.HorizontalSeparator(),
                sg.Text(sg.SYMBOL_RIGHT_ARROWHEAD, font=self.GUI_FONT)
            ]
        ]

        for prayer, time in current_times.items():  # append upcoming prayers to list
            # setting the main window layout with the inital prayer times
            if prayer in self.FUROOD_NAMES or prayer == "Sunrise":
                self.init_layout.append(
                    [
                        sg.Text(f"{prayer}:", key=f"-{prayer.upper()}-",
                                font=self.GUI_FONT),
                        sg.Push(),
                        sg.Text(time.strftime('%I:%M %p'), key=f"-{prayer.upper()}-TIME-",
                                font=self.GUI_FONT)
                    ]
                )

                print(prayer, time)  # Debugging
                if self.now < time:  # adding upcoming prayers from the point of application start, this list will be modified as prayer times pass
                    self.UPCOMING_PRAYERS.append([prayer, time])
                else:
                    self.current_fard = [prayer, time]

        # the rest of the main window layout
        self.init_layout += [
            [sg.HorizontalSeparator(color="dark brown")],
            [
                sg.Button("Settings", key="-SETTINGS-",
                          font=self.BUTTON_FONT),
                sg.Button("Stop athan", key="-STOP-ATHAN-",
                          font=self.BUTTON_FONT),
                sg.Push(),
                sg.Text("current time", font=self.MONO_FONT),
                sg.Text("~", font=self.MONO_FONT),
                sg.Text(key="-CURRENT-TIME-", font=self.MONO_FONT)
            ]
        ]

        if not self.current_fard:
            self.current_fard = ["Isha", current_times["Isha"]]

        print("="*50)

    # ----------------------------- Main Windows And SystemTray Functions ------------------------ #

    def choose_location_if_not_saved(self) -> dict:
        """function to get & set the user location
        :return: (dict) dictionary of the current month json data
        """
        if self.settings["-city-"] is None and self.settings["-country-"] is None:
            # If there are no saved settings, display the choose location window to set these values
            self.choose_location = sg.Window("Athany - set location",
                                             self.location_win_layout,
                                             font=self.GUI_FONT)

            self.choose_location.perform_long_operation(
                self.get_current_location, "-AUTOMATIC-LOCATION-THREAD-")
            while True:
                m_data = False
                event, values = self.choose_location.read()

                if event in (sg.WIN_CLOSED, "-CANCEL-"):
                    self.close_app_windows()
                    break

                elif event == "-AUTOMATIC-LOCATION-THREAD-":
                    self.location_api = values["-AUTOMATIC-LOCATION-THREAD-"]
                    self.choose_location["-AUTO-LOCATION-"].update(value=f"({self.location_api[0]}, {self.location_api[1]})" if not isinstance(
                        self.location_api, str) else "(Internet connection required)")
                else:
                    if event == "-OK-" and values["-CITY-"].strip() and values["-COUNTRY-"].strip():
                        city = values["-CITY-"].strip().capitalize()
                        country = values["-COUNTRY-"].strip().capitalize()
                        if len(country) == 2:
                            country = country.upper()

                        self.choose_location["-LOC-TXT-"].update(
                            value=f"Fetching prayer times for {city}, {country}....")
                        self.choose_location.refresh()

                        m_data = self.fetch_calendar_data(city,
                                                          country,
                                                          self.now.month,
                                                          self.now.year)

                        if m_data is None:  # if invalid city/country dont continue
                            self.choose_location["-LOC-TXT-"].update(
                                value="Invalid city or country, enter a valid location")
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
                                value="An error occurred, try entering location manually")
                            self.choose_location.refresh()

                        else:
                            city = self.location_api[0]
                            country = self.location_api[1]

                            self.choose_location["-LOC-TXT-"].update(
                                value=f"Fetching prayer times for {city}, {country}...")
                            self.choose_location.refresh()

                            m_data = self.fetch_calendar_data(city,
                                                              country,
                                                              self.now.month,
                                                              self.now.year)

                    if not m_data:
                        continue

                    if m_data == "RequestError":
                        self.choose_location["-LOC-TXT-"].update(
                            value="Internet connection required")
                    else:
                        self.settings["-city-"] = city
                        self.settings["-country-"] = country

                        self.save_loc_check = values["-SAVE-LOC-CHECK-"]

                        # close location choosing window
                        self.close_app_windows()

                        return m_data

        else:
            self.save_loc_check = True
            m_data = self.fetch_calendar_data(
                self.settings["-city-"],
                self.settings["-country-"],
                self.now.month,
                self.now.year)

            return m_data

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

    def display_main_window(self, main_win_layout):
        """Displays the main application window, keeps running until window is closed
        :param main_win_layout: (list) main application window layout
        """
        self.window = sg.Window("Athany: a python athan app",
                                main_win_layout,
                                enable_close_attempted_event=True,
                                finalize=True)

        self.application_tray = self.start_system_tray(win=self.window)
        win2_active = False
        athan_play_obj = None
        while True:
            self.now = datetime.datetime.now().replace(microsecond=0)

            if self.now >= self.UPCOMING_PRAYERS[0][1]:
                # remove current fard from list, update remaining time to be 0 before playing athan sound
                self.current_fard = self.UPCOMING_PRAYERS.pop(0)

                if self.current_fard[0] != "Sunrise":
                    self.application_tray.show_message(
                        title="Athany", message=f"It's time for {self.current_fard[0]} prayer 🕌")
                    # play athan sound from user athan sound settings (if athan sound not muted)
                    try:
                        if not self.settings["-mute-athan-"]:
                            athan_play_obj = self.play_current_athan()
                    except:
                        print(
                            "[DEBUG] Couldn't play athan audio, rechoose your athan in the app settings")

                for f in self.FUROOD_NAMES+["Sunrise"]:
                    self.window[f"-{f.upper()}-"].update(font=self.GUI_FONT,
                                                         text_color=sg.theme_text_color())
                    self.window[f"-{f.upper()}-TIME-"].update(font=self.GUI_FONT,
                                                              text_color=sg.theme_text_color())

                # If last prayer in list (Isha), then update the whole application with the next day prayers starting from Fajr
                if len(self.UPCOMING_PRAYERS) == 0:
                    self.set_main_layout_and_tomorrow_prayers(
                        self.fetch_calendar_data(self.settings["-city-"],
                                                 self.settings["-country-"],
                                                 self.now.month,
                                                 self.now.year)
                    )
                    for prayer in self.UPCOMING_PRAYERS:
                        self.window[f"-{prayer[0].upper()}-TIME-"].update(
                            value=prayer[1].strftime("%I:%M %p"))

            # get remaining time till next prayer
            time_d = self.UPCOMING_PRAYERS[0][1] - self.now

            # Highlight current fard in main window
            if self.current_fard[0] == "Sunrise":
                self.window["-FAJR-"].update(
                    font=self.GUI_FONT+" italic", text_color='#cd8032')
                self.window["-FAJR-TIME-"].update(
                    font=self.GUI_FONT+" italic", text_color='#cd8032')
            else:
                self.window[f"-{self.current_fard[0].upper()}-"].update(
                    font=self.GUI_FONT+" italic", text_color='#cd8032')
                self.window[f"-{self.current_fard[0].upper()}-TIME-"].update(
                    font=self.GUI_FONT+" italic", text_color='#cd8032')

            # update the main window with the next prayer and remaining time
            self.window["-NEXT-PRAYER-"].update(
                value=f"{self.UPCOMING_PRAYERS[0][0]}", font=self.GUI_FONT+" bold")
            self.window["-TIME-D-"].update(value=str(time_d))

            # update the current dates
            self.window["-CURRENT-TIME-"].update(
                value=self.now.strftime("%I:%M %p"))
            self.window["-TODAY-"].update(
                value=self.now.date().strftime("%a %d %b %y"))

            # update hijri date from api response
            if self.now.month == self.UPCOMING_PRAYERS[0][1].month:
                self.window["-TODAY_HIJRI-"].update(
                    value=self.get_hijri_date_from_json(self.now, api_res=self.current_m_data))
            else:  # self.end_of_month_hijri will be set by the upcoming prayers function after Isha
                self.window["-TODAY_HIJRI-"].update(
                    value=self.end_of_month_hijri)

            # update system tray tooltip also
            self.application_tray.set_tooltip(
                f"Next prayer: {self.UPCOMING_PRAYERS[0][0]} in {time_d}")

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

            elif event1 in ("-STOP-ATHAN-", "Stop athan") and athan_play_obj:
                if athan_play_obj.is_playing():
                    athan_play_obj.stop()

            # if clicked settings button, open up the settings window and read values from it along with the main window
            elif event1 in ("-SETTINGS-", "Settings") and not win2_active:
                win2_active = True
                current_athan = self.settings["-athan-sound-"]\
                    .split(".")[0].replace("_", " ")
                last_time_down_12_mons = self.settings['-last-time-down-12-mons-'].get(
                    f"{self.settings['-city-']}-{self.settings['-country-']}", "never")

                settings_layout = [
                    [
                        sg.Text("Mute athan", pad=(5, 0)),
                        sg.Push(),
                        sg.Button(image_data=self.TOGGLE_ON_B64 if self.settings["-mute-athan-"] else self.TOGGLE_OFF_B64,
                                  key="-TOGGLE-MUTE-", pad=(5, 0), button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                  border_width=0, metadata=self.settings["-mute-athan-"])
                    ],
                    [
                        sg.Text(
                            f"Save location ({self.settings['-city-']}, {self.settings['-country-']})", pad=(5, 0)),
                        sg.Push(),
                        sg.Button(image_data=self.TOGGLE_ON_B64 if self.save_loc_check else self.TOGGLE_OFF_B64,
                                  key="-TOGGLE-GRAPHIC-", button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                  border_width=0, pad=(5, 0), metadata=self.save_loc_check)
                    ],
                    [
                        sg.Text("Current Theme:", pad=(5, 10)),
                        sg.Push(),
                        sg.Combo(enable_events=True, values=self.available_themes, key="-DROPDOWN-THEMES-",
                                 readonly=True, default_value=self.settings["-theme-"], font=self.BUTTON_FONT, pad=(5, 10))
                    ],
                    [
                        sg.Text("Current Athan:",
                                key="-DISPLAYED-MSG-", pad=(5, 10)),
                        sg.Push(),
                        sg.Combo(enable_events=True, values=self.AVAILABLE_ADHANS, key="-DROPDOWN-ATHANS-",
                                 readonly=True, default_value=current_athan, font=self.BUTTON_FONT, pad=(5, 10))
                    ],
                    [
                        sg.Button("Download next 12 months data",
                                  key="-GET-NEXT-12-MON-", disabled=self.download_thread_active or last_time_down_12_mons == f"{self.now.month}-{self.now.year}", font=self.BUTTON_FONT),
                        sg.Text(f"last updated: {last_time_down_12_mons}", key="-DOWN-12-MON-PROG-",
                                font="Segoe\ UI 8 bold"),
                        sg.Push(),
                        sg.Button("Done", key="-DONE-",
                                  font=self.BUTTON_FONT, s=6, pad=(5, 15))
                    ]
                ]

                settings_window = sg.Window("Athany - settings",
                                            settings_layout,
                                            icon=self.SETTINGS_ICON,
                                            font=self.GUI_FONT,
                                            keep_on_top=True)

            # If 2nd window (settings window) is open, read values from it
            if win2_active:
                event2, values2 = settings_window.read(timeout=100)

                if event2 in (sg.WIN_CLOSED, "-DONE-"):
                    win2_active = False
                    self.save_loc_check = settings_window["-TOGGLE-GRAPHIC-"].metadata
                    settings_window.close()

                elif event2 == "-TOGGLE-MUTE-":
                    settings_window["-TOGGLE-MUTE-"].metadata = not settings_window["-TOGGLE-MUTE-"].metadata
                    settings_window["-TOGGLE-MUTE-"].update(
                        image_data=self.TOGGLE_ON_B64 if settings_window["-TOGGLE-MUTE-"].metadata else self.TOGGLE_OFF_B64)

                    self.settings["-mute-athan-"] = settings_window["-TOGGLE-MUTE-"].metadata

                elif event2 == "-TOGGLE-GRAPHIC-":
                    settings_window["-TOGGLE-GRAPHIC-"].metadata = not settings_window["-TOGGLE-GRAPHIC-"].metadata
                    settings_window["-TOGGLE-GRAPHIC-"].update(
                        image_data=self.TOGGLE_ON_B64 if settings_window["-TOGGLE-GRAPHIC-"].metadata else self.TOGGLE_OFF_B64)

                elif event2 == "-DROPDOWN-THEMES-":
                    self.chosen_theme = values2["-DROPDOWN-THEMES-"]
                    if self.chosen_theme != self.settings["-theme-"]:
                        self.restart_app = yes_or_no_popup(
                            f"Theme was changed to {self.chosen_theme}, Do you want to restart application?")
                        if self.restart_app:
                            if athan_play_obj:
                                athan_play_obj.stop()

                            win2_active = False
                            self.save_loc_check = settings_window["-TOGGLE-GRAPHIC-"].metadata
                            settings_window.close()
                            self.window.write_event_value("-EXIT-", None)

                elif event2 == "-DROPDOWN-ATHANS-":
                    # get a list of all athans currently in folder as user might have downloaded before
                    DOWNLOADED_ATHANS = os.listdir(self.ATHANS_DIR)
                    # convert option into filename
                    chosen_athan = f"{values2['-DROPDOWN-ATHANS-'].replace(' ', '_')}.wav"

                    if chosen_athan in DOWNLOADED_ATHANS:  # athan is already in Athans directory
                        self.settings["-athan-sound-"] = chosen_athan
                        if athan_play_obj:
                            athan_play_obj.stop()
                        athan_play_obj = self.play_current_athan()

                    else:  # athan is not on pc, will be downloaded from the internet
                        settings_window["-DONE-"].update(disabled=True)
                        settings_window["-DISPLAYED-MSG-"].update(
                            value="Establishing connection...")
                        settings_window.refresh()

                        if athan_play_obj:
                            athan_play_obj.stop()

                        # run the download function to get athan from archive
                        downloaded = self.download_athan(chosen_athan)
                        if downloaded:  # if all went well, set as new athan and play audio
                            self.settings["-athan-sound-"] = chosen_athan
                            settings_window["-DISPLAYED-MSG-"].update(
                                value="Current Athan:")
                            settings_window.refresh()

                            athan_play_obj = self.play_current_athan()

                        else:  # something messed up during download or no internet
                            settings_window["-DISPLAYED-MSG-"].update(
                                value="Current Athan:")
                            settings_window["-DROPDOWN-ATHANS-"].update(
                                value=self.settings["-athan-sound-"].split(".")[0].replace("_", " "))
                            self.application_tray.show_message(
                                title="Download Failed", message=f"Couldn't download athan file: {chosen_athan}")

                        settings_window["-DONE-"].update(disabled=False)
                    # Debugging
                    print("[DEBUG] Current athan:",
                          self.settings["-athan-sound-"])

                # this event will fire only if the button is enabled
                # the button won't be enabled if there's a thread already downloading this data
                # or the function has already been called this month
                elif event2 == "-GET-NEXT-12-MON-":
                    settings_window.perform_long_operation(
                        self.download_12_months, "-DOWNLOADED-12-MONS-")
                    settings_window["-GET-NEXT-12-MON-"].update(
                        disabled=True)
                    settings_window["-DOWN-12-MON-PROG-"].update(
                        value="Downloading data, please wait...")

                elif event2 == "-DOWNLOADED-12-MONS-":
                    settings_window["-DOWN-12-MON-PROG-"].update(
                        value="Download completed successfully")

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
        if app.current_m_data:
            app.set_main_layout_and_tomorrow_prayers(app.current_m_data)
            # app.init_layout will be set by the previous line
            app.display_main_window(app.init_layout)

            # If user doesn't want to save settings, delete saved entries before closing
            if not app.save_loc_check:
                if app.settings["-city-"] and app.settings["-country-"]:
                    app.settings.delete_entry("-city-")
                    app.settings.delete_entry("-country-")

            if app.chosen_theme:  # if user changed theme in settings, save his choice
                app.settings["-theme-"] = app.chosen_theme

        RESTART_APP = app.restart_app
