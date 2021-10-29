
from PyQt5.QtCore import QObject, QSize
from PyQt5.QtWidgets import QAction, QFrame, QHBoxLayout, QMainWindow, QPushButton, QSizePolicy, QSpacerItem, QWidget
from themes import Theme

class QNavWidget(QFrame):
    """A QFrame to hold the navigation items"""
    nav_buttons = ["run", "next", "prev"]

    def __init__(self, parent: QWidget):#, nav_buttons: List[str]
        QFrame.__init__(self, parent)
        self.frame_name = parent.objectName()+"_navbar"
        self.frame_size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.frame_size.setHorizontalStretch(0)
        self.frame_size.setVerticalStretch(1)
        self.frame_size.setHeightForWidth(parent.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(self.frame_size)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setObjectName(self.frame_name)
        self.button_size = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.h_layout = QHBoxLayout(self)
        self.h_layout.setObjectName(self.frame_name+"_layout")
        self.back_button = QPushButton(self)
        self.back_button.setObjectName(self.frame_name+"_back")
        self.back_button.setMinimumSize(QSize(200, 0))
        self.back_button.setSizePolicy(self.button_size)
        self.h_layout.addWidget(self.back_button)
        self.spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.h_layout.addItem(self.spacer)
        self.next_button = QPushButton(self)
        self.next_button.setObjectName(self.frame_name+"_next")
        self.next_button.setMinimumSize(QSize(200, 0))
        self.next_button.setSizePolicy(self.button_size)
        self.h_layout.addWidget(self.next_button)
        self.run_button = QPushButton(self)
        self.run_button.setObjectName(self.frame_name+"_run")
        self.run_button.setMinimumSize(QSize(200, 0))
        self.run_button.setSizePolicy(self.button_size)
        self.h_layout.addWidget(self.run_button)

        self.back_button.clicked.connect(self.back)
        self.next_button.clicked.connect(self.next)
        self.run_button.clicked.connect(self.run)

        #print(self.nativeParentWidget().objectName())

    def next(self):
        """Go to next page"""
        mainwindow = self.nativeParentWidget()
        mainwindow.setCentralWidget(mainwindow.pages.next())

    def back(self):
        """Go back a page"""
        mainwindow = self.nativeParentWidget()
        mainwindow.setCentralWidget(mainwindow.pages.prev())

    def run(self):
        """TODO"""
        #[x.hide() for x in [self.back, self.next, self.run]]

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