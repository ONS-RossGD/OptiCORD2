import os
from uuid import uuid4
import h5py
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtCore import QObject, QSettings
from ui.active import ActiveWidget
from ui.mainwindow import MainWindow
from ui.new import NewTracker
from datetime import datetime
from ui.recovery import RecoveryPopup
from util import StandardFormats, TempFile


def set_window_title(title: str) -> None:
    """Sets the title of the Main Window"""
    # find the main window from the applications top level widgets
    mw_list = [w for w in QApplication.topLevelWidgets()
               if type(w) is MainWindow]
    # sense check we found the main window correctly
    if len(mw_list) != 1:
        raise Exception('Wrong number of MainWindows')
    mw = mw_list[0]
    mw.setWindowTitle(f'OptiCORD - Editing Change Tracker: {title}')


def create_new(parent: QObject) -> None:
    """Sets up the NewDialog and creates a new change tracker file
    using user inputs"""
    new_dialog = NewTracker(parent)
    if not new_dialog.exec():
        return  # return if user closes dialog without meeting accept criteria
    TempFile.create_new()  # init the temp file for future editing
    # write attributes to the new file and init groups
    TempFile.manager.lockForWrite()
    with h5py.File(TempFile.path, 'r+') as store:
        store.attrs['name'] = new_dialog.name
        store.attrs['description'] = new_dialog.desc
        store.attrs['creator'] = os.getlogin()
        store.attrs['creation_date'] = datetime.now().strftime(
            StandardFormats.DATETIME)
        store.attrs['id'] = uuid4().hex
        store.create_group('positions')
        store.create_group('comparisons')
    TempFile.manager.unlock()
    # redirect to activity window
    parent.window().setCentralWidget(ActiveWidget(parent.window()))
    set_window_title(new_dialog.name)


def open_file(parent: QObject) -> None:
    """Creates an open file dialog window for user to select an existing
    .opticord file to open"""
    filepath, _ = QFileDialog.getOpenFileName(parent, 'Open existing...',
                                              QSettings().value('last_open_location', ''), '*.opticord')
    if not filepath:
        return  # return if user closes dialog without selecting a file
    QSettings().setValue('last_open_location',  # update last_open_location
                         '/'.join(filepath.split('/')[:-1]))
    # init the temp file for future editing
    TempFile.create_from_existing(filepath)
    # read the h5 file
    TempFile.manager.lockForRead()
    with h5py.File(TempFile.path, 'r+') as store:
        # TODO remove the print
        name = store.attrs['name']
        [print(f'{i}: {j}') for (i, j) in store.attrs.items()]
    TempFile.manager.unlock()
    # redirect to activity window
    parent.window().setCentralWidget(ActiveWidget(parent.window()))
    set_window_title(name)


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


def attempt_recovery(parent: QObject) -> None:
    """Attempt recovery of a temp file"""
    recovery_dlg = RecoveryPopup(parent)
    if not recovery_dlg.exec():
        # if user chose not to attempt recovery delete temp file
        os.remove(TempFile.recovery_path)
        TempFile.recovery_path = ''
        return
    TempFile.recover()
    # redirect to activity window
    parent.window().setCentralWidget(ActiveWidget(parent.window()))
