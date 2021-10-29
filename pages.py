
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QWidget
from dataclasses import dataclass

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
