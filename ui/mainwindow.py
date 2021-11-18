

from PyQt5.QtCore import QObject, QSettings
from PyQt5.QtWidgets import QAction, QMainWindow
from PyQt5.uic import loadUi
from themes import ThemeRegistry, Theme
import actions

class QThemeAction(QAction):
    """A QAction Object for Theme items"""
    def __init__(self, theme: Theme, parent: QObject):
        super(QAction, self).__init__(text=theme.display, parent=parent)
        self.theme = theme
        self.settings = QSettings()
        self.setCheckable(True)
        self.setObjectName(theme.action_name)
        self.triggered['bool'].connect(self.apply)
        if self.settings.value("active_theme") == self.theme:
            self.setChecked(True)

    def apply(self):
        """Apply the associated theme to its main window"""
        self.theme.apply()
        [x.setChecked(False) for x in self.parentWidget()\
            .findChildren(QThemeAction)]
        self.setChecked(True)

class MainWindow(QMainWindow, object):
    """Main window of application"""
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("./ui/mainwindow.ui", self)
        self.themes = ThemeRegistry() # load all themes
        # apply the users selected theme defaulted to dark purple
        QSettings().value("active_theme", self.themes[2]).apply()
        # fill the themes menu 
        for theme in self.themes:
            self.menu_theme.addAction(QThemeAction(theme, self))

        self.action_new.triggered[bool].connect(
            lambda: actions.create_new(self))
        self.action_open.triggered[bool].connect(
            lambda: actions.open(self))