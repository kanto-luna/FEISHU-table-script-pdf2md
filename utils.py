"""Utility functions for file management and logging."""
import logging
import shutil
from pathlib import Path
from typing import Optional
from config import LOG_DIR, LOG_FILE, PDFS_DIR, ZIPS_DIR, EXTRACTED_DIR


def setup_logging(log_level: int = logging.INFO) -> None:
    """Configure logging to file and console."""
    # Create log directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def ensure_directories() -> None:
    """Create files subdirectories if they don't exist."""
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    ZIPS_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_files(folder: Optional[Path] = None) -> None:
    """Remove temporary files after processing.
    
    Args:
        folder: Specific folder to clean. If None, cleans all subdirectories in files/.
    """
    if folder is None:
        # Clean all subdirectories
        for subdir in [PDFS_DIR, ZIPS_DIR, EXTRACTED_DIR]:
            if subdir.exists():
                for item in subdir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
    else:
        # Clean specific folder
        if folder.exists():
            for item in folder.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

