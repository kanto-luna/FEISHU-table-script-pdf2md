"""FEISHU BaseOpenSDK client wrapper for table operations."""
import logging
from typing import List, Optional, Generator, Tuple
from baseopensdk import BaseClient
from baseopensdk.api.base.v1 import *
from baseopensdk.api.drive.v1 import *
from pathlib import Path
from config import (
    APP_TOKEN,
    PERSONAL_BASE_TOKEN,
    TABLE_ID,
    ORIGIN_COLUMN,
    TARGET_FILE_COLUMN,
    TARGET_CONTEXT_COLUMN,
    NAME_COLUMN,
    SINGLE_PAGE_SIZE
)

logger = logging.getLogger(__name__)


class FeishuClient:
    """Client for interacting with FEISHU BaseOpenSDK."""
    
    def __init__(self):
        """Initialize FEISHU client with tokens from config."""
        self.client: BaseClient = BaseClient.builder() \
            .app_token(APP_TOKEN) \
            .personal_base_token(PERSONAL_BASE_TOKEN) \
            .build()
        logger.info("FEISHU client initialized")
    
    def list_records(self) -> List:
        """Fetch all records from table, filter where origin column is not empty and target columns are empty.
        
        Returns:
            List of eligible records that need processing
        """
        eligible_records = []
        page_token = None
        base_request = ListAppTableRecordRequest.builder() \
            .table_id(TABLE_ID) \
            .page_size(SINGLE_PAGE_SIZE)

        while True:
            if page_token:
                request = base_request.page_token(page_token).build()
            else:
                request = base_request.build()
            
            try:
                response = self.client.base.v1.app_table_record.list(request)
                records = getattr(response.data, 'items', [])
                logger.info(f"Found {len(records)} records")
                
                for record in records:
                    record_id = record.record_id
                    fields = record.fields
                    
                    # Get field values
                    origin_field = fields.get(ORIGIN_COLUMN, {})
                    target_file_field = fields.get(TARGET_FILE_COLUMN, {})
                    target_context_field = fields.get(TARGET_CONTEXT_COLUMN, {})
                    
                    # Check if origin column has value (PDF file)
                    origin_has_value = origin_field and isinstance(origin_field, list) and len(origin_field) > 0
                    
                    # Check if target columns are empty
                    target_file_empty = not target_file_field or not isinstance(target_file_field, list) or len(target_file_field) == 0
                    target_context_empty = not target_context_field or (isinstance(target_context_field, str) and not target_context_field.strip())
                    
                    # Record is eligible if origin has value and targets are empty
                    if origin_has_value and target_file_empty and target_context_empty:
                        eligible_records.append(record)
                        logger.debug(f"Found eligible record: {record_id}")
                
                # Check if there are more pages
                page_token = getattr(response.data, 'page_token', None)
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"Error listing records: {e}")
                raise
        
        logger.info(f"Found {len(eligible_records)} eligible records")
        return eligible_records
    
    def list_records_streaming(self) -> Generator[Tuple[str, dict, List], None, None]:
        """Fetch all records from table with streaming progress updates for each page.
        
        Yields:
            Tuples of (event_type, page_info, records) where:
            - event_type: 'page_loaded' for page progress, 'records_ready' for final records
            - page_info: Dictionary with page number, records in page, eligible count
            - records: List of eligible records from current page (for 'page_loaded') or all records (for 'records_ready')
        """
        eligible_records = []
        page_token = None
        page_number = 0
        base_request = ListAppTableRecordRequest.builder() \
            .table_id(TABLE_ID) \
            .page_size(SINGLE_PAGE_SIZE)

        while True:
            page_number += 1
            if page_token:
                request = base_request.page_token(page_token).build()
            else:
                request = base_request.build()
            
            try:
                response = self.client.base.v1.app_table_record.list(request)
                records = getattr(response.data, 'items', [])
                logger.info(f"Found {len(records)} records on page {page_number}")
                
                page_eligible_count = 0
                for record in records:
                    record_id = record.record_id
                    fields = record.fields
                    
                    # Get field values
                    origin_field = fields.get(ORIGIN_COLUMN, {})
                    target_file_field = fields.get(TARGET_FILE_COLUMN, {})
                    target_context_field = fields.get(TARGET_CONTEXT_COLUMN, {})
                    
                    # Check if origin column has value (PDF file)
                    origin_has_value = origin_field and isinstance(origin_field, list) and len(origin_field) > 0
                    
                    # Check if target columns are empty
                    target_file_empty = not target_file_field or not isinstance(target_file_field, list) or len(target_file_field) == 0
                    target_context_empty = not target_context_field or (isinstance(target_context_field, str) and not target_context_field.strip())
                    
                    # Record is eligible if origin has value and targets are empty
                    if origin_has_value and target_file_empty and target_context_empty:
                        eligible_records.append(record)
                        page_eligible_count += 1
                        logger.debug(f"Found eligible record: {record_id}")
                
                # Check if there are more pages
                page_token = getattr(response.data, 'page_token', None)
                logger.info(f"Page token: {page_token}")

                if not page_token:
                    break
                
            except Exception as e:
                logger.error(f"Error listing records: {e}")
                raise

            page_info = {
                'page_number': page_number,
                'records_in_page': len(records),
                'eligible_in_page': page_eligible_count,
                'total_eligible_so_far': len(eligible_records),
                'has_more_pages': page_token is not None
            }
            yield ('page_loaded', page_info, eligible_records[-page_eligible_count:] if page_eligible_count > 0 else [])
        
        logger.info(f"Found {len(eligible_records)} eligible records total")
        # Yield final records ready event
        yield ('records_ready', {'total_eligible': len(eligible_records), 'total_pages': page_number}, eligible_records)
    
    def get_record_by_id(self, record_id: str):
        """Get a specific record by ID.
        
        Args:
            record_id: The record ID to retrieve
            
        Returns:
            Record object or None if not found
        """
        try:
            request = GetAppTableRecordRequest.builder() \
                .table_id(TABLE_ID) \
                .record_id(record_id) \
                .build()
            
            response = self.client.base.v1.app_table_record.get(request)
            return getattr(response.data, 'record', None)
        except Exception as e:
            logger.error(f"Error getting record {record_id}: {e}")
            return None
    
    def get_record_name(self, record) -> str:
        """Extract name from record's NAME_COLUMN field.
        
        Args:
            record: Record object from FEISHU
            
        Returns:
            Name string from the record
        """
        fields = record.fields
        name_field = fields.get(NAME_COLUMN, {})
        
        # Handle different field types (text, number, etc.)
        if isinstance(name_field, (str, int, float)):
            return str(name_field).strip()
        elif isinstance(name_field, list) and len(name_field) > 0:
            # Handle multi-select or other list types
            return str(name_field[0]).strip()
        else:
            # Fallback to record_id if name is not available
            return record.record_id
    
    def get_origin_file_token(self, record) -> Optional[str]:
        """Extract file token from record's origin column.
        
        Args:
            record: Record object from FEISHU
            
        Returns:
            File token string or None if not found
        """
        fields = record.fields
        origin_field = fields.get(ORIGIN_COLUMN, {})
        
        if isinstance(origin_field, list) and len(origin_field) > 0:
            file_item = origin_field[0]
            if isinstance(file_item, dict):
                return file_item.get('file_token') or file_item.get('token')
            elif isinstance(file_item, str):
                return file_item
        
        return None
    
    def download_pdf(self, record_id: str, file_token: str, name: str, output_path: Path) -> Path:
        """Download PDF using DownloadMediaRequest.
        
        Args:
            record_id: Record ID for logging
            file_token: File token from FEISHU
            name: Name to use for the file
            output_path: Directory to save the PDF
            
        Returns:
            Path to downloaded PDF file
        """
        try:
            request = DownloadMediaRequest.builder() \
                .file_token(file_token) \
                .build()
            
            response = self.client.drive.v1.media.download(request)
            
            # Sanitize filename
            from utils import sanitize_filename
            safe_name = sanitize_filename(name)
            pdf_path = output_path / f"{safe_name}.pdf"
            
            with open(pdf_path, 'wb') as f:
                f.write(response.file.read())
            
            logger.info(f"Downloaded PDF for record {record_id}: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF for record {record_id}: {e}")
            raise
    
    def upload_zip_and_context(self, record_id: str, zip_path: Path, context: str) -> None:
        """Upload ZIP file and update record with file_token and context text.
        
        Args:
            record_id: Record ID to update
            zip_path: Path to ZIP file to upload
            context: Context text to set in target context column
        """
        try:
            # Upload ZIP file
            with open(zip_path, 'rb') as f:
                file_size = zip_path.stat().st_size
                request = UploadAllMediaRequest.builder() \
                    .request_body(UploadAllMediaRequestBody.builder() \
                        .file_name(zip_path.name) \
                        .parent_type("bitable_file") \
                        .parent_node(APP_TOKEN) \
                        .size(file_size) \
                        .file(f.read()) \
                        .build()) \
                    .build()
                
                response: UploadAllMediaResponse = self.client.drive.v1.media.upload_all(request)
                file_token = response.data.file_token
            
            # Update record with file token and context
            request = UpdateAppTableRecordRequest.builder() \
                .table_id(TABLE_ID) \
                .record_id(record_id) \
                .request_body(AppTableRecord.builder() \
                    .fields({
                        TARGET_CONTEXT_COLUMN: context,
                        TARGET_FILE_COLUMN: [{"file_token": file_token}]
                    }) \
                    .build()) \
                .build()
            
            response: UpdateAppTableRecordResponse = self.client.base.v1.app_table_record.update(request)
            logger.info(f"Updated record {record_id} with ZIP file and context")
            
        except Exception as e:
            logger.error(f"Error uploading ZIP and context for record {record_id}: {e}")
            raise


# Global client instance
client = FeishuClient()

