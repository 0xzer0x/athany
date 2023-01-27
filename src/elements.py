"""Module that contains custom GUI elements used"""
import os
from pygame import mixer
import PySimpleGUI as sg
from psgtray import SystemTray


DATA_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "Data")
ATHANS_DIR = os.path.join(DATA_DIR, "Athans")

with open(os.path.join(DATA_DIR, "app_icon.dat"), mode="rb") as icon:
    APP_ICON = icon.read()
with open(os.path.join(DATA_DIR, "toggle_off.dat"), mode="rb") as toff:
    TOGGLE_OFF_B64 = toff.read()
with open(os.path.join(DATA_DIR, "toggle_on.dat"), mode="rb") as ton:
    TOGGLE_ON_B64 = ton.read()


class TranslatedText(sg.Text):
    """A modified version of PySimpleGUI.Text
    that translates the given text before creating the text element"""

    def __init__(self, translator, text='', **kwargs):
        self.translator = translator
        if text:
            super().__init__(text=translator.translate(text), **kwargs)
        else:
            super().__init__(text=text, **kwargs)

    def update(self, value=None, background_color=None, text_color=None, font=None, visible=None):
        if value:
            return super().update(self.translator.translate(value), background_color, text_color, font, visible)
        else:
            return super().update(value, background_color, text_color, font, visible)


class TranslatedButton(sg.Button):
    """A modified version of PySimpleGUI.Button
    that translates the given text before creating the button element"""

    def __init__(self, translator, text, **kwargs):
        super().__init__(button_text=translator.translate(text), **kwargs)


class MainWindow(sg.Window):
    """A modified version of PySimpleGUI.Window
     that contains methods for handling & modifying the main UI window"""

    def __init__(self, parent, **kwargs):
        self.sys_tray = None
        self.parent = parent
        super().__init__(**kwargs)
        self.disable_debugger()

    def show_notification_and_athan(self):
        """method to send notification to the user and play athan sound when prayer time comes
        """
        if self.parent.pt.current_fard[0] != "Sunrise":
            self.sys_tray.show_message(
                title="Athany 🕌", message=self.parent.translator.translate(f"It's time for {self.parent.pt.current_fard[0]} prayer"))

            # play athan sound from user athan sound settings (if athan sound not muted)
            if not self.parent.settings["-mute-athan-"]:
                try:
                    self.parent.play_current_athan()
                except RuntimeError:
                    print(
                        "[DEBUG] Couldn't play athan audio, rechoose your athan in the app settings")

    def highlight_current_fard_in_ui(self):
        """method to highlight the current fard in the main app UI
        """
        for name in self.parent.displayed_times:
            self[f"-{name.upper()}-"].update(font=self.parent.GUI_FONT,
                                             text_color=sg.theme_text_color())
            self[f"-{name.upper()}-TIME-"].update(font=self.parent.GUI_FONT,
                                                  text_color=sg.theme_text_color())

        if self.parent.pt.current_fard[0] == "Sunrise":
            self["-FAJR-"].update(
                font=(self.parent.GUI_FONT[0], self.parent.GUI_FONT[1], "italic"), text_color='#cd8032')
            self["-FAJR-TIME-"].update(
                font=(self.parent.GUI_FONT[0], self.parent.GUI_FONT[1], "italic"), text_color='#cd8032')
        else:
            self[f"-{self.parent.pt.current_fard[0].upper()}-"].update(
                font=(self.parent.GUI_FONT[0], self.parent.GUI_FONT[1], "italic"), text_color='#cd8032')
            self[f"-{self.parent.pt.current_fard[0].upper()}-TIME-"].update(
                font=(self.parent.GUI_FONT[0], self.parent.GUI_FONT[1], "italic"), text_color='#cd8032')

    def refresh_prayers_in_ui(self, prayer_times_changed: bool):
        """method to update the display of the main window depending on the current fard
            & display tomorrow prayer times if isha passed

        :param bool prayer_times_changed: True if the current_furood dict was changed
        """
        # Highlight current fard in main window
        self.highlight_current_fard_in_ui()

        # If current_furood dict was changed,
        # then update the ui with the next day prayers starting from Fajr
        if prayer_times_changed:
            for prayer, time in self.parent.pt.current_furood.items():
                self[f"-{prayer.upper()}-TIME-"].update(
                    value=time.strftime("%I:%M %p"))

    # ---------------------------- event handlers ---------------------------- #

    def run_event_loop(self, timeout=100):
        """main window event handling loop
        """
        win2_active = False
        while True:
            self.parent.pt.update_time()

            if self.parent.pt.prayer_time_came():
                pt_changed = self.parent.pt.update_current_and_next_prayer()
                self.show_notification_and_athan()
                self.refresh_prayers_in_ui(pt_changed)

            # get remaining time till next prayer
            time_d = self.parent.pt.upcoming_fard[1] - self.parent.pt.now

            # update the main window with the next prayer and remaining time
            self["-NEXT-PRAYER-"].update(
                value=self.parent.pt.upcoming_fard[0])
            self["-TIME-D-"].update(value=str(time_d))

            # update the current dates
            self["-CURRENT-TIME-"].update(
                value=self.parent.pt.now.strftime("%I:%M %p"))
            self["-TODAY-"].update(
                value=self.parent.pt.now.strftime("%a %d %b %y"))
            self["-TODAY_HIJRI-"].update(
                value=self.parent.get_hijri_date())

            # update system tray tooltip also
            self.sys_tray.set_tooltip(
                f"{self.parent.pt.upcoming_fard[0]} in {time_d}")

            # main event reading
            event1, values1 = self.read(timeout=timeout)

            if event1 == self.sys_tray.key:
                event1 = values1[event1]
                # Debugging
                print("[DEBUG] SystemTray event:", event1)

            # Event check and preform action
            if event1 == sg.TIMEOUT_KEY:
                pass

            elif event1 in (sg.WIN_CLOSED, "-EXIT-", "Exit"):
                self.sys_tray.close()
                del self.sys_tray
                break

            elif event1 in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "Hide Window"):
                self.hide()
                self.sys_tray.show_icon()
                self.sys_tray.show_message(title="Athany minimized to system tray",
                                           message="To completely close the app, press 'Exit'")

            elif event1 in ("Show Window", sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
                self.un_hide()
                self.bring_to_front()

            elif event1 in ("-STOP-ATHAN-", "Stop athan"):
                mixer.music.unload()

            # if clicked settings button,
            # open up the settings window and read values from it along with the main window
            elif event1 in ("-SETTINGS-", "Settings") and not win2_active:
                win2_active = True
                settings_window: SettingsWindow = self.parent.generate_settings_window()

            # If 2nd window (settings window) is open, run the settings window event handling method
            if win2_active:
                win2_active = settings_window.run_event_loop()
            else:
                settings_window = None

    # ---------------------- startup & shutdown methods ---------------------- #

    def start_system_tray(self):
        """starts the SystemTray object and instantiates it"s menu and tooltip
        """
        menu = ["", ["Show Window", "Hide Window", "---", "Stop athan",
                     "Settings", "Exit"]]
        self.sys_tray = SystemTray(menu=menu, tooltip="Next Prayer",
                                   window=self, icon=APP_ICON)
        self.sys_tray.show_message(
            title="Athany", message="Choose 'Hide Window' or close the window to minimize application to system tray")


class SettingsWindow(sg.Window):
    """A modified version of PySimpleGUI.Window
     that contains methods for handling & modifying the settings window events/elements"""

    def __init__(self, parent, **kwargs):
        self.parent = parent
        super().__init__(**kwargs)

    def run_event_loop(self, timeout=100):
        """method for handling events that come from the settings window

        :param int timeout: the timeout for the read method
        :return bool: boolean value that indicates whether the settings window is still open or not
        """
        win_active = True
        event2, values2 = self.read(timeout=timeout)
        self.disable_debugger()

        if event2 == sg.TIMEOUT_KEY:
            pass

        elif event2 in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "-DONE-"):
            win_active = False
            action_type = values2.get("-DONE-", None)
            print("[DEBUG] Settings exit action:", action_type)
            self.parent.save_loc_check = self["-TOGGLE-SAVE-LOCATION-"].metadata
            self.parent.settings["-custom-athan-"] = self["-CUSTOM-ATHAN-NAME-"].get()

            if self.offset_changed():
                self.parent.pt.update_prayer_offset()
                self.apply_calculation_changes()

            self.close()
            if action_type == "-RESTART-":
                mixer.music.unload()
                self.parent.restart_app = True
                self.parent.window.write_event_value("-EXIT-", None)

            elif action_type == "-EXIT-":
                self.parent.window.write_event_value("-EXIT-", None)

        elif event2 in ("-EXIT-", "-RESTART-"):
            self.write_event_value(
                "-DONE-", event2)

        elif event2 == "-TOGGLE-MUTE-":
            self.change_toggle_button_state(event2)
            self.parent.settings["-mute-athan-"] = self["-TOGGLE-MUTE-"].metadata

        elif event2 == "-TOGGLE-CUSTOM-ATHAN-":
            self.change_toggle_button_state(event2)
            self.parent.settings["-use-custom-athan-"] = self["-TOGGLE-CUSTOM-ATHAN-"].metadata

            self["-DROPDOWN-ATHANS-"].update(
                disabled=self.parent.settings["-use-custom-athan-"])
            self["-CUSTOM-ATHAN-BROWSE-"].update(
                disabled=not self.parent.settings["-use-custom-athan-"])

            if self.parent.settings["-use-custom-athan-"]:
                self["-DROPDOWN-ATHANS-"].update(
                    value="Custom")
            else:
                self["-DROPDOWN-ATHANS-"].update(
                    value=self.parent.settings["-athan-sound-"][:-4].replace("_", " "))

        elif event2 == "-TOGGLE-SAVE-LOCATION-":
            self.change_toggle_button_state(event2)

        elif event2 == "-DROPDOWN-LANG-" and self.parent.settings["-lang-"] != values2["-DROPDOWN-LANG-"]:
            self.parent.settings["-lang-"] = values2["-DROPDOWN-LANG-"]
            self.parent.restart_app = self.parent.yes_or_no_popup(
                "App language was changed, do you want to restart?")
            if self.parent.restart_app:
                self.write_event_value(
                    "-DONE-", "-RESTART-")

        elif event2 == "-DROPDOWN-THEMES-":
            self.parent.chosen_theme = values2["-DROPDOWN-THEMES-"]
            if self.parent.chosen_theme != self.parent.settings["-theme-"]:
                self.parent.restart_app = self.parent.yes_or_no_popup(
                    "Theme was changed, Do you want to restart application?")
                if self.parent.restart_app:
                    self.write_event_value(
                        "-DONE-", "-RESTART-")

        elif event2 == "-DROPDOWN-ATHANS-":
            # get a list of all athans currently in folder
            # as user might have downloaded before
            downloaded_athans = os.listdir(ATHANS_DIR)
            chosen_athan = f"{values2['-DROPDOWN-ATHANS-'].replace(' ', '_')}.mp3"
            if chosen_athan in downloaded_athans:  # athan is already in Athans directory
                self.parent.settings["-athan-sound-"] = chosen_athan
                self.parent.play_current_athan()

            else:  # athan is not on pc, will be downloaded from the internet
                self.start_download_process(chosen_athan)

            # Debugging
            print("[DEBUG] Current athan:",
                  self.parent.settings["-athan-sound-"])

        elif event2 == "-DROPDOWN-METHODS-":
            self.parent.settings["-used-method-"] = self.parent.pt.get_method_id(
                values2["-DROPDOWN-METHODS-"])

            if self.parent.settings["-used-method-"] == 99:
                self["-SET-CUSTOM-ANGLES-"].update(disabled=False)
                self["-FAJR-ANGLE-IN-"].update(
                    disabled=False, text_color=sg.theme_input_text_color())
                self["-ISHA-ANGLE-IN-"].update(
                    disabled=False, text_color=sg.theme_input_text_color())
            else:
                self["-SET-CUSTOM-ANGLES-"].update(disabled=True)
                used_method_params = self.parent.pt.get_method_params(
                    self.parent.settings["-used-method-"])
                self["-FAJR-ANGLE-IN-"].update(
                    value=used_method_params["fajr_angle"], disabled=True, text_color="grey")
                self["-ISHA-ANGLE-IN-"].update(
                    value=used_method_params.get("isha_angle", "not used"), disabled=True, text_color="grey")

            self.apply_calculation_changes()

        elif event2 == "-SET-CUSTOM-ANGLES-":
            try:
                fajr = float(self["-FAJR-ANGLE-IN-"].get())
                isha = float(self["-ISHA-ANGLE-IN-"].get())
                if fajr < 0 or isha < 0 or fajr > 20 or isha > 20:
                    raise ValueError

                self.parent.settings["-custom-angles-"] = [fajr, isha]
                self.apply_calculation_changes()

                self["-FAJR-ANGLE-IN-"].update(
                    background_color=sg.theme_input_background_color())
                self["-ISHA-ANGLE-IN-"].update(
                    background_color=sg.theme_input_background_color())

            except (TypeError, ValueError):
                self["-FAJR-ANGLE-IN-"].update(
                    background_color="dark red")
                self["-ISHA-ANGLE-IN-"].update(
                    background_color="dark red")

        elif event2 == "-RESET-OFFSET-":
            self.reset_prayer_offsets()

        return win_active

    def change_toggle_button_state(self, key):
        """method to toggle the state of a button using it's metadata attribute

        :param str key: toggle button key in the window
        """
        self[key].metadata = not self[key].metadata
        self[key].update(
            image_data=TOGGLE_ON_B64 if self[key].metadata else TOGGLE_OFF_B64)

    def start_download_process(self, athan_filename):
        """method to handle downloading of athan file"""
        self["-DONE-"].update(disabled=True)
        self["-RESTART-"].update(disabled=True)
        self["-EXIT-"].update(disabled=True)
        self["-DISPLAYED-MSG-"].update(
            value="Establishing connection...")
        self.refresh()

        mixer.music.unload()

        # run the download function to get athan from archive
        downloaded = self.parent.download_athan(athan_filename)
        if downloaded:  # if all went well, set as new athan and play audio
            self.parent.settings["-athan-sound-"] = athan_filename
            self.parent.play_current_athan()

        else:  # something messed up during download or no internet
            self["-DROPDOWN-ATHANS-"].update(
                value=self.parent.settings["-athan-sound-"][:-4].replace("_", " "))
            self.parent.window.sys_tray.show_message(
                title="Download Failed", message=f"Couldn't download athan file: {athan_filename}")

        self["-DISPLAYED-MSG-"].update(
            value="Current athan")
        self["-EXIT-"].update(disabled=False)
        self["-RESTART-"].update(disabled=False)
        self["-DONE-"].update(disabled=False)

    def apply_calculation_changes(self):
        """method to apply changes made to prayer times calculation and display the new times"""
        self.parent.pt.update_current_furood(self.parent.pt.now)
        self.parent.pt.update_current_and_next_prayer()
        self.parent.window.refresh_prayers_in_ui(True)

    def offset_changed(self) -> bool:
        """method to check whether prayer offsets were changed & save their new values
        :return: (bool) boolean value to indicate whether prayer offsets changed or no
        """
        offset_changed = False
        for prayer in self.parent.displayed_times:
            pt_offset = self[f"-{prayer.upper()}-OFFSET-"].get()
            if self.parent.settings["-offset-"][f"-{prayer}-"] != pt_offset:
                self.parent.settings["-offset-"][f"-{prayer}-"] = pt_offset
                self.parent.settings.save()
                offset_changed = True

        return offset_changed

    def reset_prayer_offsets(self):
        """method to reset all prayer offsets to zero"""
        for prayer in self.parent.displayed_times:
            self.parent.settings["-offset-"][f"-{prayer}-"] = 0
            self[f"-{prayer.upper()}-OFFSET-"].update(value=0)


class ChooseLocationWindow(sg.Window):
    """A modified version of PySimpleGUI.Window
     that contains methods for setting the inital settings by getting the location from the user"""

    def __init__(self, parent, **kwargs):
        self.parent = parent
        super().__init__(**kwargs)

    def run_event_loop(self):
        """event handling for the location window
        :return: (dict) dictionary of location data required for calculation
        """
        self.perform_long_operation(
            self.parent.get_current_location, "-AUTOMATIC-LOCATION-THREAD-")
        while True:
            location_data = False
            event, values = self.read()

            if event in (sg.WIN_CLOSED, "-CANCEL-"):
                self.parent.close_app_windows()
                break

            elif event == "-AUTOMATIC-LOCATION-THREAD-":
                self.parent.location_api = values["-AUTOMATIC-LOCATION-THREAD-"]
                self["-AUTO-LOCATION-"].update(value=f"({self.parent.location_api[0]}, {self.parent.location_api[1]})" if not isinstance(
                    self.parent.location_api, str) else f"({self.parent.translator.translate('Internet connection required')})")
            else:
                if event == "-OK-":
                    city = values["-CITY-"].strip().capitalize()
                    country = values["-COUNTRY-"].strip().capitalize()
                    if len(city+country) < 4:
                        continue
                    if len(country) == 2:
                        country = country.upper()

                    self["-LOC-TXT-"].update(
                        value="Fetching location data for:")
                    self["-LOCATION-NAME-"].update(
                        value=f"({city}, {country})")
                    self.refresh()

                    location_data = self.parent.fetch_calculation_data(city,
                                                                       country)

                    if location_data is None:  # if invalid city/country dont continue
                        self["-LOC-TXT-"].update(
                            value="Invalid city or country, enter a valid location")
                        self["-LOCATION-NAME-"].update(
                            value="")
                        self["-CITY-"].update(
                            background_color="dark red")
                        self["-COUNTRY-"].update(
                            background_color="dark red")
                        continue

                elif event == "-USE-CURRENT-LOCATION-":
                    if not isinstance(self.parent.location_api, tuple):
                        self.parent.location_api = self.parent.get_current_location()
                    if self.parent.location_api == "RequestError":
                        self["-LOC-TXT-"].update(
                            value="An error occurred, try entering location manually")
                        self["-LOCATION-NAME-"].update(
                            value="")
                        self.refresh()

                    else:
                        city = self.parent.location_api[0]
                        country = self.parent.location_api[1]

                        self["-LOC-TXT-"].update(
                            value="Fetching location data for:")
                        self["-LOCATION-NAME-"].update(
                            value=f"({city}, {country})")
                        self.refresh()

                        location_data = self.parent.fetch_calculation_data(city,
                                                                           country)

                if not location_data:
                    continue

                if location_data == "RequestError":
                    self["-LOC-TXT-"].update(
                        value="Internet connection required")
                    self["-LOCATION-NAME-"].update(
                        value="")
                else:
                    self.parent.settings["-location-"]["-city-"] = city
                    self.parent.settings["-location-"]["-country-"] = country
                    self.parent.settings["-location-"]["-coordinates-"] = (
                        location_data["latitude"],
                        location_data["longitude"]
                    )
                    self.parent.settings["-location-"]["-timezone-"] = location_data["timezone"]
                    self.parent.settings.save()

                    self.parent.save_loc_check = values["-SAVE-LOC-CHECK-"]

                    # close location choosing window
                    self.parent.close_app_windows()

                    return location_data
