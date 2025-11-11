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

# Load Table
def load_base():
    pass

# Download PDF
def load_PDF_from_URL(url: str):
    pass

# Parse PDF 2 Markdown
def parse_PDF_2_MD(file_path: Path):
    pass

# unzip result and get the context
def unzip_N_load_context(file_path: Path):
    pass


if __name__ == '__main__':
    client: BaseClient = BaseClient.builder() \
    .app_token(APP_TOKEN) \
    .personal_base_token(PERSONAL_BASE_TOKEN) \
    .build()

    request = ListAppTableRecordRequest.builder() \
    .table_id(TABLE_ID) \
    .page_size(20) \
    .build()

    response = client.base.v1.app_table_record.list(request)

    print(JSON.marshal(response.data, indent=2))