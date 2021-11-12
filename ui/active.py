

from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, QSettings
from PyQt5.QtWidgets import QLabel, QMainWindow, QWidget
from PyQt5.uic import loadUi

class NavButton(QLabel):
    """"""
    def __init__(self, text: str, parent: QObject):
        super(QLabel, self).__init__(parent=parent)
        self.text = text
        self.setObjectName("nav_button_"+text.replace(' ', '_'))
        self.setContentsMargins(0, 0, 0, 0)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(QtCore.QSize(120, 60))
        self.setMaximumSize(QtCore.QSize(160, 60))
        font = QtGui.QFont()
        font.setFamily("Bahnschrift SemiBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.setFont(font)
        self.setStyleSheet(
            "QLabel:hover{\n"
                    "background: red;\n"
                "}\n"
                "QLabel{\n"
                    "border-bottom: 1px solid black;\n"
                "}")
        self.retranslate()

    def retranslate(self):
        _translate = QtCore.QCoreApplication.translate
        self.setText(_translate(self.objectName(), self.text))

class ActiveWidget(QWidget, object):
    """Main window of application"""
    def __init__(self, parent: QObject):
        super(QWidget, self).__init__(parent)
        self.settings = QSettings()
        #self.logger.debug('loading main.ui')
        loadUi("./ui/active.ui", self)

        spacer = QtWidgets.QSpacerItem(20, 518, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.nav_frame_layout.addWidget(NavButton("Load", self.nav_frame), 0, 0, 1, 1)
        self.nav_frame_layout.addWidget(NavButton("Compare", self.nav_frame), 1, 0, 1, 1)
        self.nav_frame_layout.addWidget(NavButton("Explore", self.nav_frame), 2, 0, 1, 1)
        self.nav_frame_layout.addItem(spacer, 3, 0, 1, 1)
        
        self.nav_frame.setStyleSheet("QFrame#nav_frame{\n"
            "border-right: 2px solid black;\n"
            "padding-right: 0px;\n"
            "}")