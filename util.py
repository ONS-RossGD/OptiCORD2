import sys
import logging
from PyQt5.QtGui import QValidator, QPainter, QPixmap
from PyQt5.QtCore import QDir, QObject, QReadWriteLock, QTemporaryFile, QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty, pyqtSignal, pyqtSlot, QCoreApplication, QSettings
from shutil import copyfile
from PyQt5.QtWidgets import QApplication, QAbstractButton, QSizePolicy, QDialog
from PyQt5.uic import loadUi
import os
import json
import h5py

log = logging.getLogger('OptiCORD')


def resource_path():
    """Gets the resource path for in development or production"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(sys.argv[0])

    return base_path


class StandardFormats():
    """Standard formats used across OptiCORD scripts"""
    DATETIME = '%d/%m/%Y, %H:%M:%S'


class FileManager(QReadWriteLock):
    """QReadWriteLock with additional function to tell if file
    has been written to."""
    changed: bool = False

    def lockForWrite(self) -> None:
        self.changed = True
        return super().lockForWrite()


class ProcessingManager(QObject):
    """Manager to track running processes witin OptiCORD"""
    locked = pyqtSignal()
    unlocked = pyqtSignal()
    processing: bool = False

    @pyqtSlot()
    def lock(self):
        if not self.processing:
            self.processing = True
            self.locked.emit()

    @pyqtSlot()
    def unlock(self):
        if self.processing:
            self.processing = False
            self.unlocked.emit()


class TempFile:
    """Holds information of the temporary file where changes are made
    before saving."""
    saved_path: str = ''
    recovery_path: str = ''
    path: str = ''
    manager: FileManager = FileManager()
    proc_manager: ProcessingManager = ProcessingManager()

    def check_existing() -> bool:
        """Checks for an existing TempFile in case user wants to 
        attempt recovery"""
        existing_files = [filename for filename in os.listdir(
            QDir.temp().absolutePath()) if filename.startswith("OptiCORD-")]
        if len(existing_files) > 1:
            # TODO raise error?
            log.error('Too many unexpected files')
        if existing_files:
            TempFile.recovery_path = QDir.temp().absoluteFilePath(
                existing_files[0])

    def create_new() -> None:
        """Creates a brand new temp file"""
        TempFile.reset()
        f = QTemporaryFile(QDir.temp().absoluteFilePath(
            'OptiCORD-XXXXXX.tmp'))
        # open and close the temp file to ensure it gets a fileName
        f.open()
        f.close()
        # auto remove = false so we can use file for recovery
        f.setAutoRemove(False)
        TempFile.path = f.fileName()

    def create_from_existing(existing_path: str) -> None:
        """Creates a temp file by copying an existing file"""
        TempFile.reset()
        log.debug('creating temp file from existing')
        f = QTemporaryFile(QDir.temp().absoluteFilePath(
            'OptiCORD-XXXXXX.tmp'))
        # open and close the temp file to ensure it gets a fileName
        f.open()
        f.close()
        # auto remove = false so we can use file for recovery
        f.setAutoRemove(False)
        TempFile.saved_path = existing_path
        TempFile.path = f.fileName()
        copyfile(existing_path, f.fileName())

    def recover() -> None:
        """Opens the recovery file"""
        log.debug('Opening recovered file')
        TempFile.path = TempFile.recovery_path
        # lock and unlock so that save changes warning appears
        TempFile.manager.lockForWrite()
        TempFile.manager.unlock()

    def save_to_location(filepath: str) -> None:
        """Saves the temp file to a specified filepath, overwriting any
        existing files in that path."""
        log.debug(f'Saving to location: {filepath}')
        TempFile.manager.lockForWrite()
        copyfile(TempFile.path, filepath)
        TempFile.manager.unlock()
        TempFile.saved_path = filepath
        TempFile.manager.changed = False

    def delete() -> None:
        """Delete's the temp file (if it exists)"""
        if TempFile.path != '':
            os.remove(TempFile.path)

    def reset() -> None:
        """Reset the TempFile as if it were brand new"""
        TempFile.saved_path = ''
        TempFile.recovery_path = ''
        TempFile.path = ''
        TempFile.manager = FileManager()
        TempFile.proc_manager = ProcessingManager()


class MetaDict(dict):
    """A dictionary containing a visualisations meta data.
    Requires:
        - path: path to the visualisation within the TempFile"""

    def __init__(self, path) -> None:
        TempFile.manager.lockForRead()
        with h5py.File(TempFile.path, 'r+') as store:
            i = store[path]
            for key, val in i.attrs.items():
                # if val is a string attempt to decode it assuming it's json
                if type(val) is str:
                    try:
                        self[key] = json.loads(val)
                    except ValueError:
                        # json will raise a value error if string
                        # couldn't be converted, in this case just use
                        # its string value
                        self[key] = val
                else:
                    self[key] = val
        TempFile.manager.unlock()


class CharacterSet:
    FULL: set = {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}
    PARTIAL: set = {'\\', '/'}


class NameValidator(QValidator):
    """Custom validator signal that reacts to mode updates"""

    def __init__(self, parent: QObject, bad_chars: CharacterSet = {}):
        QValidator.__init__(self, parent)
        self.bad_chars = bad_chars

    def validate(self, value, pos):
        if len(value) > 0 and len(value) <= 27:
            if value[-1] not in self.bad_chars:
                return QValidator.Acceptable, value, pos
        else:
            if value == "":
                return QValidator.Intermediate, value, pos
        QApplication.beep()
        return QValidator.Invalid, value, pos


class Switch(QAbstractButton):
    def __init__(self, parent=None, track_radius=10, thumb_radius=8):
        super().__init__(parent=parent)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._track_radius = track_radius
        self._thumb_radius = thumb_radius

        self._margin = max(0, self._thumb_radius - self._track_radius)
        self._base_offset = max(self._thumb_radius, self._track_radius)
        self._end_offset = {
            True: lambda: self.width() - self._base_offset,
            False: lambda: self._base_offset,
        }
        self._offset = self._base_offset

        self.ensurePolished()  # manditory to use theme palette
        palette = self.palette()
        if self._thumb_radius > self._track_radius:
            self._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            self._thumb_color = {
                True: palette.highlight(),
                False: palette.light(),
            }
            self._text_color = {
                True: palette.highlightedText().color(),
                False: palette.dark().color(),
            }
            self._thumb_text = {
                True: '',
                False: '',
            }
            self._track_opacity = 0.5
        else:
            self._thumb_color = {
                True: palette.highlightedText(),
                False: palette.light(),
            }
            self._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            self._text_color = {
                True: palette.highlight().color(),
                False: palette.dark().color(),
            }
            self._thumb_text = {
                True: '✔',
                False: '✕',
            }
            self._track_opacity = 1

    @pyqtProperty(int)
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        self._offset = value
        self.update()

    def sizeHint(self):  # pylint: disable=invalid-name
        return QSize(
            4 * self._track_radius + 2 * self._margin,
            2 * self._track_radius + 2 * self._margin,
        )

    def setChecked(self, checked):
        super().setChecked(checked)
        self.offset = self._end_offset[checked]()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.offset = self._end_offset[self.isChecked()]()

    def paintEvent(self, event):  # pylint: disable=invalid-name, unused-argument
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        track_opacity = self._track_opacity
        thumb_opacity = 1.0
        text_opacity = 1.0
        if self.isEnabled():
            track_brush = self._track_color[self.isChecked()]
            thumb_brush = self._thumb_color[self.isChecked()]
            text_color = self._text_color[self.isChecked()]
        else:
            track_opacity *= 0.8
            track_brush = self.palette().shadow()
            thumb_brush = self.palette().mid()
            text_color = self.palette().shadow().color()

        p.setBrush(track_brush)
        p.setOpacity(track_opacity)
        p.drawRoundedRect(
            self._margin,
            self._margin,
            self.width() - 2 * self._margin,
            self.height() - 2 * self._margin,
            self._track_radius,
            self._track_radius,
        )
        p.setBrush(thumb_brush)
        p.setOpacity(thumb_opacity)
        p.drawEllipse(
            self.offset - self._thumb_radius,
            self._base_offset - self._thumb_radius,
            2 * self._thumb_radius,
            2 * self._thumb_radius,
        )
        p.setPen(text_color)
        p.setOpacity(text_opacity)
        font = p.font()
        font.setPixelSize(1.5 * self._thumb_radius)
        p.setFont(font)
        p.drawText(
            QRectF(
                self.offset - self._thumb_radius,
                self._base_offset - self._thumb_radius,
                2 * self._thumb_radius,
                2 * self._thumb_radius,
            ),
            Qt.AlignCenter,
            self._thumb_text[self.isChecked()],
        )

    def mouseReleaseEvent(self, event):  # pylint: disable=invalid-name
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            anim = QPropertyAnimation(self, b'offset', self)
            anim.setDuration(120)
            anim.setStartValue(self.offset)
            anim.setEndValue(self._end_offset[self.isChecked()]())
            anim.start()

    def enterEvent(self, event):  # pylint: disable=invalid-name
        self.setCursor(Qt.PointingHandCursor)
        super().enterEvent(event)


class DeleteConfirmation(QDialog):
    """Popup window to get confirmation that visualisation is to be 
    deleted"""

    def __init__(self, parent: QObject, text: str) -> None:
        super(QDialog, self).__init__(parent, Qt.WindowTitleHint)
        loadUi(resource_path()+"/ui/confirm_delete.ui", self)
        self.text_label.setText(text)
        # get theme folder
        theme_folder = QSettings().value("active_theme").folder
        # create icon pixmap
        self.pixmap = QPixmap(
            f'{resource_path()}/ui/resources/{theme_folder}/message_warning.svg')
        # re-scale icon
        self.icon_label.setPixmap(self.pixmap.scaled(
            60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self._retranslate()
        QApplication.beep()

    def _retranslate(self) -> None:
        """creates automatically translated text"""
        _translate = QCoreApplication.translate
        self.text_label.setText(_translate(self.objectName(),
                                           self.text_label.text()))
