

from PyQt5.QtCore import QObject, QSettings
from PyQt5.QtWidgets import QAction, QMainWindow
from PyQt5.uic import loadUi
from themes import ThemeRegistry, Theme

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
        self.settings = QSettings()
        #self.logger.debug('loading main.ui')
        loadUi("./ui/mainwindow.ui", self)
        self.themes = ThemeRegistry() # load all themes
        # apply the users selected theme defaulted to dark purple
        self.settings.value("active_theme", self.themes[2]).apply()
        #self.pages = Pages(self)
        #self.nav = QNavWidget(self, self.pages)
        # fill the themes menu 
        for theme in self.themes:
            self.menu_theme.addAction(QThemeAction(theme, self))

        # add pages widget and nav bar to the layout
        #self.main_grid.addWidget(self.pages, 1, 0, 1, 1)
        #self.main_grid.addWidget(self.nav, 2, 0, 1, 1)