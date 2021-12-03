

import re
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QSettings, Qt
from PyQt5.QtGui import QCloseEvent, QPixmap
from PyQt5.QtWidgets import QAction, QApplication, QDialog, QDialogButtonBox, QMainWindow
from PyQt5.uic import loadUi
from themes import ThemeRegistry, Theme
import actions
from util import TempFile

class QThemeAction(QAction):
    """A QAction Object for Theme items"""
    def __init__(self, theme: Theme, parent: QObject):
        super(QAction, self).__init__(text=theme.display, parent=parent)
        self.theme = theme
        self.setCheckable(True)
        self.setObjectName(theme.action_name)
        self.triggered['bool'].connect(self.apply)
        if QSettings().value("active_theme") == self.theme:
            self.setChecked(True)

    def apply(self):
        """Apply the associated theme to its main window"""
        self.theme.apply()
        [x.setChecked(False) for x in self.parentWidget()\
            .findChildren(QThemeAction)]
        self.setChecked(True)

class QFontAction(QAction):
    """A QAction Object for Theme items"""
    def __init__(self, text: str, size: int, parent: QObject):
        super(QAction, self).__init__(parent, text=text)
        self.text = text
        self.size = size
        self.setCheckable(True)
        self.setObjectName(f'action_{text.replace(" ", "_").lower()}')
        self.triggered['bool'].connect(self.apply)
        if QSettings().value("font") == {'text': text, 'size': size}:
            self.apply()

    def apply(self):
        """Apply the selected font size"""
        QSettings().setValue("font", dict({'text': self.text,
            'size': self.size}))
        ss = QApplication.instance().styleSheet()
        font = f'font: {self.size}pt'
        new_ss = re.sub('font: (.*?)pt', font, ss)
        QApplication.instance().setStyleSheet(new_ss)
        [x.setChecked(False) for x in self.parentWidget()\
            .findChildren(QFontAction)]
        self.setChecked(True)

class UnsavedChanges(QDialog):
    """Popup window to get direction from user on what to do with
    unsaved changes."""
    def __init__(self, parent: QObject) -> None:
        super(QDialog, self).__init__(parent, Qt.WindowTitleHint)
        loadUi("./ui/unsaved_changes.ui", self)
        # get theme folder
        theme_folder = QSettings().value("active_theme").folder
        # create icon pixmap
        self.pixmap = QPixmap(
            f'./ui/resources/{theme_folder}/message_warning.svg')
        # re-scale icon
        self.icon_label.setPixmap(self.pixmap.scaled(
            60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # connect the button box buttons
        self.button_box.button(QDialogButtonBox.Discard).clicked.connect(
            self.discard)
        self.button_box.button(QDialogButtonBox.Save).clicked.connect(
            self.save)
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(
            self.reject)

        self._retranslate()
        QApplication.beep()

    def _retranslate(self) -> None:
        """creates automatically translated text"""
        _translate = QtCore.QCoreApplication.translate
        self.text_label.setText(_translate(self.objectName(),
            self.text_label.text()))

    def save(self) -> None:
        """Activates the save action, returns accept if save
        is successful, returns reject if not"""
        if actions.save(self):
            TempFile.delete()
            return super().accept()
        else:
            return super().reject()

    def discard(self) -> None:
        """Deletes the temp file then returns accept"""
        TempFile.delete()
        return super().accept()

class MainWindow(QMainWindow, object):
    """Main window of application"""
    def __init__(self):
        super(QMainWindow, self).__init__()
        loadUi("./ui/mainwindow.ui", self)
        self.themes = ThemeRegistry() # load all themes
        # apply the users selected theme defaulted to dark purple
        QSettings().value("active_theme", self.themes[2]).apply()
        # fill the themes menu 
        for theme in self.themes:
            self.menu_theme.addAction(QThemeAction(theme, self))

        # add font size options
        self.menu_font_size.addAction(QFontAction('Small',
            10, self))
        self.menu_font_size.addAction(QFontAction('Medium',
            12, self))
        self.menu_font_size.addAction(QFontAction('Large',
            14, self))

        self.action_new.triggered[bool].connect(
            lambda: actions.create_new(self))
        self.action_open.triggered[bool].connect(
            lambda: actions.open_file(self))
        self.action_save.triggered[bool].connect(
            lambda: actions.save(self))
        self.action_save_as.triggered[bool].connect(
            lambda: actions.save_as(self))

    def closeEvent(self, a0: QCloseEvent) -> None:
        """Additional checks when user tries to intentionally close
        the window"""
        if actions.detect_unsaved_changes():
            dlg = UnsavedChanges(self)
            # if user closes the popup or fails to save do not exit
            if dlg.exec() != QDialog.Accepted:
                return a0.ignore()
        else:
            TempFile.delete()
        return super().closeEvent(a0)