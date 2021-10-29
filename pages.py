
from typing import List
from PyQt5.QtCore import QObject
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QWidget
from dataclasses import dataclass, field

@dataclass
class Page:
    ui_path: str
    replacements: dict
    page: QWidget = field(init=False)

    def __post_init__(self):
        """Create the page variable after initalisation so we
        use of dataclass init"""
        self.page = loadUi(self.ui_path)
        for obj_name in self.replacements.keys():
            (old, new) = self.replacements[obj_name]
            self.replace_widget_type(obj_name, old, new)
    
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
        parent = old.parentWidget() # store its parent
        layout = parent.layout() # get the parent layout
        new = new_type(parent) # create a new widget with the same parent
        new.setObjectName(old.objectName()) # set the new widgets object name to replace the old
        layout.replaceWidget(old, new) # replace the old widget with the new in the layout
        old.deleteLater() # delete the old widget
        old = None

class PageRegistry:
    """A Registry for all available Page's"""
    pages = []
    active_page: int
    
    def __init__(self):
        """Define and add Page's here"""
        self.active_page = 0
        #self.pages.append(Page("test.ui", {})) #"commandLinkButton_next": (QPushButton, QNavButton),"commandLinkButton_prev": (QPushButton, QNavButton)
        self.pages.append(Page("load.ui", {}))
        self.pages.append(Page("options.ui", {}))
        self.pages.append(Page("execute.ui", {}))

    def __getitem__(self, i: int) -> Page:
        """Return a specific Page if PageRegistry()[i] is called"""
        return self.pages[i]

    def __iter__(self) -> Page:
        """Defines how to iterate over PageRegistry"""
        for page in self.pages:
            yield page

    def next(self):
        """Returns the next page as QWidget"""
        if self.active_page == len(self.pages):
            return self.pages[self.active_page]
        self.active_page += 1
        return self.pages[self.active_page]()

    def prev(self):
        """Returns the previous page as QWidget"""
        if self.active_page == 0:
            return self.pages[self.active_page]
        self.active_page -= 1
        return self.pages[self.active_page]()
