from __future__ import print_function

import functools
import os

from datetime import datetime
from openpyxl import load_workbook
from PyPDF2 import PdfFileReader, PdfFileWriter


# Max size of pdf file - bytes
FILE_MAX_SIZE = 10485760

DOWNLOAD_DIR = 'downloads'


def get_file_size(file):
    pos = file.tell()
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(pos)
    return size


def validate_and_save_pdf(pdf_path: str):
    if not os.path.exists(pdf_path):
        raise ValueError('File does not exists')
    if not pdf_path.endswith('.pdf'):
        raise ValueError('Wrong file format')

    with open(pdf_path, 'rb') as file:
        file_size = get_file_size(file)
        if file_size > FILE_MAX_SIZE:
            raise ValueError('Maximum file size: 10 Mb')
        try:
            pdf = PdfFileReader(file)
        except Exception:
            raise ValueError('You must upload a valid PDF file')
        if pdf.is_encrypted:
            raise ValueError('Your pdf file is encrypted')

        pdf_writer = PdfFileWriter()
        for page in range(pdf.getNumPages()):
            pdf_writer.addPage(pdf.getPage(page))

        file_name = f'{DOWNLOAD_DIR}/{os.path.basename(pdf_path)}'
        if os.path.exists(file_name):
            file_name = f'{file_name}_{datetime.now()}'

        with open(file_name, 'wb') as output_pdf:
            pdf_writer.write(output_pdf)
            output_pdf.close()
        file.close()
    return f'File has been successfully checked and saved ' \
           f'to folder "{DOWNLOAD_DIR}"'


def get_xlsx_data(file_path: str):
    wb = load_workbook(file_path)
    sheet = wb.active
    xlsx_dict = {folder_name.value: url.value.strip().split(';')
                 for folder_name in sheet['A'] for url in sheet['B']}
    return xlsx_dict


def make_xlsx_report(func):
    @functools.wraps(func)
    def wrapper_make_xlsx_report(*args, **kwargs):
        args_repr = [repr(a) for a in args]  # 1
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2
        signature = ", ".join(args_repr + kwargs_repr)
        print(f"Calling {func.__name__}({signature})")
        value = func(*args, **kwargs)
        print(f"{func.__name__!r} returned {value!r}")
        return value
    return wrapper_make_xlsx_report
