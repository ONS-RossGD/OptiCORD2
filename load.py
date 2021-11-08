from dataclasses import dataclass, field
import os
from typing import List, Tuple
import numpy as np
import pandas as pd
import validation

@dataclass
class Visualisation:
    """CORD Visualisation in python friendly format"""
    data: dict = field(init=False, repr=False)
    meta: str = field(init=False, repr=False)
    name: str = field(init=False)
    filepath: str

    def determine_modified(self, filepath: str):
        """Determines whether or not a csv file has been opened and saved
        in excel which changes the format from the default CORD format.
        Requires;
            filepath: filepath of csv to be read
        Return;
            True if file has been modified in excel
            False if file has not been modified"""
        # read the csv into a single column
        df = pd.read_csv(filepath, encoding='unicode_escape', 
                    header=None, names=[0], skip_blank_lines=False,
                    dtype=str, nrows=3, delimiter='|')
        # by CORD definition one line of the first 3 should be blank
        if not df.isnull().values.any():
            return True
        else:
            return False

    def determine_periodicity(self, filepath: str, info: dict) -> List[str]:
        """Determines the periodicity of a marked row of dates.
        Requires;
            filepath: filepath of csv to be read
            info: info dict containing markers
        Returns;
            periods: list of periodicities in file in order they appear"""
        periods = []
        # for each marked slice except first which is metadata
        for start, _ in info['markers'][1:]:
            # retrieve a date from the slice
            date = pd.read_csv(self.filepath, encoding='unicode_escape', 
                    header=None, skiprows=start+1, nrows=1, dtype=str)\
                    .dropna(axis='columns').iloc[0].tolist()[0]
            # validate that the date is of known format then add to list
            periods.append(validation.validate_date(date))
        return periods


    def retrieve_markers(self, df: pd.DataFrame) -> List[tuple]:
        """Find start and end indices that will later be used to slice
        the visualisation into parts
        Requires;
            df: the visualisation csv read as a single column
        Returns;
            markers: list of tuples containing the start and end indices
                for each slice"""
        dates = df.loc[df[0].str.contains(',Date', na=False)].index.tolist()
        criteria = df.loc[df[0].str.contains('Criteria: ', na=False)].index.tolist()
        markers = [(0, dates[0]-1)] # initialize markers with metadata
        # create markers for each periodicity of data within csv
        for i, d in enumerate(dates):
            # if its the last section dont expect a criteria marker
            if d == dates[-1]:
                markers.append((d, len(df.index)))
            # otherwise get end index from criteria marker
            else: # criteria[i+1] to ignore first criteria above date
                # TODO check this doesn't include the criteria line in slice
                markers.append((d, criteria[i+1]))
        return markers

    def retrieve_dates(self, prelim_df: pd.DataFrame,
        markers: List[tuple]) -> List[List[str]]:
        """Process rows from prelim_df that contain dates into
        a list of lists containing only the date values.
        Requires:
            prelim_df: the preliminary dataframe
            markers: list of slice markers
        Returns:
            master_list: List of lists containing the dates"""
        master_list = []
        # retrieve the lines containing dates using markers
        for x, _ in markers[1:]:
            # strip trailing commas then split by commas
            dates = prelim_df.loc[x+1,0].rstrip(',').split(',')
            # remove any quotations
            dates = [date.replace('"', '') for date in dates]
            # filter out any empty items
            dates = list(filter(lambda date: date != '', dates))
            master_list.append(dates) # add to master list
        return master_list

    def retrieve_dimensions(self, prelim_df: pd.DataFrame,
        markers: List[tuple]) -> List[str]:
        """Read rows from prelim_df that contain the dimension headers 
        and return a list of dimensions.
        Requires:
            prelim_df: the preliminary dataframe
            markers: list of slice markers
        Returns:
            dimensions: List of dimensions"""
        # retrieve the lines containing dates using markers
        for x, _ in markers[1:]:
            # strip trailing commas then split by commas
            dimensions = prelim_df.loc[x,0].rstrip(',').split(',')
            # remove any quotations
            dimensions = [dim.replace('"', '') for dim in dimensions]
            # filter out any empty items
            dimensions = list(filter(lambda dim: dim != '', dimensions))
            # remove the Date
            dimensions.remove('Date')
            print(dimensions)
        return dimensions

    def prelim_read(self, filepath: str) -> dict:
        """Preliminarily read the csv file as a much smaller dataframe
        to gather info for full read of dataframe
        Requires;
            filepath: filepath of csv to be read
        Returns;
            markers: index numbers of points to split dataframe as list
            num_of_rows: number of rows csv contains data for
            num_of_cols: number of columns csv contains data for"""
        # TODO add validation for structure of visualisation here
        # read the input csv as a single column
        info = dict()
        prelim_df = pd.read_csv(filepath, encoding='unicode_escape',
                delimiter='|', skip_blank_lines=False, header=None,
                dtype=str, names=[0])
        # gather marker points where dataframe will be sliced
        info['markers'] = self.retrieve_markers(prelim_df)
        # get the dates for each slice as a list
        info['dates'] = self.retrieve_dates(prelim_df, info['markers'])
        info['dimensions'] = self.retrieve_dimensions(prelim_df, info['markers'])
        del prelim_df # clear the prelim df from memory
        # get the periodicities in the order they appear
        info['periodicities'] = self.determine_periodicity(filepath, info)
        print(info)
        return info

    def read_meta(self, filepath: str, info: dict):
        """Read the metadata from the top of the visualisation file.
        Requires: 
            filepath: filepath of csv to be read
        Returns:
            meta: dict of metadata from visualisation"""
        meta = dict()
        _, end = info['markers'][0]
        # read the csv into a single column
        df = pd.read_csv(filepath, encoding='unicode_escape', 
                header=None, nrows=end, skip_blank_lines=False,
                dtype=str, delimiter='|')
        meta_series = df[0].str.rstrip(',').replace('',np.nan)\
            .dropna().reset_index(drop=True)
        del df # remove df from memory
        # validate_meta for instances where line contains more info
        # than required
        meta['Stat Act'] = validation.validate_meta('Stat Act', 
            'Statistical Activity = (.*?)$', meta_series)
        dataset_mode = validation.validate_meta('Dataset:Mode',
            '.*?Dataset:(.*?),', meta_series)
        meta['Dataset'] = (':').join(dataset_mode.split(':')[:-1])
        meta['Mode'] = dataset_mode.split(':')[-1]
        meta['Status'] = validation.validate_meta('Status', 
            '.*?Status:(.*?),|.*?Status:(.*?)$', meta_series)
        coverage = dict() # init a dict to be nested
        store = False # store toggle will activate in correct section
        for r, item in enumerate(meta_series):
            if store:
                # get criteria and value from line
                criteria, value = item.split(',')
                # store them in nested dict
                coverage[criteria] = value.replace('"', '')
            # activate store once "Coverage Descriptors" is found
            if item == "Coverage Descriptors": store = True
        meta['Coverage'] = coverage
        return meta

    def read_data_slice(self, filepath: str, start: int,
        end: int, columns: int) -> pd.DataFrame:
        """"""
        df = pd.read_csv(filepath, encoding='unicode_escape', 
                header=None, nrows=end-start, skip_blank_lines=False,
                dtype=str)

    def read(self, filepath: str):
        """"""
        modified = self.determine_modified(filepath)
        # TODO show through UI
        if modified: print("File has been modified in excel")
        # get info through a preliminary read
        info = self.prelim_read(filepath)
        # obtain the metadata
        self.meta = self.read_meta(filepath, info)

    def __post_init__(self) -> None:
        """"""
        validation.validate_csv(self.filepath) # validate file is a csv
        self.name = os.path.basename(self.filepath).split('.')[0]
        self.read(self.filepath)

class DataRegistry:
    """Registry to hold all imported data"""
    register: dict

    def __init__(self) -> None:
        """"""
        self.register = {}

    def read(self, file: str) -> bool:
        """"""
        vis = Visualisation(file)
        self.register[vis.name] = vis