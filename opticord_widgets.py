
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QAction
from themes import Theme

class QThemeAction(QAction):
    """A QAction Object for Theme items"""
    def __init__(self, theme: Theme, parent: QObject):
        QAction.__init__(self, text=theme.display, parent=parent)
        self.theme = theme
        self.setCheckable(True)
        self.setObjectName(theme.action_name)
        self.triggered['bool'].connect(self.apply)

    def apply(self):
        """Apply the associated theme to its main window"""
        self.theme.apply()
        [x.setChecked(False) for x in self.parentWidget().findChildren(QThemeAction)]
        self.setChecked(True)