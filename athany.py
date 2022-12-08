"""Python application to fetch prayer times, display them in a GUI and play adhan"""
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

# ------------------------------------- Application Settings ------------------------------------- #
DATA_DIR = os.path.join(os.path.abspath(__file__).split("athany.py")[0],
                        'Data')

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

sg.theme("DarkAmber")
sg.user_settings_filename(filename='athany-config.json')
if not sg.user_settings_get_entry('-athan_sound-'):
    sg.user_settings_set_entry('-athan_sound-', value='Default.wav')
if not sg.user_settings_get_entry('-mute-athan-'):
    sg.user_settings_set_entry('-mute-athan-', value=False)


UPCOMING_PRAYERS = []
save_loc_check = False
API_ENDPOINT = "https://api.aladhan.com/v1/calendarByCity"
FUROOD_NAMES = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
AVAILABLE_ADHANS = ['Default',
                    'Alaqsa', 'Alaqsa (short)',
                    'Egypt', 'Egypt (short)',
                    'Makkah', 'Makkah (short)',
                    'Abdul-basit Abdul-samad', 'Abdul-basit Abdul-samad (short)',
                    'Mishari Alafasy', 'Mishari Alafasy (short)',
                    'Islam Sobhy', 'Islam Sobhy (short)']


GUI_FONT = "Segoe\ UI 11"
BUTTON_FONT = "Segoe\ UI 10"
ARABIC_FONT = "Segoe\ UI 12" if sys.platform != "win32" else "Arabic\ Typesetting 20"


with open(os.path.join(DATA_DIR, "icon.dat"), mode='rb') as icon:
    APP_ICON = icon.read()
with open(os.path.join(DATA_DIR, "toggle_off.dat"), mode='rb') as toff:
    TOGGLE_OFF_B64 = toff.read()
with open(os.path.join(DATA_DIR, "toggle_on.dat"), mode='rb') as ton:
    TOGGLE_ON_B64 = ton.read()

# ------------------------------------- Main Application logic ------------------------------------- #


def play_selected_athan() -> simpleaudio.PlayObject:
    """ fetches current settings for athan and plays the corresponding athan
        Return:
            play_obj (simpleaudio.PlayObject) - play object to control playback of athan
    """
    current_athan_path = os.path.join(
        DATA_DIR, sg.user_settings_get_entry('-athan_sound-'))
    wave_obj = simpleaudio.WaveObject.from_wave_file(current_athan_path)
    play_obj = wave_obj.play()
    return play_obj


def get_current_location() -> tuple[str, str] | str:
    """ function that gets the current city and country of the user IP\n
    Return:
        (city, country) - tuple containing 2 strings of the city & country fetched
    """
    try:
        IP_city = requests.get("https://ipinfo.io/city", timeout=100).text
        IP_country = requests.get(
            "https://ipinfo.io/country", timeout=100).text
        print("[DEBUG]", IP_city.strip(), IP_country.strip())
        return (IP_city.strip(), IP_country.strip())
    except:
        return "RequestError"


def fetch_calender_data(cit: str, count: str, date: datetime.datetime) -> dict:
    """ check if calender data for the city+country+month+year exists and fetch it if not
     Return:
        month_data (dict) - api response json data dictionary
    """
    json_month_file = os.path.join(
        DATA_DIR, f"{date.year}-{date.month}-{cit}-{count}.json")

    if not os.path.exists(json_month_file):
        try:
            res = requests.get(
                API_ENDPOINT+f"?city={cit}&country={count}&month={date.month}&year={date.year}", timeout=300)
        except:
            return "RequestError"
        if res.status_code != 200:  # if invalid city or country, return None instead of filename
            return None

        with open(json_month_file, mode="w", encoding='utf-8') as f:
            f.write(res.text)

    with open(json_month_file, encoding='utf-8') as month_prayers:
        month_data = json.load(month_prayers)

    return month_data


def get_hijri_date_from_json(date: datetime.datetime, api_res) -> str:
    """ function to return arabic hijri date string to display in main window """
    hirjir_date = api_res["data"][date.day - 1]["date"]["hijri"]
    text = f"{hirjir_date['weekday']['ar']} {hirjir_date['day']} {hirjir_date['month']['ar']} {hirjir_date['year']}"
    if sys.platform != "win32" and not MISSING_ARABIC_MODULES:
        arabic_text = get_display(arabic_reshaper.reshape(text))
        return arabic_text
    else:
        return text


def get_main_layout_and_tomorrow_prayers(api_res: dict) -> tuple[list, dict]:
    """ sets the prayer times window layout and sets the inital upcoming prayers on application startup\n
        Arguments:
            api_res (dict) - adhan api month json response as a dictionary
        Return:
            initial_layout (list) - main window layout based on the timings fetched from api_res\n
            api_res (dict) - the month api data or the new month api data\n
    """
    now = datetime.datetime.now()
    tomorrow = now+datetime.timedelta(days=1)
    current_times = api_res["data"][now.day-1]["timings"]
    global UPCOMING_PRAYERS

    ISHA_OBJ = current_times['Isha'].split()
    ISHA_PASSED = False
    # Check if Isha passed as to get the following day timings
    # Prayer times change after Isha athan to the times of the following day
    # if NOW is after current Isha time
    if datetime.datetime.now() > datetime.datetime.strptime(f"{ISHA_OBJ[0]} {now.day} {now.month} {now.year}", "%H:%M %d %m %Y"):
        # replace all prayer times with the next day prayers
        if tomorrow.day < now.day:  # SPECIAL CASE: if today is the last day in the month, fetch new month calender and adjust the timings
            api_res = fetch_calender_data(sg.user_settings_get_entry(
                '-city-'), sg.user_settings_get_entry('-country-'), date=tomorrow)
            if api_res == "RequestError":
                sg.user_settings_delete_entry('-city-')
                sg.user_settings_delete_entry('-country-')
                sys.exit()

            current_times = api_res["data"][tomorrow.day - 1]["timings"]
            # remove last month data after setting up the new month json file
            os.remove(os.path.join(
                DATA_DIR, f"{now.year}-{now.month}-{sg.user_settings_get_entry('-city-')}-{sg.user_settings_get_entry('-country-')}.json")
            )
        else:
            current_times = api_res["data"][now.day]["timings"]

        ISHA_PASSED = True

    # loop through all prayer times to convert timing to datetime objects to be able to preform operations on them
    for k, v in current_times.items():
        # to adjust the day,month, year of the prayer datetime object
        date = tomorrow if ISHA_PASSED else now
        t = v.split(" ")[0] + f" {date.day} {date.month} {date.year}"
        current_times[k] = datetime.datetime.strptime(
            t, "%H:%M %d %m %Y")

    print(" DEBUG ".center(50, "="))
    initial_layout = [
        [sg.Text(key="-TODAY-", font=GUI_FONT+" bold"),
         sg.Push(),
         sg.Text(sg.SYMBOL_CIRCLE, font="Segoe\ UI 6"),
         sg.Push(),
         sg.Text(key="-TODAY_HIJRI-", font=ARABIC_FONT)],
        [sg.Text(sg.SYMBOL_LEFT_ARROWHEAD, font=GUI_FONT),
            sg.HorizontalSeparator(),
            sg.Text(font=GUI_FONT, key="-NEXT PRAYER-"),
            sg.Text("in", font=GUI_FONT),
            sg.Text(font=GUI_FONT, key="-TIME_D-"),
            sg.HorizontalSeparator(),
            sg.Text(sg.SYMBOL_RIGHT_ARROWHEAD, font=GUI_FONT)]
    ]
    for prayer, time in current_times.items():  # append upcoming prayers to list
        if prayer in FUROOD_NAMES:  # setting the main window layout with the inital prayer times
            initial_layout.append([sg.Text(f"{prayer}:", font=GUI_FONT), sg.Push(),
                                   sg.Text(f"{time.strftime('%I:%M %p')}", font=GUI_FONT, key=f"-{prayer.upper()} TIME-")])

            print(prayer, time)  # Debugging
            if now < time:  # adding upcoming prayers from the point of application start, this list will be modified as prayer times pass
                UPCOMING_PRAYERS.append([prayer, time])

    # the rest of the main window layout
    initial_layout += [[sg.HorizontalSeparator(color="dark brown")],
                       [sg.Button("Settings", font=BUTTON_FONT), sg.Button("Stop athan", font=BUTTON_FONT), sg.Push(),
                       sg.Button("Minimize", font=BUTTON_FONT), sg.Button("Exit", font=BUTTON_FONT)]]

    print("="*50)

    return (initial_layout, api_res)


# ------------------------------------- Main Windows And SystemTray Functions ------------------------------------- #

def start_system_tray(win: sg.Window):
    """starts the SystemTray object and instantiates it's menu and tooltip"""
    menu = ['', ['Show Window', 'Hide Window', '---', 'Stop athan',
                 'Settings', 'Exit']]
    tray = SystemTray(menu=menu, tooltip="Next Prayer",
                      window=win, icon=APP_ICON)
    tray.show_message(
        title="Athany", message="Press 'Minimize' or close to minimize application to system tray")
    return tray


def display_main_window(main_win_layout, current_month_data) -> bool:
    """Displays the main application window, keeps running until window is closed\n
    Return:
        save_loc_check (bool) - boolean value whether the user wants to save his location data or not after application is closed
    """
    window = sg.Window("Athany: a python athan app",
                       main_win_layout,
                       icon=APP_ICON,
                       enable_close_attempted_event=True,
                       finalize=True)

    application_tray = start_system_tray(win=window)
    win2_active = False
    athan_play_obj = None
    end_of_month_hijri = None
    global UPCOMING_PRAYERS
    global save_loc_check
    while True:
        now = datetime.datetime.now().replace(microsecond=0)

        if now >= UPCOMING_PRAYERS[0][1]:
            application_tray.show_message(
                title="Athany", message=f"It's time for {UPCOMING_PRAYERS[0][0]} prayer")

            # remove current fard from list, update remaining time to be 0 before playing athan sound
            UPCOMING_PRAYERS.pop(0)

            # play athan sound from user athan sound settings (if athan sound not muted)
            if not sg.user_settings_get_entry('-mute-athan-'):
                athan_play_obj = play_selected_athan()

            # If last prayer in list (Isha), then update the whole application with the next day prayers starting from Fajr
            if len(UPCOMING_PRAYERS) == 0:
                new_data = get_main_layout_and_tomorrow_prayers(fetch_calender_data(
                    sg.user_settings_get_entry('-city-'), sg.user_settings_get_entry('-country-'), date=now))
                current_month_data = new_data[1]
                del new_data
                for prayer in UPCOMING_PRAYERS:
                    window[f'-{prayer[0].upper()} TIME-'].update(
                        value=prayer[1].strftime("%I:%M %p"))

        # get remaining time till next prayer
        time_d = UPCOMING_PRAYERS[0][1] - now

        # update the main window with the next prayer and remaining time
        window['-NEXT PRAYER-'].update(
            value=f'{UPCOMING_PRAYERS[0][0]}', font=GUI_FONT+" bold")
        window['-TIME_D-'].update(value=f'{time_d}')
        # update the current dates
        window['-TODAY-'].update(
            value=now.date().strftime("%a %d %b %y"))

        if now.month == UPCOMING_PRAYERS[0][1].month:
            end_of_month_hijri = None
            window['-TODAY_HIJRI-'].update(
                value=get_hijri_date_from_json(now, api_res=current_month_data))

        else:

            if not end_of_month_hijri:
                end_of_month_hijri = get_hijri_date_from_json(now, api_res=fetch_calender_data(
                    sg.user_settings_get_entry('-city-'), sg.user_settings_get_entry('-country-'), now))

            window['-TODAY_HIJRI-'].update(value=end_of_month_hijri)
        # update system tray tooltip also
        application_tray.set_tooltip(
            f"Next prayer: {UPCOMING_PRAYERS[0][0]} in {time_d}")

        # main event reading
        event1, values1 = window.read(timeout=100)

        if event1 == application_tray.key:
            event1 = values1[event1]
            # Debugging
            print("[DEBUG] SystemTray event:", event1)

        # Event check and preform action
        if event1 in (sg.WIN_CLOSED, "Exit"):
            break

        if event1 in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "Minimize", "Hide Window"):
            window.hide()
            application_tray.show_icon()
            application_tray.show_message(title="Athany minimized to system tray",
                                          message="To completely close the app, press the 'Exit' button")

        elif event1 in ('Show Window', sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
            window.un_hide()
            window.bring_to_front()

        elif event1 == "Stop athan" and athan_play_obj:
            if athan_play_obj.is_playing():
                athan_play_obj.stop()

        # if clicked settings button, open up the settings window and read values from it along with the main window
        elif event1 == "Settings" and not win2_active:
            win2_active = True
            current_athan = sg.user_settings_get_entry(
                '-athan_sound-').split('.')[0].replace("_", " ")
            settings_layout = [[sg.Text("Mute athan"),
                                sg.Push(),
                                sg.Button(image_data=TOGGLE_ON_B64 if sg.user_settings_get_entry('-mute-athan-') else TOGGLE_OFF_B64,
                                          key='-TOGGLE-MUTE-', button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                          border_width=0, metadata=sg.user_settings_get_entry('-mute-athan-'))],
                               [sg.Text(f"Save location ({sg.user_settings_get_entry('-city-')}, {sg.user_settings_get_entry('-country-')})"),
                                sg.Push(),
                                sg.Button(image_data=TOGGLE_ON_B64 if save_loc_check else TOGGLE_OFF_B64,
                                          key='-TOGGLE-GRAPHIC-', button_color=(sg.theme_background_color(), sg.theme_background_color()),
                                          border_width=0, metadata=save_loc_check)],
                               [sg.Text(f"Current Athan:", key="-DISPLAYED_MSG-"),
                                sg.Push(),
                                sg.Combo(enable_events=True, values=AVAILABLE_ADHANS, key="-DROPDOWN-ATHANS-", readonly=True, default_value=current_athan, font=BUTTON_FONT)],
                               [sg.Push(), sg.Button("Done", font=BUTTON_FONT, pad=(5, 15))]]

            settings_window = sg.Window("Athany - settings",
                                        settings_layout,
                                        icon=APP_ICON,
                                        font=GUI_FONT,
                                        keep_on_top=True)

        # If 2nd window (settings window) is open, read values from it
        if win2_active:
            event2, values2 = settings_window.read(timeout=100)
            if event2 in (sg.WIN_CLOSED, "Done"):
                win2_active = False
                save_loc_check = settings_window['-TOGGLE-GRAPHIC-'].metadata
                settings_window.close()
            elif event2 == "-DROPDOWN-ATHANS-" and values2["-DROPDOWN-ATHANS-"] in AVAILABLE_ADHANS:
                sg.user_settings_set_entry('-athan_sound-',
                                           value=f"{values2['-DROPDOWN-ATHANS-'].replace(' ', '_')}.wav")

                # Debugging
                print("[DEBUG]", sg.user_settings_get_entry("-athan_sound-"))
                if athan_play_obj:
                    athan_play_obj.stop()
                athan_play_obj = play_selected_athan()

            elif event2 == "-TOGGLE-GRAPHIC-":
                settings_window['-TOGGLE-GRAPHIC-'].metadata = not settings_window['-TOGGLE-GRAPHIC-'].metadata
                settings_window['-TOGGLE-GRAPHIC-'].update(
                    image_data=TOGGLE_ON_B64 if settings_window['-TOGGLE-GRAPHIC-'].metadata else TOGGLE_OFF_B64)
            elif event2 == "-TOGGLE-MUTE-":
                settings_window['-TOGGLE-MUTE-'].metadata = not settings_window['-TOGGLE-MUTE-'].metadata
                settings_window['-TOGGLE-MUTE-'].update(
                    image_data=TOGGLE_ON_B64 if settings_window['-TOGGLE-MUTE-'].metadata else TOGGLE_OFF_B64)
                sg.user_settings_set_entry("-mute-athan-",
                                           value=settings_window['-TOGGLE-MUTE-'].metadata)
    # close application on exit
    application_tray.close()
    window.close()
    del application_tray
    del window

# ------------------------------------- Option To Choose Location If Not Saved Before ------------------------------------- #


location_api = get_current_location()
# define the layout for the 'choose location' window
location_win_layout = [[sg.Text("Enter your location", size=(50, 1), key='-LOC TXT-')],
                       [sg.Text("City"), sg.Input(size=(15, 1), key="-CITY-", focus=True),
                       sg.Text("Country"), sg.Input(size=(15, 1), key="-COUNTRY-"), sg.Push(), sg.Checkbox("Save settings", key='-SAVE_LOC_CHECK-')],
                       [sg.Button("Ok", size=(10, 1), font=BUTTON_FONT, bind_return_key=True),
                       sg.Button("Use current location", font=BUTTON_FONT),
                       sg.Text(f"({location_api[0]}, {location_api[1]})" if location_api != "RequestError" else "(Internet connection required)",
                               key='-AUTO-LOCATION-'),
                       sg.Push(), sg.Button("Cancel", size=(10, 1), font=BUTTON_FONT)]]


if sg.user_settings_get_entry('-city-') is None and sg.user_settings_get_entry('-country-') is None:
    # If there are no saved settings, display the choose location window to set these values
    choose_location = sg.Window("Athany - set location",
                                location_win_layout,
                                icon=APP_ICON,
                                font=GUI_FONT)

    while True:
        m_data = False
        event, values = choose_location.read()

        if event == sg.WIN_CLOSED or event == "Cancel":
            choose_location.close()
            sys.exit()

        # Run the athan api code
        else:
            if event == "Ok" and values['-CITY-'].strip() and values['-COUNTRY-'].strip():
                city = values['-CITY-'].strip().capitalize()
                country = values['-COUNTRY-'].strip().capitalize()

                choose_location['-LOC TXT-'].update(
                    value=f'Fetching prayer times for {city},{country}....')
                choose_location.refresh()

                m_data = fetch_calender_data(city,
                                             country,
                                             date=datetime.datetime.now())

                if m_data is None:  # if invalid city/country dont continue
                    choose_location['-LOC TXT-'].update(
                        value='Invalid city or country, enter a valid location')
                    choose_location['-CITY-'].update(
                        background_color='dark red')
                    choose_location['-COUNTRY-'].update(
                        background_color='dark red')
                    continue

            elif event == "Use current location":
                location_api = get_current_location(
                ) if location_api == "RequestError" else location_api

                if location_api == "RequestError":
                    choose_location["-AUTO-LOCATION-"].update(
                        value="(Internet connection required)")
                    continue

                city = location_api[0]
                country = location_api[1]

                choose_location['-LOC TXT-'].update(
                    value=f'Fetching prayer times for {city},{country}...')
                choose_location.refresh()

                m_data = fetch_calender_data(city,
                                             country,
                                             date=datetime.datetime.now())

            if not m_data:
                continue
            elif m_data == "RequestError":
                choose_location["-LOC TXT-"].update(
                    value="Internet connection required")
            else:
                sg.user_settings_set_entry('-city-',
                                           city)
                sg.user_settings_set_entry('-country-',
                                           country)

                save_loc_check = values['-SAVE_LOC_CHECK-']

                start_data = get_main_layout_and_tomorrow_prayers(m_data)

                # close location choosing window, start main app window
                break

    choose_location.close()
    del choose_location  # tkinter cleanup
else:
    save_loc_check = True
    m_data = fetch_calender_data(sg.user_settings_get_entry('-city-'),
                                 sg.user_settings_get_entry('-country-'),
                                 date=datetime.datetime.now())

    start_data = get_main_layout_and_tomorrow_prayers(m_data)

# ------------------------------------- Starts The GUI ------------------------------------- #

try:
    display_main_window(main_win_layout=start_data[0],
                        current_month_data=start_data[1])
except KeyboardInterrupt:
    sys.exit()

# If user doesn't want to save settings, delete saved entries before closing
if not save_loc_check and sg.user_settings_get_entry('-city-') and sg.user_settings_get_entry('-country-'):
    sg.user_settings_delete_entry('-city-')
    sg.user_settings_delete_entry('-country-')
