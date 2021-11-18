import os
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QObject, QSettings
from ui import new
from datetime import datetime

def create_new(parent: QObject) -> None:
    """Sets up the NewDialog and creates a new change tracker file
    using user inputs"""
    new_dialog = new.NewDialog(parent)
    if not new_dialog.exec():
        return # return if user closes dialog without meeting accept criteria
    filepath = f'{new_dialog.url}\\{new_dialog.name}.opticord'
    df = pd.DataFrame(columns=['Value'])
    df.loc['Name', 'Value'] = new_dialog.name
    df.loc['Desc', 'Value'] = new_dialog.desc
    df.loc['Creator', 'Value'] = os.getlogin()
    df.loc['Date', 'Value'] = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    df.to_hdf(filepath, 'creation', 'w')

def open(parent: QObject) -> None:
    """Creates an open file dialog window for user to select an existing
    .opticord file to open"""
    filepath, _ = QFileDialog.getOpenFileName(parent, 'Open existing...',
        QSettings().value('last_open_location', ''), '*.opticord')
    if not filepath:
        return # return if user closes dialog without selecting a file
    QSettings().setValue('last_open_location', # update last_open_location
        '/'.join(filepath.split('/')[:-1]))
    # read file with pandas
    df = pd.read_hdf(filepath, 'creation')
    print(df.loc['Desc', 'Value'])