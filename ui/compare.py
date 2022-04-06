import os
import time
from typing import List
from wsgiref import validate
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QPixmap, QPainter, QFont, QFontMetrics
from PyQt5.uic import loadUi
from PyQt5.QtCore import QEvent, QObject, QSettings, QModelIndex, QPoint, QRectF, Qt, pyqtSlot, QDate, QRunnable, pyqtSignal, QThreadPool
from PyQt5.Qt import QSvgRenderer
from PyQt5.QtWidgets import QAbstractItemView, QListView, QTreeView, QWidget, QStyledItemDelegate, QStyleOptionViewItem, QDateEdit, QFileDialog, QMessageBox, QPushButton, QDialog, QApplication
import h5py
import pandas as pd
from comparison import InvalidComparison, PandasComparison
from util import CharacterSet, NameValidator, StandardFormats, TempFile, Switch


class ComparisonSignals(QObject):
    """Signals for ComparisonWorkers, must be in it's
    own QObject class as QRunnable doesn't support signals"""
    update_tooltip = pyqtSignal(str)
    update_msg = pyqtSignal(str)


class SelectAllItem(QStandardItem):
    """Returns a select all item for the ComparisonList"""

    def __init__(self) -> None:
        super(QStandardItem, self).__init__("(Select All)")
        self.setCheckable(True)
        self.setCheckState(2)


class ComparisonItem(QStandardItem):
    """Custom QListWidget item for comparison items"""
    # states
    LONELY = -1
    QUEUED = 0
    PROCESSING = 1
    FAILURE = 2
    SUCCESS = 3
    name: str  # name of the visualisation
    state: int  # state of the item
    msg: str  # additional messages to be displayed in line

    def __init__(self, name: str) -> None:
        super(QStandardItem, self).__init__(name)
        self.name = name
        self.state = self.QUEUED
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
    def update_text(self, text: str) -> None:
        """pyqtSlot to update item text accessible to operations
        in other threads"""
        self.setText(text)


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
        # connect double click with checkbox
        self.doubleClicked.connect(self.toggle_item_check)

    @pyqtSlot(QModelIndex)
    def toggle_item_check(self, index) -> None:
        """Checks or unchecks an item given by QModelIndex"""
        row = index.row()
        item = self.model.item(row)
        if item.isCheckable():
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
                     if self.model.item(i).isCheckable()]
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
                item.setCheckable(True)
                item.setCheckState(2)
                if item.name in existing:
                    item.state = ComparisonItem.SUCCESS
                    meta = self.get_meta(f'comparisons/{pre_name} vs {post_name}'
                                         f'/{item.name}')
                    item.update_diffs(meta['differences'])
            else:
                item.state = ComparisonItem.LONELY
                item.setEnabled(False)
                if vis in pre:
                    item.msg = f'Missing in {post_name}'
                if vis in post:
                    item.msg = f'Missing in {pre_name}'
            # add item to the list
            self.model.appendRow(item)

    @pyqtSlot(str, str)
    def get_existing(self, pre_it: str, post_it: str) -> list:
        """Returns a list of existing comparisons given a pre and post
        iteration"""
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
        iteration"""
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
        # svg icon for success
        self.success = QPixmap('./ui/resources/'
                               f'{QSettings().value("active_theme").folder}'
                               '/success.svg')
        # svg icon for failed
        self.failed = QPixmap('./ui/resources/'
                              f'{QSettings().value("active_theme").folder}'
                              '/failed.svg')

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
        if item.isCheckable():
            hgap = 30
        else:
            hgap = 10
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
            if item.state != ComparisonItem.QUEUED:
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
        # setup comparison options
        self.options = ComparisonOptions(self)
        self.setup_options()
        # get fixed width for container in ComparisonWidget
        self.fixedWidth = self.columnWidth(0) + 150

    def setup_options(self) -> None:
        """Where options are managed"""
        # Sheet Options
        self.options.create("Sheets", ComparisonOption.BLANK)
        self.options.create(
            "Pre-change sheet", ComparisonOption.TOGGLE, parent="Sheets")
        self.options.create(
            "Post-change sheet", ComparisonOption.TOGGLE, parent="Sheets")
        self.options.create(
            "MetaData sheet", ComparisonOption.TOGGLE, parent="Sheets",
            default_value=True)
        # Analysis Columns
        self.options.create("Analysis Columns", ComparisonOption.BLANK)
        self.options.create("Overall ABS Diff",
                            ComparisonOption.TOGGLE, parent="Analysis Columns")
        self.options.create("Overall Diff",
                            ComparisonOption.TOGGLE, parent="Analysis Columns")
        self.options.create("Max ABS Diff",
                            ComparisonOption.TOGGLE, parent="Analysis Columns")
        self.options.create("Max ABS Diff (%)",
                            ComparisonOption.TOGGLE, parent="Analysis Columns")
        self.options.create("Max ABS Diff Date",
                            ComparisonOption.TOGGLE, parent="Analysis Columns")
        # Date Range Options
        self.options.create("Compare within specific Date Range",
                            ComparisonOption.TOGGLE)
        self.options.create("From: ", ComparisonOption.DATE,
                            parent="Compare within specific Date Range",
                            default_value=QDate(1997, 1, 1))
        self.options.create("To: ", ComparisonOption.DATE,
                            parent="Compare within specific Date Range",
                            default_value=QDate.currentDate())
        # Export Options
        self.options.create("Skip exporting if no differences",
                            ComparisonOption.TOGGLE, default_value=True)
        self.options.create("Include series without differences",
                            ComparisonOption.TOGGLE,
                            parent="Skip exporting if no differences")


class ComparisonOption(QStandardItem):
    """A customised QStandardItem object to hold all information
    relating to a comparison option."""
    # actions
    BLANK = 0
    TOGGLE = 1
    DATE = 2
    widget: QObject

    def __init__(self, text: str, action: int, default_value) -> None:
        if action not in [self.BLANK, self.TOGGLE, self.DATE]:
            raise Exception("Comparison selection not recognised.")
        super(QStandardItem, self).__init__(text)
        self.action = action
        self.setting_name = "CompOpt_"+text
        # align with user settings
        self.value = QSettings().value(self.setting_name, default_value)
        # setup assosciate widget using user settings
        if self.action is self.TOGGLE:
            switch = Switch()
            switch.setMaximumSize(switch.sizeHint())
            # switch.isChecked() returns "true" or "false"
            # so need to allow for string version of bool
            if self.value in [True, "true"]:
                switch.setChecked(True)
            # connect switch toggle to QSetting
            switch.toggled.connect(lambda: QSettings().setValue(
                self.setting_name, switch.isChecked()))
            self.widget = switch
        if self.action is self.DATE:
            date = QDateEdit()
            date.setDisplayFormat('MMM yyyy')
            date.setMaximumSize(120, date.sizeHint().height())
            # connect Date to QSetting
            date.setDate(QSettings().value(self.setting_name, self.value))
            date.dateChanged.connect(lambda: QSettings().setValue(
                self.setting_name, date.date()))
            self.widget = date


class ComparisonOptions():
    """A registry of all comparison options"""
    tree: OptionsTree  # The OptionsTree parent widget
    options = dict()  # A dictionary of all options

    def __init__(self, tree: OptionsTree) -> None:
        self.tree = tree

    def create(self, text: str, action: int,
               parent: str = None, default_value=False) -> None:
        """Create a new option"""
        if text in self.options:
            raise Exception(f'An option for "{text}" already exists.')
        opt = ComparisonOption(text, action, default_value)
        placeholder = QStandardItem()
        if parent:  # if a parent is given in creation
            parent = self.options[parent]  # overwrite with parent item
            parent.appendRow([opt, placeholder])  # add new item as child
            # if parent is togglable, set child enabled/disabled based on parent
            if parent.action is ComparisonOption.TOGGLE:
                self.toggle_row_state(opt, placeholder,
                                      parent.widget.isChecked())
                parent.widget.toggled.connect(lambda: self.toggle_row_state(
                    opt, placeholder, parent.widget.isChecked()))
        else:  # otherwise add it as new root row
            self.tree.model.appendRow([opt, placeholder])
        # add widget to column 2 if option has an action
        if action is not ComparisonOption.BLANK:
            self.tree.setIndexWidget(placeholder.index(), opt.widget)
        # register option in the dict
        self.options[text] = opt

    def toggle_row_state(self, opt, placeholder, state) -> None:
        """Disable/Enable a given row"""
        opt.setEnabled(state)
        opt.widget.setEnabled(state)
        # turn child TOGGLE widget to False
        if opt.action is ComparisonOption.TOGGLE:
            if opt.widget.isChecked():
                opt.widget.setChecked(False)
        placeholder.setEnabled(state)


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


class CompareWidget(QWidget, object):
    """Compare page ui and functionality"""

    def __init__(self, parent: QObject) -> None:
        super(QWidget, self).__init__(parent)
        # load the vanilla elements from QT Designer file
        loadUi("./ui/compare.ui", self)
        # magic line to get styling to work
        self.pre_dropdown.setView(QListView(self))
        self.post_dropdown.setView(QListView(self))
        # install event filter to auto-load iterations
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
        self.pre_dropdown.currentIndexChanged.connect(
            self.name_desc_manager)
        self.post_dropdown.currentIndexChanged.connect(
            self.name_desc_manager)
        self.comp_list.model.itemChanged.connect(self.manage_buttons)
        self.compare_button.clicked.connect(self.compare_action)
        self.export_button.clicked.connect(self.export_action)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """Event filter to customise events of ui children"""
        # load available iterations in dropdown menus
        if source in [self.pre_dropdown, self.post_dropdown] and \
                event.type() == QEvent.MouseButtonPress:
            # get the iterations
            iterations = self.get_iterations()
            # get the current selection
            old_pre = self.pre_dropdown.currentText()
            old_post = self.post_dropdown.currentText()
            # temporarily stop signals from firing
            self.pre_dropdown.blockSignals(True)
            self.post_dropdown.blockSignals(True)
            # refresh the dropdowns
            if source is self.pre_dropdown:
                if self.post_dropdown.currentText() != \
                        'Select post-change iteration...':
                    iterations.remove(self.post_dropdown.currentText())
                self.pre_dropdown.clear()
                self.pre_dropdown.addItems(
                    ['Select pre-change iteration...']+iterations)
            if source is self.post_dropdown:
                if self.pre_dropdown.currentText() != \
                        'Select pre-change iteration...':
                    iterations.remove(self.pre_dropdown.currentText())
                self.post_dropdown.clear()
                self.post_dropdown.addItems(
                    ['Select post-change iteration...']+iterations)
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

    def name_desc_manager(self) -> None:
        """Manages the enabling/disabling of the name and description edits
        depending on the ui state."""

        def enable_edits() -> None:
            self.desc_edit.setEnabled(True)

        def disable_edits() -> None:
            self.desc_edit.setEnabled(False)
            self.desc_edit.setPlaceholderText('Comparison description...')

        if self.pre_dropdown.currentText() != 'Select pre-change iteration...' \
            and self.post_dropdown.currentText() != \
                'Select post-change iteration...':
            enable_edits()
            self.load_visualisations()
        else:
            disable_edits()
            self.comp_list.clear()

    def load_visualisations(self):
        """Loads all visualisations from selected iterations into
        the ComparisonList"""
        with h5py.File(TempFile.path, 'r+') as store:
            pre_vis = list(store[
                f'iterations/{self.pre_dropdown.currentText()}'].keys())
            post_vis = list(store[
                f'iterations/{self.post_dropdown.currentText()}'].keys())
        common = [x for x in post_vis if x in pre_vis]
        pre_only = [x for x in pre_vis if x not in post_vis]
        post_only = [x for x in post_vis if x not in pre_vis]
        self.comp_list.create(self.pre_dropdown.currentText(),
                              self.post_dropdown.currentText(),
                              common, pre_only, post_only)
        # initally manage buttons
        self.manage_buttons()

    @pyqtSlot()
    def manage_buttons(self):
        """Manages the state (Enabled/Disabled) of the Compare and 
        Export buttons."""
        checked_items = self.comp_list.get_checked_items()
        # if no checked items or items contain a failure, dont allow anything
        if checked_items.empty or checked_items.eq(
                ComparisonItem.FAILURE)['State'].any():
            self.compare_button.setEnabled(False)
            self.export_button.setEnabled(False)
        # if all items are already compared, allow export but not compare
        elif checked_items.eq(ComparisonItem.SUCCESS)['State'].all():
            self.compare_button.setEnabled(False)
            self.export_button.setEnabled(True)
        # otherwise allow compare but not export
        else:
            self.compare_button.setEnabled(True)
            self.export_button.setEnabled(False)

    @pyqtSlot()
    def compare_action(self) -> None:
        """Starts correct action based on whether or not a comparison
        is in progress."""
        if self.compare_button.text() == 'Compare':
            checked_items = self.comp_list.get_checked_items()
            not_compared = checked_items.loc[
                checked_items['State']
                != ComparisonItem.SUCCESS, 'Item'].tolist()
            print(not_compared)
            if not_compared:
                self.compare_items(not_compared)
        else:
            self.cancel()

    @pyqtSlot()
    def export_action(self) -> None:
        """Starts correct action based on whether or not a comparison
        is in progress."""
        if self.export_button.text() == 'Export':
            self.export_path = False
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
            self.export_path = export_name.path
            print('begin export')
        else:
            self.cancel()

    def compare_items(self, items: list) -> None:
        """Starts running ComparisonWorkers for checked list items that
        have not yet been compared."""
        self.register = []
        self.lock(self.compare_button)
        for item in items:
            self.comparison_worker = ComparisonWorker(
                self.register,
                self.pre_dropdown.currentText(),
                self.post_dropdown.currentText(),
                item)
            QThreadPool.globalInstance().start(self.comparison_worker)
            self.comparison_worker.signals.finished.connect(self.try_unlock)

    def lock(self, cancel_button: QPushButton) -> None:
        """Locks the UI for comparison"""
        self.pre_dropdown.setEnabled(False)
        self.post_dropdown.setEnabled(False)
        self.options.setEnabled(False)
        self.comp_list.setEnabled(False)
        # disable both buttons
        self.compare_button.setEnabled(False)
        self.export_button.setEnabled(False)
        # re-enable the one controlling cancel operation
        cancel_button.setEnabled(True)
        cancel_button.setText('Cancel')

    @pyqtSlot()
    def try_unlock(self) -> None:
        """Checks if to see if the register is empty, if so unlocks"""
        if self.register == []:
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
        self.comp_list.setEnabled(True)
        self.manage_buttons()

    @pyqtSlot()
    def cancel(self) -> None:
        """Cancels any active comparisons if they have not yet started."""
        self.compare_button.setEnabled(False)
        for worker in self.register:
            if QThreadPool.globalInstance().tryTake(worker):
                self.register.remove(worker)

    def ask_export(self) -> None:
        """Starts a pop-up for user to choose export folder."""
        folder = QFileDialog.getExistingDirectory(
            None, 'Select folder where comparisons will be exported',
            '', QFileDialog.ShowDirsOnly)
        return folder


class ComparisonSignals(QObject):
    """"""
    update_tooltip = pyqtSignal(str)
    update_msg = pyqtSignal(str)
    finished = pyqtSignal()


class ComparisonWorker(QRunnable):
    """A QRunnable object to handle reading Comparison files"""
    pre: str  # pre iteration as string
    post: str  # post iteration as string
    item: ComparisonItem  # ComparisonItem to be compared

    def __init__(self, reg: list, pre: str, post: str,
                 item: ComparisonItem) -> None:
        super(QRunnable, self).__init__()
        self.reg = reg
        self.item = item
        self.pre = pre
        self.post = post
        self.reg.append(self)
        self.signals = ComparisonSignals()
        self.signals.update_msg.connect(
            lambda text: self.item.update_text(text))
        self.signals.update_tooltip.connect(
            lambda text: self.item.update_tooltip(text))

    def run(self) -> None:
        """"""
        try:
            self.item.state = ComparisonItem.PROCESSING
            comp = PandasComparison(self.pre, self.post, self.item)
            comp.compare()
            self.item.state = ComparisonItem.SUCCESS
        except InvalidComparison as e:
            self.signals.update_tooltip.emit(e.full)
            self.signals.update_msg.emit(e.short)
            self.item.state = ComparisonItem.FAILURE
        finally:
            self.reg.remove(self)
            self.signals.finished.emit()
