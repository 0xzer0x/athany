"""
module for translating UI into a given language
"""
import os
import sys
import json
import arabic_reshaper
from bidi.algorithm import get_display


class Translator:
    """class that provides an interface for translation & layout adjustment"""

    def __init__(self, lang: str, trans_files_dir: str):
        self.lang = lang
        self.translation_dict = None
        self.bidirectional = False

        if lang == 'ar':
            self.bidirectional = True
        if lang != 'en':
            self.translation_dict = json.load(
                open(os.path.join(trans_files_dir, lang+'_trans.json'), 'r', encoding='utf-8'))

    # ------------------------------------- UI Translation methods ------------------------------- #
    @staticmethod
    def display_ar_text(text: str) -> str:
        """
        :param text: (str) arabic text to display correctly
        :return: (str) correctly formatted arabic string
        """
        if sys.platform != "win32":
            ar_txt = arabic_reshaper.reshape(text)
            bidi_txt = get_display(ar_txt)
            return bidi_txt
        else:
            return text

    def translate(self, sentence):
        """method to translate the given string in the language of the translator object
        :param str sentence: string to translate
        :return str: translated text correctly formatted
        """
        if not self.translation_dict:
            text = sentence
        else:
            text = self.display_ar_text(
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
