import pandas as pd
import numpy as np
import xlsxwriter
from timeit import timeit
import os


def pandas_file(df):
    try:
        os.remove("pandas_table.xlsx")
    except:
        pass
    writer = pd.ExcelWriter('pandas_table.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    df.to_excel(writer, sheet_name='Sheet2', index=False)
    df.to_excel(writer, sheet_name='Sheet3', index=False)
    worksheet1 = writer.sheets['Sheet1']
    worksheet2 = writer.sheets['Sheet2']
    worksheet3 = writer.sheets['Sheet3']
    (max_row, max_col) = df.shape
    worksheet1.add_table(0, 0, max_row, max_col, {})
    worksheet2.add_table(0, 0, max_row, max_col, {})
    worksheet3.add_table(0, 0, max_row, max_col, {})
    writer.save()


def xlsxwriter_file(df):
    try:
        os.remove("xlsxwriter_table.xlsx")
    except:
        pass
    workbook = xlsxwriter.Workbook('xlsxwriter_table.xlsx')
    worksheet1 = workbook.add_worksheet('Sheet1')
    worksheet2 = workbook.add_worksheet('Sheet2')
    worksheet3 = workbook.add_worksheet('Sheet3')
    (max_row, max_col) = df.shape
    worksheet1.add_table(0, 0, max_row, max_col, {'data': df.values})
    worksheet2.add_table(0, 0, max_row, max_col, {'data': df.values})
    worksheet3.add_table(0, 0, max_row, max_col, {'data': df.values})
    workbook.close()


def main():
    df = pd.DataFrame(np.random.randint(0, 100, size=(100000, 56)))
    pandas_time = timeit(lambda: pandas_file(df), number=3)
    xlsx_time = timeit(lambda: xlsxwriter_file(df), number=3)
    print(f'Pandas finished in {pandas_time}')
    print(f'xlsxwriter finished in {xlsx_time}')


if __name__ == "__main__":
    main()
