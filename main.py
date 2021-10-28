import sys
import BreezeStyleSheets.breeze_resources # looks redundant but is used to activate stylesheets
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
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
    theme_name: str
    app: QApplication

    def __post_init__(self):
        file = QFile(":/"+self.theme_name+"/stylesheet.qss")
        file.open(QFile.ReadOnly | QFile.Text)
        stream = QTextStream(file)
        self.theme = stream.readAll()
    
    def activate(self):
        self.app.setStyleSheet(self.theme)

class MainWindow(QMainWindow, object):
    def __init__(self, themes: dict):
        super(MainWindow, self).__init__()
        loadUi("main.ui", self)
        self.pages = Pages()
        self.themes = themes
        self.themes["dark-purple"].activate()
        self.setCentralWidget(self.pages.list[0])
        self.centralWidget().commandLinkButton_next.clicked.connect(lambda: self.themes["dark-purple"].activate())
        self.setup_singals()
    
    def setup_singals(self):
        self.dark_blue_theme.triggered.connect(lambda: self.themes["dark-blue"].activate())
        self.dark_green_theme.triggered.connect(lambda: self.themes["dark-green"].activate())
        self.dark_purple_theme.triggered.connect(lambda: self.themes["dark-purple"].activate())
        self.light_blue_theme.triggered.connect(lambda: self.themes["light-blue"].activate())
        self.light_green_theme.triggered.connect(lambda: self.themes["light-green"].activate())
        self.light_purple_theme.triggered.connect(lambda: self.themes["light-purple"].activate())

    def set_active_page(self, page: QWidget):
        self.setCentralWidget(page)

    def next_page(self):
        self.setCentralWidget(self.pages.next(self.centralWidget()))

    def prev_page(self):
        self.setCentralWidget(self.pages.prev(self.centralWidget()))


def setup_themes(app: QApplication):
    themes = {}
    themes["dark-blue"] = Theme("dark", app)
    themes["dark-green"] = Theme("dark-green", app)
    themes["dark-purple"] = Theme("dark-purple", app)
    themes["light-blue"] = Theme("light", app)
    themes["light-green"] = Theme("light-green", app)
    themes["light-purple"] = Theme("light-purple", app)
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