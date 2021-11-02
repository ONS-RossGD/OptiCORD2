"""OptiCORD - An Optimisation tool for CORD users.
"""

__version__ = '2.0.0'

import sys

from PyQt5.QtCore import QSettings
import BreezeStyleSheets.breeze_resources # looks redundant but is used to activate stylesheets
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QMainWindow
from themes import ThemeRegistry
from opticord_widgets import QNavWidget, QThemeAction
from pages import Pages
import opticord_logging

class MainWindow(QMainWindow, object):
    """Main window of application"""
    logger = opticord_logging.get_log('MainWindow')
    def __init__(self):
        super(MainWindow, self).__init__()
        self.settings = QSettings()
        self.logger.debug('loading main.ui')
        loadUi("main.ui", self)
        self.themes = ThemeRegistry()
        # apply the users selected theme defaulted to dark purple
        self.settings.value("active_theme", self.themes[2]).apply()
        self.pages = Pages(self)
        self.nav = QNavWidget(self, self.pages)
        # fill the themes menu 
        for theme in self.themes:
            self.menuTheme.addAction(QThemeAction(theme, self))

        # add pages widget and nav bar to the layout
        self.main_grid.addWidget(self.pages, 1, 0, 1, 1)
        self.main_grid.addWidget(self.nav, 2, 0, 1, 1)

def main():
    """Main loop"""
    app = QApplication(sys.argv)
    # set up the path for QSettings so it can be accessed anywhere
    app.setApplicationName("OptiCORD")
    app.setOrganizationName("ONS")
    app.setOrganizationDomain("ons.gov.uk")
    mainwindow = MainWindow() # creates the main window instance
    mainwindow.show() # begin showing to user
    try:
        sys.exit(app.exec_())
    except: # TODO catch correct Exception.
        print("Exiting")

if __name__ == "__main__":
    main()