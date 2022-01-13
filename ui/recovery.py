from PyQt5.QtCore import QObject, QSettings, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog
from PyQt5.uic import loadUi
from util import TempFile
import h5py


class RecoveryPopup(QDialog, object):
    """Dialog window for creating a new iteration."""

    def __init__(self, parent: QObject) -> None:
        super(QDialog, self).__init__(parent, Qt.WindowTitleHint)
        # load the vanilla elements from QT Designer file
        loadUi("./ui/recovery.ui", self)
        # get theme folder
        theme_folder = QSettings().value("active_theme").folder
        # create icon pixmap
        self.pixmap = QPixmap(
            f'./ui/resources/{theme_folder}/recover.svg')
        # re-scale icon
        self.icon_label.setPixmap(self.pixmap.scaled(
            60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        TempFile.manager.lockForRead()
        with h5py.File(TempFile.recovery_path, 'r+') as store:
            name = store.attrs['name']
        TempFile.manager.unlock()

        self.details_text.setText(f'Recovered Change: {name}')
