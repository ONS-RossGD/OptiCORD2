import json
import os
import re
from typing import List
import warnings
from PyQt5 import QtCore
from PyQt5.Qt import QSvgRenderer
from PyQt5.QtCore import QEvent, QModelIndex, QObject, QPoint, QRectF, QRunnable, QSettings, QThreadPool, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QFontMetrics, QPainter, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAbstractItemView, QAction, QApplication, QDialog, QListView, QMenu, QStyleOptionViewItem, QStyledItemDelegate, QTabWidget
from PyQt5.uic import loadUi
import h5py
import numpy as np
import pandas as pd
from util import DeleteConfirmation, TempFile, resource_path
from validation import InvalidVisualisation, validate_date, validate_filepath, validate_meta, validate_unique
import logging

log = logging.getLogger('OptiCORD')


class VisualisationList(QListView):
    """ListWidget for loaded visualisations"""
    pool: QThreadPool
    existing: List[str]
    position: str
    lock = pyqtSignal()
    unlock = pyqtSignal()

    def __init__(self, parent: QTabWidget) -> None:
        super(QListView, self).__init__(parent)
        # get the threadpool
        self.pool = QThreadPool.globalInstance()
        # init existing list
        self.existing = []
        self.tabs = parent
        # ListView setup
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setObjectName('load_vis_list')
        # event filter to add right click menu
        self.installEventFilter(self)
        # init the custom model
        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(['Visualisation'])
        self.setModel(self.model)
        # init the custom deligate
        self.deligate = VisualisationDeligate(self)
        self.setItemDelegate(self.deligate)
        # update viewport when svg render frame changes
        self.deligate.loading.repaintNeeded.connect(
            self.viewport().update)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """Custom event filter to manage item right click event"""
        if event.type() == QEvent.ContextMenu and source is self:
            item = self.model.item(
                self.currentIndex().row(), 0)
            menu = QMenu()
            delete_action = QAction('Delete', menu)
            dismiss_action = QAction('Dismiss', menu)
            available_actions = []
            if item.state == VisualisationFile.SUCCESS:
                available_actions.append(delete_action)
            if item.state == VisualisationFile.FAILURE:
                available_actions.append(dismiss_action)
            menu.addActions(available_actions)
            delete_action.triggered.connect(lambda:
                                            self.delete_visualisation(item))
            dismiss_action.triggered.connect(lambda:
                                             self.model.removeRow(self.currentIndex().row()))
            menu.exec(event.globalPos())
        return super().eventFilter(source, event)

    @pyqtSlot()
    def determine_unlock(self) -> None:
        """Determine whether or not to emit unlock signal"""
        unlock = True
        items = [self.model.item(i) for i in range(1, self.model.rowCount())]
        for item in items:
            if item.state in [VisualisationFile.LOADING,
                              VisualisationFile.QUEUED]:
                unlock = False
        if unlock:
            self.unlock.emit()

    @pyqtSlot(str)
    def add_file(self, file: str) -> None:
        """Add the file to the pool and execute when thread is
        available"""
        # make sure visualisation list is showing
        self.show_in_tabs()
        worker = VisualisationWorker(file, self)
        worker.signals.finished.connect(self.determine_unlock)
        # add item to the list
        self.model.appendRow(worker.item)
        # check filepath of the worker, must be done before threading
        # otherwise non-unique visualisations will still pass
        # validation when run in parallel
        if worker.check_filepath():
            # add worker to the pool and execute when thread is available
            self.lock.emit()
            self.pool.start(worker)

    def read_from_file(self) -> None:
        """Reads the visualisation names already stored in the 
        file and adds them to the visualisation list."""
        # add visualisations from file to the list
        TempFile.manager.lockForRead()
        with h5py.File(TempFile.path, 'r+') as store:
            i = store[f'positions/{self.position}']
            for vis in i.keys():
                self.existing.append(vis)
                vis_item = VisualisationFile(vis)
                vis_item.state = VisualisationFile.SUCCESS
                self.model.appendRow(vis_item)
        # make sure visualisation list is shown/hidden
        if self.existing != []:
            self.show_in_tabs()
        else:
            self.hide_in_tabs()
        TempFile.manager.unlock()

    @pyqtSlot(str)
    def add_to_existing(self, vis: str) -> None:
        """Adds a visualisation to the list of existing 
        visualisations"""
        self.existing.append(vis)

    def remove_existing(self, vis: str) -> None:
        """Removes a visualisation from the list of existing 
        visualisations"""
        self.existing.remove(vis)

    def show_in_tabs(self) -> None:
        """Shows the Visualisation tab if not already present"""
        if self.tabs.tabText(0) != ' Visualisations ':
            self.tabs.addTab(self,
                             " Visualisations ")
            self.tabs.setCurrentWidget(self)
            self.tabs.tabBar().moveTab(0, 1)

    def hide_in_tabs(self) -> None:
        """Shows the Visualisation tab if not already present"""
        if self.tabs.tabText(0) == ' Visualisations ':
            self.tabs.removeTab(0)

    @pyqtSlot(str)
    def change_position(self, position: str) -> None:
        """Update the Visualisation List to match the active
        position"""
        if position == 'Select position...':
            return
        self.position = position
        # clear the list and existing
        self.model.removeRows(0, self.model.rowCount())
        self.existing = []
        self.read_from_file()

    def delete_visualisation(self, item: QStandardItem) -> None:
        """Delete the visualisation from the list and the file"""
        delete_dlg = DeleteConfirmation(self,
                                        f'Are you sure you want to delete the visualisation "{item.text()}" '
                                        'and all of its data (including assosciated comparisons)?\n\nThis operation is irreversible.')
        if delete_dlg.exec():
            TempFile.manager.lockForWrite()
            with h5py.File(TempFile.path, 'r+') as store:
                del (store[f'positions/{self.position}/{item.text()}'])
                for comp in store['comparisons'].keys():
                    poss = comp.split(' vs ')
                    if self.position in poss:
                        if item.text() in store[f'comparisons/{comp}'].keys():
                            del (store[f'comparisons/{comp}/{item.text()}'])
            TempFile.manager.unlock()
            self.remove_existing(item.text())
            self.model.removeRow(self.currentIndex().row())


class VisualisationFile(QStandardItem):
    """Custom QListWidget item for Visualisation files"""
    # states
    QUEUED = 0
    LOADING = 1
    FAILURE = 2
    SUCCESS = 3
    filepath: str  # full filepath of the csv
    state: int  # state of the file
    msg: str  # additional messages to be displayed in line

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.state = self.QUEUED
        self.msg = ''
        super(QStandardItem, self).__init__(filepath.split('/')[-1])

    @pyqtSlot(str)
    def update_tooltip(self, tip: str) -> None:
        """pyqtSlot to update toolTip accessible to operations
        in other threads"""
        self.setToolTip(tip)

    @pyqtSlot(str)
    def update_text(self, text: str) -> None:
        """pyqtSlot to update item text accessible to operations
        in other threads"""
        self.setText(text)

    @pyqtSlot(str)
    def update_msg(self, msg: str) -> None:
        """pyqtSlot to update item message accessible to operations
        in other threads"""
        self.msg = msg


class VisualisationDeligate(QStyledItemDelegate):
    """Item deligate for setting progress icons"""
    loading: QSvgRenderer

    def __init__(self, parent: VisualisationList) -> None:
        """Init QStyledItemDelegate but parent must be of type
        VisualisationList"""
        super().__init__(parent=parent)
        self.list = parent
        # svg animation for loading/queued
        self.loading = QSvgRenderer(resource_path()+'/ui/resources/'
                                    f'{QSettings().value("active_theme").folder}'
                                    '/loading.svg', parent)
        # svg icon for success
        self.success = QPixmap(resource_path()+'/ui/resources/'
                               f'{QSettings().value("active_theme").folder}'
                               '/success.svg')
        # svg icon for failed
        self.failed = QPixmap(resource_path()+'/ui/resources/'
                              f'{QSettings().value("active_theme").folder}'
                              '/failed.svg')

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        """Custom painting to put icons to the right"""
        super().paint(painter, option, index)
        # get the VisualisationFile object
        item = self.list.model.item(index.row(), 0)
        # verify state is recognised
        if item.state not in [VisualisationFile.QUEUED,
                              VisualisationFile.LOADING, VisualisationFile.SUCCESS,
                              VisualisationFile.FAILURE]:
            raise ValueError('VisualisationFile state not recognised.')
        option = option.__class__(option)
        # get bounding box of list items text
        font_metrics = QFontMetrics(option.font)
        rect = font_metrics.boundingRect(index.data())
        message_width = option.rect.width()-(rect.right()+30)
        message_bounds = QRectF(rect.right()+10+option.rect.height(),
                                option.rect.top(), message_width, option.rect.height())
        # if loading or queued render the loading animation
        if item.state in [VisualisationFile.QUEUED,
                          VisualisationFile.LOADING]:
            icon_bounds = QRectF(rect.right()+10, option.rect.top()+2,
                                 option.rect.height()-4, option.rect.height()-4)
            self.loading.render(painter, icon_bounds)
        # otherwise just paint the success/failure icon and message
        else:
            if item.state == VisualisationFile.SUCCESS:
                pixmap = self.success.scaled(option.rect.height()-4,
                                             option.rect.height()-4,
                                             Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if item.state == VisualisationFile.FAILURE:
                pixmap = self.failed.scaled(option.rect.height()-4,
                                            option.rect.height()-4,
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # create elided text for error message
                fail_text = font_metrics.elidedText(item.msg,
                                                    Qt.ElideRight, message_width)
                # set custom font to make message italic
                italic = QFont('Segoe UI', painter.font().pointSize())
                italic.setItalic(True)
                painter.setFont(italic)
                # draw message in custom bounds
                painter.drawText(message_bounds, Qt.AlignVCenter, fail_text)
            painter.drawPixmap(QPoint(rect.right()+10,
                                      option.rect.top()+2), pixmap)


class VisualisationParser():
    """A parser to read a CORD visualisation csv into
    an OptiCORD python Visualisation"""
    filepath: str  # full filepath of visualisation file
    name: str  # visualisation name
    info: dict  # info dict used by various internal functions
    data: dict  # data dict to hold visualisation data
    meta: dict  # meta dict to hold visualisation metadata

    def __init__(self, filepath: str,
                 vis_list: VisualisationList) -> None:
        self.filepath = filepath
        self.vis_list = vis_list

    def check_filepath(self) -> None:
        """Checks a given filepath is of correct format
        for a CORD visualisation and unique in th vis_list.
        Assigns the visualisation name if it is."""
        # validate the filepath is of correct format
        validate_filepath(self.filepath)
        self.meta = dict()  # init the meta dict
        # assign the name
        self.name = self._determine_name()
        # get the download time from the windows file creation time
        self.meta['Downloaded'] = os.path.getctime(self.filepath)
        # validate visualisation is unique
        validate_unique(self.name, self.vis_list.existing)

    def parse(self) -> None:
        """Attempt to parse csv from filepath as an
        OptiCORD Visualisation. Returns a Visualisation."""
        log.debug(f'Parsing visualisation "{self.name}"')
        # create info through a preliminary read
        self._prelim_read()
        # determine if file has been modified
        self.info['modified'] = self._determine_modified()
        # TODO clean up this print
        if self.info['modified']:
            print("File has been modified in excel")
        # create the metadata dict
        self._read_meta()
        # create the data dict
        self._create_data()

    def save(self) -> None:
        """Saves the visualisation to the TempFile under a given 
        position"""
        # safely write to the file using TempFile's manager
        TempFile.manager.lockForWrite()
        with h5py.File(TempFile.path, 'r+') as store:
            iter_group = store[f'positions/{self.vis_list.position}']
            vis_store = iter_group.create_group(self.name)
            # save the metadata to attributes
            for key, val in self.meta.items():
                # unable to store dict as attribute so convert to json
                if type(val) is dict:
                    val = json.dumps(val)
                vis_store.attrs[key] = val
        # save the visualisation data via pandas
        for per in self.meta['Periodicities']:
            # format='fixed' is a lot faster to read/write than 'table'
            # but means that the data cannot be read in parallel.
            # After testing with dask it took longer to read data in
            # parallel anyway and 58M obs can be read/written and compared
            # using pandas so there should be no need to run in parallel.
            self.data[per].to_hdf(TempFile.path,
                                  f'positions/{self.vis_list.position}/{self.name}/{per}',
                                  mode='a', complib='blosc:zlib', complevel=9,
                                  format='fixed')
            # complibs were benchmarked using the lines below.
            # blosc:zlib was chosen for its small file size
            # and speedy execution.
            # visualisation_compression_test.benchmark(
            #   f'{self.name}_{per}', self.data[per])
        TempFile.manager.unlock()

    def _determine_modified(self):
        """Determines whether or not a csv file has been opened and saved
        in excel which changes the format from the default CORD format.
        Returns:
            True if file has been modified in excel
            False if file has not been modified"""
        # read the csv into a single column
        df = pd.read_csv(self.filepath, encoding='unicode_escape',
                         header=None, names=[0], skip_blank_lines=False,
                         dtype=str, nrows=3, delimiter='|')
        # by CORD definition one line of the first 3 should be blank
        if not df.isnull().values.any():
            return True
        else:
            return False

    def _determine_periodicity(self) -> List[str]:
        """Determines the periodicity of a marked row of dates, returns
        a list of periodicities in the order they appear"""
        periods = []
        # for each marked slice except first which is metadata
        for start, _ in self.info['markers'][1:]:
            # retrieve a date from the slice
            date = pd.read_csv(self.filepath, encoding='unicode_escape',
                               header=None, skiprows=start+1, nrows=1, dtype=str)\
                .dropna(axis='columns').iloc[0].tolist()[0]
            # validate that the date is of known format then add to list
            periods.append(validate_date(date))
        return periods

    def _determine_name(self) -> tuple:
        """Determines the visualisation name from it's filepath"""
        results = re.match('(.*?)_\d\d\d\d\d\d_\d\d\d\d\d\d.csv|(.*?)_\d*\(VisualisationCSV\)',
                           self.filepath.split('/')[-1])
        if results.group(1):
            return results.group(1)
        else:
            return results.group(2)

    def _retrieve_markers(self) -> List[tuple]:
        """Find start and end indices that will later be used to slice
        the visualisation into parts. Returns list of tuples containing
        the start and end indices for each slice."""
        df = self.info['prelim_df']
        date = df.loc[df[0].str.contains(',Date', na=False)].index.tolist()
        criteria = df.loc[df[0].str.contains(
            'Criteria: ', na=False)].index.tolist()
        markers = [(0, date[0]-1)]  # initialize markers with metadata
        # create markers for each periodicity of data within csv
        for i, d in enumerate(date):
            # if its the last section dont expect a criteria marker
            if d == date[-1]:
                last = len(df.index)-1  # -1 because pandas counts from 0
                # ensure we get the last line with data
                while pd.isna(df.loc[last, 0]):
                    last -= 1
                markers.append((d, last))
            # otherwise get end index from criteria marker
            else:
                # TODO check this doesn't include the criteria line in slice
                # criteria[i+1] to get start of next periodicity as end marker
                # -2 as last data line is 2 above criteria
                markers.append((d, criteria[i+1]-2))
        return markers

    def _retrieve_dates(self) -> List[List[str]]:
        """Process rows from prelim_df that contain dates into
        a list of lists containing only the date values."""
        master_list = []
        # retrieve the lines containing dates using markers
        for x, _ in self.info['markers'][1:]:
            # strip trailing commas then split by commas
            dates = self.info['prelim_df'].loc[x+1, 0].rstrip(',').split(',')
            # remove any quotations
            dates = [date.replace('"', '') for date in dates]
            # filter out any empty items
            dates = list(filter(lambda date: date != '', dates))
            master_list.append(dates)  # add to master list
        return master_list

    def _retrieve_dimensions(self) -> List[str]:
        """Read rows from prelim_df that contain the dimension headers 
        and return a list of dimensions."""
        # retrieve the lines containing dates using markers
        for x, _ in self.info['markers'][1:]:
            # strip trailing commas then split by commas
            dimensions = self.info['prelim_df'].loc[x,
                                                    0].rstrip(',').split(',')
            # remove any quotations
            dimensions = [dim.replace('"', '') for dim in dimensions]
            # filter out any empty items
            dimensions = list(filter(lambda dim: dim != '', dimensions))
            # remove the Date
            dimensions.remove('Date')
        return dimensions

    def _prelim_read(self) -> dict:
        """Preliminarily read the csv file as a much smaller dataframe
        to gather info for full read of dataframe."""
        # TODO add validation for structure of visualisation here
        # read the input csv as a single column
        self.info = dict()
        self.info['prelim_df'] = pd.read_csv(self.filepath,
                                             encoding='unicode_escape', delimiter='|',
                                             skip_blank_lines=False, header=None, dtype=str, names=[0])
        # gather marker points where dataframe will be sliced
        self.info['markers'] = self._retrieve_markers()
        # get the dates for each slice as a list
        self.info['dates'] = self._retrieve_dates()
        self.meta['Dimensions'] = self._retrieve_dimensions()
        # get the periodicities in the order they appear
        self.meta['Periodicities'] = self._determine_periodicity()

    def _read_meta(self):
        """Read the metadata from the top of the visualisation file."""
        _, end = self.info['markers'][0]
        # read the csv into a single column
        df = pd.read_csv(self.filepath, encoding='unicode_escape',
                         header=None, nrows=end, skip_blank_lines=False,
                         dtype=str, delimiter='|')
        meta_series = df[0].str.rstrip(',').replace('', np.nan)\
            .dropna().reset_index(drop=True)
        del df  # remove df from memory
        # validate_meta for instances where line contains more info
        # than required
        self.meta['Statistical Activity'] = validate_meta('Statistical Activity',
                                                          'Statistical Activity = (.*?)$', meta_series)
        dataset_mode = validate_meta('Dataset:Mode',
                                     '.*?Dataset:(.*?),', meta_series)
        self.meta['Dataset'] = (':').join(dataset_mode.split(':')[:-1])
        self.meta['Mode'] = dataset_mode.split(':')[-1]
        self.meta['Status'] = validate_meta('Status',
                                            '.*?Status:(.*?),|.*?Status:(.*?)$', meta_series)
        coverage = dict()  # init a dict to be nested
        store = False  # store toggle will activate in correct section
        for item in meta_series:
            if store:
                # get criteria and value from line
                criteria, value = item.split(',')
                # store them in nested dict
                coverage[criteria] = value.replace('"', '')
            # activate store once "Coverage Descriptors" is found
            if item == "Coverage Descriptors":
                store = True
        self.meta['Coverage Descriptors'] = coverage
        self.meta

    def _convert_column_dates(self, per: str,
                              columns: pd.Series) -> pd.Series:
        """Convert a given series 'columns' to a datetime series based
        on periodicity 'per'."""
        if per == "A":
            return pd.to_datetime(columns, format="%Y")
        if per == "Q":
            return pd.to_datetime(pd.PeriodIndex(
                columns, freq='Q').to_timestamp())
        if per == "M":
            return pd.to_datetime(columns, format="%Y%b")

    def _create_data(self) -> pd.DataFrame:
        """Reads the visualisation in explicit slices to create self.data,
        a dict of dataframes with their periods as the keys."""
        self.data = dict()  # init data dict
        # ignore data loss warnings if file has been modified
        if self.info['modified']:
            # we're not actually losing data, it's just the extra commas
            # added in by excels saving format
            warnings.simplefilter(action='ignore',
                                  category=pd.errors.ParserWarning)
        # create a dataframe for each periodicity of data
        for i, per in enumerate(self.meta['Periodicities']):
            # get start and end markers (skipping meta marker with +1)
            start, end = self.info['markers'][i+1]
            start += 2  # +2 to get where data starts
            # create names
            names = self.meta['Dimensions'] + self.info['dates'][i]
            # create dtypes list
            # without compression 'category' type for dimensions uses less
            # memory, a compressed object however uses less memory than a
            # compressed category
            dtype_list = (['object']*len(self.meta['Dimensions'])) +\
                (['float64']*len(self.info['dates'][i]))
            # read the data slice
            df = pd.read_csv(self.filepath,
                             encoding='unicode_escape', header=None, skiprows=start,
                             nrows=end-start+1, skip_blank_lines=False, index_col=False,
                             names=names, dtype=dict(zip(names, dtype_list)),
                             keep_default_na=False, na_values=['.', 'NULL', ''])
            # forward fill the dimension columns
            df[self.meta['Dimensions']] = df[self.meta['Dimensions']].ffill()
            # set dimension columns as index
            df.set_index(self.meta['Dimensions'], inplace=True)
            # convert the columns to regular python datetime
            df.columns = self._convert_column_dates(per, df.columns)
            # store dataset in data dict under the key: periodicity
            self.data[per] = df
        # stop ignoring any parser warnings
        warnings.simplefilter(action='default',
                              category=pd.errors.ParserWarning)


class VisualisationSignals(QObject):
    """Signals for VisualisationWorkers, must be in it's
    own QObject class as QRunnable doesn't support signals"""
    update_tooltip = pyqtSignal(str)
    update_name = pyqtSignal(str)
    update_msg = pyqtSignal(str)
    finished = QtCore.pyqtSignal()


class VisualisationWorker(QRunnable):
    """A QRunnable object to handle reading visualisation files"""
    item: VisualisationFile
    parser: VisualisationParser

    def __init__(self, filepath: str,
                 vis_list: VisualisationList):
        super(QRunnable, self).__init__()
        self.signals = VisualisationSignals()
        self.filepath = filepath
        self.vis_list = vis_list
        self.item = VisualisationFile(filepath)
        self.parser = VisualisationParser(filepath, vis_list)
        self.item.state = VisualisationFile.QUEUED
        self.signals.update_tooltip.connect(lambda tip:
                                            self.item.update_tooltip(tip))
        self.signals.update_name.connect(lambda text:
                                         self.item.update_text(text))
        self.signals.update_name.connect(lambda name:
                                         self.vis_list.add_to_existing(name))
        self.signals.update_msg.connect(lambda msg:
                                        self.item.update_msg(msg))

    def check_filepath(self) -> bool:
        """Checks the filepath of the passed file looks
        valid. Returns the visualisation name.
        Returns True if filepath is valid, False if not."""
        try:
            # validate the filepath
            self.parser.check_filepath()
            # update name of visualisation if it's valid
            self.signals.update_name.emit(self.parser.name)
            return True
        except InvalidVisualisation as e:
            self.signals.update_tooltip.emit(e.full)
            self.signals.update_msg.emit(e.short)
            self.item.state = VisualisationFile.FAILURE
        except:
            log.exception(f'{self.item.filepath} failed to check filepath due'
                          ' to an unexpected error:\n')
            self.signals.update_msg.emit(
                'Failed to upload, contact OptiCORD team')
            self.item.state = VisualisationFile.FAILURE
        return False

    def run(self):
        """Attempts to read the csv as a visualisation"""
        self.item.state = VisualisationFile.LOADING
        try:
            self.parser.parse()
            self.parser.save()
            self.item.state = VisualisationFile.SUCCESS
        except InvalidVisualisation as e:
            self.signals.update_tooltip.emit(e.full)
            self.signals.update_msg.emit(e.short)
            self.item.state = VisualisationFile.FAILURE
        except:
            log.exception(f'{self.item.filepath} failed to upload due'
                          ' to an unexpected error:\n')
            self.signals.update_msg.emit(
                'Failed to upload, contact OptiCORD team')
            self.item.state = VisualisationFile.FAILURE
        finally:
            self.signals.finished.emit()
