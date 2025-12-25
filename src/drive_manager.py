# src/drive_manager.py
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io
import json

class DriveManager:
    def __init__(self, creds):
        self.service = build('drive', 'v3', credentials=creds)

    def get_or_create_folder(self, folder_name, parent_id=None):
        q = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id: q += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(q=q, fields="files(id)").execute()
        items = results.get('files', [])
        
        if items: return items[0]['id']
        
        metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id: metadata['parents'] = [parent_id]
        
        folder = self.service.files().create(body=metadata, fields='id').execute()
        return folder.get('id')

    def upload_file(self, folder_id, filename, content, mime_type):
        q = f"name = '{filename}' and '{folder_id}' in parents and trashed = false"
        results = self.service.files().list(q=q, fields="files(id)").execute()
        items = results.get('files', [])

        if isinstance(content, str): content = content.encode('utf-8')
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)

        if items:
            self.service.files().update(fileId=items[0]['id'], media_body=media).execute()
            return items[0]['id']
        else:
            meta = {'name': filename, 'parents': [folder_id]}
            f = self.service.files().create(body=meta, media_body=media, fields='id').execute()
            return f.get('id')

    def read_file(self, file_id):
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False: _, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read().decode('utf-8')

    def list_files(self, folder_id):
        q = f"'{folder_id}' in parents and trashed = false"
        results = self.service.files().list(q=q, fields="files(id, name, mimeType)").execute()
        return results.get('files', [])
