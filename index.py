# -*- coding: utf-8 -*-

import logging
import shutil
from multiprocessing import context
from os import environ, path, mkdir, remove
from pathlib import Path
from zipfile import ZipFile

from requests import get
from baseopensdk import BaseClient, JSON
from baseopensdk.api.base.v1 import *
from baseopensdk.api.drive.v1 import *
from dotenv import find_dotenv, load_dotenv
from pdfdeal import Doc2X

load_dotenv(find_dotenv())

LOG_LEVEL = environ['LOG_LEVEL']
APP_TOKEN = environ['APP_TOKEN']
PERSONAL_BASE_TOKEN = environ['PERSONAL_BASE_TOKEN']
TABLE_ID = environ['TABLE_ID']
PDFDEAL_TOKEN = environ['PDFDEAL_TOKEN']

# logging in console and file
logging.basicConfig(level=LOG_LEVEL)
# logging.getLogger().addHandler(logging.StreamHandler())
logging.getLogger().addHandler(logging.FileHandler('script.log', mode='a', encoding='utf-8'))
logger = logging.getLogger(__name__)

pdf_deal_client = Doc2X(apikey=PDFDEAL_TOKEN, debug=True)

client: BaseClient = BaseClient.builder() \
    .app_token(APP_TOKEN) \
    .personal_base_token(PERSONAL_BASE_TOKEN) \
    .build()
scope_response_list = None

# Load Table
def load_base():

    global scope_response_list

    request = ListAppTableRecordRequest.builder() \
    .table_id(TABLE_ID) \
    .page_size(1000) \
    .build()

    scope_response_list = client.base.v1.app_table_record.list(request)

    records = getattr(scope_response_list.data, 'items', [])
    resume_links = []
    for record in records: 
        record_id, fields = record.record_id, record.fields
        resumes = (fields.get('简历', {}))
        name = (fields.get('姓名', {}))
        context = (fields.get('脚本测试-简历Markdown文本', {}))
        context_file = (fields.get('脚本测试-简历Markdown文件', {}))
        if context and context_file:
            continue
        for resume in resumes:
            link = resume.get('url', '')
            token = resume.get('file_token', '')
            if link:
                resume_links.append({ 'url': link, 'token': token, 'name': name[:] })
    return resume_links

# Download PDF
def load_PDF_from_URL(url: str, token: str, name: str):
    file_path = Path(f'pdf/{name}.pdf')

    if (path.exists(file_path)):
        logger.info(f'{name} already exists at {file_path}')
        return file_path

    request = DownloadMediaRequest.builder() \
    .file_token(token) \
    .build()

    response = client.drive.v1.media.download(request)

    if not path.exists('pdf'):
        mkdir('pdf')

    with open(f'pdf/{name}.pdf', 'wb') as f:
        f.write(response.file.read())

    logger.info(f'{name} downloaded')

    return file_path

# Parse PDF 2 Markdown
def parse_PDF_2_MD_zip(path_list: list[Path]):
    if not path.exists('md-zip'):
        mkdir('md-zip')

    all_zip_file_list = list(map(lambda path: Path(f'md-zip/{path.name.split(".")[0]}.zip'), path_list))
    waitting_process_list = list(filter(lambda path: not Path(f'md-zip/{path.name.split(".")[0]}.zip').exists(), path_list))
    renamed_path_list = list(map(lambda path: Path(f'{path.name.split(".")[0]}.zip'), waitting_process_list))

    logger.info(f'Parsing PDF list: {waitting_process_list}; Renamed list: {renamed_path_list};')

    pdf_deal_client.pdf2file(waitting_process_list, output_path=Path('md-zip'), output_names=renamed_path_list, output_format='md')

    return all_zip_file_list

# unzip result and get the context
def unzip_N_load_context(zip_file_list: list[Path]):
    md_dir = Path('md')
    if not md_dir.exists():
        mkdir(md_dir)

    context_with_zip_list = []
    for zip_file in zip_file_list:
        unzip_dir = md_dir / Path(zip_file.name.split(".")[0])
        # any child ?
        if (unzip_dir / Path('*.md')).exists():
            logger.info(f'{zip_file} already unzipped')
            itermd_list = [file for file in unzip_dir.iterdir() if file.is_file() and file.name.endswith('.md')]
            with open(itermd_list[0], 'r', encoding='utf-8') as f:
                context = f.read()
                context_with_zip_list.append({ 'context': context, 'zip_file': zip_file })
            continue
        try:
            with ZipFile(zip_file, 'r') as zip_ref:
                if not unzip_dir.exists():
                    mkdir(unzip_dir)
                zip_ref.extractall(unzip_dir)
                itermd_list = [file for file in unzip_dir.iterdir() if file.is_file() and file.name.endswith('.md')]
                if len(itermd_list) == 0:
                    logger.error(f'{zip_file} no md file found')
                    continue
                with open(itermd_list[0], 'r', encoding='utf-8') as f:
                    context = f.read()
                    context_with_zip_list.append({ 'context': context, 'zip_file': zip_file, 'name': zip_file.name.split(".")[0] })
        except Exception as e:
            logger.error(f'{zip_file} unzip failed: {e}')
            continue
    
    return context_with_zip_list

def upload_context_N_zip(context_list: list[Dict[str, str | Path]]):
    '''
    Upload context and zip file to FEISHU Table.
    '''
    global scope_response_list
    records = getattr(scope_response_list.data, 'items', [])
    for record in records:
        record_id, fields = record.record_id, record.fields
        name = (fields.get('姓名', {}))
        for context in context_list:
            if context['name'] == name:
                with open(context['zip_file'], 'rb') as f:
                    request = UploadAllMediaRequest.builder() \
                    .request_body(UploadAllMediaRequestBody.builder() \
                    .file_name(f'{context["name"]}.zip') \
                    .parent_type("bitable_file") \
                    .parent_node(APP_TOKEN) \
                    .size(path.getsize(context['zip_file'])) \
                    .file(f.read()) \
                    .build()) \
                    .build()
                    response: UploadAllMediaResponse = client.drive.v1.media.upload_all(request)
                    request = UpdateAppTableRecordRequest.builder() \
                        .table_id(TABLE_ID) \
                        .record_id(record_id) \
                        .request_body(AppTableRecord.builder() 
                        .fields({
                            "脚本测试-简历Markdown文本": context['context'],
                            "脚本测试-简历Markdown文件": [{"file_token": response.data.file_token}]
                        })
                        .build()) \
                        .build()
                    response: UpdateAppTableRecordResponse = client.base.v1.app_table_record.update(request)

def release_cache():
    shutil.rmtree('md-zip')
    shutil.rmtree('md')
    shutil.rmtree('pdf')


if __name__ == '__main__':
    context_with_zip_list = unzip_N_load_context(parse_PDF_2_MD_zip([ load_PDF_from_URL(link['url'], link['token'], link['name']) for link in load_base() ]))
    upload_context_N_zip(context_with_zip_list)
    release_cache()