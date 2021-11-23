import os
import h5py
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QObject, QSettings
from ui.active import ActiveWidget
from ui.new import NewTracker
from datetime import datetime
from util import TempFile

def create_new(parent: QObject) -> None:
    """Sets up the NewDialog and creates a new change tracker file
    using user inputs"""
    new_dialog = NewTracker(parent)
    if not new_dialog.exec():
        return # return if user closes dialog without meeting accept criteria
    TempFile.create_new() # init the temp file for future editing
    # write attributes to the new file
    with h5py.File(TempFile.path, 'r+') as store:
        store.attrs['name'] = new_dialog.name
        store.attrs['description'] = new_dialog.desc
        store.attrs['creator'] = os.getlogin()
        store.attrs['creation_date'] = datetime.now().strftime(
            "%d/%m/%Y, %H:%M:%S")

def open_file(parent: QObject) -> None:
    """Creates an open file dialog window for user to select an existing
    .opticord file to open"""
    filepath, _ = QFileDialog.getOpenFileName(parent, 'Open existing...',
        QSettings().value('last_open_location', ''), '*.opticord')
    if not filepath:
        return # return if user closes dialog without selecting a file
    QSettings().setValue('last_open_location', # update last_open_location
        '/'.join(filepath.split('/')[:-1]))
    # init the temp file for future editing
    TempFile.create_from_existing(filepath)
    # read the h5 file
    with h5py.File(TempFile.path, 'r+') as store:
        # TODO remove the print
        [print(f'{i}: {j}') for (i,j) in store.attrs.items()]
    parent.window().setCentralWidget(ActiveWidget(parent.window()))

def save(parent: QObject) -> bool:
    """Saves the temp file to the location a temp file was created 
    from. If temp file was brand new default to save_as method.
    Returns True if save was successful, False if file was not saved."""
    # if a saved path doesn't exist default to save as
    if TempFile.saved_path == '':
        return save_as(parent)
    # otherwise overwrite the file where it was opened
    TempFile.save_to_location(TempFile.saved_path)
    return True

def save_as(parent: QObject) -> bool:
    """Creates a Save As file dialog window for user to select save
    name and location, then saves the temp file to that location.
    Returns True if save was successful, False if user closes dialog
    without saving."""
    # create a save dialog window
    save_dialog = QFileDialog(parent, 'Save As...',
        TempFile.saved_path)
    save_dialog.setFileMode(QFileDialog.AnyFile)
    save_dialog.setNameFilter("OptiCORD file (*.opticord)")
    save_dialog.setAcceptMode(QFileDialog.AcceptSave)
    if not save_dialog.exec():
        return False
    path = save_dialog.selectedFiles()[0]
    TempFile.save_to_location(path)
    return True

def detect_unsaved_changes() -> bool:
    """Detects whether a temp file contains changes"""
    print('detecting changes')
    # get saved_path from settings
    saved_path = TempFile.saved_path
    temp_path = TempFile.path

    print(f'saved: {saved_path}, temp: {temp_path}')
    
    if saved_path == '':
        # if there is no saved or temp file we can assume no changes
        if temp_path == '':
            return False
        # if there is a temp path but no saved path then file is brand new
        else:
            return True
    # if the files are different sizes there are changes
    if os.path.getsize(temp_path) != os.path.getsize(saved_path):
        return True
    with open(saved_path, 'rb') as saved,\
        open(temp_path, 'rb') as temp:
        # compare the files byte by byte
        print('comparing files')
        # read the first byte of each file
        saved_byte = saved.read(1)
        temp_byte = temp.read(1)
        # loop over all bytes in the temp file
        while temp_byte:
            # return true as soon as a difference is found
            if temp_byte != saved_byte:
                return True
            # read next byte for each file
            saved_byte = saved.read(1)
            temp_byte = temp.read(1)
        # if loop gets passed files are identical
        return False