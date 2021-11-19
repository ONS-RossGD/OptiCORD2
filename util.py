
from PyQt5.QtGui import QValidator
from PyQt5.QtCore import QDir, QTemporaryFile, pyqtSignal
from shutil import copyfile
import os

class TempFile():
    """Class to hold information for the temporary file where
    changes are made before saving."""
    saved_path: str = ''
    path: str = ''

    def check_existing() -> None:
        """Checks for an existing TempFile in case user wants to 
        attempt recovery"""
        existing_files = [filename for filename in os.listdir(
            QDir.temp().absolutePath()) if filename.startswith("OptiCORD-")]
        print(existing_files)

    def create_new() -> None:
        """Creates a brand new temp file"""
        print('creating new temp file')
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
        print('creating temp file from existing')
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

    def save_to_location(filepath: str) -> None:
        """Saves the temp file to a specified filepath, overwriting any
        existing files in that path."""
        copyfile(TempFile.path, filepath)
        TempFile.saved_path = filepath

    def delete() -> None:
        """Delete's the temp file (if it exists)"""
        if TempFile.path != '':
            os.remove(TempFile.path)

# TODO currently legacy, remove before release if still legacy
class FilenameValidator(QValidator):
    """Custom validator signal that reacts to state updates"""
    
    def __init__(self, *args, **kwargs):
        QValidator.__init__(self, *args, **kwargs)
        self.bad_chars = {'\\','/',':','*','?','"','<','>','|'}

    def validate(self, value, pos):
        if len(value) > 0:
            if value[-1] not in self.bad_chars:
                return QValidator.Acceptable, value, pos
        else:
            if value == "":
                return QValidator.Intermediate, value, pos
        return QValidator.Invalid, value, pos