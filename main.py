from __future__ import print_function

import io
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from PyPDF2 import PdfFileReader

from utils import convert_url_to_file_id


# Max size of pdf file - bytes
FILE_MAX_SIZE = 10485760

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

DOWNLOAD_DIR = 'downloads'


class GoogleDriveAPI:
    def __init__(self):
        self.creds = None
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
        self.service = build('drive', 'v3', credentials=self.creds)

    def get_files_id_and_name_from_folder(self, folder_id: str):
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
                    print('No files found.')
                    return
                print('Files:')
                for item in items:
                    files_id.append(item['id'])
                    file_names.append(item['name'])
                    print(f'File name: {item["name"]} | id: {item["id"]}')

                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
        except HttpError as error:
            print(f'An error occurred: {error}')

        result = zip(files_id, file_names)

        return result

    def get_file_name_from_id(self, files_id: list):
        file_names = []
        for file_id in files_id:
            try:
                response = self.service.files().get(
                    fileId=file_id).execute()
                name = response.get('name', [])
                if not name:
                    print('File not found.')
                    return
                file_names.append(name)

            except HttpError as error:
                print(f'An error occurred: {error}')

        result = zip(files_id, file_names)

        return result

    def download_pdf(self, file_id):
        try:
            request = self.service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(F'Download {int(status.progress() * 100)}.')

        except HttpError as error:
            print(F'An error occurred: {error}')
            file = None

        file.seek(0)

        try:
            PdfFileReader(file)
        except Exception as error:
            print(F'An error occurred: {error}')
            file = None

        return file.getvalue()


def main(urls: list):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    id_list = convert_url_to_file_id(urls)
    client = GoogleDriveAPI()

    for file_id, file_name in client.get_file_name_from_id(id_list):
        file = client.download_pdf(file_id)
        if os.path.exists(f'{DOWNLOAD_DIR}/{file_name}'):
            file_name = f'{file_id}_{file_name}'
        with open(f'{DOWNLOAD_DIR}/{file_name}', 'wb') as f:
            f.write(file)


if __name__ == '__main__':
    test_urls = ['https://drive.google.com/file/d/1hCMhVeqc3hnfbikpz0dhBPLRH8Bfa3-V/view',
                 'https://drive.google.com/file/d/1lOCNpewxec_wMwIqvSUAzaEPW_Uu2j54/view',
                 'https://drive.google.com/file/d/1Dh_VJG-yHqP4yrjE7nBZ7HuwWtAlN-ha/view']
    main(test_urls)
