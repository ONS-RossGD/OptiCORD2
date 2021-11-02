
from typing import List
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QSize, Qt
from PyQt5.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt5.QtWidgets import QAction, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem, QStackedWidget, QTreeView, QWidget
from themes import Theme

class QDropBox(QGroupBox):
    urls: List[str]

    def __init__(self, parent: QWidget):
        QGroupBox.__init__(self, parent)
        self.obj_name = self.objectName()
        self.setAcceptDrops(True)
        # set up ui
        self.main_grid = QGridLayout(self)
        self.main_grid.setObjectName(self.obj_name + "_main_grid")
        self.drag_drop_frame = QFrame(self)
        self.drag_drop_frame.setObjectName(self.obj_name + "_drag_drop_frame")
        self.drag_drop_grid = QGridLayout(self.drag_drop_frame)
        self.drag_drop_label = QLabel(self)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.drag_drop_label.sizePolicy().hasHeightForWidth())
        self.drag_drop_label.setSizePolicy(sizePolicy)
        self.drag_drop_label.setMinimumSize(QtCore.QSize(200, 50))
        self.drag_drop_label.setAlignment(QtCore.Qt.AlignCenter)
        self.drag_drop_label.setObjectName(self.obj_name + "_drag_drop_label")
        self.drag_drop_grid.addWidget(self.drag_drop_label, 1, 0, 1, 1)
        spacerItem = QSpacerItem(20, 80, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        self.drag_drop_grid.addItem(spacerItem, 3, 0, 1, 1)
        self.browse_button = QPushButton(self)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.browse_button.sizePolicy().hasHeightForWidth())
        self.browse_button.setSizePolicy(sizePolicy)
        self.browse_button.setMinimumSize(QtCore.QSize(200, 50))
        self.browse_button.setObjectName(self.obj_name + "_browse_button")
        self.drag_drop_grid.addWidget(self.browse_button, 2, 0, 1, 1)
        spacerItem1 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)
        self.drag_drop_grid.addItem(spacerItem1, 0, 0, 1, 1)
        self.main_grid.addWidget(self.drag_drop_frame)
        self.tree = QTreeView(self)
        self.main_grid.addWidget(self.tree)
        self.tree.hide()
        self.browse_button.clicked.connect(self.test)
        self._retranslateUi() # give ui translatable text

    def test(self):
        self.drag_drop_frame.hide()
        self.tree.show()

    def _retranslateUi(self):
        """Give buttons translatable text"""
        _translate = QtCore.QCoreApplication.translate
        self.drag_drop_label.setText(_translate(self.obj_name, "Drag & Drop files/folders here\n\nor"))
        self.browse_button.setText(_translate(self.obj_name, "Browse"))

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()

            links = []

            for url in event.mimeData().urls():
                if url.isLocalFile():
                    links.append(str(url.toLocalFile()))
                else:
                    # TODO log error, maybe signal popup
                    print(f'url: {url} is not a local file...')
            
            self.urls = links

            print(self.urls)

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
        self._retranslateUi() # give ui translatable text
        
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
        if idx < self.stack.count()-1: # -1 because count starts from 1 not 0
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
        self.settings = QSettings()
        self.setCheckable(True)
        self.setObjectName(theme.action_name)
        self.triggered['bool'].connect(self.apply)
        if self.settings.value("active_theme") == self.theme:
            self.setChecked(True)

    def apply(self):
        """Apply the associated theme to its main window"""
        self.theme.apply()
        self.settings.setValue("active_theme", self.theme)
        [x.setChecked(False) for x in self.parentWidget().findChildren(QThemeAction)]
        self.setChecked(True)