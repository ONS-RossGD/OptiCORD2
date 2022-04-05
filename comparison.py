from abc import ABC, abstractmethod
import pandas as pd
import h5py
import warnings
from util import MetaDict, TempFile


class InvalidComparison(Exception):
    """Raised when a comparison cannot be made between pre and post"""


class Comparison(ABC):
    """Abstract base class for all comparisons. Ensures a valid comparison
    can be made no matter the method."""

    def __init__(self, pre_iteration: str, post_iteration: str, item) -> None:
        self.pre_iteration = pre_iteration
        self.post_iteration = post_iteration
        self.item = item
        self.vis = item.name
        self.differences = False
        self.pre_path = f'iterations/{pre_iteration}/{self.vis}'
        self.post_path = f'iterations/{post_iteration}/{self.vis}'
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
            warnings.warn("Periodicities are not equal")
            self.differences = True
            return False
        else:
            return True

    def _check_dimensions(self) -> bool:
        """"""
        # First check if dimensions are equal ignoring the order
        if set(self.pre_meta["Dimensions"]) != set(
                self.post_meta["Dimensions"]):
            # TODO better Exception message
            raise InvalidComparison("Pre and post have different dimensions")
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
            self.pre = self.read(f'{self.pre_path}/{per}')
            self.post = self.read(f'{self.post_path}/{per}')
            # reorder the pre df if diff dims was identified
            if self.diff_dims:
                self.pre = self.pre.reorder_levels(
                    list(self.post_meta["Dimensions"]), axis=0)
            self.diff = self.calc_difference()
            # TODO ensure " vs " cannot be included in iteration name
            self.save_to_file(f'comparisons/{self.pre_iteration}'
                              f' vs {self.post_iteration}/{self.vis}/{per}')
        self.save_metadata()
        self.item.update_diffs(self.differences)

    @abstractmethod
    def read(self, path: str):
        ...

    @abstractmethod
    def calc_difference(self):
        ...

    @abstractmethod
    def has_differences(self) -> bool:
        ...

    @abstractmethod
    def save_to_file(self, path: str) -> None:
        ...

    def save_metadata(self) -> None:
        """Saves metadata items for the overall visualisation comparison"""
        TempFile.manager.lockForWrite()
        with h5py.File(TempFile.path, 'r+') as store:
            comp = store[f'comparisons/{self.pre_iteration}'
                         f' vs {self.post_iteration}/{self.vis}']
            comp.attrs['periodicities'] = self.periodicities
            comp.attrs['differences'] = self.differences
        TempFile.manager.unlock()


class PandasComparison(Comparison):
    """"""

    def read(self, path: str) -> pd.DataFrame:
        # even though it's reading it needs a write lock, h5py raises a
        # permission error even while read lock is on
        TempFile.manager.lockForWrite()
        df = pd.read_hdf(TempFile.path, path)
        TempFile.manager.unlock()
        return df

    def calc_difference(self) -> pd.DataFrame:
        return self.post.sub(self.pre)

    def has_differences(self) -> bool:
        """Returns true if differences are found between pre and post,
        false if not."""
        # use pandas testing assertion to check for any differences
        # e.g. in shape, index/columns and values
        try:
            pd.testing.assert_frame_equal(self.pre, self.post, check_like=True)
            return False
        except AssertionError as e:
            # TODO maybe return the type of difference?
            self.differences = True
            return True

    def save_to_file(self, path: str) -> None:
        TempFile.manager.lockForWrite()
        self.diff.to_hdf(TempFile.path,
                         path,
                         mode='a', complib='blosc:zlib', complevel=9,
                         format='table')
        # save the metadata
        with h5py.File(TempFile.path, 'r+') as store:
            comp = store[path]
            comp.attrs['periodicities'] = self.periodicities
            comp.attrs['different'] = self.has_differences()
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
