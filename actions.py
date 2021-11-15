from PyQt5.QtCore import QObject
from ui import new

def create_new(parent: QObject) -> None:
    """Sets up the NewDialog and creates a new change tracker file
    using user inputs"""
    new_dialog = new.NewDialog(parent)
    if not new_dialog.exec():
        return
    
    print(new_dialog.url, new_dialog.name, new_dialog.desc)