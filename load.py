from dataclasses import dataclass, field
import os
import pandas as pd

class InvalidVisualisation(Exception):
    """"""

class CSVValidator:
    """Validates whether or not a file is a csv"""
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath

    def validate(self):
        _, file_extension = os.path.splitext(self.filepath)
        return bool(file_extension == ".csv")

@dataclass
class Visualisation:
    """CORD Visualisation in python friendly format"""
    periodicities: dict = field(init=False, repr=False)
    name: str = field(init=False)
    filepath: str

    def read(self):
        """"""
    
    def isValid(self) -> bool:
        """"""
        #is_csv = CSVValidator(self.filepath)
        if not CSVValidator(self.filepath).validate():
            return False
        return True

    def __post_init__(self) -> None:
        """"""
        self.name = os.path.basename(self.filepath).split('.')[0]
        try:
            self.read()
        except InvalidVisualisation as e:
            self.valid = False
            pass

class DataRegistry:
    """Registry to hold all imported data"""
    data: dict

    def __init__(self) -> None:
        """"""
        self.data = {}

    def open(self, file: str) -> bool:
        """"""
        vis = Visualisation(file)
        if vis.isValid():
            self.data[vis.name] = vis
            return True
        else:
            return False