import os
from time import time
import pandas as pd  
from memory_profiler import memory_usage

def get_size(flnm):  
    return round(os.path.getsize(flnm) / (1024*1024), 2)

def store_df(original_df: pd.DataFrame, flnm: str, clib: str):
    if clib == 'no_comp':
        original_df.to_hdf(flnm, key='df', format='fixed')
        return
    original_df.to_hdf(flnm, key='df', complib=clib, complevel=9,
    format='fixed')

def benchmark(filename:str, original_df: pd.DataFrame):  
    results = pd.DataFrame(columns=['Time', 'Size', 'Max Memory Usage'])
    for clib in ['no_comp', 'zlib', 'blosc', 'blosc:blosclz', 'blosc:lz4', 
                'blosc:lz4hc', 'blosc:snappy', 'blosc:zlib', 'blosc:zstd']:
        flnm = f'test_scripts/{filename}_{clib}.hdf'
        def strdf():
            return store_df(original_df, flnm, clib)
        started = time()
        memus = memory_usage(strdf, interval=1)
        results.loc[clib, 'Time'] = time() - started
        results.loc[clib, 'Size'] = get_size(flnm)
        results.loc[clib, 'Max Memory Usage'] = max(memus)
    print(results)