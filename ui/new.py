from typing import List
from PyQt5.QtCore import Qt, QObject
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QWidget
from PyQt5.uic import loadUi
import os
import logging
from util import CharacterSet, NameValidator, resource_path

log = logging.getLogger('OptiCORD')


class NewTracker(QDialog, object):
    """Dialog window for creating a new change tracker file."""

    def __init__(self, parent: QObject) -> None:
        super(QDialog, self).__init__(parent, Qt.WindowTitleHint)
        # load the vanilla elements from QT Designer file
        loadUi(resource_path()+"/ui/new_tracker.ui", self)
        self.name_edit.textChanged.connect(lambda:
                                           self.reset_invalid_input(self.name_edit))

    def reset_invalid_input(self, w: QWidget) -> None:
        """Resets the invalid_input property of a given widget"""
        if w.property("invalid_input") == "true":
            w.setProperty("invalid_input", "false")
            # style has to be unpolished and polished to update
            w.style().unpolish(w)
            w.style().polish(w)

    def accept(self):
        """Overwritten the default accept function to validate
        criteria needed to create new change tracker file"""
        if not self.name_edit.text():
            # update property to reflect invalid input
            self.name_edit.setProperty("invalid_input", "true")
            # style has to be unpolished and polished to update
            self.name_edit.style().unpolish(self.name_edit)
            self.name_edit.style().polish(self.name_edit)
            return QApplication.beep()  # makes warning noise
        # set name property to be the text given in name_edit
        self.name = self.name_edit.text()
        # if no desc is given default to preset using username
        if self.description_edit.toPlainText():
            self.desc = self.description_edit.toPlainText()
        else:
            self.desc = f'Ask user "{os.getlogin()}" for more info.'
        log.debug(f'Created new tracker: {self.name}')
        # return default ok action if everything is valid
        return super().accept()


class NewPosition(QDialog, object):
    """Dialog window for creating a new position."""

    def __init__(self, parent: QObject, existing: List[str]) -> None:
        super(QDialog, self).__init__(parent, Qt.WindowTitleHint)
        # load the vanilla elements from QT Designer file
        loadUi(resource_path()+"/ui/new_position.ui", self)
        self.existing = existing
        self.name_edit.textChanged.connect(lambda:
                                           self.reset_invalid_input(self.name_edit))

        self.name_validator = NameValidator(self, CharacterSet.PARTIAL)
        self.name_edit.setValidator(self.name_validator)

        self.name_edit.setFocus(True)  # put keyboard cursor on name edit

    def reset_invalid_input(self, w: QWidget) -> None:
        """Resets the invalid_input property of a given widget"""
        if w.property("invalid_input") == "true":
            w.setProperty("invalid_input", "false")
            # style has to be unpolished and polished to update
            w.style().unpolish(w)
            w.style().polish(w)

    def _vs_in_name(self) -> bool:
        """Checks the name string to ensure "vs" is not part of it."""
        name = self.name_edit.text()
        if name == 'vs':
            return True
        if ' vs ' in name:
            return True
        if name[:3] == 'vs ':
            return True
        if name[-3:] == ' vs':
            return True
        return False

    def accept(self):
        """Overwritten the default accept function to validate
        criteria needed to create new position"""
        if not self.name_edit.text() or self.name_edit.text()\
                in self.existing or self._vs_in_name():
            # update property to reflect invalid input
            self.name_edit.setProperty("invalid_input", "true")
            # style has to be unpolished and polished to update
            self.name_edit.style().unpolish(self.name_edit)
            self.name_edit.style().polish(self.name_edit)
            if self.name_edit.text() in self.existing:
                # return a popup explaining name must be unique
                return QMessageBox.warning(self,
                                           'Position name already exists',
                                           'An position with that name already exists'
                                           ' in this change tracker, your new position'
                                           ' must have a unique name.')
            elif self._vs_in_name():
                # return a popup explaining vs can't be in name
                return QMessageBox.warning(self,
                                           'Invalid position name',
                                           '" vs " cannot be a part of your'
                                           'position name.')
            else:
                return QApplication.beep()  # makes warning noise
        # set name property to be the text given in name_edit
        self.name = self.name_edit.text()
        # if no desc is given default to preset using username
        if self.description_edit.toPlainText():
            self.desc = self.description_edit.toPlainText()
        else:
            self.desc = f'Ask user "{os.getlogin()}" for more info.'
        log.debug(f'Created new position: {self.name}')
        # return default ok action if everything is valid
        return super().accept()
