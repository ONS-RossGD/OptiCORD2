from enum import auto
import logging
import os
from typing import List
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QPixmap, QPainter, QFont, QFontMetrics, QShowEvent
from PyQt5.uic import loadUi
from PyQt5.QtCore import QEvent, QObject, QSettings, QModelIndex, QPoint, QRectF, Qt, pyqtSlot, QRunnable, pyqtSignal, QThreadPool
from PyQt5.Qt import QSvgRenderer
from PyQt5.QtWidgets import QAbstractItemView, QListView, QTreeView, QWidget, QStyledItemDelegate, QStyleOptionViewItem, QFileDialog, QMessageBox, QPushButton, QDialog, QApplication
import h5py
import pandas as pd
from comparison import InvalidComparison, PandasComparison
from export import Export, ExportOptions
from util import CharacterSet, NameValidator, StandardFormats, TempFile

log = logging.getLogger('OptiCORD')


class ComparisonSignals(QObject):
    """Signals for ComparisonWorkers, must be in it's
    own QObject class as QRunnable doesn't support signals"""
    update_tooltip = pyqtSignal(str)
    update_msg = pyqtSignal(str)


class SelectAllItem(QStandardItem):
    """Returns a select all item for the ComparisonList"""

    def __init__(self) -> None:
        super(QStandardItem, self).__init__("(Select All)")
        # Set to true to render the checkbox, but then false so that
        # the checkbox's signals don't interfere with our overrides
        self.setCheckable(True)
        self.setCheckable(False)
        self.setCheckState(2)
        self.state = ComparisonItem.SELECT_ALL
        self.name = 'Select All'


class ComparisonItem(QStandardItem):
    """Custom QListWidget item for comparison items"""
    # states
    SELECT_ALL = auto()
    LONELY = auto()
    IDLE = auto()
    QUEUED = auto()
    PROCESSING = auto()
    EXPORTING = auto()
    FAILURE = auto()
    SUCCESS = auto()
    name: str  # name of the visualisation
    state: int  # state of the item
    msg: str  # additional messages to be displayed in line

    def __init__(self, name: str) -> None:
        super(QStandardItem, self).__init__(name)
        self.name = name
        self.state = self.IDLE
        self.msg = ''

    @pyqtSlot(str)
    def set_lonely(self, missing_in: str) -> None:
        """pyqtSlot to set the item as LONELY"""
        self.state = self.LONELY
        self.setCheckable(False)
        self.msg = f'Missing in {missing_in}'
        self.setEnabled(False)

    @pyqtSlot(bool)
    def update_diffs(self, diffs: bool) -> None:
        """pyqtSlot to update item message accessible to operations
        in other threads"""
        if diffs:
            self.msg = "Differences found"
        else:
            self.msg = "No differences"

    @pyqtSlot(str)
    def update_tooltip(self, tip: str) -> None:
        """pyqtSlot to update toolTip accessible to operations
        in other threads"""
        self.setToolTip(tip)

    @pyqtSlot(str)
    def update_name(self, text: str) -> None:
        """pyqtSlot to update item text accessible to operations
        in other threads"""
        self.setText(text)

    @pyqtSlot(str)
    def update_msg(self, msg: str) -> None:
        """pyqtSlot to update item text accessible to operations
        in other threads"""
        self.msg = msg


class ComparisonList(QListView):
    """ListWidget for visualisation comparisons"""

    def __init__(self, parent: QWidget) -> None:
        super(QListView, self).__init__(parent)
        # ListView setup
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setObjectName('comparison_list')
        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(['Visualisation'])
        self.model.itemChanged.connect(self.select_all_check)
        self.setModel(self.model)
        # init the custom deligate
        self.deligate = ComparisonDeligate(self)
        self.setItemDelegate(self.deligate)
        # update viewport when svg render frame changes
        self.deligate.loading.repaintNeeded.connect(
            self.viewport().update)
        # connect click with checkbox
        self.clicked.connect(self.toggle_item_check)

    @pyqtSlot(QModelIndex)
    def toggle_item_check(self, index) -> None:
        """Checks or unchecks an item given by QModelIndex"""
        row = index.row()
        item = self.model.item(row)
        if not item.isSelectable():
            return
        if item.state != ComparisonItem.LONELY:
            if item.checkState() == 0 or item.checkState() == 1:
                item.setCheckState(2)
            elif item.checkState() == 2:
                item.setCheckState(0)

    @pyqtSlot(QStandardItem)
    def select_all_check(self, item) -> None:
        """Check if the select all item has been toggled. If it has,
    act accordingly."""
        # Temporarily block signals
        self.model.blockSignals(True)
        # Get all checkable items
        checkable = [self.model.item(i) for i in range(1, self.model.rowCount())
                     if self.model.item(i).state != ComparisonItem.LONELY]
        # Filter new list of only items that are checked
        checked = list(filter(lambda i: i.checkState(), checkable))
        if item is self.select_all:  # if select all's state is changed
            # If not all items are checked, check them all
            if len(checked) < len(checkable):
                for c in checkable:
                    c.setCheckState(2)
                self.select_all.setCheckState(2)
            else:  # otherwise uncheck them all
                for c in checkable:
                    c.setCheckState(0)
                self.select_all.setCheckState(0)
        else:  # if a comparison item's state is changed
            # if an item is unchecked
            if item.checkState() == 0:
                # set select all to a square if there are still checked items
                if len(checked) > 0:
                    self.select_all.setCheckState(1)
                else:  # otherwise uncheck select all
                    self.select_all.setCheckState(0)
            # if an item is checked
            if item.checkState() == 2:
                # if not all items are checked, set select all to a square
                if len(checked) < len(checkable):
                    self.select_all.setCheckState(1)
                else:  # otherwise fully check select all
                    self.select_all.setCheckState(2)
        self.model.blockSignals(False)

    def create(self, pre_name: str, post_name: str, common: List[str],
               pre: List[str], post: List[str]) -> None:
        """Creates/Overwrites the visualisation list with the given
        visualisation lists"""
        # check all items and set state
        existing = self.get_existing(pre_name, post_name)
        # clear list and fill with new items
        self.clear()
        self.select_all = SelectAllItem()
        self.model.appendRow(self.select_all)
        # loop over every visualisation
        for vis in common + pre + post:
            # init the item
            item = ComparisonItem(vis)
            if vis in common:
                # set checkable to true so that the checkbox gets rendered
                item.setCheckable(True)
                # then turn it to false so that the checkbox cannot control
                # its own state as we'll override it with the clicked event
                # of the ComparisonList.
                item.setCheckable(False)
                item.setCheckState(2)
                if item.name in existing:
                    item.state = ComparisonItem.SUCCESS
                    meta = self.get_meta(f'comparisons/{pre_name} vs {post_name}'
                                         f'/{item.name}')
                    item.update_diffs(meta['differences'])
            else:
                if vis in pre:
                    missing = post_name
                if vis in post:
                    missing = pre_name
                item.set_lonely(missing)
            # add item to the list
            self.model.appendRow(item)

    @pyqtSlot(str, str)
    def get_existing(self, pre_it: str, post_it: str) -> list:
        """Returns a list of existing comparisons given a pre and post
        position"""
        existing = []
        TempFile.manager.lockForRead()
        with h5py.File(TempFile.path, 'r+') as store:
            comparison_list = store[f'comparisons'].keys()
            theoretical_comp = f'{pre_it} vs {post_it}'
            if theoretical_comp in comparison_list:
                existing = list(
                    store[f'comparisons/{theoretical_comp}'].keys())
        TempFile.manager.unlock()
        return existing

    @pyqtSlot(str)
    def get_meta(self, path: str) -> list:
        """Returns a list of existing comparisons given a pre and post
        position"""
        meta = dict()
        TempFile.manager.lockForRead()
        with h5py.File(TempFile.path, 'r+') as store:
            for key, val in store[path].attrs.items():
                meta[key] = val
        TempFile.manager.unlock()
        return meta

    @pyqtSlot()
    def clear(self) -> None:
        """Clears the visualisation list"""
        self.model.removeRows(0, self.model.rowCount())

    @pyqtSlot()
    def get_checked_items(self) -> pd.DataFrame:
        """Returns a dataframe with 2 columns: 'Item' and 'State'.
        'Item' column contains all of the checked ComparisonItem's
        (excluding the 'Select All' item) and 'State' column contains each
        item's state."""
        df = pd.DataFrame()
        df['Item'] = [self.model.item(i) for i in range(1, self.model.rowCount())
                      if self.model.item(i).checkState() == 2]
        df['State'] = [i.state for i in df['Item']]
        return df

    @pyqtSlot()
    def lock_selection(self) -> None:
        """Ensures the state of the comparison list cannot be changed"""
        self.select_all.setSelectable(False)
        self.locked = [self.model.item(i)
                       for i in range(1, self.model.rowCount())]
        for i in self.locked:
            i.setSelectable(False)

    @pyqtSlot()
    def unlock_selection(self) -> None:
        """Allows comparison list items to have their state changed again"""
        self.select_all.setSelectable(True)
        for i in self.locked:
            i.setSelectable(True)
        self.locked = []


class ComparisonDeligate(QStyledItemDelegate):
    """Item deligate for setting progress icons"""
    loading: QSvgRenderer

    def __init__(self, parent: ComparisonList) -> None:
        """Init QStyledItemDelegate but parent must be of type
        ComparisonList"""
        super().__init__(parent=parent)
        self.list = parent
        # svg animation for loading
        self.loading = QSvgRenderer('./ui/resources/'
                                    f'{QSettings().value("active_theme").folder}'
                                    '/loading.svg', parent)
        # svg animation for exporting
        self.exporting = QSvgRenderer('./ui/resources/'
                                      f'{QSettings().value("active_theme").folder}'
                                      '/exporting.svg', parent)
        # svg icon for success
        self.success = QPixmap('./ui/resources/'
                               f'{QSettings().value("active_theme").folder}'
                               '/success.svg')
        # svg icon for failed
        self.failed = QPixmap('./ui/resources/'
                              f'{QSettings().value("active_theme").folder}'
                              '/failed.svg')
        # svg icon for queued
        self.queued = QPixmap('./ui/resources/'
                              f'{QSettings().value("active_theme").folder}'
                              '/queued.svg')

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        """Custom painting to put icons to the right"""
        super().paint(painter, option, index)
        # get the ComparisonItem object
        item = self.list.model.item(index.row(), 0)
        # verify item is a comparison item
        if type(item) is not ComparisonItem:
            return
        option = option.__class__(option)
        # get bounding box of list items text
        vgap = 4
        if item.state == ComparisonItem.LONELY:
            hgap = 10
        else:
            hgap = 30
        font_metrics = QFontMetrics(option.font)
        rect = font_metrics.boundingRect(index.data())
        message_width = option.rect.width()-(rect.right()+30)
        message_bounds = QRectF(rect.right()+hgap+option.rect.height(),
                                option.rect.top(), message_width, option.rect.height())
        # if processing render the loading animation
        if item.state == ComparisonItem.PROCESSING:
            icon_bounds = QRectF(rect.right()+hgap, option.rect.top()+(vgap/2),
                                 option.rect.height()-vgap, option.rect.height()-vgap)
            self.loading.render(painter, icon_bounds)
        # if exporting render the exporting animation
        elif item.state == ComparisonItem.EXPORTING:
            icon_bounds = QRectF(rect.right()+hgap, option.rect.top()+(vgap/2),
                                 option.rect.height()-vgap, option.rect.height()-vgap)
            self.exporting.render(painter, icon_bounds)
        # otherwise just paint the success/failure icon and message
        else:
            if item.state == ComparisonItem.SUCCESS:
                pixmap = self.success.scaled(option.rect.height()-vgap,
                                             option.rect.height()-vgap,
                                             Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if item.state in [ComparisonItem.FAILURE,
                              ComparisonItem.LONELY]:
                pixmap = self.failed.scaled(option.rect.height()-vgap,
                                            option.rect.height()-vgap,
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if item.state == ComparisonItem.QUEUED:
                pixmap = self.queued.scaled(option.rect.height()-vgap,
                                            option.rect.height()-vgap,
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if item.state != ComparisonItem.IDLE:
                painter.drawPixmap(QPoint(rect.right()+hgap,
                                          option.rect.top()+(vgap/2)), pixmap)
        # set custom font to make message italic
        italic = QFont('Segoe UI', painter.font().pointSize())
        italic.setItalic(True)
        painter.setFont(italic)
        # create elided text for message
        msg_text = font_metrics.elidedText(
            item.msg, Qt.ElideRight, message_width)
        # draw message in custom bounds
        painter.drawText(message_bounds, Qt.AlignVCenter, msg_text)


class OptionsTree(QTreeView):
    """Comparison options customised TreeView"""
    model: QStandardItemModel

    def __init__(self, parent: QObject) -> None:
        super(QWidget, self).__init__(parent)
        # TreeView setup
        self.setTextElideMode(Qt.ElideNone)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setObjectName('options_tree')
        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(['Options', 'Val'])
        # auto expand tree
        self.model.rowsInserted.connect(lambda a: self.expandRecursively(a))
        # ensure horizontal scroll bar appears
        self.expanded.connect(lambda: self.resizeColumnToContents(0))
        self.setHeaderHidden(True)
        self.setModel(self.model)
        # setup export options tree
        self.create_tree()
        # get fixed width for container in ComparisonWidget
        self.fixedWidth = self.columnWidth(0) + 150

    def create_tree(self) -> None:
        for key, option in list(vars(ExportOptions).items()):
            if key.startswith('__'):
                continue
            option.add_to_tree(self)


class ExportDialog(QDialog, object):
    """Dialog window for creating a new change tracker file."""
    path: str  # path to the export folder

    def __init__(self, parent: QObject, folder: str,
                 name_guess: str) -> None:
        super(QDialog, self).__init__(parent, Qt.WindowCloseButtonHint)
        # load the vanilla elements from QT Designer file
        loadUi("./ui/export.ui", self)
        self.folder = folder
        self.name_guess = name_guess
        self.name_edit.setText(self.name_guess)
        self.name_edit.setFocus()
        self.warning.hide()
        validator = NameValidator(self, CharacterSet.FULL)
        self.name_edit.setValidator(validator)
        self.name_edit.textChanged.connect(
            lambda: self.reset_invalid_input(self.name_edit))

    def reset_invalid_input(self, w: QWidget) -> None:
        """Resets the invalid_input property of a given widget"""
        if w.property("invalid_input") == "true":
            w.setProperty("invalid_input", "false")
            # style has to be unpolished and polished to update
            w.style().unpolish(w)
            w.style().polish(w)
        self.warning.hide()

    def validate_name(self) -> bool:
        """Validates that the entered name is a valid folder name.
        If it is, the folder is created and returns True. If not udpates
        the ui and returns False."""
        if os.path.isdir(self.path):
            # update property to reflect invalid input
            self.name_edit.setProperty("invalid_input", "true")
            # style has to be unpolished and polished to update
            self.name_edit.style().unpolish(self.name_edit)
            self.name_edit.style().polish(self.name_edit)
            self.warning.show()
            return False
        else:
            os.mkdir(self.path)
            return True

    def accept(self) -> None:
        self.path = f'{self.folder}/{self.name_edit.text()}'
        if not self.validate_name():
            return QApplication.beep()
        return super().accept()


class ComparePageSignals(QObject):
    """Signals for the compare page, signals require QObject inheritance
    hence being in a seperate class"""
    cancel = pyqtSignal()


class CompareWidget(QWidget, object):
    """Compare page ui and functionality"""

    def __init__(self, parent: QObject) -> None:
        super(QWidget, self).__init__(parent)
        # load the vanilla elements from QT Designer file
        loadUi("./ui/compare.ui", self)
        # magic line to get styling to work
        self.pre_dropdown.setView(QListView(self))
        self.post_dropdown.setView(QListView(self))
        # install event filter to auto-load positions
        self.pre_dropdown.installEventFilter(self)
        self.post_dropdown.installEventFilter(self)
        # create comparison list
        self.comp_list = ComparisonList(self.list_container)
        self.list_container_layout.addWidget(self.comp_list, 0, 0)
        # create options tree
        self.options = OptionsTree(self.options_container)
        self.options_container_layout.addWidget(self.options, 0, 0)
        # fix the options container to
        self.options_container.setMaximumWidth(self.options.fixedWidth)
        self.options_container.setMinimumWidth(self.options.fixedWidth)
        # signals
        self.signals = ComparePageSignals()
        self.pre_dropdown.currentIndexChanged.connect(
            self.name_desc_manager)
        self.post_dropdown.currentIndexChanged.connect(
            self.name_desc_manager)
        self.comp_list.model.itemChanged.connect(self.manage_ui_states)
        self.compare_button.clicked.connect(self.compare_action)
        self.export_button.clicked.connect(self.export_action)

    def showEvent(self, a0: QShowEvent) -> None:
        self.name_desc_manager()
        return super().showEvent(a0)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """Event filter to customise events of ui children"""
        # load available positions in dropdown menus
        if source in [self.pre_dropdown, self.post_dropdown] and \
                event.type() == QEvent.MouseButtonPress:
            # get the positions
            positions = self.get_positions()
            # get the current selection
            old_pre = self.pre_dropdown.currentText()
            old_post = self.post_dropdown.currentText()
            # temporarily stop signals from firing
            self.pre_dropdown.blockSignals(True)
            self.post_dropdown.blockSignals(True)
            # refresh the dropdowns
            if source is self.pre_dropdown:
                if self.post_dropdown.currentText() != \
                        'Select post-change position...':
                    positions.remove(self.post_dropdown.currentText())
                self.pre_dropdown.clear()
                self.pre_dropdown.addItems(
                    ['Select pre-change position...']+positions)
            if source is self.post_dropdown:
                if self.pre_dropdown.currentText() != \
                        'Select pre-change position...':
                    positions.remove(self.pre_dropdown.currentText())
                self.post_dropdown.clear()
                self.post_dropdown.addItems(
                    ['Select post-change position...']+positions)
            pre_matching = self.pre_dropdown.findText(
                old_pre, Qt.MatchFixedString)
            post_matching = self.post_dropdown.findText(
                old_post, Qt.MatchFixedString)
            if pre_matching >= 0:
                self.pre_dropdown.setCurrentIndex(pre_matching)
            if post_matching >= 0:
                self.post_dropdown.setCurrentIndex(post_matching)
            # resume signals
            self.pre_dropdown.blockSignals(False)
            self.post_dropdown.blockSignals(False)
        return super().eventFilter(source, event)

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

    def name_desc_manager(self) -> None:
        """Manages the enabling/disabling of the name and description edits
        depending on the ui state."""

        if self.pre_dropdown.currentText() != 'Select pre-change position...' \
            and self.post_dropdown.currentText() != \
                'Select post-change position...':
            self.load_visualisations()
        else:
            self.comp_list.clear()
        self.manage_ui_states()

    def load_visualisations(self):
        """Loads all visualisations from selected positions into
        the ComparisonList"""
        log.debug('loading visualisations into comparison list for '
                  f'{self.pre_dropdown.currentText()} vs {self.post_dropdown.currentText()}')
        with h5py.File(TempFile.path, 'r+') as store:
            pre_vis = list(store[
                f'positions/{self.pre_dropdown.currentText()}'].keys())
            post_vis = list(store[
                f'positions/{self.post_dropdown.currentText()}'].keys())
        common = [x for x in post_vis if x in pre_vis]
        pre_only = [x for x in pre_vis if x not in post_vis]
        post_only = [x for x in post_vis if x not in pre_vis]
        self.comp_list.create(self.pre_dropdown.currentText(),
                              self.post_dropdown.currentText(),
                              common, pre_only, post_only)
        # initally manage buttons
        self.manage_ui_states()

    @pyqtSlot()
    def manage_ui_states(self):
        """Manages the various ui states (Enabled/Disabled) based on the
        checked items in the comparison list."""
        checked_items = self.comp_list.get_checked_items()
        # if no checked items or items contain a failure, dont allow anything
        if checked_items.empty or checked_items.eq(
                ComparisonItem.FAILURE)['State'].any():
            self.compare_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.desc_edit.clear()
            self.desc_edit.setEnabled(False)
        # if all items are already compared, allow export but not compare
        elif checked_items.eq(ComparisonItem.SUCCESS)['State'].all():
            self.compare_button.setEnabled(False)
            self.export_button.setEnabled(True)
            self.desc_edit.setEnabled(True)
            self.desc_edit.setPlaceholderText(
                'Enter description for export...')
        # otherwise allow compare but not export
        else:
            self.compare_button.setEnabled(True)
            self.export_button.setEnabled(False)
            self.desc_edit.clear()
            self.desc_edit.setEnabled(False)

    @ pyqtSlot()
    def compare_action(self) -> None:
        """Starts correct action based on whether or not a comparison
        is in progress."""
        if self.compare_button.text() == 'Compare':
            checked_items = self.comp_list.get_checked_items()
            not_compared = checked_items.loc[
                checked_items['State']
                != ComparisonItem.SUCCESS, 'Item'].tolist()
            if not_compared:
                self.compare_items(not_compared)
        else:
            self.signals.cancel.emit()
            self.compare_button.setEnabled(False)
            self.compare_button.setText('Cancelling...')

    @ pyqtSlot()
    def export_action(self) -> None:
        """Starts correct action based on whether or not a comparison
        is in progress."""
        if self.export_button.text() == 'Export':
            self.export_path = False
            # check date filter
            if ExportOptions.date_filter():
                if ExportOptions.date_filter_from() > \
                        ExportOptions.date_filter_to():
                    QMessageBox.warning(
                        self,
                        'Invalid Date Filter',
                        'When using a date filter, the "From" date must'
                        ' be before the "To" date.')
                    return
            folder = self.ask_export()
            if not folder:
                QMessageBox.warning(
                    self,
                    'Comparisons were not exported',
                    'You must choose a location for comparison reports'
                    ' to be exported.')
                return
            export_name = ExportDialog(
                self, folder, f'{self.pre_dropdown.currentText()} vs '
                f'{self.post_dropdown.currentText()}')
            if not export_name.exec():
                QMessageBox.warning(
                    self,
                    'Comparisons were not exported',
                    'You must enter a valid name for the export folder.')
                return
            self.export_items(export_name.path)
        else:
            self.signals.cancel.emit()
            self.export_button.setEnabled(False)
            self.export_button.setText('Cancelling...')

    def compare_items(self, items: list) -> None:
        """Starts running ComparisonWorkers for checked list items that
        have not yet been compared."""
        log.debug(f'attempting comparison of {[i.name for i in items]}')
        self.lock(self.compare_button)
        log.debug(f'comparing {self.pre_dropdown.currentText()} vs '
                  f'{self.post_dropdown.currentText()}')
        for item in items:
            self.comparison_worker = ComparisonWorker(
                self.pre_dropdown.currentText(),
                self.post_dropdown.currentText(),
                item)
            self.comparison_worker.signals.finished.connect(self.try_unlock)
            self.signals.cancel.connect(self.comparison_worker.cancel)
            QThreadPool.globalInstance().start(self.comparison_worker)

    def export_items(self, export_folder: str):
        """Starts running ExportWorkers for checked list items."""
        def _get_description() -> list:
            """Get the description string from the description box.
            If the description box is empty, fill with preset string."""
            desc = self.desc_edit.toPlainText()
            if desc == '':
                desc = f'Ask {os.getlogin()} for more info'
            desc = desc.split('\n')
            return desc
        log.debug('attempting export')
        items = self.comp_list.get_checked_items()['Item'].tolist()
        self.lock(self.export_button)
        for item in items:
            self.export_worker = ExportWorker(
                _get_description(),
                self.pre_dropdown.currentText(),
                self.post_dropdown.currentText(),
                export_folder,
                item)
            self.export_worker.signals.finished.connect(self.try_unlock)
            self.signals.cancel.connect(self.export_worker.cancel)
            QThreadPool.globalInstance().start(self.export_worker)

    def lock(self, cancel_button: QPushButton) -> None:
        """Locks the UI for comparison"""
        self.comp_list.model.blockSignals(True)
        self.pre_dropdown.setEnabled(False)
        self.post_dropdown.setEnabled(False)
        self.options.setEnabled(False)
        # self.comp_list.setEnabled(False)
        self.comp_list.lock_selection()
        # disable both buttons
        self.compare_button.setEnabled(False)
        self.export_button.setEnabled(False)
        # re-enable the one controlling cancel operation
        cancel_button.setEnabled(True)
        cancel_button.setText('Cancel')

    @ pyqtSlot()
    def try_unlock(self) -> None:
        """Checks if to see if items are being processed, if not unlocks"""
        unlock = True
        items = [self.comp_list.model.item(i) for i in range(
            1, self.comp_list.model.rowCount())]
        for item in items:
            if item.state in [ComparisonItem.PROCESSING,
                              ComparisonItem.EXPORTING,
                              ComparisonItem.QUEUED]:
                unlock = False
        if unlock:
            self.unlock()

    def unlock(self) -> None:
        """Unlocks the UI so another comparison can be made"""
        self.compare_button.setText('Compare')
        self.compare_button.setEnabled(True)
        self.export_button.setText('Export')
        self.export_button.setEnabled(True)
        self.pre_dropdown.setEnabled(True)
        self.post_dropdown.setEnabled(True)
        self.options.setEnabled(True)
        # self.comp_list.setEnabled(True)
        self.comp_list.unlock_selection()
        self.manage_ui_states()
        self.desc_edit.clear()
        self.comp_list.model.blockSignals(False)

    def ask_export(self) -> str:
        """Starts a pop-up for user to choose export folder."""
        folder = QFileDialog.getExistingDirectory(
            None, 'Select folder where comparisons will be exported',
            '', QFileDialog.ShowDirsOnly)
        if folder:
            # if folder doesn't exist then start again
            if not os.path.isdir(folder):
                return self.ask_export()
            # otherwise folder exists so return it
            return folder


class ComparisonSignals(QObject):
    """"""
    update_tooltip = pyqtSignal(str)
    update_msg = pyqtSignal(str)
    finished = pyqtSignal()


class ComparisonWorker(QRunnable):
    """A QRunnable object to handle reading Comparison files"""
    item: ComparisonItem  # ComparisonItem to be compared

    def __init__(self, pre: str, post: str,
                 item: ComparisonItem) -> None:
        super(QRunnable, self).__init__()
        self.item = item
        self.pre = pre
        self.post = post
        self.signals = ComparisonSignals()
        self.signals.update_msg.connect(
            lambda text: self.item.update_msg(text))
        self.signals.update_tooltip.connect(
            lambda text: self.item.update_tooltip(text))
        self.item.state = ComparisonItem.QUEUED
        self.should_cancel = False

    def cancel(self) -> None:
        self.should_cancel = True

    def run(self) -> None:
        """"""
        try:
            if self.should_cancel:
                log.debug(f'Comparison cancelled for {self.item.name}')
                self.item.state = ComparisonItem.IDLE
            else:
                log.debug(f'Attempting comparison for {self.item.name}')
                self.item.state = ComparisonItem.PROCESSING
                comp = PandasComparison(self.pre, self.post, self.item)
                comp.compare()
                self.item.state = ComparisonItem.SUCCESS
                log.debug(f'{self.item.name} compared successfully')
        except InvalidComparison as e:
            log.error(
                f'{self.item.name} was invalid with error: {e.short}')
            log.debug(e.full)
            self.signals.update_tooltip.emit(e.full)
            self.signals.update_msg.emit(e.short)
            self.item.state = ComparisonItem.FAILURE
        except:
            log.exception(
                f'{self.item.name} encountered error during comparison:\n')
            self.signals.update_msg.emit(
                'Failed to compare, contact OptiCORD team')
            self.item.state = ComparisonItem.FAILURE
        finally:
            self.signals.finished.emit()


class ExportSignals(QObject):
    """"""
    update_tooltip = pyqtSignal(str)
    update_msg = pyqtSignal(str)
    finished = pyqtSignal()


class ExportWorker(QRunnable):
    """A QRunnable object to handle reading Comparison files"""
    item: ComparisonItem  # ComparisonItem to be compared

    def __init__(self, desc: list, pre: str, post: str,
                 export_folder: str, item: ComparisonItem) -> None:
        super(QRunnable, self).__init__()
        self.desc = desc
        self.item = item
        self.pre = pre
        self.post = post
        self.exp_fol = export_folder
        self.signals = ExportSignals()
        self.signals.update_msg.connect(
            lambda text: self.item.update_msg(text))
        self.signals.update_tooltip.connect(
            lambda text: self.item.update_tooltip(text))
        self.original_state = self.item.state
        self.item.state = ComparisonItem.QUEUED
        self.should_cancel = False

    def cancel(self) -> None:
        self.should_cancel = True

    def run(self) -> None:
        """"""
        try:
            if self.should_cancel:
                log.debug(f'Cancelled export for {self.item.name}')
                self.item.state = self.original_state
            else:
                log.debug(f'Attempting export for {self.item.name}')
                self.item.state = ComparisonItem.EXPORTING
                exporter = Export(self.desc, self.pre, self.post,
                                  self.exp_fol, self.item)
                if exporter.should_skip:
                    log.info(f'Skipped export of {self.item.name}'
                             ' (no differences)')
                else:
                    exporter.export()
                self.item.state = ComparisonItem.SUCCESS
                log.debug(f'{self.item.name} exported successfully')
        except:
            log.exception(
                f'{self.item.name} encountered error during export:\n')
            self.signals.update_msg.emit(
                'Failed to export, contact OptiCORD team')
            self.item.state = ComparisonItem.FAILURE
        finally:
            self.signals.finished.emit()
