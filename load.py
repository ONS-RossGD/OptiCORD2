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
    meta: dict = field(init=False, repr=False)
    info: dict = field(init=False, repr=False)
    name: str = field(init=False)
    filepath: str

    def determine_modified(self):
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

    def determine_periodicity(self) -> List[str]:
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
            periods.append(validation.validate_date(date))
        return periods


    def retrieve_markers(self) -> List[tuple]:
        """Find start and end indices that will later be used to slice
        the visualisation into parts. Returns list of tuples containing
        the start and end indices for each slice."""
        df = self.info['prelim_df']
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

    def retrieve_dates(self) -> List[List[str]]:
        """Process rows from prelim_df that contain dates into
        a list of lists containing only the date values."""
        master_list = []
        # retrieve the lines containing dates using markers
        for x, _ in self.info['markers'][1:]:
            # strip trailing commas then split by commas
            dates = self.info['prelim_df'].loc[x+1,0].rstrip(',').split(',')
            # remove any quotations
            dates = [date.replace('"', '') for date in dates]
            # filter out any empty items
            dates = list(filter(lambda date: date != '', dates))
            master_list.append(dates) # add to master list
        return master_list

    def retrieve_dimensions(self) -> List[str]:
        """Read rows from prelim_df that contain the dimension headers 
        and return a list of dimensions."""
        # retrieve the lines containing dates using markers
        for x, _ in self.info['markers'][1:]:
            # strip trailing commas then split by commas
            dimensions = self.info['prelim_df'].loc[x,0].rstrip(',').split(',')
            # remove any quotations
            dimensions = [dim.replace('"', '') for dim in dimensions]
            # filter out any empty items
            dimensions = list(filter(lambda dim: dim != '', dimensions))
            # remove the Date
            dimensions.remove('Date')
        return dimensions

    def prelim_read(self) -> dict:
        """Preliminarily read the csv file as a much smaller dataframe
        to gather info for full read of dataframe."""
        # TODO add validation for structure of visualisation here
        # read the input csv as a single column
        self.info = dict()
        self.info['prelim_df'] = pd.read_csv(self.filepath,
            encoding='unicode_escape', delimiter='|',
            skip_blank_lines=False, header=None, dtype=str, names=[0])
        # gather marker points where dataframe will be sliced
        self.info['markers'] = self.retrieve_markers()
        # get the dates for each slice as a list
        self.info['dates'] = self.retrieve_dates()
        self.info['dimensions'] = self.retrieve_dimensions()
        # get the periodicities in the order they appear
        self.info['periodicities'] = self.determine_periodicity()

    def read_meta(self):
        """Read the metadata from the top of the visualisation file."""
        self.meta = dict()
        _, end = self.info['markers'][0]
        # read the csv into a single column
        df = pd.read_csv(self.filepath, encoding='unicode_escape', 
                header=None, nrows=end, skip_blank_lines=False,
                dtype=str, delimiter='|')
        meta_series = df[0].str.rstrip(',').replace('',np.nan)\
            .dropna().reset_index(drop=True)
        del df # remove df from memory
        # validate_meta for instances where line contains more info
        # than required
        self.meta['Stat Act'] = validation.validate_meta('Stat Act', 
            'Statistical Activity = (.*?)$', meta_series)
        dataset_mode = validation.validate_meta('Dataset:Mode',
            '.*?Dataset:(.*?),', meta_series)
        self.meta['Dataset'] = (':').join(dataset_mode.split(':')[:-1])
        self.meta['Mode'] = dataset_mode.split(':')[-1]
        self.meta['Status'] = validation.validate_meta('Status', 
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
        self.meta['Coverage'] = coverage

    def __post_init__(self) -> None:
        """Main setup for the Visualisation object"""
        validation.validate_csv(self.filepath) # validate file is a csv
        self.name = os.path.basename(self.filepath).split('.')[0]
        modified = self.determine_modified()
        # TODO show through UI
        if modified: print("File has been modified in excel")
        # create info through a preliminary read
        self.prelim_read()
        # create the metadata dict
        self.read_meta()

class DataRegistry:
    """Registry to hold all imported data"""
    register: dict

    def __init__(self) -> None:
        """"""
        self.register = {}

    def open(self, file: str) -> bool:
        """"""
        vis = Visualisation(file)
        self.register[vis.name] = vis