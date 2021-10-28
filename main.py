import sys
import BreezeStyleSheets.breeze_resources # looks redundant but is used to activate stylesheets
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QAction, QApplication, QMainWindow, QMenu, QMenuBar, QWidget
from dataclasses import dataclass, field
from typing import List

@dataclass
class Pages:
    list = []
    
    def add_page(self, ui_path):
        widg = loadUi(ui_path)
        self.list.append(widg)

    def __init__(self):
        self.add_page("load.ui")
        self.add_page("options.ui")
        self.add_page("execute.ui")

    def next(self, current: QWidget):
        return self.list[self.list.index(current)+1]

    def prev(self, current: QWidget):
        return self.list[self.list.index(current)-1]

    def first(self):
        return self.list[0]

    def last(self):
        return self.list[-1]

@dataclass
class Theme:
    """Object for Themes to be used in QtApplication"""
    theme: str = field(init=False)
    folder: str
    action_name: str
    display: str

    def __post_init__(self):
        """Create theme data based on input variables"""
        file = QFile(":/"+self.folder+"/stylesheet.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        self.theme = stream.readAll()
    
    def apply(self):
        """Apply the Theme"""
        QApplication.instance().setStyleSheet(self.theme)

class ThemeRegistry:
    """A Registry for all available Theme's"""
    themes = []
    def __init__(self):
        """Define and add Theme's here"""
        self.themes.append(Theme("dark", "dark_blue_theme", "Dark (Blue)"))
        self.themes.append(Theme("dark-green", "dark_green_theme", "Dark (Green)"))
        self.themes.append(Theme("dark-purple", "dark_purple_theme", "Dark (Purple)"))
        self.themes.append(Theme("light", "light_blue_theme", "Light (Blue)"))
        self.themes.append(Theme("light-green", "light_green_theme", "Light (Green)"))
        self.themes.append(Theme("light-purple", "light_purple_theme", "Light (Purple)"))
    
    def __call__(self) -> List[Theme]:
        """Return a list of Theme's if ThemeRegistry is called"""
        return self.themes

    def __iter__(self) -> Theme:
        """Defines how to iterate over Themes"""
        for theme in self.themes:
            yield theme

class QThemeAction(QAction):
    """A QAction Object for Theme items"""
    def __init__(self, theme: Theme, parent=None):
        QAction.__init__(self, text=theme.display, parent=parent)
        self.theme = theme
        self.setCheckable(True)
        self.setObjectName(theme.action_name)
        self.triggered['bool'].connect(self.apply)

    def apply(self):
        """Apply the associated theme to its main window"""
        self.theme.apply()
        [x.setChecked(False) for x in self.parentWidget().findChildren(QThemeAction)]
        self.setChecked(True)

class MainWindow(QMainWindow, object):
    """Main window of application"""
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("main.ui", self)
        self.app = QApplication.instance()
        self.pages = Pages()
        self.themes = ThemeRegistry()
        for theme in self.themes:
            self.menuTheme.addAction(QThemeAction(theme, self))
        
        # temporarily apply dark purple theme while QSettings is set up
        self.findChild(QThemeAction, "dark_purple_theme").apply()
        self.setCentralWidget(self.pages.list[0])
        self.centralWidget().commandLinkButton_next.clicked.connect(lambda: self.themes["dark-purple"].apply())

    def set_active_page(self, page: QWidget):
        self.setCentralWidget(page)

    def next_page(self):
        self.setCentralWidget(self.pages.next(self.centralWidget()))

    def prev_page(self):
        self.setCentralWidget(self.pages.prev(self.centralWidget()))

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