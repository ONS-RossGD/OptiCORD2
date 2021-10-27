import sys
from PyQt5.uic import loadUi, loadUiType
from PyQt5.QtWidgets import QApplication, QGridLayout, QMainWindow, QWidget
from dataclasses import dataclass

@dataclass(frozen=True)
class Page(QWidget):
    """"""
    id: int
    ui_path: str

class MainWindow(QMainWindow, object):
    def __init__(self, *args: QWidget):
        super(MainWindow, self).__init__()
        loadUi("main.ui", self)
    
    def set_active_page(self, page: Page):
        self.setCentralWidget(loadUi(page.ui_path))


def main():
    app = QApplication(sys.argv)
    mainwindow = MainWindow()
    load_page = Page(1, "load.ui")
    print(load_page.id)
    mainwindow.show()
    mainwindow.set_active_page(load_page)
    try:
        sys.exit(app.exec_())
    except:
        print("Exiting")

if __name__ == "__main__":
    main()