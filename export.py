from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import os
from typing import Any
from util import MetaDict, StandardFormats, Switch, TempFile
from PyQt5.QtCore import QSettings, QObject,  QDate
from PyQt5.QtWidgets import QDateEdit, QTreeView
from PyQt5.QtGui import QStandardItem
from distutils.util import strtobool
import pandas as pd
import numpy as np
import xlsxwriter


class ExportOptionAction(Enum):
    NONE = auto()
    TOGGLE = auto()
    DATE = auto()


@dataclass
class ExportOption():
    text: str
    action: ExportOptionAction
    default_value: Any = False
    parent: Any = None
    setting: str = field(init=False, repr=False)
    item: QStandardItem = field(init=False, repr=False)
    placeholder_item: QStandardItem = field(init=False, repr=False)
    widget: QObject = field(init=False, repr=False)

    def __post_init__(self):
        self.setting = f'ExpOpt_{self.text}'
        self.item = QStandardItem(self.text)
        self.placeholder_item = QStandardItem()

    @property
    def value(self):
        if self.action == ExportOptionAction.NONE:
            return
        if self.action == ExportOptionAction.TOGGLE:
            val = QSettings().value(self.setting, self.default_value)
            if type(val) is str:
                return strtobool(val)
            elif type(val) is bool:
                return val
            else:
                raise TypeError(
                    f'{self.setting} has val: {val} of incorrect type: {type(val)}')
        if self.action == ExportOptionAction.DATE:
            return QSettings().value(
                self.setting, self.default_value)

    def set_widget(self) -> None:
        """Creates the widget based on the ExportOptionAction"""
        if self.action == ExportOptionAction.TOGGLE:
            switch = Switch()
            switch.setMaximumSize(switch.sizeHint())
            if self.value:
                switch.setChecked(True)
            # connect switch toggle to QSetting
            switch.toggled.connect(lambda: QSettings().setValue(
                self.setting, switch.isChecked()))
            self.widget = switch
        if self.action is ExportOptionAction.DATE:
            date = QDateEdit()
            date.setDisplayFormat('MMM yyyy')
            date.setMaximumSize(120, date.sizeHint().height())
            # connect Date to QSetting
            date.setDate(self.value)
            date.dateChanged.connect(lambda: QSettings().setValue(
                self.setting, date.date()))
            self.widget = date

    def add_to_tree(self, tree: QTreeView) -> None:
        """Add the export option to a QTreeView given by 'tree' under
        an optional parent QStandardItem. If parent is None then the 
        ExportOption will be added to the root."""
        self.set_widget()
        if self.parent:  # if a parent is given in creation
            # add new item as child
            self.parent.item.appendRow([self.item, self.placeholder_item])
            # if parent is togglable, set child enabled/disabled based on parent
            if self.parent.action is ExportOptionAction.TOGGLE:
                self.toggle_row_state(self.parent.widget.isChecked())
                self.parent.widget.toggled.connect(
                    lambda: self.toggle_row_state(self.parent.widget.isChecked()))
        else:  # otherwise add it as new root row
            tree.model.appendRow([self.item, self.placeholder_item])
        # add widget to column 2 if option has an action
        if self.action is not ExportOptionAction.NONE:
            tree.setIndexWidget(
                self.placeholder_item.index(), self.widget)

    def toggle_row_state(self, state: bool) -> None:
        """Disable/Enable a given row"""
        self.item.setEnabled(state)
        self.widget.setEnabled(state)
        # turn child TOGGLE widget to False if parent is false
        if self.action is ExportOptionAction.TOGGLE:
            if not self.parent.widget.isChecked():
                self.widget.setChecked(False)
        self.placeholder_item.setEnabled(state)

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return self.value


class ExportOptions(object):
    """Object class where export options can be added and removed"""
    sheets = ExportOption("Sheets", ExportOptionAction.NONE)
    pre_sheet = ExportOption(
        "Pre-change data", ExportOptionAction.TOGGLE, parent=sheets)
    post_sheet = ExportOption(
        "Post-change data", ExportOptionAction.TOGGLE, parent=sheets)
    meta_sheet = ExportOption(
        "MetaData", ExportOptionAction.TOGGLE, default_value=True,
        parent=sheets)
    analysis = ExportOption("Analysis Columns", ExportOptionAction.NONE)
    total_diff = ExportOption(
        "Total Difference", ExportOptionAction.TOGGLE, parent=analysis)
    total_abs_diff = ExportOption(
        "Total ABS Difference", ExportOptionAction.TOGGLE, parent=analysis)
    max_abs_diff = ExportOption(
        "Max ABS Difference", ExportOptionAction.TOGGLE, parent=analysis)
    max_abs_perc_diff = ExportOption(
        "Max ABS % Difference", ExportOptionAction.TOGGLE, parent=analysis)
    max_abs_diff_date = ExportOption(
        "Max ABS Difference Date", ExportOptionAction.TOGGLE, parent=analysis)
    missing_data = ExportOption(
        "Missing Data", ExportOptionAction.TOGGLE, parent=analysis,
        default_value=True)
    date_filter = ExportOption("Filter dates", ExportOptionAction.TOGGLE)
    date_filter_from = ExportOption(
        "From: ", ExportOptionAction.DATE, default_value=QDate(1997, 1, 1),
        parent=date_filter)
    date_filter_to = ExportOption(
        "To: ", ExportOptionAction.DATE, default_value=QDate.currentDate(),
        parent=date_filter)
    skip_no_diffs = ExportOption(
        "Skip exporting if no differences", ExportOptionAction.TOGGLE,
        default_value=True)
    excl_zero_series = ExportOption(
        "Exclude series with no differences", ExportOptionAction.TOGGLE,
        parent=skip_no_diffs)


class Export():
    """"""

    def __init__(self, desc: list, pre: str, post: str,
                 export_folder: str, item) -> None:
        self.desc = desc
        self.pre = pre
        self.post = post
        self.exp_fol = export_folder
        self.item = item
        self.comp_path = f'comparisons/{pre} vs {post}/{item.name}'
        self.meta = MetaDict(self.comp_path)
        self.options = ExportOptions()

    @property
    def should_skip(self) -> bool:
        """Decide whether or not to skip exporting based on difference
        meta data and user settings"""
        if not self.meta['differences'] and self.options.skip_no_diffs():
            return True
        else:
            return False

    def export(self):
        """Export the comparison data to an xlsx file using user 
        specified settings."""
        self.wb = xlsxwriter.Workbook(f'{self.exp_fol}/{self.item.name}.xlsx')
        self._create_formats()
        # keep track of whether or not we've written anything to the file
        self.written = False
        for per in self.meta['periodicities']:
            per_path = f'{self.comp_path}/{per}'
            # if skip_no_diffs option is checked and the periodicity
            # has no differences then skip exporting it
            if self.options.skip_no_diffs() and \
                    not MetaDict(per_path)['different']:
                continue
            # if it does have differences then read and process the pre and
            # post dataframes then check again for differences as they may
            # not have differences within the filtered dates.
            pre = self._read_vis(
                f'positions/{self.pre}/{self.item.name}/{per}')
            post = self._read_vis(
                f'positions/{self.post}/{self.item.name}/{per}')
            post = self._process_vis(post, per)
            pre = self._process_vis(pre, per)
            if self.options.date_filter() and self.options.skip_no_diffs() and \
                    not self._has_differences(pre, post):
                continue
            diff, nans = self._get_compared(per_path)
            pre, post, diff = self._process_comparison(
                pre, post, diff, nans, per)
            if self.options.pre_sheet():
                self._write_sheet(f'{self.pre} ({per})',
                                  pre, self.pre_style)
            if self.options.post_sheet():
                self._write_sheet(f'{self.post} ({per})',
                                  post, self.post_style)
            self._write_sheet(f'Differences ({per})', diff, self.diff_style,
                              difference=True)
            if self.options.meta_sheet():
                self._write_meta()
        self.wb.close()
        # if nothing has been written in the file, delete it
        if not self.written:
            os.remove(f'{self.exp_fol}/{self.item.name}.xlsx')

    def _create_formats(self) -> None:
        """Creates the formats and styling for the output Excel sheet."""
        self.idx_format = self.wb.add_format({
            'bold': True,
            'align': 'center'})
        self.missing_pre_format = self.wb.add_format({
            'italic': True,
            'font_color': '#3B9CB7',
            'bg_color': '#daeef3',
            'border': 2,
            'border_color': '#3B9CB7',
            'align': 'center'})
        self.missing_series_pre_format = self.wb.add_format({
            'italic': True,
            'font_color': '#3B9CB7',
            'bg_color': '#daeef3',
            'align': 'center'})
        self.missing_post_format = self.wb.add_format({
            'italic': True,
            'font_color': '#F6882E',
            'bg_color': '#fde9d9',
            'border': 2,
            'border_color': '#F6882E',
            'align': 'center'})
        self.missing_series_post_format = self.wb.add_format({
            'italic': True,
            'font_color': '#F6882E',
            'bg_color': '#fde9d9',
            'align': 'center'})
        self.meta_idx_format = self.wb.add_format({
            'bold': True,
            'align': 'right'})
        self.meta_val_format = self.wb.add_format({
            'bold': False,
            'align': 'left',
            'num_format': 'd/m/yyyy, hh:MM AM/PM'})
        self.meta_pre_idx_format = self.wb.add_format({
            'bold': True,
            'font_color': '#3B9CB7',
            'bg_color': '#daeef3',
            'align': 'right'})
        self.meta_pre_val_format = self.wb.add_format({
            'bold': False,
            'font_color': '#3B9CB7',
            'bg_color': '#daeef3',
            'align': 'left',
            'num_format': 'd/m/yyyy, hh:MM AM/PM'})
        self.meta_post_idx_format = self.wb.add_format({
            'bold': True,
            'font_color': '#F6882E',
            'bg_color': '#fde9d9',
            'align': 'right'})
        self.meta_post_val_format = self.wb.add_format({
            'bold': False,
            'font_color': '#F6882E',
            'bg_color': '#fde9d9',
            'align': 'left',
            'num_format': 'd/m/yyyy, hh:MM AM/PM'})

        self.pre_style = 'Table Style Medium 6'
        self.post_style = 'Table Style Medium 7'
        self.diff_style = 'Table Style Medium 1'

    def _read_vis(self, path: str) -> pd.DataFrame:
        """Read a visualisation dataframe from the .opticord file at the
        given path."""
        TempFile.manager.lockForWrite()
        df = pd.read_hdf(TempFile.path, path)
        TempFile.manager.unlock()
        # Best to fill the nan values with '.' now for excel writing
        return df.fillna('.')

    def _has_differences(self, pre: pd.DataFrame, post: pd.DataFrame) -> bool:
        """Returns true if differences are found between pre and post,
        false if not."""
        # use pandas testing assertion to check for any differences
        # e.g. in shape, index/columns and values
        try:
            pd.testing.assert_frame_equal(pre, post, check_like=True)
            return False
        except AssertionError:
            return True

    def _get_compared(self, path: str) -> tuple:
        """Read the comparison data dataframe as well as the nans dataframe
        from the .opticord file base at the given path.
        Returns both as pandas dataframes in a tuple (diff, nans)."""
        TempFile.manager.lockForWrite()
        diff = pd.read_hdf(TempFile.path, f'{path}/data')
        nans = pd.read_hdf(TempFile.path, f'{path}/nans')
        TempFile.manager.unlock()
        return diff, nans

    def _process_vis(self, df: pd.DataFrame, per: str) -> pd.DataFrame:
        """Processes visualisation data and returns it ready to be written
        in a sheet."""
        if self.options.date_filter():
            df = self._apply_date_filter(df)
        df = self._convert_columns(df, per)
        return df

    def _process_comparison(self, pre: pd.DataFrame, post: pd.DataFrame,
                            diff: pd.DataFrame, nans: pd.DataFrame,
                            per: str) -> pd.DataFrame:
        """Processes the comparison data and returns it ready to be written
        in a sheet."""
        if self.options.date_filter():
            diff = self._apply_date_filter(diff)
            nans = self._apply_date_filter(nans)
        diff = self._convert_columns(diff, per)
        nans = self._convert_columns(nans, per)
        # add the analysis columns to the index
        diff = self._add_analysis(pre, post, diff)
        # recombine difference and configured nans dataframes
        diff[diff.isna()] = nans
        # add missing data col, only possible after nans have been replaced
        if self.options.missing_data():
            diff = self._add_missing_data_col(diff)
        if self.options.excl_zero_series():
            pre, post, diff = self._drop_zero_series(pre, post, diff)
        return pre, post, diff

    def _drop_zero_series(self, pre: pd.DataFrame, post: pd.DataFrame,
                          diff: pd.DataFrame) -> tuple:
        """Returns pre, post and diff dataframes with series that have no
        differences removed."""
        # get the index names that aren't in pre or post dataframes
        extra_idxs = [
            col for col in diff.index.names if col not in post.index.names]
        # make a new version of diff with the extra idxs removed
        search_diff = diff.reset_index().drop(extra_idxs, axis=1)
        search_diff = search_diff.set_index(post.index.names).replace('.', 0.0)
        # search through modified diff to find idxs of rows that have no diffs
        idxs_to_drop = search_diff[(search_diff == 0.0).all(axis=1)].index
        # remove the modified diff df from memory
        del(search_diff)
        # search through the normal diff to find idxs of rows without diffs
        diff_idxs_to_drop = diff[(diff.replace(
            '.', 0.0) == 0.0).all(axis=1)].index
        # drop the rows with no differences
        pre = pre.drop(idxs_to_drop)
        post = post.drop(idxs_to_drop)
        diff = diff.drop(diff_idxs_to_drop)
        return pre, post, diff

    def _apply_date_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop all dates from the given dataframe outside of the 
        user specified range."""
        df.columns = pd.to_datetime(df.columns)
        date_from = self.options.date_filter_from().toPyDate()
        date_to = self.options.date_filter_to().toPyDate()
        df = df[[c for c in df.columns if c >= date_from and c <= date_to]]
        return df

    def _add_missing_data_col(self, df: pd.DataFrame) -> pd.DataFrame:
        """Creates the "Missing Data" analysis columns and adds it to the
        given dataframe. Must be done after df has configured nans as it
        relies on their string values to tell where the data is missing."""
        # stack the dataframe and cast values to type str
        # this turns the dataframe into a series and allows us to use .str
        stacked = df.astype(str).stack()
        # Find values which match the appropriate missing data string. Cells
        # where a match was found will be True, everywhere else will be False.
        # Replace the False values with np.nan and drop them from the series.
        # Unstack the dataframe otherwise the date column will be an index,
        # this leaves us with the index of the original df where all rows that
        # do not contain a match of the desired string have been dropped.
        missing_pre = stacked.str.match(
            f'Missing in {self.pre}').replace(
            False, np.nan).dropna().unstack().index
        missing_post = stacked.str.match(
            f'Missing in {self.post}').replace(
            False, np.nan).dropna().unstack().index
        series_missing_pre = stacked.str.match(
            f'Series not in {self.pre}').replace(
            False, np.nan).dropna().unstack().index
        series_missing_post = stacked.str.match(
            f'Series not in {self.post}').replace(
            False, np.nan).dropna().unstack().index
        # get the index for both from the intersection of the missing_pre/post
        missing_both = missing_pre.intersection(missing_post)
        # By default the value of missing data will be None
        df['Missing Data'] = 'None'
        # The below sets the value of Missing data in an if elif fashion so
        # order is important.
        df.loc[missing_pre, 'Missing Data'] = self.pre
        df.loc[missing_post, 'Missing Data'] = self.post
        df.loc[series_missing_pre, 'Missing Data'] = self.pre
        df.loc[series_missing_post, 'Missing Data'] = self.post
        df.loc[missing_both, 'Missing Data'] = 'BOTH'
        # return the dataframe with missing data set as an index
        return df.set_index('Missing Data', append=True)

    def _convert_columns(self, df: pd.DataFrame, per: str) -> pd.DataFrame:
        """Converts the columns in a dataframe for datetime to
        string format based on the periodicity per and returns the
        dataframe."""
        # ensure columns are of datetime format
        df.columns = df.columns.astype('datetime64[ns]')
        # convert them to strings
        if per == "A":
            df.columns = df.columns.strftime("%Y")
        if per == "Q":
            df.columns = df.columns.to_period("Q").astype(str)
        if per == "M":
            df.columns = df.columns.strftime("%Y%b")
        return df

    def _add_analysis(self, pre: pd.DataFrame, post: pd.DataFrame,
                      diff: pd.DataFrame) -> None:
        """Adds all analysis columns selected by user to the given
        dataframe 'df' and returns it."""
        analysis = pd.DataFrame()

        if self.options.total_diff():
            analysis['Total Diff'] = diff.sum(axis=1)
        if self.options.total_abs_diff():
            analysis['Total ABS Diff'] = diff.abs().sum(axis=1)
        if self.options.max_abs_diff():
            analysis['Max ABS Diff'] = diff.abs().max(axis=1)
        if self.options.max_abs_perc_diff():
            analysis['Max ABS % Diff'] = diff.div(
                pre.replace('.', np.nan)
            ).fillna(0.0).mul(100).abs().max(axis=1).round(1)
        if self.options.max_abs_diff_date():
            analysis['Max ABS Diff Date'] = diff.abs().idxmax(
                axis=1)
        # tidy up analysis before adding to diff
        analysis = analysis.fillna('').replace(np.inf, 'inf')
        # better for performance to add new columns to a small dataframe
        # and then concatenate all at once to the large dataframe.
        diff = pd.concat((analysis, diff), axis=1)
        diff = diff.set_index(analysis.columns.tolist(), append=True)
        return diff

    def _write_sheet(self, name: str, df: pd.DataFrame,
                     table_style: str = 'Table Style Medium 1',
                     difference: bool = False) -> None:
        """Creates a new sheet with given name and writes 'df' as a 
        formatted table."""
        def _format() -> list:
            format_list = []
            for idx in df.index.names:
                options = dict()
                options['header'] = idx
                options['format'] = self.idx_format
                format_list.append(options)
            for col in df.columns:
                options = dict()
                options['header'] = col
                format_list.append(options)
            return format_list

        def _set_col_widths():
            for i, col in enumerate(df.columns.tolist()):
                # width is dynamic but has max of 16 and min of 8
                width = min(max(len(col) + 3, 8), 16)
                ws.set_column(i, i, width)

        def _conditional_formatting():
            ws.conditional_format(1, len(idx_cols), nrows, ncols,
                                  {'type': '3_color_scale',
                                   'min_color': 'red',
                                   'max_color': 'green',
                                   'mid_color': 'white'})
            ws.conditional_format(1, len(idx_cols), nrows, ncols,
                                  {'type': 'cell',
                                   'criteria': 'equal to',
                                   'value': f'"Date not in {self.pre}"',
                                   'format': self.missing_series_pre_format})
            ws.conditional_format(1, len(idx_cols), nrows, ncols,
                                  {'type': 'cell',
                                   'criteria': 'equal to',
                                   'value': f'"Series not in {self.pre}"',
                                   'format': self.missing_series_pre_format})
            ws.conditional_format(1, len(idx_cols), nrows, ncols,
                                  {'type': 'cell',
                                   'criteria': 'equal to',
                                   'value': f'"Missing in {self.pre}"',
                                   'format': self.missing_pre_format})
            ws.conditional_format(1, len(idx_cols), nrows, ncols,
                                  {'type': 'cell',
                                   'criteria': 'equal to',
                                   'value': f'"Date not in {self.post}"',
                                   'format': self.missing_series_post_format})
            ws.conditional_format(1, len(idx_cols), nrows, ncols,
                                  {'type': 'cell',
                                   'criteria': 'equal to',
                                   'value': f'"Series not in {self.post}"',
                                   'format': self.missing_series_post_format})
            ws.conditional_format(1, len(idx_cols), nrows, ncols,
                                  {'type': 'cell',
                                   'criteria': 'equal to',
                                   'value': f'"Missing in {self.post}"',
                                   'format': self.missing_post_format})

        self.written = True
        ws = self.wb.add_worksheet(name)
        table_name = name.replace(' ', '_').replace('(', '').replace(')', '')
        column_format = _format()
        idx_cols = df.index.names
        df = df.reset_index()
        nrows, ncols = df.values.shape
        ws.add_table(0, 0, nrows, ncols-1, {
            'name': table_name,
            'columns': column_format,
            'data': df.values,
            'style': table_style
        })
        _set_col_widths()
        if difference:
            _conditional_formatting()
        ws.freeze_panes(1, len(idx_cols))

    def _write_meta(self) -> None:
        """Write the metadata sheet for the comparison."""
        pre_meta = MetaDict(f'positions/{self.pre}/{self.item.name}')
        post_meta = MetaDict(f'positions/{self.post}/{self.item.name}')
        ws = self.wb.add_worksheet('MetaData')
        r = 0
        ws.write(r, 0, 'OptiCORD File:', self.meta_idx_format)
        ws.write(r, 1, TempFile.saved_path, self.meta_val_format)
        r += 1
        ws.write(r, 0, 'Exported By:', self.meta_idx_format)
        ws.write(r, 1, os.getlogin(), self.meta_val_format)
        r += 1
        ws.write(r, 0, 'Exported:', self.meta_idx_format)
        ws.write_datetime(r, 1, datetime.now(), self.meta_val_format)
        r += 1
        ws.write(r, 0, 'Description:', self.meta_idx_format)
        for line in self.desc:
            ws.write(r, 1, line, self.meta_val_format)
            r += 1
        r += 1
        ws.write(r, 0, 'Pre Position:', self.meta_pre_idx_format)
        ws.write(r, 1, self.pre, self.meta_pre_val_format)
        ws.write(r, 3, 'Post Position:', self.meta_post_idx_format)
        ws.write(r, 4, self.post, self.meta_post_val_format)
        r += 1

        def _write_pos_meta(sub_r: int, col: int, pos: dict,
                            idx_format, val_format) -> None:
            # order that the metadata will be written
            order = ['Downloaded', 'Statistical Activity', 'Mode',
                     'Status', 'Dataset', 'Dimensions', 'Periodicities']
            # create a new ordered dictionary based on the above
            ordered = dict()
            for o in order:
                if o in pos.keys():
                    ordered[o] = pos.pop(o)
            # ensure any extra metadata items are added
            for key, val in pos.items():
                ordered[key] = val
            # write items from the  ordered dictionary
            for key, val in ordered.items():
                key += ':'
                ws.write(sub_r, col, key, idx_format)
                if type(val) is np.ndarray:
                    val = val.tolist()
                if type(val) is dict:
                    ws.write(sub_r, col+1, '', val_format)
                    for sub_key, sub_val in val.items():
                        sub_r += 1
                        ws.write(sub_r, col, sub_key, idx_format)
                        ws.write(sub_r, col+1, sub_val, val_format)
                elif type(val) is list:
                    ws.write(sub_r, col+1, (', '.join(val)), val_format)
                elif type(val) is datetime:
                    ws.write_datetime(sub_r, col+1, val, val_format)
                else:
                    ws.write(sub_r, col+1, val, val_format)
                sub_r += 1

        _write_pos_meta(r, 0, pre_meta, self.meta_pre_idx_format,
                        self.meta_pre_val_format)
        _write_pos_meta(r, 3, post_meta, self.meta_post_idx_format,
                        self.meta_post_val_format)

        ws.set_column(0, 0, width=25)
        ws.set_column(1, 1, width=40)
        ws.set_column(3, 3, width=25)
        ws.set_column(4, 4, width=40)


"""
# I attempted to add the analysis columns in as Excel formulas but unfortunately
# Excel was automatically adding in an "@" before the table name which
# broke most formulas. The below forumlas are all correct and working if entered
# manually into Excel. The columns can be added to the sheet if they are added
# to the formatting options dict and given extra columns in the table.
# More info here: https://xlsxwriter.readthedocs.io/working_with_tables.html
# Might be possible to fix using write_array_formula:
# Q. Why do my formulas have a @ in them?
# Microsoft refers to the @ in formulas as the Implicit Intersection Operator. 
# It indicates that an input range is being reduced from multiple values to a 
# single value. In some cases it is just a warning indicator and doesnt affect 
# the calculation or result. However, in practical terms it generally means that 
# your formula should be written as an array formula using either 
# write_array_formula() or write_dynamic_array_formula().

def _analysis_columns(self, table: str, df: pd.DataFrame) -> tuple:
        """"""
        cols = []
        start_col = df.columns.tolist()[0]
        end_col = df.columns.tolist()[-1]
        if self.options.total_diff():
            cols.append(AnalysisColumn(
                'Total Difference',
                f'=SUM({table}[@[{start_col}]:[{end_col}]])'))
        if self.options.total_abs_diff():
            cols.append(AnalysisColumn(
                'Total ABS Difference',
                f'=SUM(IF(ISNUMBER({table}[@[{start_col}]:[{end_col}]]),'
                f'ABS({table}[@[{start_col}]:[{end_col}]])))'))
        if self.options.max_abs_diff():
            cols.append(AnalysisColumn(
                'Max ABS Difference',
                f'=MAX(IF(ISNUMBER({table}[@[{start_col}]:[{end_col}]]),'
                f'ABS({table}[@[{start_col}]:[{end_col}]])))'))
        if self.options.max_abs_diff_date():
            cols.append(AnalysisColumn(
                'Max ABS Difference Date',
                f'=INDEX({table}[[#Headers],[{start_col}]:[{end_col}]],'
                f'MATCH(MAX(IF(ISNUMBER({table}[@[{start_col}]:[{end_col}]]),'
                f'ABS({table}[@[{start_col}]:[{end_col}]]))),'
                f'ABS({table}[@[{start_col}]:[{end_col}]]),0))'))
        for col in cols:
            df[col.header] = ''
        df = df.set_index([col.header for col in cols], append=True)
        return cols, df

@dataclass
class AnalysisColumn:
    header: str
    pandas: pd.Series
    excel: str"""
