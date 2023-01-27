"""modified version of PrayerTimes class that contains
all calculation methods & furood-related attributes
"""
import datetime
from zoneinfo import ZoneInfo

from adhanpy.PrayerTimes import PrayerTimes
from adhanpy.calculation.PrayerAdjustments import PrayerAdjustments
from adhanpy.calculation import CalculationMethod, CalculationParameters
from adhanpy.calculation.MethodsParameters import methods_parameters


class ModifiedPrayerTimes(PrayerTimes):
    """Class that provides interface for prayer times, furood & calculation methods"""

    def __init__(self, parent, date=datetime.datetime.now()):
        self.parent = parent
        self.now = None
        self.update_time()
        self.tomorrow = self.now+datetime.timedelta(days=1)

        self.prayer_offsets = None
        self.update_prayer_offset()
        self.coords = self.parent.settings["-location-"]["-coordinates-"]
        self.calculation_methods = {
            1: (CalculationMethod.KARACHI, "University of Islamic Sciences in Karachi"),
            2: (CalculationMethod.NORTH_AMERICA, "Islamic Society of North America (ISNA)"),
            3: (CalculationMethod.MUSLIM_WORLD_LEAGUE, "Muslim World League (MWL)"),
            4: (CalculationMethod.UMM_AL_QURA, "Umm Al-Qura University in Makkah"),
            5: (CalculationMethod.EGYPTIAN, "Egyptian General Authority of Survey"),
            15: (CalculationMethod.MOON_SIGHTING_COMMITTEE, "Moonsighting Committee"),
            9: (CalculationMethod.KUWAIT, "Kuwait"),
            10: (CalculationMethod.QATAR, "Qatar"),
            11: (CalculationMethod.SINGAPORE, "Singapore"),
            12: (CalculationMethod.UOIF, "UOIF"),
            99: (CalculationParameters(fajr_angle=self.parent.settings["-custom-angles-"][0],
                                       isha_angle=self.parent.settings["-custom-angles-"][1],
                                       adjustments=self.prayer_offsets), "Custom")
        }
        self.current_furood = None
        self.current_fard, self.upcoming_fard = None, None

        if self.parent.calculation_data["method"]["id"] in self.calculation_methods:
            self.parent.settings["-default-method-"] = self.parent.calculation_data["method"]["id"]
        else:
            self.parent.settings["-default-method-"] = 4

        if not self.parent.settings["-used-method-"]:
            self.parent.settings["-used-method-"] = self.parent.settings["-default-method-"]

        self.update_current_furood(date=date)

    def update_time(self):
        """method to update the 'now' attribute of the application according to the local time
        """
        self.now = datetime.datetime.now(
            tz=ZoneInfo(self.parent.settings["-location-"]["-timezone-"])).replace(microsecond=0)

    def update_prayer_offset(self):
        """method to update the currently used prayer offsets from the settings file"""
        self.prayer_offsets = PrayerAdjustments(
            self.parent.settings["-offset-"]["-Fajr-"],
            self.parent.settings["-offset-"]["-Sunrise-"],
            self.parent.settings["-offset-"]["-Dhuhr-"],
            self.parent.settings["-offset-"]["-Asr-"],
            self.parent.settings["-offset-"]["-Maghrib-"],
            self.parent.settings["-offset-"]["-Isha-"]
        )

    def prayer_time_came(self):
        """method to check whether next prayer time came & notify the user if that's the case

        :return bool: whether the upcoming prayer time came or not
        """
        return self.now >= self.upcoming_fard[1]

    def update_current_furood(self, date: datetime.datetime):
        """method to update the current_furood attribute with prayer times of the given date

        :param datetime.datetime date: date to get pt for
        """
        if self.parent.settings["-used-method-"] == 99:
            params: CalculationParameters = self.calculation_methods[99][0]
            params.method = None
            params.fajr_angle = self.parent.settings["-custom-angles-"][0]
            params.isha_angle = self.parent.settings["-custom-angles-"][1]
        else:
            method: CalculationMethod = \
                self.calculation_methods[self.parent.settings["-used-method-"]][0]
            params = CalculationParameters(method,
                                           adjustments=self.prayer_offsets)

        super().__init__(self.coords, date,
                         calculation_parameters=params,
                         time_zone=ZoneInfo(self.parent.settings["-location-"]["-timezone-"]))

        self.current_furood = {name: getattr(self, name.lower())
                               for name in self.parent.displayed_times}

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
            self.update_current_furood(self.tomorrow)
            self.upcoming_fard = ("Fajr", self.current_furood["Fajr"])
            isha_passed = True

        elif self.now >= self.current_furood["Maghrib"]:
            self.current_fard = ("Maghrib", self.current_furood["Maghrib"])
            self.upcoming_fard = ("Isha", self.current_furood["Isha"])

        elif self.now >= self.current_furood["Asr"]:
            self.current_fard = ("Asr", self.current_furood["Asr"])
            self.upcoming_fard = ("Maghrib", self.current_furood["Maghrib"])

        elif self.now >= self.current_furood["Dhuhr"]:
            self.current_fard = ("Dhuhr", self.current_furood["Dhuhr"])
            self.upcoming_fard = ("Asr", self.current_furood["Asr"])

        elif self.now >= self.current_furood["Sunrise"]:
            self.current_fard = ("Sunrise", self.current_furood["Sunrise"])
            self.upcoming_fard = ("Dhuhr", self.current_furood["Dhuhr"])

        elif self.now >= self.current_furood["Fajr"]:
            self.current_fard = ("Fajr", self.current_furood["Fajr"])
            self.upcoming_fard = ("Sunrise", self.current_furood["Sunrise"])

        else:
            self.current_fard = ("Isha", self.current_furood["Isha"])
            self.upcoming_fard = ("Fajr", self.current_furood["Fajr"])

        return isha_passed

    def get_method_id(self, method_name: str):
        """method to set the id of the given calculation method name in the settings file

        :param (str) method_name: name of the method to get the id for
        :return (int): the id of the given method
        """
        for identifier, details in self.calculation_methods.items():
            if method_name == details[1]:
                return identifier

    def get_method_params(self, method_id):
        """method to get the parameters used for calculation by one of the standard methods

        :param int method_id: method id as in the calculation_methods dictionary
        :return dict: dictionary containing key-value pairs of calculation parameters
        """
        return methods_parameters[self.calculation_methods[method_id][0]]
