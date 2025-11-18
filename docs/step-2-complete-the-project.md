# Step 2 Complete The Project

In this document i will show you how do i do for complete this mission.

## Above All

We should always follow the following rules.

- All the table actions using `BaseOpenSDK(Python)`made by FEISHU. You can learn it though reading [Doc]([‌﻿⁠﻿﻿‌⁠‍‌‍‍⁠‍﻿‍⁠⁠﻿‬﻿‬‬﻿⁠﻿﻿‍⁠BaseOpenSDK（Python）官方文档 - 飞书云文档](https://feishu.feishu.cn/docx/AtcId8w25oAj4WxOaxicsXgGn8b)) or following section *How to do actions with `BaseOpenSDK(Python)`*.
- We need a simple HTTP server to show user about the process in real time. `Flask` may be a good choice. By the way we need at least 2 API, one for translating all records (A get-request without any params), another for translating special one(A get-request with a param `record_id`). 
- We want to done quickly so we may use multi-threading with `threading`.
- All required arguments should store in `.env`. It should be copied in `.env.sample` without any sensitive value if we add new one in `.env`.
- All middle files and final files should be stored in sub folders in folder  `files`. They will be deleted when the mission completed.
- All path should be stored in class `pathlib.Path`.
- Using `pdfdeal` to translate PDF into ZIP.
- Using `unzip` or `shutil` to unzip ZIP.
- Using `logging` to record logs of all actions.

### How to do actions with `BaseOpenSDK(Python)`

#### Before coding

Install requirements.

```shell
python -m pip install dotenv https://lf3-static.bytednsdoc.com/obj/eden-cn/lmeh7phbozvhoz/base-open-sdk/baseopensdk-0.0.13-py3-none-any.whl
```

We will store all useful token in `.env` and load it with `dotenv`.

```python
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

APP_TOKEN = os.environ['APP_TOKEN']
PERSONAL_BASE_TOKEN = os.environ['PERSONAL_BASE_TOKEN']
TABLE_ID = os.environ['TABLE_ID']
```

#### Build base client

``````python
from baseopensdk import BaseClient
from baseopensdk.api.base.v1 import *
from baseopensdk.api.drive.v1 import *

client: BaseClient = BaseClient.builder() \
    .app_token(APP_TOKEN) \
    .personal_base_token(PERSONAL_BASE_TOKEN) \
    .build()
``````

#### Request the table and get value of field in any record

```python
request = ListAppTableRecordRequest.builder() \
    .table_id(TABLE_ID) \
    .page_size(20) \
    .build()

response = client.base.v1.app_table_record.list(request)

records = getattr(scope_response_list.data, 'items', [])
for record in records: 
    record_id, fields = record.record_id, record.fields
    name = (fields.get('example', {})) # Get the field 'example' in current record
```

#### Download file from remote

```python
request = DownloadMediaRequest.builder() \
    .file_token(token) \
    .build()
response = client.drive.v1.media.download(request)
with open(f'</your/path>/{name}.pdf', 'wb') as f:
    f.write(response.file.read())
```

#### Upload files to remote

```python
with open(f'</your/path>/{name}.zip', 'rb') as f:
    request = UploadAllMediaRequest.builder() \
    .request_body(UploadAllMediaRequestBody.builder() \
    .file_name(f'{name}.zip') \
    .parent_type("bitable_file") \
    .parent_node(APP_TOKEN) \
    .size(path.getsize('{name}.zip')) \
    .file(f.read()) \
    .build()) \
    .build()
    response: UploadAllMediaResponse = client.drive.v1.media.upload_all(request)
    request = UpdateAppTableRecordRequest.builder() \
        .table_id(TABLE_ID) \
        .record_id(record_id) \
        .request_body(AppTableRecord.builder() 
        .fields({
            "example-context": context,
            "example-file": [{"file_token": response.data.file_token}]
        })
        .build()) \
        .build()
    response: UpdateAppTableRecordResponse = client.base.v1.app_table_record.update(request)
```

### How to translating PDF into ZIP includes MD

```python
from pdfdeal import Doc2X
PDFDEAL_TOKEN = environ['PDFDEAL_TOKEN']
pdf_deal_client = Doc2X(apikey=PDFDEAL_TOKEN, debug=True)
waitting_process_list = list() # [ Path('</your/path/*.pdf>') ]
renamed_path_list = list() # [ Path('</your/path/*.zip>') ]
pdf_deal_client.pdf2file(waitting_process_list, output_path=Path('</your/path>'), output_names=renamed_path_list, output_format='md')
```

