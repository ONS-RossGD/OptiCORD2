from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtGui import QCursor, QMouseEvent, QPixmap, QTransform
from PyQt5.QtCore import QEvent, QObject, QSettings, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QFrame, QLabel, QStackedWidget, QWidget
from PyQt5.uic import loadUi
from ui.load import LoadWidget
from ui.compare import CompareWidget
from util import TempFile, resource_path


class NavButton(QFrame):
    """Navigation 'Button', really a QFrame modified to act like
    a button."""
    clicked = pyqtSignal()

    def __init__(self, text: str, svg: str, widget: QWidget,
                 stack: QStackedWidget, parent: QObject) -> None:
        super(QFrame, self).__init__(parent=parent)
        loadUi(resource_path()+"/ui/navbutton.ui", self)
        self.text = text
        self.parent = parent
        self.stack = stack
        self.widget = widget
        self.nav_buttons = self.parent.findChildren(NavButton)
        # add widget to stack
        self.stack.addWidget(widget)
        # get theme folder
        theme_folder = QSettings().value("active_theme").folder
        # create icon pixmaps
        self.pixmap = QPixmap(
            f'{resource_path()}/ui/resources/{theme_folder}/{svg}.svg')
        # re-scale icons
        self.nav_icon.setPixmap(self.pixmap.scaled(
            30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self._retranslate()

        self.enterEvent = lambda e: self._enter(e)
        TempFile.proc_manager.locked.connect(lambda: self.setEnabled(False))
        TempFile.proc_manager.unlocked.connect(lambda: self.setEnabled(True))

    def _retranslate(self) -> None:
        _translate = QtCore.QCoreApplication.translate
        self.nav_text.setText(_translate(self.objectName(), self.text))

    def _enter(self, a0: QEvent) -> None:
        """Changes the cursor to a hand when over the button"""
        # change cursor to hand
        self.setCursor(QCursor(Qt.PointingHandCursor))
        return super().enterEvent(a0)

    def activate(self):
        """Activate the widget assosciated with the nav button"""
        nav_buttons = self.parent.findChildren(NavButton)
        # deactivate all NavButtons
        [x.setProperty("active", "false") for x in nav_buttons]
        # set the clicked button active
        self.setProperty("active", "true")
        # style has to be unpolished and polished to update
        [x.style().unpolish(x) for x in nav_buttons]
        [x.style().polish(x) for x in nav_buttons]
        # set the widget
        self.stack.setCurrentWidget(self.widget)

    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        """Custom clicked event"""
        self.clicked.emit()  # emit clicked signal
        self.activate()
        return super().mouseReleaseEvent(a0)


class ActiveWidget(QWidget, object):
    """Main navigation element to show the ui for the user's
    chosen activity. Consists of a collapsable frame to show the
    navigation buttons and a widget stack to show the correct widget
    to the user."""

    def __init__(self, parent: QObject) -> None:
        super(QWidget, self).__init__(parent)
        loadUi(resource_path()+"/ui/active.ui", self)
        self.expand_label = QLabel(self)
        self.expand_label.setObjectName("active_expand")
        # get theme folder
        theme_folder = QSettings().value("active_theme").folder
        # create transformation map
        self.rotate_collapse = QTransform().rotate(90)
        self.rotate_expand = QTransform().rotate(270)
        # create icon pixmaps
        self.expand_icon = QPixmap(
            f'{resource_path()}/ui/resources/{theme_folder}/double_arrow.svg')
        self.expand_icon_hover = QPixmap(
            f'{resource_path()}/ui/resources/{theme_folder}/double_arrow_hover.svg')

        self.nav_button_load = NavButton("Load", 'import',
                                         LoadWidget(self.stack), self.stack, self.nav_frame)
        self.nav_button_load.setObjectName("nav_button_load")
        self.nav_button_compare = NavButton("Compare", 'compare',
                                            CompareWidget(self.stack), self.stack, self.nav_frame)
        self.nav_button_compare.setObjectName("nav_button_compare")
        # self.nav_button_explore = NavButton("Explore", 'explore',
        #                                     LoadWidget(self.stack), self.stack, self.nav_frame)
        # self.nav_button_explore.setObjectName("nav_button_explore")
        spacer = QtWidgets.QSpacerItem(20, 518, QtWidgets.QSizePolicy.Minimum,
                                       QtWidgets.QSizePolicy.Expanding)
        self.nav_frame_layout.addWidget(self.nav_button_load, 0, 0, 1, 1)
        self.nav_frame_layout.addWidget(self.nav_button_compare, 1, 0, 1, 1)
        # self.nav_frame_layout.addWidget(self.nav_button_explore, 2, 0, 1, 1)
        self.nav_frame_layout.addItem(spacer, 3, 0, 1, 1)
        self.nav_frame_layout.addWidget(self.expand_label, 4, 0, 1, 1)

        # init to load page
        self.nav_button_load.activate()

        # initialise navbar state depending on user setting
        if QSettings().value('navbar_expanded', 'true') == 'true':
            self._expand(False)
        else:
            self._collapse(False)

        self.expand_label.enterEvent = lambda e: self._expand_hover_enter(e)
        self.expand_label.leaveEvent = lambda e: self._expand_hover_leave(e)
        self.expand_label.mousePressEvent = lambda e: self._toggle_expand()

    def _get_expand_icon(self, hover: bool) -> QPixmap:
        """Returns a QPixmap of the expanded icon in the
        correct state given the hover and expanded inputs"""
        if QSettings().value('navbar_expanded', 'true') == 'true':
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
        [navbutton.nav_text.show() for navbutton in
            self.findChildren(NavButton)]
        # align to right
        self.expand_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing |
            QtCore.Qt.AlignVCenter)
        self.expand_label.setPixmap(self._get_expand_icon(hovering))

    def _collapse(self, hovering: bool) -> None:
        """Collapses the navbar"""
        [navbutton.nav_text.hide() for navbutton in
            self.findChildren(NavButton)]
        # align to center
        self.expand_label.setAlignment(QtCore.Qt.AlignCenter)
        self.expand_label.setPixmap(self._get_expand_icon(hovering))

    def _toggle_expand(self) -> None:
        """Toggle the navbar state adjusting settings to match"""
        if QSettings().value('navbar_expanded', 'true') == 'true':
            QSettings().setValue('navbar_expanded', 'false')
            self._collapse(True)
        else:
            QSettings().setValue('navbar_expanded', 'true')
            self._expand(True)
