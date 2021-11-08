""""""

import pandas as pd
import os
import re

class InvalidVisualisationFileType(Exception):
    """Raised when visualisation has wrong file type"""
    def __init__(self, extension: str) -> None:
        super().__init__(f'File has invalid extension: "{extension}"')

class InvalidVisualisationColumns(Exception):
    """Raised when csv is read with extra columns"""
    def __init__(self, base: int, dropped: int) -> None:
        super().__init__(f'Visualisation was read with {base}'
            f' columns but only {dropped} have data')

class InvalidDateFormat(Exception):
    """Raised when a date element is read with an unrecognised
    format"""
    def __init__(self, date: str) -> None:
        super().__init__(f'The format of the date: "{date}" is not'
            ' recognised')

class InvalidMetaNoMatch(Exception):
    """Raised when a metadata element is not found"""
    def __init__(self, key: str, series: pd.Series) -> None:
        super().__init__('Unable to metadata match for:'
            f' "{key}" in "{series.tolist()}"')

def validate_csv(filepath: str) -> None:
    """Validates whether or not a file is a csv"""
    _, file_extension = os.path.splitext(filepath)
    if file_extension != ".csv":
        raise InvalidVisualisationFileType(file_extension)

def validate_columns(df: pd.DataFrame) -> None:
    """Sense check that we captured all columns and no 
    extras from csv"""
    base = len(df.columns.tolist())
    dropped = len(df.dropna(axis='columns', how='all').columns.tolist())
    if base != dropped:
        raise InvalidVisualisationColumns(base, dropped)

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
        raise InvalidDateFormat(date)
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
        if results: break # break once results are found

    # raise error if no match is found
    if not results:
        raise InvalidMetaNoMatch(key, meta_series)
    
    # if there's just a single match return the only group
    if len(results.groups()) == 1:
        match = results.group(1)
    else: # otherwise return the first group which isn't None
        for i in range(len(results.groups())):
            if results.group(i+1) != None:
                match = results.group(i+1)
    return match