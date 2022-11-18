import PySimpleGUI as sg
import json
import datetime
import os
import requests
from psgtray import SystemTray

DATA_DIR = os.path.join(os.getcwd(), 'Data')
if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)
API_ENDPOINT = "https://api.aladhan.com/v1/calendarByCity"
FUROOD_NAMES = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
UPCOMING_PRAYERS = []

NOW = datetime.datetime.now()
CURRENT_YEAR = NOW.year
CURRENT_MON = NOW.month
CURRENT_DAY = NOW.day

GUI_FONT = "Calibri"

sg.user_settings_delete_filename(filename='athany-config.json')


def fetch_calender_data(cit: str, count: str) -> str:
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


def set_main_layout_and_upcoming_prayers(api_res: dict) -> (list, list):

    CURRENT_PRAYER_TIMES = api_res["data"][CURRENT_DAY-1]["timings"]

    ISHA_OBJ = CURRENT_PRAYER_TIMES['Isha'].split()

    # Check if Isha passed as to get the following day timings
    # Prayer times change after Isha athan to the times of the following day
    # if NOW is after current Isha time
    ISHA_PASSED = False
    if NOW > datetime.datetime.strptime(f"{ISHA_OBJ[0]} {CURRENT_DAY} {CURRENT_MON} {CURRENT_YEAR}", "%H:%M %d %m %Y"):
        # replace all prayer times with the next day prayers
        CURRENT_PRAYER_TIMES = api_res["data"][CURRENT_DAY]["timings"]
        ISHA_PASSED = True

    # loop through all prayer times to convert timing to datetime objects to be able to preform operations on them
    for k, v in CURRENT_PRAYER_TIMES.items():
        # to adjust the day,month, year of the prayer datetime object
        DAY = CURRENT_DAY+1 if ISHA_PASSED else CURRENT_DAY
        t = v.split(" ")[0] + f" {DAY} {CURRENT_MON} {CURRENT_YEAR}"
        CURRENT_PRAYER_TIMES[k] = datetime.datetime.strptime(
            t, "%H:%M %d %m %Y")
        # for debugging
        if k in FUROOD_NAMES:
            print(k, CURRENT_PRAYER_TIMES[k].strftime("%I:%M %p"))

    for prayer, time in CURRENT_PRAYER_TIMES.items():  # append upcoming prayers to list
        if NOW < time and prayer in FUROOD_NAMES:
            UPCOMING_PRAYERS.append([prayer, time])

    prayer_times_layout = [
        [sg.Text("Current Date", font=GUI_FONT), sg.Push(), sg.Text("~", font=GUI_FONT), sg.Push(), sg.Text(
            f"{NOW.date()}", font=GUI_FONT, key="-CURRENT_DATE-")],
        [sg.Text("Next Prayer:", font=GUI_FONT), sg.Push(), sg.Text(font=GUI_FONT, key="-NEXT PRAYER-"),
            sg.Text("in", font=GUI_FONT), sg.Text(font=GUI_FONT, key="-TIME_D-")],
        [sg.Text("Fajr: ", font=GUI_FONT), sg.Push(), sg.Text(f"{CURRENT_PRAYER_TIMES['Fajr'].strftime('%I:%M %p')}",
                                                              font=GUI_FONT, key="-FAJR TIME-")],
        [sg.Text("Dhuhr: ", font=GUI_FONT), sg.Push(), sg.Text(f"{CURRENT_PRAYER_TIMES['Dhuhr'].strftime('%I:%M %p')}",
                                                               font=GUI_FONT, key="-DHUHR TIME-")],
        [sg.Text("Asr: ", font=GUI_FONT), sg.Push(), sg.Text(f"{CURRENT_PRAYER_TIMES['Asr'].strftime('%I:%M %p')}",
                                                             font=GUI_FONT, key="-ASR TIME-")],
        [sg.Text("Maghrib: ", font=GUI_FONT), sg.Push(), sg.Text(f"{CURRENT_PRAYER_TIMES['Maghrib'].strftime('%I:%M %p')}",
                                                                 font=GUI_FONT, key="-MAGHRIB TIME-")],
        [sg.Text("Isha: ", font=GUI_FONT), sg.Push(), sg.Text(f"{CURRENT_PRAYER_TIMES['Isha'].strftime('%I:%M %p')}",
                                                              font=GUI_FONT, key="-ISHA TIME-")],
        [sg.Button("Exit")]
    ]
    return prayer_times_layout, UPCOMING_PRAYERS


sg.theme("DarkAmber")
# define the layouts for the app
location_win_layout = [[sg.Text("Enter your location", size=(50, 1), key='-LOC TXT-', font=GUI_FONT)],
                       [sg.Text("City", font=GUI_FONT), sg.Input(size=(15, 1), key="-CITY-", focus=True),
                        sg.Text("Country", font=GUI_FONT), sg.Input(size=(15, 1), key="-COUNTRY-"), sg.Push(), sg.Checkbox("Save settings", key='-SAVE_LOC_CHECK-')],
                       [sg.Button("Ok", font=GUI_FONT), sg.Button("Cancel", font=GUI_FONT)]]

sg.user_settings_filename(filename='athany-config.json')

if sg.user_settings_get_entry('-city-') is None and sg.user_settings_get_entry('-country-') is None:
    choose_location = sg.Window("Athany", location_win_layout)

    while True:
        event, values = choose_location.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            break
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
                if values['-SAVE_LOC_CHECK-']:
                    sg.user_settings_set_entry('-city-',
                                               values['-CITY-'])
                    sg.user_settings_set_entry('-country-',
                                               values['-COUNTRY-'])

                main_win_layout, UPCOMING_PRAYERS = set_main_layout_and_upcoming_prayers(
                    m_data)

                break

    print(event, values)
    choose_location.close()
else:
    saved_location_api_res = fetch_calender_data(
        sg.user_settings_get_entry('-city-'),
        sg.user_settings_get_entry('-country-')
    )

    main_win_layout, UPCOMING_PRAYERS = set_main_layout_and_upcoming_prayers(
        saved_location_api_res)

main_window = sg.Window("Athany: a python athan app",
                        main_win_layout, finalize=True) if main_win_layout else exit()

while True:
    NOW = datetime.datetime.now().replace(microsecond=0)

    if NOW >= UPCOMING_PRAYERS[0][1]:
        UPCOMING_PRAYERS.pop(0)

    TIME_D = UPCOMING_PRAYERS[0][1] - NOW

    main_window['-NEXT PRAYER-'].update(value=f'{UPCOMING_PRAYERS[0][0]}')
    main_window['-TIME_D-'].update(value=f'{TIME_D}')
    print(UPCOMING_PRAYERS)

    event, values = main_window.read(timeout=1000)
    if event == sg.WIN_CLOSED or event == "Exit":
        break
