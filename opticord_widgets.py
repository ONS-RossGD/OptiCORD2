
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QSize
from PyQt5.QtWidgets import QAction, QFrame, QHBoxLayout, QPushButton, QSizePolicy, QSpacerItem, QStackedWidget, QWidget
from themes import Theme

class QNavWidget(QFrame):
    """A QFrame to hold the navigation items"""
    stack: QStackedWidget

    def __init__(self, parent: QWidget, stack: QStackedWidget):#, nav_buttons: List[str]
        QFrame.__init__(self, parent)
        self.stack = stack # store the QStackWidget for later reference
        # set up ui
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.frame_name = "nav_bar"
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

        self._signals() # set up signals
        self._assign_buttons() # assign which buttons appear
        self._retranslateUi() # give ui text
        
    def _signals(self):
        """Set up the signals for the nav bar"""
        self.back_button.clicked.connect(self.back)
        self.next_button.clicked.connect(self.next)
        self.run_button.clicked.connect(self.run)

    def _retranslateUi(self):
        """Give buttons translatable text"""
        _translate = QtCore.QCoreApplication.translate
        self.run_button.setText(_translate("nav_bar", "Run"))
        self.next_button.setText(_translate("nav_bar", "Next"))
        self.back_button.setText(_translate("nav_bar", "Back"))

    def _assign_buttons(self):
        """Assign which buttons appear on the nav bar based on the 
        current index of the stack widget. The first page will have
        only a next button, and the last page will have run instead
        of next. All other pages contain back and next."""
        self.back_button.hide()
        self.next_button.hide()
        self.run_button.hide()
        idx = self.stack.currentIndex()
        count = self.stack.count()-1 # -1 to match index
        if idx == count: # last page
            self.back_button.show()
            self.run_button.show()
        elif idx == 0: # first page
            self.next_button.show()
        else: # all other pages
            self.back_button.show()
            self.next_button.show()

    def next(self):
        """Changes the index of the stack by +1 if valid"""
        idx = self.stack.currentIndex()
        if idx < self.stack.count():
            self.stack.setCurrentIndex(idx+1)
            self._assign_buttons()

    def back(self):
        """Changes the index of the stack by -1 if valid"""
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx-1)
            self._assign_buttons()

    def run(self):
        """TODO"""
        self._assign_buttons()

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