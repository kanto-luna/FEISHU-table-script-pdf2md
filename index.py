from os import environ
from pathlib import Path

from baseopensdk import BaseClient, JSON
from baseopensdk.api.base.v1 import *
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

APP_TOKEN = environ['APP_TOKEN']
PERSONAL_BASE_TOKEN = environ['PERSONAL_BASE_TOKEN']
TABLE_ID = environ['TABLE_ID']
PDFDEAL_TOKEN = environ['PDFDEAL_TOKEN']

cached_files = []

# Load Table
def load_base():
    client: BaseClient = BaseClient.builder() \
    .app_token(APP_TOKEN) \
    .personal_base_token(PERSONAL_BASE_TOKEN) \
    .build()

    request = ListAppTableRecordRequest.builder() \
    .table_id(TABLE_ID) \
    .page_size(1000) \
    .build()

    response = client.base.v1.app_table_record.list(request)

    records = getattr(response.data, 'items', [])
    resume_links = []
    for record in records: 
        record_id, fields = record.record_id, record.fields
        resumes = (fields.get('简历', {}))
        for resume in resumes:
            link = resume.get('url', '')
            if link:
                resume_links.append(link)
    return resume_links

# Download PDF
def load_PDF_from_URL(url: str):
    print(url)
    return ''

# Parse PDF 2 Markdown
def parse_PDF_2_MD(file_path: Path):
    pass

# unzip result and get the context
def unzip_N_load_context(file_path: Path):
    pass


if __name__ == '__main__':
    for link in load_base():
        pdf_path = load_PDF_from_URL(link)
