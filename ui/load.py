

from datetime import datetime
import os
import re
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
import pandas as pd
from typing import List
from PyQt5.QtCore import QEvent, QObject, QSettings, QUrl, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QDialog, QFileDialog, QListView, QWidget
from PyQt5.uic import loadUi
from uuid import uuid4
from ui.new import NewPosition, EditPosition
from visualisations import VisualisationList
from util import StandardFormats, TempFile, resource_path
import h5py


class DragDrop(QWidget):
    """Widget for drag+drop and click file uploads"""

    def __init__(self, parent: QWidget, file_signal: pyqtSignal) -> None:
        super(QWidget, self).__init__(parent)
        # load the vanilla elements from QT Designer file
        loadUi(resource_path()+"/ui/drag_drop.ui", self)
        self.file_added = file_signal
        # signals
        self.browse.clicked.connect(self.browse_dialog)

    def browse_dialog(self):
        """Opens a File Dialog window for user to select files
        or folders"""
        selection = QFileDialog.getOpenFileNames(self,
                                                 'Select visualisations to add...', '',
                                                 'CORD Visualisations (*.csv)')
        # emit each selected file
        [self.file_added.emit(f) for f in selection[0]]


class ImportExisting(QDialog):
    """UI window for selecting an iteraration to import for an exisitng
    OptiCORD Change Tracker."""

    def __init__(self, parent: QWidget, filepath: str) -> None:
        super(QDialog, self).__init__(parent, Qt.WindowCloseButtonHint)
        # load the vanilla elements from QT Designer file
        loadUi(resource_path()+"/ui/import_existing.ui", self)
        self.filepath = filepath
        self.pos_dict = dict()
        # read position names and descs from file
        with h5py.File(filepath, 'r') as store:
            for name, item in store['positions'].items():
                desc = []
                desc.append(f'Description: {item.attrs["description"]}')
                desc.append('')
                desc.append(f'Created by: {item.attrs["creator"]}')
                desc.append('Creation Date: '
                            f'{item.attrs["creation_date"]}')
                self.pos_dict[name] = '\n'.join(desc)
        # add positions to the list widget
        [self.list.addItem(i) for i in self.pos_dict.keys()]
        # signals
        self.list.itemClicked.connect(self.update_desc)
        self.import_button.clicked.connect(self.import_action)

    def update_desc(self) -> None:
        """Update the description box with the relevant description"""
        if not self.import_button.isEnabled():
            self.import_button.setEnabled(True)
        self.desc.setText(self.pos_dict[self.list.currentItem().text()])

    def import_action(self) -> None:
        """Called when the import button is clicked. Copies the selected
        position to current working file and screens the position
        name to ensure it's unique."""
        TempFile.manager.lockForWrite()
        iter_text = self.list.currentItem().text()
        path = f'positions/{iter_text}'
        with h5py.File(self.filepath, 'r') as source,\
                h5py.File(TempFile.path, 'r+') as destination:
            # rename the position if it already exists in destination
            existing = destination['positions'].keys()
            if iter_text in existing:
                # create compile function for filtering items that match
                compilation = re.compile(f'^{iter_text} \(\d+\)$')
                # list of just the integers within the brackets
                copies_list = [re.match(f'^{iter_text} \((\d+)\)$', match).group(1)
                               for match in list(filter(compilation.match, existing))]
                # if list is empty make the copy number the max + 1
                if copies_list:
                    c = int(max(copies_list))+1
                else:
                    c = 1
                name = f'{iter_text} ({c})'
            else:
                name = iter_text
            source.copy(path, destination['positions'], name=name)
            if 'history' in destination[f'positions/{name}'].attrs.keys():
                destination[f'positions/{name}'].attrs['history'] += \
                    f'\n({datetime.now().strftime(StandardFormats.DATETIME)})'\
                    f' - Imported from {source.attrs["name"]} by {os.getlogin()}'
            else:
                destination[f'positions/{name}'].attrs['history'] = \
                    f'({datetime.now().strftime(StandardFormats.DATETIME)})'\
                    f' - Imported from {source.attrs["name"]} by {os.getlogin()}'
        TempFile.manager.unlock()
        self.name = name
        super().accept()


class LoadWidget(QWidget, object):
    """Load page ui and functionality"""
    file_added = pyqtSignal(str)  # custom signal

    def __init__(self, parent: QObject) -> None:
        super(QWidget, self).__init__(parent)
        # load the vanilla elements from QT Designer file
        loadUi(resource_path()+"/ui/load.ui", self)
        # fill the dropdown menu
        self.refresh_position_dropdown()
        # magic line to get styling to work
        self.position_dropdown.setView(QListView(self))
        # setting up tab widget
        self.drag_drop_tab = DragDrop(self.load_tabs, self.file_added)
        self.vis_list = VisualisationList(self.load_tabs)
        self.vis_list.hide()  # hide until there are vis's to display
        # extra spaces in tab name to avoid ui bug
        self.load_tabs.addTab(self.drag_drop_tab, " Add Files ")
        self.load_tabs.setCurrentWidget(self.drag_drop_tab)
        self.load_tabs.installEventFilter(self)
        self.edit_position.setEnabled(False)
        # signals
        self.edit_position.clicked.connect(self.change_position)
        self.new_position.clicked.connect(self.create_position)
        self.import_position.clicked.connect(self.import_existing)
        self.position_dropdown.currentIndexChanged.connect(
            self.update_info)
        self.position_dropdown.currentIndexChanged.connect(
            lambda i: self.vis_list.change_position(
                self.position_dropdown.itemText(i)))
        self.drag_drop_tab.file_added.connect(self.vis_list.add_file)
        self.vis_list.lock.connect(self.lock)
        self.vis_list.unlock.connect(self.unlock)
        TempFile.proc_manager.locked.connect(self.lock)
        TempFile.proc_manager.unlocked.connect(self.unlock)

    def check_drop(self, urls: List[QUrl]) -> bool:
        """Check that all given files are local files of 
        type: .csv"""
        for url in urls:
            if not url.isLocalFile():
                return False
            if str(url.toLocalFile()).split('.')[-1] != 'csv':
                return False
        return True

    def drag_enter(self, event: QDragEnterEvent):
        """Called when files are dragged into widget"""
        if event.mimeData().hasUrls():
            if self.check_drop(event.mimeData().urls()):
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def drop(self, event: QDropEvent):
        """Called when files are dropped into widget"""
        event.setDropAction(Qt.CopyAction)
        event.accept()
        # emit each file
        [self.file_added.emit(str(url.toLocalFile()))
            for url in event.mimeData().urls()]

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """Event filter to customise events of ui children"""
        if source is self.load_tabs:
            if event.type() == QEvent.Type.DragEnter:
                self.drag_enter(event)
            if event.type() == QEvent.Type.Drop:
                self.drop(event)
        return super().eventFilter(source, event)

    def update_info(self) -> None:
        """Update the information box with info of the selected
        position"""
        # get current seletion
        selection = self.position_dropdown.currentText()
        # if waiting for selection use placeholder text and return early
        if selection == 'Select position...':
            self.reset_load_tabs()
            self.edit_position.setEnabled(False)
            return
        # enable loading files
        self.load_tabs.setEnabled(True)
        self.edit_position.setEnabled(True)
        # create description list
        desc = []
        # get info from file
        TempFile.manager.lockForRead()
        with h5py.File(TempFile.path, 'r+') as store:
            position = store[f'positions/{selection}']
            desc.append(f'Description: {position.attrs["description"]}')
            desc.append('')
            desc.append(f'Created by: {position.attrs["creator"]}')
            desc.append('Creation Date: '
                        f'{position.attrs["creation_date"]}')
            if 'history' in position.attrs.keys():
                desc.append(f'History: {position.attrs["history"]}')
        TempFile.manager.unlock()
        # write to info box
        self.selection_info.setText('\n'.join(desc))

    def get_positions(self) -> List[str]:
        """Returns a list of position names from current change tracker
        file sorted by creation date."""
        TempFile.manager.lockForRead()
        with h5py.File(TempFile.path, 'r+') as store:
            # store in dataframe for easier sorting
            df = pd.DataFrame(columns=['Name', 'Datetime'])
            # fetch name of each position as list
            df['Name'] = list(store['positions'].keys())
            # fetch assosciated creation date for each position
            df['Datetime'] = [pd.to_datetime(
                store[f'positions/{x}'].attrs['creation_date'],
                format=StandardFormats.DATETIME)
                for x in df['Name'].tolist()]
        TempFile.manager.unlock()
        # sort by creation date and return as list
        return df.sort_values(by='Datetime')['Name'].tolist()

    def refresh_position_dropdown(self) -> None:
        """Refresh the position dropdown box with up to date
        positions"""
        # temporarily stop signals from firing
        self.position_dropdown.blockSignals(True)
        # refresh the dropdown
        self.position_dropdown.clear()
        self.position_dropdown.addItems(
            ['Select position...']+self.get_positions())
        # resume signals
        self.position_dropdown.blockSignals(False)

    def position_dropdown_select(self, item: str) -> None:
        """Set the position dropdown to a given item"""
        index = self.position_dropdown.findText(item)
        if index == -1:  # -1 if item not found
            return print('NOT FOUND')  # TODO raise error ?
        return self.position_dropdown.setCurrentIndex(index)

    def change_position(self) -> None:
        """Create a new position based on user inputs"""
        edit_dlg = EditPosition(self, self.get_positions(),
                                self.position_dropdown.currentText())
        # return if user closes dialog without meeting accept criteria
        if not edit_dlg.exec():
            return
        # copy/paste a position with the new name and desc in file
        # then delete the old one
        TempFile.manager.lockForWrite()
        with h5py.File(TempFile.path, 'r+') as store:
            if self.position_dropdown.currentText() != edit_dlg.name:
                store.copy(f'positions/{self.position_dropdown.currentText()}',
                           f'positions/{edit_dlg.name}')
            position = store[f'positions/{edit_dlg.name}']
            position.attrs['description'] = edit_dlg.desc
            if self.position_dropdown.currentText() != edit_dlg.name:
                del store[f'positions/{self.position_dropdown.currentText()}']
        TempFile.manager.unlock()
        self.refresh_position_dropdown()
        self.position_dropdown_select(edit_dlg.name)

    def create_position(self) -> None:
        """Create a new position based on user inputs"""
        new_dlg = NewPosition(self, self.get_positions())
        # return if user closes dialog without meeting accept criteria
        if not new_dlg.exec():
            return
        # create the new position in file
        TempFile.manager.lockForWrite()
        with h5py.File(TempFile.path, 'r+') as store:
            position = store['positions'].create_group(new_dlg.name)
            # generate a unique id for the position
            position.attrs['id'] = uuid4().hex
            position.attrs['description'] = new_dlg.desc
            position.attrs['creator'] = os.getlogin()
            position.attrs['creation_date'] = datetime.now().strftime(
                StandardFormats.DATETIME)
        TempFile.manager.unlock()
        self.refresh_position_dropdown()
        self.position_dropdown_select(new_dlg.name)

    def import_existing(self) -> None:
        """Create a new position from an existing position"""
        filepath, _ = QFileDialog.getOpenFileName(self, 'Open existing...',
                                                  QSettings().value('last_open_location', ''), '*.opticord')
        if not filepath:
            return  # return if user closes dialog without selecting a file
        import_dlg = ImportExisting(self, filepath)
        if import_dlg.exec():
            self.refresh_position_dropdown()
            self.position_dropdown_select(import_dlg.name)

    def reset_load_tabs(self) -> None:
        """Resets the load_tabs widget"""
        self.selection_info.setText('')
        # remove the visualisation list if in tabs
        if self.load_tabs.count() > 1:
            self.load_tabs.removeTab(0)
        self.load_tabs.setEnabled(False)

    @ pyqtSlot()
    def lock(self) -> None:
        """Locks the Load page UI"""
        self.position_dropdown.setEnabled(False)
        self.new_position.setEnabled(False)
        self.import_position.setEnabled(False)
        # lock in the process manager
        TempFile.proc_manager.lock()

    @ pyqtSlot()
    def unlock(self) -> None:
        """Unlocks the Load page UI"""
        self.position_dropdown.setEnabled(True)
        self.new_position.setEnabled(True)
        self.import_position.setEnabled(True)
        # unlock in the process manager
        TempFile.proc_manager.unlock()
