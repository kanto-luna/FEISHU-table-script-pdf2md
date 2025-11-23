"""PDF processing module for downloading, converting, and extracting context."""
import logging
import zipfile
import shutil
from pathlib import Path
from typing import Optional
from pdfdeal import Doc2X
from config import PDFDEAL_TOKEN, PDFS_DIR, ZIPS_DIR, EXTRACTED_DIR, ORIGIN_COLUMN
from feishu_client import FeishuClient

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Processor for PDF download, conversion, and context extraction."""
    
    def __init__(self, feishu_client: FeishuClient):
        """Initialize PDF processor with FEISHU client.
        
        Args:
            feishu_client: FeishuClient instance for downloading PDFs
        """
        self.feishu_client = feishu_client
        self.pdf_deal_client = Doc2X(apikey=PDFDEAL_TOKEN, debug=True)
        self._field_id_cache = None
        logger.info("PDF processor initialized")
    
    def _get_field_id(self) -> Optional[str]:
        """Get field_id for ORIGIN_COLUMN, with caching.
        
        Returns:
            Field ID string or None if not found
        """
        if self._field_id_cache is None:
            self._field_id_cache = self.feishu_client.get_field_id(ORIGIN_COLUMN)
        return self._field_id_cache
    
    def download_pdf(self, record) -> Optional[Path]:
        """Download PDF for a single record.
        
        Args:
            record: Record object from FEISHU
            
        Returns:
            Path to downloaded PDF file or None if failed
        """
        try:
            record_id = record.record_id
            name = self.feishu_client.get_record_name(record)
            file_token = self.feishu_client.get_origin_file_token(record)
            
            if not file_token:
                logger.warning(f"No file token found for record {record_id}")
                return None

            logger.info(f"Downloading PDF for record {record_id} ({name}), file token: {file_token}")
            
            # Get field_id for the origin column
            field_id = self._get_field_id()
            if not field_id:
                logger.error(f"Failed to get field_id for column '{ORIGIN_COLUMN}'")
                return None
            
            pdf_path = self.feishu_client.download_pdf(
                record_id=record_id,
                file_token=file_token,
                field_id=field_id,
                name=name,
                output_path=PDFS_DIR
            )
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF for record {record.record_id}: {e}")
            return None
    
    def convert_pdf_to_zip(self, pdf_path: Path, name: str) -> Optional[Path]:
        """Convert PDF to ZIP format using pdfdeal.
        
        Args:
            pdf_path: Path to PDF file
            name: Name to use for the ZIP file
            
        Returns:
            Path to converted ZIP file or None if failed
        """
        try:
            from utils import sanitize_filename
            
            # Sanitize filename
            safe_name = sanitize_filename(name)
            zip_path = ZIPS_DIR / f"{safe_name}.zip"
            
            # Prepare lists for pdfdeal
            waiting_process_list = [pdf_path]
            renamed_path_list = [zip_path]
            
            # Convert PDF to ZIP
            self.pdf_deal_client.pdf2file(
                waiting_process_list,
                output_path=ZIPS_DIR,
                output_names=renamed_path_list,
                output_format='md'
            )
            
            if zip_path.exists():
                logger.info(f"Converted PDF to ZIP: {zip_path}")
                return zip_path
            else:
                logger.error(f"ZIP file not created: {zip_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting PDF to ZIP for {pdf_path}: {e}")
            return None
    
    def extract_context(self, zip_path: Path) -> Optional[str]:
        """Unzip ZIP file and read .md file content.
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            Content of the Markdown file as string or None if failed
        """
        try:
            # Create extraction directory for this ZIP
            extract_dir = EXTRACTED_DIR / zip_path.stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find .md file in extracted contents
            md_files = list(extract_dir.rglob('*.md'))
            
            if not md_files:
                logger.warning(f"No .md file found in ZIP: {zip_path}")
                return None
            
            # Read the first .md file found (usually there's only one)
            md_file = md_files[0]
            with open(md_file, 'r', encoding='utf-8') as f:
                context = f.read()
            
            logger.info(f"Extracted context from {md_file} ({len(context)} characters)")
            return context
            
        except Exception as e:
            logger.error(f"Error extracting context from {zip_path}: {e}")
            return None
    
    def process_record(self, record) -> bool:
        """Complete workflow for single record: download → convert → extract → upload.
        
        Args:
            record: Record object from FEISHU
            
        Returns:
            True if successful, False otherwise
        """
        record_id = record.record_id
        name = self.feishu_client.get_record_name(record)
        
        try:
            logger.info(f"Processing record {record_id} ({name})")
            
            # Step 1: Download PDF
            pdf_path = self.download_pdf(record)
            if not pdf_path:
                logger.error(f"Failed to download PDF for record {record_id}")
                return False
            
            # Step 2: Convert PDF to ZIP
            zip_path = self.convert_pdf_to_zip(pdf_path, name)
            if not zip_path:
                logger.error(f"Failed to convert PDF to ZIP for record {record_id}")
                # Cleanup PDF
                if pdf_path.exists():
                    pdf_path.unlink()
                return False
            
            # Step 3: Extract context from ZIP
            context = self.extract_context(zip_path)
            if not context:
                logger.error(f"Failed to extract context for record {record_id}")
                # Cleanup files
                if pdf_path.exists():
                    pdf_path.unlink()
                if zip_path.exists():
                    zip_path.unlink()
                return False
            
            # Step 4: Upload ZIP and context to FEISHU
            self.feishu_client.upload_zip_and_context(
                record_id=record_id,
                zip_path=zip_path,
                context=context
            )
            
            # Step 5: Cleanup temporary files
            if pdf_path.exists():
                pdf_path.unlink()
            
            # Cleanup extracted directory
            extract_dir = EXTRACTED_DIR / zip_path.stem
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            
            logger.info(f"Successfully processed record {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing record {record_id}: {e}")
            return False

