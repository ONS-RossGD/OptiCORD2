import os
import typing
from uuid import uuid4
import h5py
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtCore import QObject, QSettings, QUrl
from PyQt5.QtGui import QDesktopServices
from ui.active import ActiveWidget
from ui.mainwindow import MainWindow
from ui.new import NewTracker
from datetime import datetime
from ui.recovery import RecoveryPopup
from util import StandardFormats, TempFile
import logging

log = logging.getLogger('OptiCORD')


def findMainWindow() -> typing.Union[MainWindow, None]:
    # Global function to find the (open) QMainWindow in application
    mw_list = [w for w in QApplication.topLevelWidgets()
               if type(w) is MainWindow]
    # sense check we found the main window correctly
    if len(mw_list) != 1:
        raise Exception('Wrong number of MainWindows')
    return mw_list[0]


def set_window_title(title: str) -> None:
    """Sets the title of the Main Window"""
    mw = findMainWindow()
    mw.setWindowTitle(f'OptiCORD - Editing Change Tracker: {title}')


def create_new(parent: QObject) -> None:
    """Sets up the NewDialog and creates a new change tracker file
    using user inputs"""
    mw = findMainWindow()
    mw.close()
    new_dialog = NewTracker(parent)
    if not new_dialog.exec():
        return mw.show()  # return if user closes dialog without meeting accept criteria
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
    mw.show()


def open_file(parent: QObject) -> None:
    """Creates an open file dialog window for user to select an existing
    .opticord file to open"""
    mw = findMainWindow()
    filepath, _ = QFileDialog.getOpenFileName(parent, 'Open existing...',
                                              QSettings().value('last_open_location', ''), '*.opticord')
    mw.close()
    if not filepath:
        print("no filepath")
        mw.show()
        return   # return if user closes dialog without selecting a file
    log.debug(f'Opening from existing file: {filepath}')
    QSettings().setValue('last_open_location',  # update last_open_location
                         '/'.join(filepath.split('/')[:-1]))
    # init the temp file for future editing
    TempFile.create_from_existing(filepath)
    # read the h5 file
    TempFile.manager.lockForRead()
    with h5py.File(TempFile.path, 'r+') as store:
        name = store.attrs['name']
        [log.debug(f'{i}: {j}') for (i, j) in store.attrs.items()]
    TempFile.manager.unlock()
    # redirect to activity window
    parent.window().setCentralWidget(ActiveWidget(parent.window()))
    set_window_title(name)
    mw.show()


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


def user_guide(parent: QObject):
    """Opens the user guide"""
    url = QUrl("https://teams.microsoft.com/l/channel/19%3ABcKT__6ih0tBZqDwkaeQTtCXyGpD6ujI1YqTODzF8lw1%40thread.tacv2/tab%3A%3A04c69e0f-53a2-4492-93a1-05b435326799?groupId=d59e7db9-44b8-4118-93ce-41b343dce921&tenantId=078807bf-ce82-4688-bce0-0d811684dc46&allowXTenantAccess=false")
    QDesktopServices.openUrl(url)


def contact_support(parent: QObject):
    """Opens the user guide"""
    url = QUrl("https://teams.microsoft.com/l/entity/81fef3a6-72aa-4648-a763-de824aeafb7d/_djb2_msteams_prefix_1077049739?context=%7B%22subEntityId%22%3Anull%2C%22channelId%22%3A%2219%3ABcKT__6ih0tBZqDwkaeQTtCXyGpD6ujI1YqTODzF8lw1%40thread.tacv2%22%7D&groupId=d59e7db9-44b8-4118-93ce-41b343dce921&tenantId=078807bf-ce82-4688-bce0-0d811684dc46&allowXTenantAccess=false")
    QDesktopServices.openUrl(url)
