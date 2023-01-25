"""main file to start athany app instance"""
import src.athany

if __name__ == "__main__":

    RESTART_APP = True
    while RESTART_APP:

        app = src.athany.Athany()
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
