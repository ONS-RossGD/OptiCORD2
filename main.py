import sys
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
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


class MainWindow(QMainWindow, object):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("main.ui", self)
        self.pages = Pages()
        self.setCentralWidget(self.pages.list[0])
        self.centralWidget().commandLinkButton_next.clicked.connect(lambda: self.next_page())
    
    def set_active_page(self, page: QWidget):
        self.setCentralWidget(page)

    def next_page(self):
        self.setCentralWidget(self.pages.next(self.centralWidget()))

    def prev_page(self):
        self.setCentralWidget(self.pages.prev(self.centralWidget()))


def main():
    app = QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    try:
        sys.exit(app.exec_())
    except:
        print("Exiting")

if __name__ == "__main__":
    main()