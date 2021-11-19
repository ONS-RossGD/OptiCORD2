import os
import pandas as pd
import util
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QObject, QSettings
from ui import new, active
from datetime import datetime

def create_new(parent: QObject) -> None:
    """Sets up the NewDialog and creates a new change tracker file
    using user inputs"""
    new_dialog = new.NewDialog(parent)
    if not new_dialog.exec():
        return # return if user closes dialog without meeting accept criteria
    #filepath = f'{new_dialog.url}\\{new_dialog.name}.opticord'
    # init the temp file for future editing
    util.TempFile.create_new()
    df = pd.DataFrame(columns=['Value'])
    df.loc['Name', 'Value'] = new_dialog.name
    df.loc['Desc', 'Value'] = new_dialog.desc
    df.loc['Creator', 'Value'] = os.getlogin()
    df.loc['Date', 'Value'] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    df.to_hdf(util.TempFile.path, 'creation', 'w')

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
    util.TempFile.create_from_existing(filepath)
    # read file with pandas
    df = pd.read_hdf(filepath, 'creation')
    print(df.head())
    parent.window().setCentralWidget(active.ActiveWidget(parent.window()))

def save(parent: QObject) -> bool:
    """Saves the temp file to the location a temp file was created 
    from. If temp file was brand new default to save_as method.
    Returns True if save was successful, False if file was not saved."""
    # if a saved path doesn't exist default to save as
    if util.TempFile.saved_path == '':
        return save_as(parent)
    # otherwise overwrite the file where it was opened
    util.TempFile.save_to_location(util.TempFile.saved_path)
    return True

def save_as(parent: QObject) -> bool:
    """Creates a Save As file dialog window for user to select save
    name and location, then saves the temp file to that location.
    Returns True if save was successful, False if user closes dialog
    without saving."""
    # create a save dialog window
    save_dialog = QFileDialog(parent, 'Save As...',
        util.TempFile.saved_path)
    save_dialog.setFileMode(QFileDialog.AnyFile)
    save_dialog.setNameFilter("OptiCORD file (*.opticord)")
    save_dialog.setAcceptMode(QFileDialog.AcceptSave)
    if not save_dialog.exec():
        return False
    path = save_dialog.selectedFiles()[0]
    util.TempFile.save_to_location(path)
    return True


def detect_unsaved_changes() -> bool:
    """Detects whether a temp file contains changes"""
    print('detecting changes')
    # get saved_path from settings
    saved_path = util.TempFile.saved_path
    temp_path = util.TempFile.path

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