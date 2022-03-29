from enum import Enum, auto
import pandas as pd
from util import MetaDict, TempFile


class ComparisonMethods(Enum):
    PANDAS = auto()
    DASK = auto()


class ComparisonManager:
    """"""
    pre_path: str
    post_path: str

    def __init__(self, pre_path: str, post_path: str) -> None:
        """"""
        self.pre_path = pre_path
        self.post_path = post_path

    def compare(self, method: ComparisonMethods) -> None:
        """"""
        if method is ComparisonMethods.PANDAS:
            comparison = PandasComparison(self.pre_path, self.post_path)
            comparison.compare()


class PandasComparison:
    """"""

    def __init__(self, pre_path: str, post_path) -> None:
        self.pre_path = pre_path
        self.post_path = post_path
        self.pre_meta = MetaDict(pre_path)
        self.post_meta = MetaDict(post_path)

    def compare(self):
        """"""
        for per in self.pre_meta["Periodicities"]:
            TempFile.manager.lockForRead()
            df = pd.read_hdf(TempFile.path, f'{self.pre_path}/{per}')
            TempFile.manager.unlock()
            print(df)


class DaskComparison:
    """"""

    def __init__(self, pre_path: str, post_path) -> None:
        self.pre_path = pre_path
        self.post_path = post_path
        self.pre_meta = MetaDict(pre_path)
        self.post_meta = MetaDict(post_path)
