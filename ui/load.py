

from datetime import datetime
import os
import re
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
import pandas as pd
from typing import List
from PyQt5.QtCore import QEvent, QObject, QSettings, QUrl, Qt, pyqtSignal
from PyQt5.QtWidgets import  QDialog, QFileDialog, QListView, QWidget
from PyQt5.uic import loadUi
from uuid import uuid4
from ui.new import NewIteration
from ui.visualisations import VisualisationList
from util import StandardFormats, TempFile
import h5py

class DragDrop(QWidget):
    """Widget for drag+drop and click file uploads"""

    def __init__(self, parent: QWidget, file_signal: pyqtSignal) -> None:
        super(QWidget, self).__init__(parent)
        # load the vanilla elements from QT Designer file
        loadUi("./ui/drag_drop.ui", self)
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
        loadUi("./ui/import_existing.ui", self)
        self.filepath = filepath
        self.iter_dict = dict()
        # read iteration names and descs from file
        with h5py.File(filepath, 'r') as store:
            for name, item in store['iterations'].items():
                desc = []
                desc.append(f'Description: {item.attrs["description"]}')
                desc.append('')
                desc.append(f'Created by: {item.attrs["creator"]}')
                desc.append('Creation Date: '
                    f'{item.attrs["creation_date"]}')
                self.iter_dict[name] = '\n'.join(desc)
        # add iterations to the list widget
        [self.list.addItem(i) for i in self.iter_dict.keys()]
        #signals
        self.list.itemClicked.connect(self.update_desc)
        self.import_button.clicked.connect(self.import_action)

    def update_desc(self) -> None:
        """Update the description box with the relevant description"""
        if not self.import_button.isEnabled():
            self.import_button.setEnabled(True)
        self.desc.setText(self.iter_dict[self.list.currentItem().text()])
    
    def import_action(self) -> None:
        """"""
        TempFile.manager.lockForWrite()
        iter_text = self.list.currentItem().text()
        path = f'iterations/{iter_text}'
        with h5py.File(self.filepath, 'r') as source,\
            h5py.File(TempFile.path, 'r+') as destination:
            # rename the iteration if it already exists in destination
            existing = destination['iterations'].keys()
            if iter_text in existing:
                # create compile function for filtering items that match
                compilation = re.compile(f'^{iter_text} \(\d+\)$')
                # list of just the integers within the brackets
                copies_list = [re.match(f'^{iter_text} \((\d+)\)$', match).group(1)\
                    for match in list(filter(compilation.match, existing))]
                # if list is empty make the copy number the max + 1
                if copies_list:
                    c = int(max(copies_list))+1
                else:
                    c = 1
                name = f'{iter_text} ({c})'
            else:
                name = iter_text
            source.copy(path, destination['iterations'], name=name)
        TempFile.manager.unlock()
        self.name = name
        super().accept()

class LoadWidget(QWidget, object):
    """Welcome page ui. Load's vanilla ui elements from a QT Designer
    .ui file whilst also allowing custom elements to be built on top."""
    file_added = pyqtSignal(str) # custom signal

    def __init__(self, parent: QObject) -> None:
        super(QWidget, self).__init__(parent)
        # load the vanilla elements from QT Designer file
        loadUi("./ui/load.ui", self)
        # fill the dropdown menu
        self.refresh_iteration_dropdown()
        # magic line to get styling to work
        self.iteration_dropdown.setView(QListView(self))
        # setting up tab widget
        self.drag_drop_tab = DragDrop(self.load_tabs, self.file_added)
        self.vis_list = VisualisationList(self.load_tabs)
        self.vis_list.hide() # hide until there are vis's to display
        # extra spaces in tab name to avoid ui bug
        self.load_tabs.addTab(self.drag_drop_tab, " Add Files ")
        self.load_tabs.setCurrentWidget(self.drag_drop_tab)
        self.load_tabs.installEventFilter(self)
        # signals
        self.new_iteration.clicked.connect(self.create_iteration)
        self.import_iteration.clicked.connect(self.import_existing)
        self.iteration_dropdown.currentIndexChanged.connect(
            self.update_info)
        self.iteration_dropdown.currentIndexChanged.connect(
            lambda i: self.vis_list.change_iteration(
                self.iteration_dropdown.itemText(i)))
        self.drag_drop_tab.file_added.connect(self.vis_list.add_file)

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
        [self.file_added.emit(str(url.toLocalFile())) \
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
        iteration"""
        # get current seletion
        selection = self.iteration_dropdown.currentText()
        # if waiting for selection use placeholder text and return early
        if selection == 'Select iteration...':
            self.reset_load_tabs()
            return
        # enable loading files
        self.load_tabs.setEnabled(True)
        # create description list
        desc = []
        # get info from file
        TempFile.manager.lockForRead()
        with h5py.File(TempFile.path, 'r+') as store:
            iteration = store[f'iterations/{selection}']
            desc.append(f'Description: {iteration.attrs["description"]}')
            desc.append('')
            desc.append(f'Created by: {iteration.attrs["creator"]}')
            desc.append('Creation Date: '
                f'{iteration.attrs["creation_date"]}')
        TempFile.manager.unlock()
        # write to info box
        self.selection_info.setText('\n'.join(desc))

    def get_iterations(self) -> List[str]:
        """Returns a list of iteration names from current change tracker
        file sorted by creation date."""
        TempFile.manager.lockForRead()
        with h5py.File(TempFile.path, 'r+') as store:
            # store in dataframe for easier sorting
            df = pd.DataFrame(columns=['Name', 'Datetime'])
            # fetch name of each iteration as list
            df['Name'] = list(store['iterations'].keys())
            # fetch assosciated creation date for each iteration
            df['Datetime'] = [pd.to_datetime(
                store[f'iterations/{x}'].attrs['creation_date'],
                format=StandardFormats.DATETIME)
                for x in df['Name'].tolist()]
        TempFile.manager.unlock()
        # sort by creation date and return as list
        return df.sort_values(by='Datetime')['Name'].tolist()

    def refresh_iteration_dropdown(self) -> None:
        """Refresh the iteration dropdown box with up to date
        iterations"""
        # temporarily stop signals from firing
        self.iteration_dropdown.blockSignals(True)
        # refresh the dropdown
        self.iteration_dropdown.clear()
        self.iteration_dropdown.addItems(
            ['Select iteration...']+self.get_iterations())
        # resume signals
        self.iteration_dropdown.blockSignals(False)

    def iteration_dropdown_select(self, item: str) -> None:
        """Set the iteration dropdown to a given item"""
        index = self.iteration_dropdown.findText(item)
        if index == -1: #-1 if item not found
            return print('NOT FOUND') # TODO raise error ?
        return self.iteration_dropdown.setCurrentIndex(index)

    def create_iteration(self) -> None:
        """Create a new iteration based on user inputs"""
        new_dlg = NewIteration(self, self.get_iterations())
        # return if user closes dialog without meeting accept criteria
        if not new_dlg.exec():
            return
        # create the new iteration in file
        TempFile.manager.lockForWrite()
        with h5py.File(TempFile.path, 'r+') as store:
            iteration = store['iterations'].create_group(new_dlg.name)
            # generate a unique id for the iteration
            iteration.attrs['id'] = uuid4().hex
            iteration.attrs['description'] = new_dlg.desc
            iteration.attrs['creator'] = os.getlogin()
            iteration.attrs['creation_date'] = datetime.now().strftime(
                StandardFormats.DATETIME)
        TempFile.manager.unlock()
        self.refresh_iteration_dropdown()
        self.iteration_dropdown_select(new_dlg.name)

    def import_existing(self) -> None:
        """Create a new iteration from an existing iteration"""
        filepath, _ = QFileDialog.getOpenFileName(self, 'Open existing...',
        QSettings().value('last_open_location', ''), '*.opticord')
        if not filepath:
            return # return if user closes dialog without selecting a file
        import_dlg = ImportExisting(self, filepath)
        if import_dlg.exec():
            self.refresh_iteration_dropdown()
            self.iteration_dropdown_select(import_dlg.name)

    def reset_load_tabs(self) -> None:
        """Resets the load_tabs widget"""
        self.selection_info.setText('')
        # remove the visualisation list if in tabs
        if self.load_tabs.count() > 1:
            self.load_tabs.removeTab(0)
        self.load_tabs.setEnabled(False)