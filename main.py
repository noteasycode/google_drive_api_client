from __future__ import print_function

import io
import logging
import os
import re
import sys
import socket

from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logging.handlers import RotatingFileHandler
from PyPDF2 import PdfFileReader
from typing import Dict, List

from utils import get_xlsx_data, make_xlsx_report


logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Time format
TF = '%Y-%m-%d %H-%M-%S'


class GoogleDriveAPI:
    """
    This class provides connection to the Google Drive API service
    and allow user to read and download data.
    """
    def __init__(self):
        self.creds = None
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file(
                'token.json', SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
                logging.info('The token is expired, it will be refreshed')
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
                logging.info('Request for a new token')
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
        try:
            self.service = build('drive', 'v3', credentials=self.creds)
        except Exception as error:
            logging.error(f'Resource for interacting with an '
                          f'API was not built: {error}')
            sys.exit('Resource for interacting with an API was not built')

        logging.info('Connected to the API service')

    @staticmethod
    def convert_url_to_file_id(url: str):
        """
        Gets file`s id from the url path to a file
        on Google Drive
        """
        file_id = str()
        pattern = '\/d\/(.*)\/view'
        try:
            file_id = re.findall(pattern, url)[0]

        except Exception:
            logging.error(f'Invalid url: {url}')
            file_id = None

        return file_id

    def get_files_id_and_name_from_folder(self, folder_id: str):
        """
        Returns the tuple of all file names and ids in gdrive folder
        the user has access to.
        """
        files_id = []
        file_names = []
        try:
            page_token = None
            while True:
                response = self.service.files().list(
                    q=f'parents ="{folder_id}"',
                    pageSize=1000,
                    fields='nextPageToken, files(id, name)',
                    pageToken=page_token).execute()
                items = response.get('files', [])
                if not items:
                    logging.error('No files found.')
                    return
                for item in items:
                    files_id.append(item['id'])
                    file_names.append(item['name'])
                    logging.info(
                        f'File name: {item["name"]} | id: {item["id"]}'
                    )

                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
        except HttpError as error:
            logging.error(f'An error occurred: {error}')

        result = dict(zip(files_id, file_names))

        return result

    def get_file_name_from_id(self, file_id: str):
        """
        Gets a file`s name by gdrive`s id of a file.
        """
        name = str()
        try:
            response = self.service.files().get(fileId=file_id).execute()
            name = response.get('name', [])
            if not name:
                logging.info('File not found.')
                return

        except HttpError as error:
            logging.error(f'An error occurred: {error}')

        return name

    def get_pdf(self, file_id):
        """get a file
        Args:
            file_id: ID of the file to download
        Returns: IO object with location.
        Checks: Is A File object a PDF file?
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f'Download {int(status.progress() * 100)}.')

        except HttpError as error:
            logging.error(f'An error occurred: {error}')
            return
        except socket.timeout as error:
            logging.error(f'An error occurred: {error}')
            return

        file.seek(0)
        try:
            PdfFileReader(file)
        except Exception as error:
            logging.error(f'An error occurred: {error}')
            return

        return file.getvalue()

    def download_pdf(self, urls):
        """
        Download pdf file to your operating system
        :param urls:
        :return:
        """
        id_list = [self.convert_url_to_file_id(url) for url in urls
                   if self.convert_url_to_file_id(url) is not None]
        files_dict = {file_id: self.get_file_name_from_id(file_id)
                      for file_id in id_list}
        counter = 0
        for file_id, file_name in files_dict.items():
            file = self.get_pdf(file_id)
            if file is None:
                logging.error(
                    f'File with id: {file_id} & name: {file_name} is None'
                )
                continue
            if os.path.exists(f'{DOWNLOAD_DIR}/{file_name}'):
                file_name = f'{file_id}_' \
                            f'{datetime.now().strftime(TF)}_{file_name}'
            with open(f'{DOWNLOAD_DIR}/{file_name}', 'wb') as f:
                f.write(file)
            counter += 1

        print(f'{len(urls)} URLs were provided | {counter} files downloaded')


@make_xlsx_report
def main(data: dict) -> Dict[str, List[list]]:
    """
    Downloads PDF files;
    :param data: dict data type which contains name of
    folder for saving file as key
    and nested lists of urls in each list as values of a dict;
    :return: data for creating reports
    """
    report = {}
    client = GoogleDriveAPI()
    for folder_name, urls in data.items():
        file_path = f'{DOWNLOAD_DIR}/{folder_name}/'
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        elif os.path.exists(file_path):
            file_path = f'{DOWNLOAD_DIR}/{folder_name}_' \
                        f'{datetime.now().strftime(TF)}/'
            os.makedirs(file_path)

        report_key = file_path.lstrip(f'{DOWNLOAD_DIR}/').rstrip('/')
        report[report_key] = [[] for _ in range(len(urls))]

        for item in range(len(urls)):
            file_id = client.convert_url_to_file_id(urls[item])
            file_name = client.get_file_name_from_id(file_id)
            file = client.get_pdf(file_id)
            if file is None:
                logging.error(
                    f'File with id: {file_id} & name: {file_name} is None'
                )
                report[report_key][item].extend(
                    [file_name, file_id, 'not found'])
                continue
            file_path += file_name
            with open(file_path, 'wb') as f:
                f.write(file)
                file_path = file_path.rstrip(file_name)
            report[report_key][item].extend([file_name, file_id, 'ok'])
    return report


if __name__ == '__main__':
    test_urls = [
        'https://drive.google.com/file/d/'
        '1hCMhVeqc3hnfbikpz0dhBPLRH8Bfa3-V/view',
        'https://drive.google.com/file/d/'
        '1lOCNpewxec_wMwIqvSUAzaEPW_Uu2j54/view',
        'https://drive.google.com/file/d/'
        '168DDAkgmGaAv3DyQ2gBLl6RIOb4_f2Ui',
        'https://drive.google.com/file/d/'
        '1Dh_VJG-yHqP4yrjE7nBZ7HuwWtAlN-ha/view',
        'https://drive.google.com/file/d/'
        '1lOCNpewxec_wMwIqvSUAzaEPW_Uu2j54/view',
    ]
    xlsx_data = get_xlsx_data('import_pdf.xlsx')
    main(xlsx_data)
