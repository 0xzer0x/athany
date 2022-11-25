"""Python application to fetch prayer times, display them in a GUI and play adhan"""
import json
import datetime
import os
import requests
import playsound
import PySimpleGUI as sg
from psgtray import SystemTray

DATA_DIR = os.path.join(os.getcwd(), 'Data')

if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

UPCOMING_PRAYERS = []
sg.user_settings_filename(filename='athany-config.json')
API_ENDPOINT = "https://api.aladhan.com/v1/calendarByCity"
FUROOD_NAMES = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
AVAILABLE_ADHANS = ['Mekka', 'Jerusalem', 'Egypt',
                    'Mishari Afasi', 'Husari', 'Abdul-basit Abdul-samad']

NOW = datetime.datetime.now()
CURRENT_YEAR = NOW.year
CURRENT_MON = NOW.month
CURRENT_DAY = NOW.day

GUI_FONT = "Calibri"
with open(os.path.join(DATA_DIR, "icon.dat"), mode='rb') as icon:
    APP_ICON = icon.read()


def display_main_window(main_win_layout, upcoming_prayers):
    """Displays the main application window, keeps running until window is closed"""
    window = sg.Window("Athany: a python athan app",
                       main_win_layout, finalize=True, icon=APP_ICON) if main_win_layout else exit()

    application_tray = start_system_tray(win=window)
    win2_active = False
    while True:
        now = datetime.datetime.now().replace(microsecond=0)

        if now >= upcoming_prayers[0][1]:
            application_tray.show_message(
                title="Athany", message=f"{upcoming_prayers[0][0]} salah time has come :D")
            # play athan sound
            upcoming_prayers.pop(0)
            playsound.playsound("Data/default-athan.mp3")

            if len(upcoming_prayers) == 0:
                upcoming_prayers = update_prayers_list()
                for prayer in upcoming_prayers:
                    window[f'-{prayer[0].upper()} TIME-'].update(
                        value=prayer[1].strftime("%I:%M %p"))

        # get remaining time till next prayer
        time_d = upcoming_prayers[0][1] - now

        # update the main window with the next prayer and remaining time
        window['-NEXT PRAYER-'].update(value=f'{upcoming_prayers[0][0]}')
        window['-TIME_D-'].update(value=f'{time_d}')

        # update system tray tooltip also
        application_tray.set_tooltip(
            f"Next prayer: {upcoming_prayers[0][0]} in {time_d}")

        # main event reading
        event1, values1 = window.read(timeout=100)

        if event1 == application_tray.key:
            event1 = values1[event1]
            print(event1)

        # Event check and preform action
        if event1 in (sg.WIN_CLOSED, "Exit"):
            break

        if event1 in (sg.WIN_CLOSE_ATTEMPTED_EVENT, "Hide Window"):
            window.hide()
            application_tray.show_icon()

        elif event1 in ('Show Window', sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
            window.un_hide()
            window.bring_to_front()

        # if clicked settings button, open up the settings window and read values from it along with the main window
        elif event1 == "Settings" and not win2_active:
            win2_active = True
            settings_layout = [
                [sg.Text("Athan sound"),
                 sg.Combo(enable_events=True, values=AVAILABLE_ADHANS), sg.Button("Set athan")],
                [sg.HorizontalSeparator(color="dark brown")],
                [sg.Button("Delete saved location data"),
                 sg.Push(), sg.Button("Exit")]
            ]

            settings_window = sg.Window(
                "Athany settings", settings_layout, icon=APP_ICON)

        if win2_active:
            event2, values2 = settings_window.read(timeout=100)
            if event2 in (sg.WIN_CLOSED, "Exit"):
                win2_active = False
                settings_window.close()
            elif event2 == "Set athan" and values2[0] in AVAILABLE_ADHANS:
                print("You chose {} athan".format(values2[0]))
            elif event2 == "Delete saved location data":
                if sg.user_settings_get_entry('-city-') and sg.user_settings_get_entry('-country-'):
                    print("[DEBUG] Deleting saved location data...")
                    sg.user_settings_delete_entry('-city-')
                    sg.user_settings_delete_entry('-country-')
                else:
                    print("[DEBUG] There's nothing to delete!")
    # close application on exit
    application_tray.close()
    window.close()


def update_prayers_list() -> list:
    """function to update upcoming prayers after isha prayer"""
    updated_list = set_main_layout_and_upcoming_prayers(
        fetch_calender_data(sg.user_settings_get_entry('-city-'),
                            sg.user_settings_get_entry('-country-'))
    )[1]

    return updated_list


def start_system_tray(win: sg.Window):
    """starts the SystemTray object and instantiates it's menu and tooltip"""
    menu = ['', ['Show Window', 'Hide Window', '---',
                 'Change Adhan sound', AVAILABLE_ADHANS, 'Exit']]
    tooltip = 'Next prayer X in Y'
    tray = SystemTray(menu=menu, tooltip=tooltip,
                      window=win, icon=APP_ICON)
    tray.show_message(title="Athany", message="System tray icon started!")
    return tray


def fetch_calender_data(cit: str, count: str) -> dict:
    """ check if calender data for the city+country+month exists and fetch it if not
     Return:
        month_data (dict) - api response json data dictionary
    """
    json_month_file = os.path.join(
        DATA_DIR, f"{CURRENT_MON}-{cit}-{count}.json")

    if not os.path.exists(json_month_file):
        res = requests.get(
            API_ENDPOINT+f"?city={cit}&country={count}", timeout=60)

        if res.status_code != 200:  # if invalid city or country, return None instead of filename
            return None

        with open(json_month_file, mode="w", encoding='utf-8') as f:
            f.write(res.text)

    with open(json_month_file, encoding='utf-8') as month_prayers:
        month_data = json.load(month_prayers)

    return month_data


def set_main_layout_and_upcoming_prayers(api_res: dict) -> tuple[list, list]:
    """ sets the prayer times window layout and sets the inital upcoming prayers on application startup
        Arguments:
            api_res (dict) - adhan api json response as a dictionary
        Return:
            prayer_times_layout (list) - main window layout based on the timings fetched from api_res
            UPCOMING_PRAYERS (list) -  list of upcoming prayers until isha or all prayers of next day if isha passed
    """
    current_times = api_res["data"][CURRENT_DAY-1]["timings"]

    ISHA_OBJ = current_times['Isha'].split()

    # Check if Isha passed as to get the following day timings
    # Prayer times change after Isha athan to the times of the following day
    # if NOW is after current Isha time
    ISHA_PASSED = False
    if datetime.datetime.now() > datetime.datetime.strptime(f"{ISHA_OBJ[0]} {CURRENT_DAY} {CURRENT_MON} {CURRENT_YEAR}", "%H:%M %d %m %Y"):
        # replace all prayer times with the next day prayers
        current_times = api_res["data"][CURRENT_DAY]["timings"]
        ISHA_PASSED = True

    # loop through all prayer times to convert timing to datetime objects to be able to preform operations on them
    for k, v in current_times.items():
        # to adjust the day,month, year of the prayer datetime object
        DAY = CURRENT_DAY+1 if ISHA_PASSED else CURRENT_DAY
        t = v.split(" ")[0] + f" {DAY} {CURRENT_MON} {CURRENT_YEAR}"
        current_times[k] = datetime.datetime.strptime(
            t, "%H:%M %d %m %Y")
        # for debugging
        if k in FUROOD_NAMES:
            print(k, current_times[k].strftime("%I:%M %p"))

    for prayer, time in current_times.items():  # append upcoming prayers to list
        if NOW < time and prayer in FUROOD_NAMES:
            UPCOMING_PRAYERS.append([prayer, time])

    prayer_times_layout = [
        [sg.Text("Current Date", font=GUI_FONT), sg.Push(), sg.Text("~", font=GUI_FONT), sg.Push(),
         sg.Text(f"{NOW.date()}", font=GUI_FONT, key="-CURRENT_DATE-")],
        [sg.Text("Next Prayer:", font=GUI_FONT), sg.Push(),
            sg.Text(font=GUI_FONT, key="-NEXT PRAYER-"), sg.Text("in", font=GUI_FONT), sg.Text(font=GUI_FONT, key="-TIME_D-")],
        [sg.Text("Fajr: ", font=GUI_FONT), sg.Push(),
         sg.Text(f"{current_times['Fajr'].strftime('%I:%M %p')}", font=GUI_FONT, key="-FAJR TIME-")],
        [sg.Text("Dhuhr: ", font=GUI_FONT), sg.Push(),
         sg.Text(f"{current_times['Dhuhr'].strftime('%I:%M %p')}", font=GUI_FONT, key="-DHUHR TIME-")],
        [sg.Text("Asr: ", font=GUI_FONT), sg.Push(),
         sg.Text(f"{current_times['Asr'].strftime('%I:%M %p')}", font=GUI_FONT, key="-ASR TIME-")],
        [sg.Text("Maghrib: ", font=GUI_FONT), sg.Push(),
         sg.Text(f"{current_times['Maghrib'].strftime('%I:%M %p')}", font=GUI_FONT, key="-MAGHRIB TIME-")],
        [sg.Text("Isha: ", font=GUI_FONT), sg.Push(),
         sg.Text(f"{current_times['Isha'].strftime('%I:%M %p')}", font=GUI_FONT, key="-ISHA TIME-")],
        [sg.HorizontalSeparator(color="dark brown")],
        [sg.Button("Settings"), sg.Push(),
            sg.Button("Hide Window"), sg.Button("Exit")]
    ]
    return prayer_times_layout, UPCOMING_PRAYERS


sg.theme("DarkAmber")
# define the layouts for the app
location_win_layout = [[sg.Text("Enter your location", size=(50, 1), key='-LOC TXT-', font=GUI_FONT)],
                       [sg.Text("City", font=GUI_FONT), sg.Input(size=(15, 1), key="-CITY-", focus=True),
                        sg.Text("Country", font=GUI_FONT), sg.Input(size=(15, 1), key="-COUNTRY-"), sg.Push(), sg.Checkbox("Save settings", key='-SAVE_LOC_CHECK-')],
                       [sg.Button("Ok", font=GUI_FONT), sg.Button("Cancel", font=GUI_FONT)]]


if sg.user_settings_get_entry('-city-') is None and sg.user_settings_get_entry('-country-') is None:
    # If there are no saved settings, display the choose location window to set these values
    choose_location = sg.Window("Athany", location_win_layout)

    while True:
        event, values = choose_location.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            exit()
        if values['-CITY-'] and values['-COUNTRY-']:  # Run the athan api code

            choose_location['-LOC TXT-'].update(
                value='Fetching prayer times....')
            choose_location.refresh()
            m_data = fetch_calender_data(values['-CITY-'], values['-COUNTRY-'])

            if m_data is None:  # if invalid city/country dont continue
                choose_location['-LOC TXT-'].update(
                    value='Invalid city or country, please try again.')
                choose_location['-CITY-'].update(background_color='dark red')
                choose_location['-COUNTRY-'].update(
                    background_color='dark red')

            else:
                sg.user_settings_set_entry('-city-',
                                           values['-CITY-'])
                sg.user_settings_set_entry('-country-',
                                           values['-COUNTRY-'])

                SAVE_LOCATION = True if values['-SAVE_LOC_CHECK-'] else False

                main_layout, UPCOMING_PRAYERS = set_main_layout_and_upcoming_prayers(
                    m_data)

                # close location choosing window, start main app window
                break

    choose_location.close()
else:
    SAVE_LOCATION = True
    saved_location_api_res = fetch_calender_data(
        sg.user_settings_get_entry('-city-'),
        sg.user_settings_get_entry('-country-')
    )

    main_layout, UPCOMING_PRAYERS = set_main_layout_and_upcoming_prayers(
        saved_location_api_res)


try:
    display_main_window(main_win_layout=main_layout,
                        upcoming_prayers=UPCOMING_PRAYERS)
except KeyboardInterrupt:
    exit()

# user doesnt want to save settings
if not SAVE_LOCATION and sg.user_settings_get_entry('-city-') and sg.user_settings_get_entry('-country-'):
    sg.user_settings_delete_entry('-city-')
    sg.user_settings_delete_entry('-country-')
