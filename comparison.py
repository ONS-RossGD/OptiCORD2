from abc import ABC, abstractmethod
import logging
import pandas as pd
import h5py
import warnings
from util import MetaDict, TempFile
log = logging.getLogger('OptiCORD')


class InvalidComparison(Exception):
    """Raised when a comparison cannot be made between pre and post"""

    def __init__(self, full, short) -> None:
        super().__init__(full)
        self.full = full
        self.short = short


class Comparison(ABC):
    """Abstract base class for all comparisons. Ensures a valid comparison
    can be made no matter the method."""

    def __init__(self, pre_position: str, post_position: str, item) -> None:
        self.pre_position = pre_position
        self.post_position = post_position
        self.item = item
        self.vis = item.name
        self.differences = False
        self.pre_path = f'positions/{pre_position}/{self.vis}'
        self.post_path = f'positions/{post_position}/{self.vis}'
        self.pre_meta = MetaDict(self.pre_path)
        self.post_meta = MetaDict(self.post_path)
        self.diff_pers = self._check_periodicities()
        self.diff_dims = self._check_dimensions()
        self.periodicities = self._get_periodicities()

    def _get_periodicities(self) -> list:
        """Returns a list of periodicities to be compared"""
        # set conversion so that order is made insignificant
        if self.diff_pers:
            return [per for per in self.post_meta["Periodicities"]
                    if per in self.pre_meta["Periodicities"]]
        else:
            return self.post_meta["Periodicities"]

    def _check_periodicities(self) -> bool:
        """Returns True if pre and post have the same periodicities, False
        if not."""
        # set conversion so that order is made insignificant
        if set(self.pre_meta["Periodicities"]) != set(
                self.post_meta["Periodicities"]):
            # TODO finalise this warning
            warnings.warn("Periodicities do not match")
            log.warning('Periodicities do not match')
            self.differences = True
            return False
        else:
            return True

    def _check_dimensions(self) -> bool:
        """"""
        # First check if dimensions are equal ignoring the order
        if set(self.pre_meta["Dimensions"]) != set(
                self.post_meta["Dimensions"]):
            raise InvalidComparison(f'{self.pre_position} has dimensions'
                                    f' {self.pre_meta["Dimensions"]}, while '
                                    f'{self.post_position} has dimensions '
                                    f'{self.post_meta["Dimensions"]}',
                                    "Different dimensions")
        # for some reason dimensions needs to be converted to a list
        # even though it already appears to be one
        # check if dimensions are in the same order, if not warn
        if list(self.pre_meta["Dimensions"]) != list(
                self.post_meta["Dimensions"]):
            warnings.warn("Dimensions have different order in pre and post")
            return True
        else:
            return False

    def compare(self):
        """Main function to compare pre and post and save the difference
        dataframe to the .opticord file."""
        for per in self.periodicities:
            log.debug(f'comparing periodicity {per}')
            log.debug('reading pre')
            self.pre = self._read(f'{self.pre_path}/{per}')
            log.debug('reading post')
            self.post = self._read(f'{self.post_path}/{per}')
            # reorder the pre df if diff dims was identified
            if self.diff_dims:
                log.warning('dimensions in different order, reordering')
                self.pre = self.pre.reorder_levels(
                    list(self.post_meta["Dimensions"]), axis=0)
            # create the difference and nan dataframes
            log.debug('calculating difference dataframes')
            self.diff, self.nans = self._calc_difference()
            # check for differences
            log.debug('checking for differences')
            if self._check_differences():
                log.debug(f'differences found in {per}')
                self.differences = True
            log.debug('saving to file')
            # TODO ensure " vs " cannot be included in position name
            self.save_to_file(f'comparisons/{self.pre_position}'
                              f' vs {self.post_position}/{self.vis}/{per}')
        self.save_metadata()
        self.item.update_diffs(self.differences)

    @abstractmethod
    def _read(self, path: str):
        ...

    @abstractmethod
    def _calc_difference(self):
        ...

    @abstractmethod
    def _check_differences(self) -> bool:
        ...

    @abstractmethod
    def save_to_file(self, path: str) -> None:
        ...

    def save_metadata(self) -> None:
        """Saves metadata items for the overall visualisation comparison"""
        TempFile.manager.lockForWrite()
        with h5py.File(TempFile.path, 'r+') as store:
            comp = store[f'comparisons/{self.pre_position}'
                         f' vs {self.post_position}/{self.vis}']
            comp.attrs['periodicities'] = self.periodicities
            comp.attrs['differences'] = self.differences
        TempFile.manager.unlock()


class PandasComparison(Comparison):
    """"""

    def _read(self, path: str) -> pd.DataFrame:
        # even though it's reading it needs a write lock, h5py raises a
        # permission error even while read lock is on
        TempFile.manager.lockForWrite()
        df = pd.read_hdf(TempFile.path, path)
        TempFile.manager.unlock()
        return df

    def _calc_difference(self) -> tuple:
        """Creates and returns the difference and configured nan dataframes. 
        The difference dataframe is post.sub(pre), the configured nan dataframe
        is the difference dataframes NaN values configured as strings. 
        NaN strings identify as:
            "Series missing in <pre/post>": Entire series doesn't exist
                in the pre/post dataframe.
            "Date missing in <pre/post>": Date column doesn't exist
                in pre/post.
            "Missing in <pre/post>": A value is nan in pre/post but data 
                for the series does exist.
            ".": Data is NaN in both pre and post."""
        # Get the difference between post and pre
        # diff_df will have the combined index and columns
        # with nan's where there was nan-nan or value-nan
        diff_df = self.post.sub(self.pre)
        # we'll need to keep track of the difference df as well
        # as the original nans to split into 2 dataframes later on
        diff_df_unconfigured = diff_df.copy()
        nans = diff_df.isna()
        # Get a boolean dataframe of everywhere there is a nan
        # in pre/post and a nan in diff
        pre_nans = self.pre.isna()[nans] == True
        post_nans = self.post.isna()[nans] == True
        # Currently pre_nans and post_nans have a True value
        # for both nan-nan=nan and value-nan=nan. We need to
        # differentiate between these nans as nan-nan should stay
        # as nan since both are missing.
        # To achieve this we mask the pre/post_nans with the
        # post/pre_nans. The mask places the value of 'other'
        # when the value in both dataframes is True. Therefore
        # by setting our value of other to False we can remove
        # the nan-nan=nan True's from the pre/post_nan dataframes.
        missing_pre = pre_nans.mask(post_nans, other=False)
        missing_post = post_nans.mask(pre_nans, other=False)
        # Outer merging pre and post dataframes gives us a
        # dataframe that has both indexes. Setting indicator=True
        # give us a new column '_merge' which has the values
        # 'left_only', 'right_only' or 'both' based on where data
        # was found.
        missing_rows = self.pre.merge(
            self.post, how='outer', left_index=True, right_index=True,
            indicator=True)['_merge']
        # We can use the values of this missing_rows column
        # to set the values of the diff df to the missing series
        # string per where they were missing
        diff_df[missing_rows ==
                'left_only'] = f'Series not in {self.post_position}'
        diff_df[missing_rows ==
                'right_only'] = f'Series not in {self.pre_position}'
        # Missing dates in pre/post can be filtered by a simple
        # list comprehension and set to the missing date string
        diff_df[[d for d in diff_df.columns if d not in self.pre.columns]
                ] = f'Date not in {self.pre_position}'
        diff_df[[d for d in diff_df.columns if d not in self.post.columns]
                ] = f'Date not in {self.post_position}'
        # Set the values of the diff_df where we found missing
        # data in just one of the pre/post dataframes to the
        # relevant missing in pre/post string. This has to be done at
        # the end as an error can be raised:
        # TypeError: Cannot do inplace boolean setting on mixed-types
        # with a non np.nan value
        # Not sure how to solve this other than doing this step last
        diff_df[missing_pre] = f'Missing in {self.pre_position}'
        diff_df[missing_post] = f'Missing in {self.post_position}'
        # Finally we are left with just the nan-nan=nan nans
        # that are not a missing column or row. These should
        # be set to '.' as this is how they are displayed
        # in CORD.
        diff_df = diff_df.fillna('.')
        # return the orignal difference dataframe and a
        # dataframe of just the configured nan values
        return (diff_df_unconfigured, diff_df[nans].astype(str))

    def _check_differences(self) -> bool:
        """Returns true if differences are found between pre and post,
        false if not."""
        # independantly check the columns as pd.equals only checks shape
        # and values
        if self.pre.columns.tolist() != self.post.columns.tolist():
            return True
        # independantly check the index for the same reasons as above
        if not self.pre.sort_index().index.equals(self.post.sort_index().index):
            return True
        return not self.post.sort_index().equals(self.pre.sort_index())

    def save_to_file(self, path: str) -> None:
        TempFile.manager.lockForWrite()
        # We have to split the dataframes into the data and nans since hdf5
        # format doesn't support saving as object data type (which is what
        # is needed for float and string in same column).
        self.diff.to_hdf(
            TempFile.path,
            f'{path}/data',
            mode='a', complib='blosc:zlib', complevel=9,
            format='fixed')
        self.nans.to_hdf(
            TempFile.path,
            f'{path}/nans',
            mode='a', complib='blosc:zlib', complevel=9,
            format='fixed')
        # save the metadata
        with h5py.File(TempFile.path, 'r+') as store:
            comp = store[path]
            comp.attrs['periodicities'] = self.periodicities
            comp.attrs['different'] = self.differences
        TempFile.manager.unlock()


"""
# Dask was tested and found to be slower than pandas. It also requires
# dataframes to be saved in a 'table' format which takes significantly
# longer to read/write than 'fixed' format. For this reason Dask is
# currently redundant for OptiCORD and will not be developed further.
class DaskComparison(Comparison):

    def read(self, path: str) -> dd.DataFrame:
        print("reading as dask")
        TempFile.manager.lockForRead()
        df = dd.read_hdf(TempFile.path, path)
        TempFile.manager.unlock()
        print(df.head())
        return df

    def calc_difference(self) -> dd.DataFrame:
        print("calc-ing dask diff")
        return self.post.sub(self.pre)

    def save_to_file(self, path: str) -> None:
        print("saving using dask...")
        TempFile.manager.lockForWrite()
        self.diff.to_hdf(TempFile.path,
                         path,
                         mode='a')
        TempFile.manager.unlock()"""
