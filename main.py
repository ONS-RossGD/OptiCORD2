import sys
import BreezeStyleSheets.breeze_resources # looks redundant but is used to activate stylesheets
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QMainWindow
from themes import ThemeRegistry
from opticord_widgets import QThemeAction
from pages import PageRegistry

class MainWindow(QMainWindow, object):
    """Main window of application"""
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("main.ui", self)
        self.app = QApplication.instance()
        self.pages = PageRegistry()
        self.themes = ThemeRegistry()
        for theme in self.themes:
            self.menuTheme.addAction(QThemeAction(theme, self))
        
        # temporarily apply dark purple theme while QSettings is set up
        self.findChild(QThemeAction, "dark_purple_theme").apply()
        self.setCentralWidget(self.pages[1]()) # set page to first page

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