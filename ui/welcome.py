

from PyQt5.QtCore import QObject, QSettings, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.uic import loadUi

class WelcomePage(QWidget, object):
    """Main window of application"""
    def __init__(self, parent: QObject):
        super(QWidget, self).__init__(parent)
        self.settings = QSettings()
        # get theme folder
        theme_folder = self.settings.value("active_theme").folder
        #self.logger.debug('loading main.ui')
        loadUi("./ui/welcome.ui", self)
        # create icon pixmaps
        self.new_pixmap = QPixmap(
            f'./ui/resources/{theme_folder}/new_project.svg')
        self.open_pixmap = QPixmap(
            f'./ui/resources/{theme_folder}/open_project.svg')
        self.new_group_image.setPixmap(self.new_pixmap.scaled(
            100, 100, Qt.KeepAspectRatio))
        self.open_group_image.setPixmap(self.open_pixmap.scaled(
            100, 100, Qt.KeepAspectRatio))