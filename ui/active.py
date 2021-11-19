

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtGui import QCursor, QPixmap, QTransform
from PyQt5.QtCore import QEvent, QObject, QSettings, Qt
from PyQt5.QtWidgets import QFrame, QGroupBox, QLabel, QMainWindow, QWidget
from PyQt5.uic import loadUi

class NavButton(QFrame):
    """Navigation 'Button', really a QFrame modified to act like
    a button"""
    def __init__(self, text: str, svg: str, parent: QObject) -> None:
        super(QFrame, self).__init__(parent=parent)
        loadUi("./ui/navbutton.ui", self)
        self.text = text
        self.setObjectName("nav_button_"+text.replace(' ', '_').lower())
        # get theme folder
        theme_folder = QSettings().value("active_theme").folder
        # create icon pixmaps
        self.pixmap = QPixmap(
            f'./ui/resources/{theme_folder}/{svg}.svg')
        # re-scale icons
        self.icon.setPixmap(self.pixmap.scaled(
            30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        self._retranslate()

        self.enterEvent = lambda e: self._enter(e)

    def _retranslate(self) -> None:
        _translate = QtCore.QCoreApplication.translate
        self.text_label.setText(_translate(self.objectName(), self.text))

    def _enter(self, a0: QEvent) -> None:
        """Changes the cursor to a hand when over the button"""
        # change cursor to hand
        self.setCursor(QCursor(Qt.PointingHandCursor))
        return super().enterEvent(a0)

class ActiveWidget(QWidget, object):
    """Main navigation element to show the ui for the user's
    chosen activity. Consists of a collapsable frame to show the
    navigation buttons and a widget stack to show the correct widget
    to the user."""
    def __init__(self, parent: QObject) -> None:
        super(QWidget, self).__init__(parent)
        loadUi("./ui/active.ui", self)
        self.expand_label = QLabel(self)
        self.expand_label.setObjectName("active_expand")
        self.expand_label.setAlignment(
            QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        # get theme folder
        theme_folder = QSettings().value("active_theme").folder
        # create transformation map
        self.rotate_collapse = QTransform().rotate(90)
        self.rotate_expand = QTransform().rotate(270)
        # create icon pixmaps
        self.expand_icon = QPixmap(
            f'./ui/resources/{theme_folder}/double_arrow.svg')
        self.expand_icon_hover = QPixmap(
            f'./ui/resources/{theme_folder}/double_arrow_hover.svg')

        spacer = QtWidgets.QSpacerItem(20, 518, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding)
        self.nav_frame_layout.addWidget(NavButton("Load", 'import',
            self.nav_frame), 0, 0, 1, 1)
        self.nav_frame_layout.addWidget(NavButton("Compare", 'compare',
            self.nav_frame), 1, 0, 1, 1)
        self.nav_frame_layout.addWidget(NavButton("Explore", 'explore',
            self.nav_frame), 2, 0, 1, 1)
        self.nav_frame_layout.addItem(spacer, 3, 0, 1, 1)
        self.nav_frame_layout.addWidget(self.expand_label, 4, 0, 1, 1)

        # initialise navbar state depending on user setting
        if QSettings().value('navbar_expanded') == 'true':
            self._expand(False)
        else:
            self._collapse(False)

        self.expand_label.enterEvent = lambda e: self._expand_hover_enter(e)
        self.expand_label.leaveEvent = lambda e: self._expand_hover_leave(e)
        self.expand_label.mousePressEvent = lambda e: self._toggle_expand()

    def _get_expand_icon(self, hover: bool) -> QPixmap:
        """Returns a QPixmap of the expanded icon in the
        correct state given the hover and expanded inputs"""
        if QSettings().value('navbar_expanded', True) == 'true':
            transformation = self.rotate_collapse
        else:
            transformation = self.rotate_expand
        if hover:
            icon = self.expand_icon_hover
        else:
            icon = self.expand_icon
        return icon.scaled(20, 20, Qt.KeepAspectRatio,
            Qt.SmoothTransformation).transformed(transformation)

    def _expand_hover_enter(self, a0: QEvent) -> None:
        """Changes the expand icon when cursor hovers it's label"""
        # change cursor to hand
        self.expand_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.expand_label.setPixmap(self._get_expand_icon(True))
        return super().enterEvent(a0)

    def _expand_hover_leave(self, a0: QEvent) -> None:
        """Changes the expand icon when cursor leaves it's label"""
        self.expand_label.setPixmap(self._get_expand_icon(False))
        return super().enterEvent(a0)

    def _expand(self, hovering: bool) -> None:
        """Expands the navbar"""
        [navbutton.text_label.show() for navbutton in \
            self.findChildren(NavButton)]
        self.nav_frame.setMinimumSize(QtCore.QSize(150, 0))
        self.nav_frame.setMaximumSize(QtCore.QSize(150, 16777215))
        self.expand_label.setPixmap(self._get_expand_icon(hovering))

    def _collapse(self, hovering: bool) -> None:
        """Collapses the navbar"""
        [navbutton.text_label.hide() for navbutton in \
            self.findChildren(NavButton)]
        self.nav_frame.setMinimumSize(QtCore.QSize(50, 0))
        self.nav_frame.setMaximumSize(QtCore.QSize(50, 16777215))
        self.expand_label.setPixmap(self._get_expand_icon(hovering))

    def _toggle_expand(self) -> None:
        """Toggle the navbar state adjusting settings to match"""
        if QSettings().value('navbar_expanded', True) == 'true':
            QSettings().setValue('navbar_expanded', False)
            self._collapse(True)
        else:
            QSettings().setValue('navbar_expanded', True)
            self._expand(True)