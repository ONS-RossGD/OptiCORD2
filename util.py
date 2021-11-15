
from PyQt5.QtGui import QValidator
from PyQt5.QtCore import pyqtSignal

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