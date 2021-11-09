from dataclasses import dataclass, field
import os
from typing import List, Tuple
import numpy as np
import pandas as pd
import validation
import warnings

@dataclass
class Visualisation:
    """CORD Visualisation in python friendly format"""
    data: dict = field(init=False, repr=False)
    meta: dict = field(init=False, repr=False)
    info: dict = field(init=False, repr=False)
    name: str = field(init=False)
    filepath: str

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
            periods.append(validation.validate_date(date))
        return periods


    def _retrieve_markers(self) -> List[tuple]:
        """Find start and end indices that will later be used to slice
        the visualisation into parts. Returns list of tuples containing
        the start and end indices for each slice."""
        df = self.info['prelim_df']
        date = df.loc[df[0].str.contains(',Date', na=False)].index.tolist()
        criteria = df.loc[df[0].str.contains('Criteria: ', na=False)].index.tolist()
        markers = [(0, date[0]-1)] # initialize markers with metadata
        # create markers for each periodicity of data within csv
        for i, d in enumerate(date):
            # if its the last section dont expect a criteria marker
            if d == date[-1]:
                last = len(df.index)-1 # -1 because pandas counts from 0
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
            dates = self.info['prelim_df'].loc[x+1,0].rstrip(',').split(',')
            # remove any quotations
            dates = [date.replace('"', '') for date in dates]
            # filter out any empty items
            dates = list(filter(lambda date: date != '', dates))
            master_list.append(dates) # add to master list
        return master_list

    def _retrieve_dimensions(self) -> List[str]:
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
        self.info['dimensions'] = self._retrieve_dimensions()
        # get the periodicities in the order they appear
        self.info['periodicities'] = self._determine_periodicity()

    def _read_meta(self):
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
        for item in meta_series:
            if store:
                # get criteria and value from line
                criteria, value = item.split(',')
                # store them in nested dict
                coverage[criteria] = value.replace('"', '')
            # activate store once "Coverage Descriptors" is found
            if item == "Coverage Descriptors": store = True
        self.meta['Coverage'] = coverage

    def _create_data(self) -> pd.DataFrame:
        """Reads the visualisation in explicit slices to create self.data,
        a dict of dataframes with their periods as the keys."""
        self.data = dict() # init data dict
        # ignore data loss warnings if file has been modified
        if self.info['modified']:
            # we're not actually losing data, it's just the extra commas 
            # added in by excels saving format
            warnings.simplefilter(action='ignore',
                category=pd.errors.ParserWarning)
        # create a dataframe for each periodicity of data
        for i, per in enumerate(self.info['periodicities']):
            # get start and end markers (skipping meta marker with +1)
            start, end = self.info['markers'][i+1]
            start += 2 # +2 to get where data starts
            # create names
            names = self.info['dimensions'] + self.info['dates'][i]
            # create dtypes list
            # catagory type uses far less memory than str type
            dtype_list = (['category']*len(self.info['dimensions']))+\
                (['float64']*len(self.info['dates'][i]))
            # read the data slice
            df = pd.read_csv(self.filepath,
                encoding='unicode_escape', header=None, skiprows=start,
                nrows=end-start+1, skip_blank_lines=False, index_col=False,
                names=names, dtype=dict(zip(names, dtype_list)),
                keep_default_na=False, na_values=['.','NULL',''])

            #forward fill the dimension columns
            df[self.info['dimensions']] = df[self.info['dimensions']].ffill()
            # set dimension columns as index
            df.set_index(self.info['dimensions'], inplace=True)

            self.data[per] = df
        
        # stop ignoring any parser warnings
        warnings.simplefilter(action='default', 
            category=pd.errors.ParserWarning)

    def __post_init__(self) -> None:
        """Main setup for the Visualisation object"""
        validation.validate_csv(self.filepath) # validate file is a csv
        self.name = os.path.basename(self.filepath).split('.')[0]
        # TODO show through UI
        # create info through a preliminary read
        self._prelim_read()
        # determine if file has been modified
        self.info['modified'] = self._determine_modified()
        if self.info['modified']: print("File has been modified in excel")
        # create the metadata dict
        self._read_meta()
        # create the data dict
        self._create_data()
        

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