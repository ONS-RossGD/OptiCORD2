

from datetime import datetime
import os
import pandas as pd
from typing import List
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QListView, QWidget
from PyQt5.uic import loadUi
from uuid import uuid4
from ui.new import NewIteration
from util import StandardFormats, TempFile
import h5py

class LoadWidget(QWidget, object):
    """Welcome page ui. Load's vanilla ui elements from a QT Designer
    .ui file whilst also allowing custom elements to be built on top."""
    def __init__(self, parent: QObject) -> None:
        super(QWidget, self).__init__(parent)
        # load the vanilla elements from QT Designer file
        loadUi("./ui/load.ui", self)
        # fill the dropdown menu
        self.refresh_iteration_dropdown()
        # magic line to get styling to work
        self.iteration_dropdown.setView(QListView(self))
        
        self.new_iteration.clicked.connect(self.create_iteration)

        self.iteration_dropdown.currentIndexChanged.connect(
            self.update_info)

    def update_info(self) -> None:
        """Update the information box with info of the selected
        iteration"""
        # get current seletion
        selection = self.iteration_dropdown.currentText()
        # if waiting for selection use placeholder text and return early
        if selection == 'Select iteration...':
            self.selection_info.setText('')
            return
        # create description list
        desc = []
        # get info from file
        with h5py.File(TempFile.path, 'r+') as store:
            iteration = store[f'iterations/{selection}']
            desc.append(f'Description: {iteration.attrs["description"]}')
            desc.append('')
            desc.append(f'Created by: {iteration.attrs["creator"]}')
            desc.append('Creation Date: '
                f'{iteration.attrs["creation_date"]}')
        # write to info box
        self.selection_info.setText('\n'.join(desc))


    def get_iterations(self) -> List[str]:
        """Returns a list of iteration names from current change tracker
        file sorted by creation date."""
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
        with h5py.File(TempFile.path, 'r+') as store:
            iteration = store['iterations'].create_group(new_dlg.name)
            # generate a unique id for the iteration
            iteration.attrs['id'] = uuid4().hex
            iteration.attrs['description'] = new_dlg.desc
            iteration.attrs['creator'] = os.getlogin()
            iteration.attrs['creation_date'] = datetime.now().strftime(
                StandardFormats.DATETIME)
        self.refresh_iteration_dropdown()
        self.iteration_dropdown_select(new_dlg.name)