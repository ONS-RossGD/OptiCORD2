"""OptiCORD - An Optimisation tool for CORD users.
"""

__version__ = '2.0.0'

import sys
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
        self.logger.debug('loading main.ui')
        loadUi("main.ui", self)
        self.app = QApplication.instance()
        self.logger.debug('creating theme registry')
        self.themes = ThemeRegistry()
        self.logger.debug('setting up pages')
        self.pages = Pages(self)
        self.logger.debug('adding navigation bar')
        self.nav = QNavWidget(self, self.pages)
        self.logger.debug('filling themes')
        for theme in self.themes:
            self.menuTheme.addAction(QThemeAction(theme, self))

        # temporarily apply dark purple theme while QSettings is set up
        self.findChild(QThemeAction, "dark_purple_theme").apply()
        # add pages widget and nav bar to the layout
        self.main_grid.addWidget(self.pages, 1, 0, 1, 1)
        self.main_grid.addWidget(self.nav, 2, 0, 1, 1)

def main():
    """Main loop"""
    app = QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    try:
        sys.exit(app.exec_())
    except: # TODO catch correct Exception.
        print("Exiting")

if __name__ == "__main__":
    main()