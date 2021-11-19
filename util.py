
from PyQt5.QtGui import QValidator
from PyQt5.QtCore import QDir, QTemporaryFile, pyqtSignal
from shutil import copyfile

class TempFile():
    """Class to hold information for the temporary file where
    changes are made before saving."""
    starter_path: str = ''
    path: str = ''

    def create_new():
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

    def create_from_existing(existing_path: str):
        """Creates a temp file by copying an existing file"""
        print('creating temp file from existing')
        f = QTemporaryFile(QDir.temp().absoluteFilePath(
            'OptiCORD-XXXXXX.tmp'))
        # open and close the temp file to ensure it gets a fileName
        f.open()
        f.close()
        # auto remove = false so we can use file for recovery
        f.setAutoRemove(False)
        TempFile.starter_path = existing_path
        TempFile.path = f.fileName()
        copyfile(existing_path, f.fileName())

class FilenameValidator(QValidator):
    """Custom validator signal that reacts to state updates"""
    validationChanged = pyqtSignal(QValidator.State)
    
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