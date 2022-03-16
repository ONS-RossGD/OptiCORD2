import os
from typing import List
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QPixmap, QPainter, QFont, QFontMetrics
from PyQt5.uic import loadUi
from PyQt5.QtCore import QEvent, QObject, QSettings, QModelIndex, QPoint, QRectF, Qt, pyqtSlot, QDate
from PyQt5.Qt import QSvgRenderer
from PyQt5.QtWidgets import QAbstractItemView, QListView, QTreeView, QWidget, QStyledItemDelegate, QStyleOptionViewItem, QDateEdit
import h5py
import pandas as pd
from util import StandardFormats, TempFile, Switch


class SelectAllItem(QStandardItem):
    """Returns a select all item for the ComparisonList"""

    def __init__(self) -> None:
        super(QStandardItem, self).__init__("(Select All)")
        self.setCheckable(True)


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

    @pyqtSlot(QStandardItem)
    def select_all_check(self, item):
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
        self.clear()
        # fill list with new items
        self.select_all = SelectAllItem()
        self.model.appendRow(self.select_all)
        for v in common:
            i = ComparisonItem(v, False)
            self.model.appendRow(i)
        for v in pre:
            i = ComparisonItem(v, True)
            i.msg = f'Missing in "{post_name}"'
            self.model.appendRow(i)
        for v in post:
            i = ComparisonItem(v, True)
            i.msg = f'Missing in "{pre_name}"'
            self.model.appendRow(i)
        # check all items
        for i in [self.model.item(i) for i in range(self.model.rowCount())
                  if self.model.item(i).isCheckable()]:
            i.setCheckState(2)

    def clear(self) -> None:
        """Clears the visualisation list"""
        self.model.removeRows(0, self.model.rowCount())


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

    def __init__(self, name: str, lonely: bool) -> None:
        super(QStandardItem, self).__init__(name)
        self.name = name
        if lonely:
            self.state = self.LONELY
            self.setEnabled(False)
            self.setCheckable(False)
        else:
            self.state = self.QUEUED
            self.setCheckable(True)
        self.msg = ''


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
        font_metrics = QFontMetrics(option.font)
        rect = font_metrics.boundingRect(index.data())
        message_width = option.rect.width()-(rect.right()+30)
        message_bounds = QRectF(rect.right()+10+option.rect.height(),
                                option.rect.top(), message_width, option.rect.height())
        # if processing render the loading animation
        if item.state == ComparisonItem.PROCESSING:
            icon_bounds = QRectF(rect.right()+10, option.rect.top()+2,
                                 option.rect.height()-4, option.rect.height()-4)
            self.loading.render(painter, icon_bounds)
        # otherwise just paint the success/failure icon and message
        else:
            if item.state == ComparisonItem.SUCCESS:
                pixmap = self.success.scaled(option.rect.height()-4,
                                             option.rect.height()-4,
                                             Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if item.state in [ComparisonItem.FAILURE,
                              ComparisonItem.LONELY]:
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
            if item.state != ComparisonItem.QUEUED:
                painter.drawPixmap(QPoint(rect.right()+10,
                                          option.rect.top()+2), pixmap)


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
        # get max width for container in ComparisonWidget
        self.maxWidth = self.columnWidth(0) + 150

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
        self.options_container.setMaximumWidth(self.options.maxWidth)
        # signals
        self.pre_dropdown.currentIndexChanged.connect(
            self.name_desc_manager)
        self.post_dropdown.currentIndexChanged.connect(
            self.name_desc_manager)

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
        print(
            f'common: {common}\npre_only: {pre_only}\npost_only: {post_only}')
        self.comp_list.create(self.pre_dropdown.currentText(),
                              self.post_dropdown.currentText(),
                              common, pre_only, post_only)
