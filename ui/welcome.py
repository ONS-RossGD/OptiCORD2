from PyQt5.QtCore import QEvent, QObject, QSettings, Qt
from PyQt5.QtGui import QCursor, QPixmap
from PyQt5.QtWidgets import QGroupBox, QWidget
from PyQt5.uic import loadUi
import actions


class WelcomePage(QWidget, object):
    """Welcome page ui. Load's vanilla ui elements from a QT Designer
    .ui file whilst also allowing custom elements to be built on top."""

    def __init__(self, parent: QObject):
        super(QWidget, self).__init__(parent)
        # load the vanilla elements from QT Designer file
        loadUi("./ui/welcome.ui", self)
        # get theme folder
        theme_folder = QSettings().value("active_theme").folder
        # create icon pixmaps
        self.new_pixmap = QPixmap(
            f'./ui/resources/{theme_folder}/new_project.svg')
        self.open_pixmap = QPixmap(
            f'./ui/resources/{theme_folder}/open_project.svg')
        # re-scale icons
        self.new_group_image.setPixmap(self.new_pixmap.scaled(
            75, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.open_group_image.setPixmap(self.open_pixmap.scaled(
            75, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # transform groupbox's into buttons
        # set up hover
        self.new_group.enterEvent = lambda e: self.group_hover_enter(
            e, self.new_group)
        self.new_group.leaveEvent = lambda e: self.group_hover_leave(
            e, self.new_group)
        self.open_group.enterEvent = lambda e: self.group_hover_enter(
            e, self.open_group)
        self.open_group.leaveEvent = lambda e: self.group_hover_leave(
            e, self.open_group)
        # substitute of .clicked.connect event
        self.new_group.mousePressEvent = lambda e: actions.create_new(self)
        self.open_group.mousePressEvent = lambda e: actions.open_file(self)

    def group_hover_enter(self, a0: QEvent, groupbox: QGroupBox) -> None:
        """Changes the styling of a groupbox when mouse starts hovering"""
        # this property has different css styling
        groupbox.setProperty("hovering", "true")
        # change cursor to hand
        groupbox.setCursor(QCursor(Qt.PointingHandCursor))
        # style has to be unpolished and polished to update
        groupbox.style().unpolish(groupbox)
        groupbox.style().polish(groupbox)
        return super().enterEvent(a0)

    def group_hover_leave(self, a0: QEvent, groupbox: QGroupBox) -> None:
        """Changes the styling of a groupbox when mouse finishes hovering"""
        # this property has different css styling
        groupbox.setProperty("hovering", "false")
        # style has to be unpolished and polished to update
        groupbox.style().unpolish(groupbox)
        groupbox.style().polish(groupbox)
        return super().enterEvent(a0)
