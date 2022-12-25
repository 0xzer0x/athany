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


def keep_trying_popup(text="A connection error occurred, Do you want to try again?"):
    ans, _ = sg.Window("Try Again?", [[sg.T(text)],
                                      [sg.Yes(s=10), sg.No(s=10)]], disable_close=True).read(close=True)
    if ans == "Yes":
        return True
    else:
        return False


class Athany():
    """Python application to fetch prayer times, display them in a GUI and play adhan"""
    # ------------------------------------- Application Settings ------------------------------------- #

    def __init__(self) -> None:
        self.DATA_DIR = os.path.join(os.path.dirname(
            os.path.abspath(__file__)),  "Data")
        self.ATHANS_DIR = os.path.join(self.DATA_DIR, "Athans")

        if not os.path.exists(self.DATA_DIR):
            os.mkdir(self.DATA_DIR)
        if not os.path.exists(self.ATHANS_DIR):
            os.mkdir(self.ATHANS_DIR)

        sg.theme("DarkAmber")
        self.settings = sg.UserSettings(
            filename="athany-config.json", path=self.DATA_DIR)
        if not self.settings["-athan-sound-"] or self.settings["-athan-sound-"] not in os.listdir(self.ATHANS_DIR):
            self.settings["-athan-sound-"] = "Default.wav"
        if not self.settings["-mute-athan-"]:
            self.settings["-mute-athan-"] = False

        self.UPCOMING_PRAYERS = []
        self.save_loc_check = False
        self.API_ENDPOINT = "https://api.aladhan.com/v1/calendarByCity"
        self.FUROOD_NAMES = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
        with open(os.path.join(self.DATA_DIR, "available_adhans.txt"), encoding="utf-8") as adhans:
            self.AVAILABLE_ADHANS = adhans.read().strip().split("\n")

        self.GUI_FONT = "Segoe\ UI 11"
        self.BUTTON_FONT = "Helvetica 10"
        self.ARABIC_FONT = "Segoe\ UI 12" if sys.platform != "win32" else "Arabic\ Typesetting 20"

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

        self.now = datetime.datetime.now()
        self.tomorrow = self.now+datetime.timedelta(days=1)
        self.location_api = self.get_current_location()
        self.location_win_layout = [[sg.Text("Set your location", size=(50, 1), key="-LOC TXT-")],
                                    [sg.Text("City"), sg.Input(size=(15, 1), key="-CITY-", focus=True),
                                     sg.Text("Country"), sg.Input(size=(15, 1), key="-COUNTRY-"), sg.Push(), sg.Checkbox("Save settings", key="-SAVE_LOC_CHECK-")],
                                    [sg.Button("Ok", key="-OK-", size=(10, 1), font=self.BUTTON_FONT, bind_return_key=True),
                                     sg.Button(
                                         "Use current location", key="-USE-CURRENT-LOCATION-", font=self.BUTTON_FONT),
                                     sg.Text(f"({self.location_api[0]}, {self.location_api[1]})" if self.location_api !=
                                             "RequestError" else "(Internet connection required)", key="-AUTO-LOCATION-"),
                                     sg.Push(), sg.Button("Cancel", key="-CANCEL-", size=(10, 1), font=self.BUTTON_FONT)]]

        self.set_main_layout_and_tomorrow_prayers(
            self.choose_location_if_not_saved())
    # ------------------------------------- Main Application logic ------------------------------------- #

    def download_athan(self, athan_filename: str) -> bool:
        """Function to download athans from app directory on archive.org
        :param athan_filename: (str) name of .wav file to download from archive.org
        :return: (bool) True if the download completed successfully without errors, False otherwise
        """
        try:
            prog_win = None
            saved_file = os.path.join(self.ATHANS_DIR, athan_filename)
            with open(saved_file, "wb") as athan_file:
                file_data = requests.get("https://archive.org/download/athany-data/"+athan_filename,
                                         stream=True, timeout=10)
                file_size = int(file_data.headers.get("content-length"))

                progress_layout = [
                    [sg.Text(
                        f"Downloading {athan_filename} ({file_size//1024} KB) from archive...")],
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
                        raise Exception

                    prog_win["-PROGRESS-METER-"].update(current_count=dl)

                prog_win.close()
                del prog_win

            return True
        except:
            if prog_win:
                prog_win.close()
                del prog_win

            os.remove(saved_file)
            return False

    def download_12_months(self):
        """function that downloads api data for the next 12 months"""
        if self.settings["-last-time-down-12-mons-"] != f"{self.now.month}-{self.now.year}":
            download_year = self.now.year
            for mon_d in range(1, 13):
                download_mon = (mon_d + self.now.month) % 12
                if download_mon == 0:
                    download_mon = 12
                elif download_mon <= self.now.month:
                    download_year = self.now.year+1
                downloaded = False
                while not downloaded:
                    downloaded = not isinstance(self.fetch_calender_data(self.settings["-city-"],
                                                                         self.settings["-country-"],
                                                                         download_mon,
                                                                         download_year), str)
                    self.settings["-last-time-down-12-mons-"] = f"{self.now.month}-{self.now.year}"

    def play_current_athan(self) -> simpleaudio.PlayObject:
        """ fetches current settings for athan and plays the corresponding athan
        :return: (simpleaudio.PlayObject) play object to control playback of athan
        """
        current_athan_path = os.path.join(
            self.ATHANS_DIR, self.settings["-athan-sound-"])
        wave_obj = simpleaudio.WaveObject.from_wave_file(current_athan_path)
        play_obj = wave_obj.play()
        return play_obj

    def get_current_location(self) -> tuple[str, str]:
        """ function that gets the current city and country of the user IP\n
        :return: (Tuple[str, str]) tuple containing 2 strings of the city & country fetched
        """
        try:
            city_res = requests.get("https://ipinfo.io/city",
                                    timeout=100)
            country_res = requests.get("https://ipinfo.io/country",
                                       timeout=100)
            IP_city = city_res.text.strip()
            IP_country = country_res.text.strip()

            if city_res.status_code != 200 or country_res.status_code != 200:
                raise Exception

            return (IP_city, IP_country)

        except:
            return "RequestError"

    def fetch_calender_data(self, cit: str, count: str, month: str, year: str) -> dict:
        """check if calender data for the city+country+month+year exists and fetch it if not
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
            except:
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
        hirjir_date = api_res["data"][date.day - 1]["date"]["hijri"]
        text = f"{hirjir_date['weekday']['ar']} {hirjir_date['day']} {hirjir_date['month']['ar']} {hirjir_date['year']}"
        return display_ar_text(text=text)

    def set_main_layout_and_tomorrow_prayers(self, api_res: dict) -> tuple[list, dict]:
        """sets the prayer times window layout and sets the inital upcoming prayers on application startup
        :param api_res: (dict) - adhan api month json response as a dictionary
        """
        self.now = datetime.datetime.now()
        self.tomorrow = self.now+datetime.timedelta(days=1)
        current_times = api_res["data"][self.now.day-1]["timings"]

        ISHA_OBJ = current_times["Isha"].split()
        ISHA_PASSED = False
        # Check if Isha passed as to get the following day timings
        # Prayer times change after Isha athan to the times of the following day
        # if self.now is after current Isha time
        if self.now > datetime.datetime.strptime(f"{ISHA_OBJ[0]} {self.now.day} {self.now.month} {self.now.year}", "%H:%M %d %m %Y"):
            # replace all prayer times with the next day prayers
            # SPECIAL CASE: if today is the last day in the month, fetch new month calender
            if self.tomorrow.day < self.now.day:
                self.end_of_month_hijri = self.get_hijri_date_from_json(
                    self.now, api_res=api_res)

                api_res = self.fetch_calender_data(
                    self.settings["-city-"],
                    self.settings["-country-"],
                    self.tomorrow.month,
                    self.tomorrow.year)

                while api_res == "RequestError":
                    keep_trying = keep_trying_popup(
                        "Couldn't fetch new month data, try again?")
                    if not keep_trying:
                        sys.exit()
                    else:
                        api_res = self.fetch_calender_data(
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

            ISHA_PASSED = True

        self.current_m_data = api_res
        # loop through all prayer times to convert timing to datetime objects to be able to preform operations on them
        for k, v in current_times.items():
            # to adjust the day,month, year of the prayer datetime object
            date = self.tomorrow if ISHA_PASSED else self.now
            t = v.split(" ")[0] + f" {date.day} {date.month} {date.year}"
            current_times[k] = datetime.datetime.strptime(
                t, "%H:%M %d %m %Y")

        print(" DEBUG ".center(50, "="))
        self.init_layout = [
            [sg.Text(key="-TODAY-", font=self.GUI_FONT+" bold"),
             sg.Push(),
             sg.Text(sg.SYMBOL_CIRCLE, font="Segoe\ UI 6"),
             sg.Push(),
             sg.Text(key="-TODAY_HIJRI-", font=self.ARABIC_FONT)],
            [sg.Text(sg.SYMBOL_LEFT_ARROWHEAD, font=self.GUI_FONT),
                sg.HorizontalSeparator(),
                sg.Text(font=self.GUI_FONT, key="-NEXT PRAYER-"),
                sg.Text("in", font=self.GUI_FONT),
                sg.Text(font=self.GUI_FONT, key="-TIME_D-"),
                sg.HorizontalSeparator(),
                sg.Text(sg.SYMBOL_RIGHT_ARROWHEAD, font=self.GUI_FONT)]
        ]
        for prayer, time in current_times.items():  # append upcoming prayers to list
            # setting the main window layout with the inital prayer times
            if prayer in self.FUROOD_NAMES or prayer == "Sunrise":
                self.init_layout.append([sg.Text(f"{prayer}:", font=self.GUI_FONT), sg.Push(),
                                         sg.Text(f"{time.strftime('%I:%M %p')}", font=self.GUI_FONT, key=f"-{prayer.upper()} TIME-")])

                print(prayer, time)  # Debugging
                if self.now < time:  # adding upcoming prayers from the point of application start, this list will be modified as prayer times pass
                    self.UPCOMING_PRAYERS.append([prayer, time])

        # the rest of the main window layout
        self.init_layout += [[sg.HorizontalSeparator(color="dark brown")],
                             [sg.Button("Settings", key="-SETTINGS-", font=self.BUTTON_FONT),
                              sg.Button("Stop athan", key="-STOP-ATHAN-",
                                        font=self.BUTTON_FONT),
                              sg.Push(),
                              sg.Text("Current time", font="consolas 10"), sg.Text("~", font="consolas 10"), sg.Text(key="-CURRENT-TIME-", font="consolas 10")]]

        print("="*50)

    # ------------------------------------- Main Windows And SystemTray Functions ------------------------------------- #

    def choose_location_if_not_saved(self) -> dict:
        """function to get & set the user location
        :return: (dict) dictionary of the current month json data
        """
        if self.settings["-city-"] is None and self.settings["-country-"] is None:
            # If there are no saved settings, display the choose location window to set these values
            choose_location = sg.Window("Athany - set location",
                                        self.location_win_layout,
                                        icon=self.APP_ICON,
                                        font=self.GUI_FONT)

            while True:
                m_data = False
                event, values = choose_location.read()

                if event in (sg.WIN_CLOSED, "-CANCEL-"):
                    choose_location.close()
                    del choose_location
                    sys.exit()

                else:
                    if event == "-OK-" and values["-CITY-"].strip() and values["-COUNTRY-"].strip():
                        city = values["-CITY-"].strip().capitalize()
                        country = values["-COUNTRY-"].strip().capitalize()
                        if len(country) == 2:
                            country = country.upper()

                        choose_location["-LOC TXT-"].update(
                            value=f"Fetching prayer times for {city}, {country}....")
                        choose_location.refresh()

                        m_data = self.fetch_calender_data(city,
                                                          country,
                                                          self.now.month,
                                                          self.now.year)

                        if m_data is None:  # if invalid city/country dont continue
                            choose_location["-LOC TXT-"].update(
                                value="Invalid city or country, enter a valid location")
                            choose_location["-CITY-"].update(
                                background_color="dark red")
                            choose_location["-COUNTRY-"].update(
                                background_color="dark red")
                            continue

                    elif event == "-USE-CURRENT-LOCATION-":
                        self.location_api = self.get_current_location(
                        ) if self.location_api == "RequestError" else self.location_api
                        if self.location_api == "RequestError":
                            choose_location["-LOC TXT-"].update(
                                value="An error occurred, try entering location manually")
                            choose_location.refresh()

                        else:
                            city = self.location_api[0]
                            country = self.location_api[1]

                            choose_location["-LOC TXT-"].update(
                                value=f"Fetching prayer times for {city}, {country}...")
                            choose_location.refresh()

                            m_data = self.fetch_calender_data(city,
                                                              country,
                                                              self.now.month,
                                                              self.now.year)

                    if not m_data:
                        continue

                    if m_data == "RequestError":
                        choose_location["-LOC TXT-"].update(
                            value="Internet connection required")
                    else:
                        self.settings["-city-"] = city
                        self.settings["-country-"] = country

                        self.save_loc_check = values["-SAVE_LOC_CHECK-"]

                        # close location choosing window
                        choose_location.close()
                        del choose_location

                        return m_data

        else:
            self.save_loc_check = True
            m_data = self.fetch_calender_data(
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
        window = sg.Window("Athany: a python athan app",
                           main_win_layout,
                           icon=self.APP_ICON,
                           enable_close_attempted_event=True,
                           finalize=True)

        application_tray = self.start_system_tray(win=window)
        win2_active = False
        athan_play_obj = None
        while True:
            self.now = datetime.datetime.now().replace(microsecond=0)

            if self.now >= self.UPCOMING_PRAYERS[0][1]:
                # remove current fard from list, update remaining time to be 0 before playing athan sound
                fard = self.UPCOMING_PRAYERS.pop(0)

                if fard[0] != "Sunrise":
                    application_tray.show_message(
                        title="Athany", message=f"It's time for {fard[0]} prayer 🕌")

                # play athan sound from user athan sound settings (if athan sound not muted)
                    try:
                        if not self.settings["-mute-athan-"]:
                            athan_play_obj = self.play_current_athan()
                    except:
                        print(
                            "[DEBUG] Couldn't play athan audio, rechoose your athan in the app settings")
                # If last prayer in list (Isha), then update the whole application with the next day prayers starting from Fajr
                if len(self.UPCOMING_PRAYERS) == 0:
                    self.set_main_layout_and_tomorrow_prayers(
                        self.fetch_calender_data(self.settings["-city-"],
                                                 self.settings["-country-"],
                                                 self.now.month,
                                                 self.now.year)
                    )
                    for prayer in self.UPCOMING_PRAYERS:
                        window[f"-{prayer[0].upper()} TIME-"].update(
                            value=prayer[1].strftime("%I:%M %p"))

            # get remaining time till next prayer
            time_d = self.UPCOMING_PRAYERS[0][1] - self.now

            # update the main window with the next prayer and remaining time
            window["-NEXT PRAYER-"].update(
                value=f"{self.UPCOMING_PRAYERS[0][0]}", font=self.GUI_FONT+" bold")
            window["-TIME_D-"].update(value=f"{time_d}")
            window["-CURRENT-TIME-"].update(
                value=self.now.strftime("%I:%M %p"))
            # update the current dates
            window["-TODAY-"].update(
                value=self.now.date().strftime("%a %d %b %y"))

            if self.now.month == self.UPCOMING_PRAYERS[0][1].month:
                self.end_of_month_hijri = None
                window["-TODAY_HIJRI-"].update(
                    value=self.get_hijri_date_from_json(self.now, api_res=self.current_m_data))

            else:  # self.end_of_month_hijri will be set by the upcoming prayers function after Isha
                window["-TODAY_HIJRI-"].update(value=self.end_of_month_hijri)
            # update system tray tooltip also
            application_tray.set_tooltip(
                f"Next prayer: {self.UPCOMING_PRAYERS[0][0]} in {time_d}")

            # main event reading
            event1, values1 = window.read(timeout=100)

            if event1 == application_tray.key:
                event1 = values1[event1]
                # Debugging
                print("[DEBUG] SystemTray event:", event1)

            # Event check and preform action
            if event1 in (sg.WIN_CLOSED, "-EXIT-", "Exit"):
                break

            if event1 in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "Hide Window"):
                window.hide()
                application_tray.show_icon()
                application_tray.show_message(title="Athany minimized to system tray",
                                              message="To completely close the app, choose the 'Exit' button")

            elif event1 in ("Show Window", sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
                window.un_hide()
                window.bring_to_front()

            elif event1 in ("-STOP-ATHAN-", "Stop athan") and athan_play_obj:
                if athan_play_obj.is_playing():
                    athan_play_obj.stop()

            # if clicked settings button, open up the settings window and read values from it along with the main window
            elif event1 in ("-SETTINGS-", "Settings") and not win2_active:
                win2_active = True
                current_athan = self.settings["-athan-sound-"]\
                    .split(".")[0].replace("_", " ")

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
                        sg.Text("Current Athan:",
                                key="-DISPLAYED_MSG-", pad=(5, 10)),
                        sg.Push(),
                        sg.Combo(enable_events=True, values=self.AVAILABLE_ADHANS, key="-DROPDOWN-ATHANS-",
                                 readonly=True, default_value=current_athan, font=self.BUTTON_FONT, pad=(5, 10))
                    ],
                    [
                        sg.Button("Download next 12 months data",
                                  key="-GET-NEXT-12-MON-", font=self.BUTTON_FONT),
                        sg.Text(f"last update: {self.settings['-last-time-down-12-mons-']}", key="-DOWN-12-MON-PROG-",
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
                elif event2 == "-EXIT-":
                    break
                elif event2 == "-DROPDOWN-ATHANS-" and values2["-DROPDOWN-ATHANS-"] in self.AVAILABLE_ADHANS:
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
                        settings_window["-GET-NEXT-12-MON-"].update(
                            disabled=True)
                        settings_window["-DISPLAYED_MSG-"].update(
                            value="Establishing connection...")
                        settings_window.refresh()

                        if athan_play_obj:
                            athan_play_obj.stop()

                        # run the download function to get athan from archive
                        downloaded = self.download_athan(chosen_athan)
                        if downloaded:  # if all went well, set as new athan and play audio
                            self.settings["-athan-sound-"] = chosen_athan
                            settings_window["-DISPLAYED_MSG-"].update(
                                value="Current Athan:")
                            settings_window.refresh()

                            athan_play_obj = self.play_current_athan()

                        else:  # something messed up during download or no internet
                            settings_window["-DISPLAYED_MSG-"].update(
                                value="Current Athan:")
                            settings_window["-DROPDOWN-ATHANS-"].update(
                                value=self.settings["-athan-sound-"].split(".")[0].replace("_", " "))
                            application_tray.show_message(
                                title="Download Failed", message=f"Couldn't download athan file: {chosen_athan}")

                        settings_window["-DONE-"].update(disabled=False)
                        settings_window["-GET-NEXT-12-MON-"].update(
                            disabled=False)
                    # Debugging
                    print("[DEBUG] Current athan:",
                          self.settings["-athan-sound-"])

                elif event2 == "-GET-NEXT-12-MON-":
                    settings_window.perform_long_operation(
                        self.download_12_months, "-DOWNLOADED-12-MONS-")
                    settings_window["-DOWN-12-MON-PROG-"].update(
                        value="Downloading data, please wait...")

                elif event2 == "-DOWNLOADED-12-MONS-":
                    settings_window["-DOWN-12-MON-PROG-"].update(
                        value=f"last update: {self.settings['-last-time-down-12-mons-']}")

                elif event2 == "-TOGGLE-GRAPHIC-":
                    settings_window["-TOGGLE-GRAPHIC-"].metadata = not settings_window["-TOGGLE-GRAPHIC-"].metadata
                    settings_window["-TOGGLE-GRAPHIC-"].update(
                        image_data=self.TOGGLE_ON_B64 if settings_window["-TOGGLE-GRAPHIC-"].metadata else self.TOGGLE_OFF_B64)

                elif event2 == "-TOGGLE-MUTE-":
                    settings_window["-TOGGLE-MUTE-"].metadata = not settings_window["-TOGGLE-MUTE-"].metadata
                    settings_window["-TOGGLE-MUTE-"].update(
                        image_data=self.TOGGLE_ON_B64 if settings_window["-TOGGLE-MUTE-"].metadata else self.TOGGLE_OFF_B64)

                    self.settings["-mute-athan-"] = settings_window["-TOGGLE-MUTE-"].metadata
        # close application on exit
        application_tray.close()
        window.close()
        del application_tray
        del window


# ------------------------------------- Starts The GUI ------------------------------------- #

if __name__ == "__main__":
    keep_trying = True
    while keep_trying:
        try:
            app = Athany()

            app.display_main_window(app.init_layout)

            # If user doesn't want to save settings, delete saved entries before closing
            if not app.save_loc_check:
                if app.settings["-city-"] and app.settings["-country-"]:
                    app.settings.delete_entry("-city-")
                    app.settings.delete_entry("-country-")

            keep_trying = False
        except TypeError:
            keep_trying = keep_trying_popup()
