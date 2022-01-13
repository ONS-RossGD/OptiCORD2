
from PyQt5.QtGui import QValidator
from PyQt5.QtCore import QDir, QObject, QReadWriteLock, QTemporaryFile
from shutil import copyfile
from PyQt5.QtWidgets import QApplication
from dataclasses import dataclass
import os
import json
import h5py
from test_scripts import visualisation_compression_test


class StandardFormats():
    """Standard formats used across OptiCORD scripts"""
    DATETIME = '%d/%m/%Y, %H:%M:%S'


class FileManager(QReadWriteLock):
    """QReadWriteLock with additional function to tell if file
    has been written to."""
    changed: bool = False

    def lockForWrite(self) -> None:
        self.changed = True
        return super().lockForWrite()


class TempFile:
    """Holds information of the temporary file where changes are made
    before saving."""
    saved_path: str = ''
    recovery_path: str = ''
    path: str = ''
    manager: FileManager = FileManager()

    def check_existing() -> bool:
        """Checks for an existing TempFile in case user wants to 
        attempt recovery"""
        existing_files = [filename for filename in os.listdir(
            QDir.temp().absolutePath()) if filename.startswith("OptiCORD-")]
        if len(existing_files) > 1:
            # TODO raise error?
            print('Too many unexpected files')
        if existing_files:
            TempFile.recovery_path = QDir.temp().absoluteFilePath(
                existing_files[0])

    def create_new() -> None:
        """Creates a brand new temp file"""
        print('creating new temp file')
        f = QTemporaryFile(QDir.temp().absoluteFilePath(
            'OptiCORD-XXXXXX.tmp'))
        # open and close the temp file to ensure it gets a fileName
        f.open()
        f.close()
        # auto remove = false so we can use file for recovery
        f.setAutoRemove(False)
        TempFile.path = f.fileName()

    def create_from_existing(existing_path: str) -> None:
        """Creates a temp file by copying an existing file"""
        print('creating temp file from existing')
        f = QTemporaryFile(QDir.temp().absoluteFilePath(
            'OptiCORD-XXXXXX.tmp'))
        # open and close the temp file to ensure it gets a fileName
        f.open()
        f.close()
        # auto remove = false so we can use file for recovery
        f.setAutoRemove(False)
        TempFile.saved_path = existing_path
        TempFile.path = f.fileName()
        copyfile(existing_path, f.fileName())

    def recover() -> None:
        """Opens the recovery file"""
        TempFile.path = TempFile.recovery_path

    def save_to_location(filepath: str) -> None:
        """Saves the temp file to a specified filepath, overwriting any
        existing files in that path."""
        TempFile.manager.lockForWrite()
        copyfile(TempFile.path, filepath)
        TempFile.manager.unlock()
        TempFile.saved_path = filepath

    def delete() -> None:
        """Delete's the temp file (if it exists)"""
        if TempFile.path != '':
            os.remove(TempFile.path)


@dataclass
class Visualisation:
    """CORD Visualisation in python friendly format"""
    name: str  # name of visualisation
    data: dict  # dict of pandas DataFrames with periodicity as key
    meta: dict  # metadata info about visualisation

    def save(self, iteration: str) -> None:
        """Saves the visualisation to the TempFile under a given 
        iteration"""
        # safely write to the file using TempFile's manager
        TempFile.manager.lockForWrite()
        with h5py.File(TempFile.path, 'r+') as store:
            iter_group = store[f'iterations/{iteration}']
            vis_store = iter_group.create_group(self.name)
            # save the metadata to attributes
            for key, val in self.meta.items():
                # unable to store dict as attribute so convert to json
                if type(val) is dict:
                    val = json.dumps(val)
                vis_store.attrs[key] = val
        # save the visualisation data via pandas
        for per in self.meta['Periodicities']:
            # rename the index to numbers as spaces in index names
            # causes issues in saving/reading from file
            self.data[per].index.names = range(len(
                self.meta['Dimensions']))
            self.data[per].to_hdf(TempFile.path,
                                  f'iterations/{iteration}/{self.name}/{per}',
                                  mode='a', complib='blosc:zlib', complevel=9,
                                  format='fixed')
            # complibs were benchmarked using the lines below.
            # blosc:zlib was chosen for its small file size
            # and speedy execution.
            # visualisation_compression_test.benchmark(
            #   f'{self.name}_{per}', self.data[per])
        TempFile.manager.unlock()


class NameValidator(QValidator):
    """Custom validator signal that reacts to mode updates"""
    FULL = 0
    PARTIAL = 1
    NONE = 2

    def __init__(self, parent: QObject, mode: int = NONE):
        QValidator.__init__(self, parent)
        if mode == self.FULL:
            self.bad_chars = {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}
        elif mode == self.PARTIAL:
            self.bad_chars = {'\\', '/'}
        elif mode == self.NONE:
            self.bad_chars = {}
        else:
            raise ValueError("Unknown mode")

    def validate(self, value, pos):
        if len(value) > 0:
            if value[-1] not in self.bad_chars:
                return QValidator.Acceptable, value, pos
        else:
            if value == "":
                return QValidator.Intermediate, value, pos
        QApplication.beep()
        return QValidator.Invalid, value, pos
