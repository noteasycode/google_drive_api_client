from __future__ import print_function

import os

from datetime import datetime
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
