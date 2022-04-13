
import os
import re
import pandas as pd


class InvalidVisualisation(Exception):
    """Raised when an file is tried to be read as a visualisation
    but does not meet some validation requirement"""

    def __init__(self, full, short) -> None:
        super().__init__(full)
        self.full = full
        self.short = short


def validate_filepath(filepath: str) -> None:
    """Validates that the filepath is of expected CORD format"""
    _, extension = os.path.splitext(filepath)
    if extension != ".csv":
        raise InvalidVisualisation(
            f'{filepath} has invalid extension: "{extension}"',
            'File is not a csv')
    visualisation_name = filepath.split('/')[-1]
    if not re.search('(.*?_\d\d\d\d\d\d_\d\d\d\d\d\d.csv)',
                     visualisation_name):
        raise InvalidVisualisation(f'Filename "{visualisation_name}" '
                                   'is not in the format of a downloaded CORD visualisation',
                                   'Invalid filename')


def validate_columns(df: pd.DataFrame) -> None:
    """Sense check that we captured all columns and no 
    extras from csv"""
    base = len(df.columns.tolist())
    dropped = len(df.dropna(axis='columns', how='all').columns.tolist())
    if base != dropped:
        raise InvalidVisualisation(f'Visualisation was read with {base}'
                                   f' columns but only {dropped} have data',
                                   'File format error')


def validate_date(date: str) -> str:
    """"""
    found = []
    # search the date using regex to determine periodicity
    if re.search('(\d\d\d\d)$', date):
        found.append('A')
    if re.search('(\d\d\d\dQ\d)$', date):
        found.append('Q')
    if re.search('(\d\d\d\d\w\w\w)$', date):
        found.append('M')
    if len(found) != 1:
        raise InvalidVisualisation(f'The format of the date: "{date}"'
                                   ' is not recognised', 'Invalid date header')
    return found[0]


def validate_meta(key: str, regex: str, meta_series: pd.Series) -> str:
    """Validates that a metadata object can be found with a single
    match
    Requires;
        key: metadata dict key
        regex: regex string used to find match
        meta_series: metadata series to find matches in
    Returns:
        match: a valid match
        otherwise raises Exception"""
    for text in meta_series:
        results = re.match(regex, text)
        if results:
            break  # break once results are found
    # raise error if no match is found
    if not results:
        raise InvalidVisualisation('Unable to match metadata for: '
                                   f'"{key}" in "{meta_series.tolist()}"',
                                   'Missing metadata')
    # if there's just a single match return the only group
    if len(results.groups()) == 1:
        match = results.group(1)
    else:  # otherwise return the first group which isn't None
        for i in range(len(results.groups())):
            if results.group(i+1) != None:
                match = results.group(i+1)
    return match


def validate_unique(vis: str, existing: str) -> None:
    """Validate that the passed visualisation 'vis' is the only 
    visualisation of its kind in the the list of existing 
    visualisations 'vis_list'"""
    if vis in existing:
        raise InvalidVisualisation(f'There is already a "{vis}" '
                                   'visualisation in this position. Delete the existing '
                                   'version in order to overwrite it.',
                                   'Visualisation already exists in position')
