
from PyQt5.QtCore import QObject
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QGroupBox, QSizePolicy, QStackedWidget, QWidget
from dataclasses import dataclass, field

from opticord_widgets import QDropBox

class WidgetNotFound(Exception):
    def __init__(self):
        """"""

@dataclass
class Page:
    ui_path: str
    stack: QStackedWidget
    replacements: dict
    page: QWidget = field(init=False)

    def __post_init__(self):
        """Create the page variable after initalisation so we
        use of dataclass init"""
        self.page = loadUi(self.ui_path)
        self.stack.addWidget(self.page)
        for obj_name in self.replacements.keys():
            (old, new) = self.replacements[obj_name]
            try:
                self.replace_widget_type(obj_name, old, new)
            except WidgetNotFound as e:
                # TODO logging error
                print(f'Unable to find the widget "{obj_name}"" in "{self.ui_path}"')
                raise
    
    def __call__(self) -> QWidget:
        """Return the Page as QWidget when Page() is called"""
        return self.page
        
    def replace_widget_type(self, obj_name: str, old_type: QObject, new_type: QObject):
        """Replaces a widget with one of a different type.
        Requires;
            obj_name: The object name of widget to be replaced.
            old_type: The old type of QObject.
            new_type: The new type of QObject."""
        old = self.page.findChild(old_type, obj_name) # find the old widget
        if old is None:
            raise WidgetNotFound
        parent = old.parentWidget() # store its parent
        layout = parent.layout() # get the parent layout
        new = new_type(parent) # create a new widget with the same parent
        new.setObjectName(old.objectName()) # set the new widgets object name to replace the old
        new.setTitle(old.title()) # set the new title to the old
        layout.replaceWidget(old, new) # replace the old widget with the new in the layout
        old.deleteLater() # delete the old widget
        old = None

class Pages(QStackedWidget):
    """A QStackedWidget containing all Page's"""
    pages = []
    
    def __init__(self):
        """Define and add Page's here. Pages should be Qt Designer made 
        widgets saved as <page>.ui"""
        QStackedWidget.__init__(self)
        self.setObjectName("stack")
        #self.pages.append(Page("test.ui", {})) #"commandLinkButton_next": (QPushButton, QNavButton),"commandLinkButton_prev": (QPushButton, QNavButton)
        self.pages.append(Page("load.ui", self, {"upload_pre": (QGroupBox, QDropBox),"upload_post": (QGroupBox, QDropBox)}))
        self.pages.append(Page("options.ui", self, {}))
        self.pages.append(Page("execute.ui", self, {}))
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(9)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
