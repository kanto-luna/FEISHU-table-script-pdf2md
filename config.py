"""Configuration module for PDF to MD FEISHU Script."""
from dotenv import load_dotenv, find_dotenv
import os
from pathlib import Path

# Load environment variables
load_dotenv(find_dotenv())

# Required environment variables
APP_TOKEN = os.environ['APP_TOKEN']
PERSONAL_BASE_TOKEN = os.environ['PERSONAL_BASE_TOKEN']
TABLE_ID = os.environ['TABLE_ID']
PDFDEAL_TOKEN = os.environ['PDFDEAL_TOKEN']

# Column names for FEISHU table
ORIGIN_COLUMN = os.environ['ORIGIN_COLUMN']
TARGET_FILE_COLUMN = os.environ['TARGET_FILE_COLUMN']
TARGET_CONTEXT_COLUMN = os.environ['TARGET_CONTEXT_COLUMN']
NAME_COLUMN = os.environ['NAME_COLUMN']
SINGLE_PAGE_SIZE = os.environ['SINGLE_PAGE_SIZE'] if os.environ['SINGLE_PAGE_SIZE'] else 500

# File paths using pathlib.Path
BASE_DIR = Path(__file__).parent
FILES_DIR = BASE_DIR / 'files'
PDFS_DIR = FILES_DIR / 'pdfs'
ZIPS_DIR = FILES_DIR / 'zips'
EXTRACTED_DIR = FILES_DIR / 'extracted'

# Logging configuration
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'app.log'
