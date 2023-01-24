"""Module that contains modified GUI elements"""
import os
from pygame import mixer
import PySimpleGUI as sg
from adhanpy.calculation.MethodsParameters import methods_parameters

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


class SettingsWindow(sg.Window):
    """A modified version of PySimpleGUI.Window
     that contains methods for handling & modifying the settings window events/elements"""

    def __init__(self, parent, **kwargs):
        self.parent = parent
        super().__init__(**kwargs)

    def handle_event_loop(self, timeout=100):
        """method for handling events that come from the settings window

        :param int timeout: the timeout for the read method
        :return bool: boolean value that indicates whether the settings window is still open or not
        """
        win_active = True
        event2, values2 = self.read(timeout=timeout)
        self.disable_debugger()

        if event2 in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "-DONE-"):
            win_active = False
            offset_changed = False
            action_type = values2.get("-DONE-", None)
            print("[DEBUG] Settings exit action:", action_type)
            self.parent.save_loc_check = self["-TOGGLE-SAVE-LOCATION-"].metadata
            self.parent.settings["-custom-athan-"] = self["-CUSTOM-ATHAN-NAME-"].get()

            for prayer in self.parent.current_furood:
                pt_offset = self[f"-{prayer.upper()}-OFFSET-"].get()
                if self.parent.settings["-offset-"][f"-{prayer}-"] != pt_offset:
                    self.parent.settings["-offset-"][f"-{prayer}-"] = pt_offset
                    self.parent.settings.save()
                    offset_changed = True

            self.close()

            if offset_changed:
                self.parent.restart_app = self.parent.yes_or_no_popup(
                    "Prayer offsets were changed, do you want to restart application?")

            if action_type == "-RESTART-" or self.parent.restart_app:
                mixer.music.unload()
                self.parent.restart_app = True
                self.parent.window.write_event_value("-EXIT-", None)

            elif action_type == "-EXIT-":
                self.parent.window.write_event_value("-EXIT-", None)

        elif event2 in ("-EXIT-", "-RESTART-"):
            self.write_event_value(
                "-DONE-", event2)

        elif event2 in "-TOGGLE-MUTE-":
            self["-TOGGLE-MUTE-"].metadata = not self["-TOGGLE-MUTE-"].metadata
            self["-TOGGLE-MUTE-"].update(
                image_data=TOGGLE_ON_B64 if self["-TOGGLE-MUTE-"].metadata else TOGGLE_OFF_B64)

            self.parent.settings["-mute-athan-"] = self["-TOGGLE-MUTE-"].metadata

        elif event2 == "-TOGGLE-CUSTOM-ATHAN-":
            self["-TOGGLE-CUSTOM-ATHAN-"].metadata = not self["-TOGGLE-CUSTOM-ATHAN-"].metadata
            self["-TOGGLE-CUSTOM-ATHAN-"].update(
                image_data=TOGGLE_ON_B64 if self["-TOGGLE-CUSTOM-ATHAN-"].metadata else TOGGLE_OFF_B64)

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
            self["-TOGGLE-SAVE-LOCATION-"].metadata = not self["-TOGGLE-SAVE-LOCATION-"].metadata
            self["-TOGGLE-SAVE-LOCATION-"].update(
                image_data=TOGGLE_ON_B64 if self["-TOGGLE-SAVE-LOCATION-"].metadata else TOGGLE_OFF_B64)

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
            DOWNLOADED_ATHANS = os.listdir(ATHANS_DIR)
            # convert option into filename
            chosen_athan = f"{values2['-DROPDOWN-ATHANS-'].replace(' ', '_')}.mp3"

            if chosen_athan in DOWNLOADED_ATHANS:  # athan is already in Athans directory
                self.parent.settings["-athan-sound-"] = chosen_athan
                self.parent.play_current_athan()

            else:  # athan is not on pc, will be downloaded from the internet
                self["-DONE-"].update(disabled=True)
                self["-RESTART-"].update(disabled=True)
                self["-EXIT-"].update(disabled=True)
                self["-DISPLAYED-MSG-"].update(
                    value="Establishing connection...")
                self.refresh()

                mixer.music.unload()

                # run the download function to get athan from archive
                downloaded = self.parent.download_athan(chosen_athan)
                if downloaded:  # if all went well, set as new athan and play audio
                    self.parent.settings["-athan-sound-"] = chosen_athan
                    self["-DISPLAYED-MSG-"].update(
                        value="Current athan")
                    self.refresh()

                    self.parent.play_current_athan()

                else:  # something messed up during download or no internet
                    self["-DISPLAYED-MSG-"].update(
                        value="Current athan")
                    self["-DROPDOWN-ATHANS-"].update(
                        value=self.parent.settings["-athan-sound-"][:-4].replace("_", " "))
                    self.parent.application_tray.show_message(
                        title="Download Failed", message=f"Couldn't download athan file: {chosen_athan}")

                self["-DONE-"].update(disabled=False)
                self["-RESTART-"].update(disabled=False)
                self["-EXIT-"].update(disabled=False)
            # Debugging
            print("[DEBUG] Current athan:",
                  self.parent.settings["-athan-sound-"])

        elif event2 == "-DROPDOWN-METHODS-":
            self.parent.settings["-used-method-"] = self.parent.get_method_id(
                values2["-DROPDOWN-METHODS-"])

            if self.parent.settings["-used-method-"] == 99:
                self["-SET-CUSTOM-ANGLES-"].update(disabled=False)
                self["-FAJR-ANGLE-IN-"].update(
                    disabled=False, text_color=sg.theme_input_text_color())
                self["-ISHA-ANGLE-IN-"].update(
                    disabled=False, text_color=sg.theme_input_text_color())
            else:
                self["-SET-CUSTOM-ANGLES-"].update(disabled=True)
                used_method = methods_parameters[
                    self.parent.calculation_methods[self.parent.settings["-used-method-"]][0]]
                self["-FAJR-ANGLE-IN-"].update(
                    value=used_method["fajr_angle"], disabled=True, text_color="grey")
                self["-ISHA-ANGLE-IN-"].update(
                    value=used_method.get("isha_angle", "not used"), disabled=True, text_color="grey")

            self.parent.current_furood = self.parent.get_prayers_dict(
                self.parent.settings["-location-"]["-coordinates-"], self.parent.now)
            self.parent.update_current_and_next_prayer()
            self.parent.refresh_prayers_in_ui(True)

        elif event2 == "-SET-CUSTOM-ANGLES-":
            try:
                fajr = float(self["-FAJR-ANGLE-IN-"].get())
                isha = float(self["-ISHA-ANGLE-IN-"].get())
                if fajr < 0 or isha < 0 or fajr > 20 or isha > 20:
                    raise TypeError

                self.parent.settings["-custom-angles-"] = [fajr, isha]
                self.parent.current_furood = self.parent.get_prayers_dict(
                    self.parent.settings["-location-"]["-coordinates-"], self.parent.now)
                self.parent.update_current_and_next_prayer()
                self.parent.refresh_prayers_in_ui(True)

                self["-FAJR-ANGLE-IN-"].update(
                    background_color=sg.theme_input_background_color())
                self["-ISHA-ANGLE-IN-"].update(
                    background_color=sg.theme_input_background_color())

            except (TypeError, ValueError):
                self["-FAJR-ANGLE-IN-"].update(
                    background_color="dark red")
                self["-ISHA-ANGLE-IN-"].update(
                    background_color="dark red")

        return win_active
