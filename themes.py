"""The themes.py module contains objects responsible for changing themes
in the main OptiCORD application.
"""
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtWidgets import QApplication
from dataclasses import dataclass, field

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

    def __getitem__(self, i: int) -> Theme:
        """Return a specific Theme if ThemeRegistry()[i] is called"""
        return self.themes[i]

    def __iter__(self) -> Theme:
        """Defines how to iterate over ThemeRegistry"""
        for theme in self.themes:
            yield theme