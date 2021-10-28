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
    theme: str = field(init=False)
    folder: str
    action_name: str
    display: str
    app: QApplication

    def __post_init__(self):
        file = QFile(":/"+self.folder+"/stylesheet.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        self.theme = stream.readAll()
    
    def activate(self):
        self.app.setStyleSheet(self.theme)

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
        self.theme.activate()
        [x.setChecked(False) for x in self.parentWidget().findChildren(QThemeAction)]
        self.setChecked(True)

class MainWindow(QMainWindow, object):
    def __init__(self, themes: dict):
        super(MainWindow, self).__init__()
        loadUi("main.ui", self)
        self.pages = Pages()
        self.themes = themes
        for theme in self.themes.values():
            self.menuTheme.addAction(QThemeAction(theme, self))
        self.findChild(QThemeAction, "dark_purple_theme").apply()
        self.setCentralWidget(self.pages.list[0])
        self.centralWidget().commandLinkButton_next.clicked.connect(lambda: self.themes["dark-purple"].activate())

    def set_active_page(self, page: QWidget):
        self.setCentralWidget(page)

    def next_page(self):
        self.setCentralWidget(self.pages.next(self.centralWidget()))

    def prev_page(self):
        self.setCentralWidget(self.pages.prev(self.centralWidget()))


def setup_themes(app: QApplication):
    themes = {}
    themes["dark-blue"] = Theme("dark", "dark_blue_theme", "Dark (Blue)", app)
    themes["dark-green"] = Theme("dark-green", "dark_green_theme", "Dark (Green)", app)
    themes["dark-purple"] = Theme("dark-purple", "dark_purple_theme", "Dark (Purple)", app)
    themes["light-blue"] = Theme("light", "light_blue_theme", "Light (Blue)", app)
    themes["light-green"] = Theme("light-green", "light_green_theme", "Light (Green)", app)
    themes["light-purple"] = Theme("light-purple", "light_purple_theme", "Light (Purple)", app)
    return themes

def main():
    app = QApplication(sys.argv)
    themes = setup_themes(app)
    mainwindow = MainWindow(themes)
    mainwindow.show()
    try:
        sys.exit(app.exec_())
    except:
        print("Exiting")

if __name__ == "__main__":
    main()