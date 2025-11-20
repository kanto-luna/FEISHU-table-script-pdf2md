"""Flask application for PDF to MD translation service."""
import json
import logging
from flask import Flask, jsonify, request, Response, stream_with_context
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Generator
from feishu_client import FeishuClient
from pdf_processor import PDFProcessor
from utils import setup_logging, ensure_directories, cleanup_files
from config import LOG_DIR, ORIGIN_COLUMN, TARGET_FILE_COLUMN, TARGET_CONTEXT_COLUMN

# Setup logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize clients
feishu_client = FeishuClient()
pdf_processor = PDFProcessor(feishu_client)

# Thread pool executor for parallel processing
executor = ThreadPoolExecutor(max_workers=5)


def _stream_error(message: str) -> Generator[str, None, None]:
    """Generator function that yields an error message in SSE format.
    
    Args:
        message: Error message to send
        
    Yields:
        JSON string with error information
    """
    error_data = {
        'type': 'error',
        'status': 'error',
        'message': message
    }
    yield f"data: {json.dumps(error_data)}\n\n"


def _stream_progress() -> Generator[str, None, None]:
    """Generator function that yields progress updates for pagination and record processing.
    
    Yields:
        JSON strings with progress updates for both pagination and processing
    """
    try:
        processed = 0
        failed = 0
        failed_records = []
        records = []
        total = 0
        
        # Send initial status for pagination
        yield f"data: {json.dumps({'type': 'pagination_start', 'message': 'Starting to fetch records from FEISHU table'})}\n\n"
        
        # Stream pagination progress
        for event_type, page_info, page_records in feishu_client.list_records_streaming():
            if event_type == 'page_loaded':
                # Yield page progress update
                page_data = {
                    'type': 'page_loaded',
                    'status': 'progress',
                    'page_number': page_info['page_number'],
                    'records_in_page': page_info['records_in_page'],
                    'eligible_in_page': page_info['eligible_in_page'],
                    'total_eligible_so_far': page_info['total_eligible_so_far'],
                    'has_more_pages': page_info['has_more_pages'],
                    'message': f"Loaded page {page_info['page_number']}: {page_info['records_in_page']} records, {page_info['eligible_in_page']} eligible"
                }
                yield f"data: {json.dumps(page_data)}\n\n"
            elif event_type == 'records_ready':
                # All records collected
                records = page_records
                total = len(records)
                ready_data = {
                    'type': 'records_ready',
                    'status': 'success',
                    'total': total,
                    'total_pages': page_info['total_pages'],
                    'message': f'Finished loading {total} eligible records from {page_info["total_pages"]} pages'
                }
                yield f"data: {json.dumps(ready_data)}\n\n"
        
        if not records:
            yield f"data: {json.dumps({'type': 'error', 'status': 'error', 'message': 'No eligible records found'})}\n\n"
            return
        
        # Send initial status for processing
        yield f"data: {json.dumps({'type': 'processing_start', 'total': total, 'message': f'Starting processing of {total} records'})}\n\n"
        
        # Process records in parallel
        futures = {}
        for record in records:
            future = executor.submit(pdf_processor.process_record, record)
            record_name = feishu_client.get_record_name(record)
            futures[future] = {'record_id': record.record_id, 'name': record_name}
        
        # Collect results and stream updates
        for future in as_completed(futures):
            record_info = futures[future]
            record_id = record_info['record_id']
            record_name = record_info['name']
            
            try:
                success = future.result()
                if success:
                    processed += 1
                    progress_data = {
                        'type': 'progress',
                        'record_id': record_id,
                        'record_name': record_name,
                        'status': 'success',
                        'processed': processed,
                        'failed': failed,
                        'total': total,
                        'message': f'Record {record_name} ({record_id}) processed successfully'
                    }
                    logger.info(f"Record {record_id} processed successfully")
                else:
                    failed += 1
                    failed_records.append(record_id)
                    progress_data = {
                        'type': 'progress',
                        'record_id': record_id,
                        'record_name': record_name,
                        'status': 'failed',
                        'processed': processed,
                        'failed': failed,
                        'total': total,
                        'message': f'Record {record_name} ({record_id}) processing failed'
                    }
                    logger.warning(f"Record {record_id} processing failed")
            except Exception as e:
                failed += 1
                failed_records.append(record_id)
                progress_data = {
                    'type': 'progress',
                    'record_id': record_id,
                    'record_name': record_name,
                    'status': 'error',
                    'processed': processed,
                    'failed': failed,
                    'total': total,
                    'message': f'Record {record_name} ({record_id}) processing error: {str(e)}'
                }
                logger.error(f"Record {record_id} processing error: {e}")
            
            # Stream progress update
            yield f"data: {json.dumps(progress_data)}\n\n"
        
        # Cleanup temporary files
        cleanup_files()
        
        # Send final status
        final_data = {
            'type': 'complete',
            'status': 'success',
            'message': f'Processed {processed} out of {total} records',
            'total': total,
            'processed': processed,
            'failed': failed,
            'failed_records': failed_records
        }
        yield f"data: {json.dumps(final_data)}\n\n"
    except Exception as e:
        logger.error(f"Error in _stream_progress: {e}", exc_info=True)
        error_data = {
            'type': 'error',
            'status': 'error',
            'message': str(e)
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@app.route('/translate/all', methods=['GET'])
def translate_all():
    """Process all eligible records using threading.
    
    Query Parameters:
        stream (optional): If 'true', returns a streaming response with real-time progress updates.
                          Default is 'false' which returns a regular JSON response.
    
    Returns:
        If stream=true: Server-Sent Events (SSE) stream with real-time progress updates
        If stream=false: JSON response with final status and progress information
    """
    # Check if streaming is requested first
    stream_mode = request.args.get('stream', 'false').lower() == 'true'
    
    try:
        logger.info("Starting translation of all eligible records")
        
        # Ensure directories exist
        ensure_directories()
        
        # If streaming mode requested, return SSE stream (which handles pagination internally)
        if stream_mode:
            return Response(
                stream_with_context(_stream_progress()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        
        # Otherwise, use original non-streaming approach
        # Get all eligible records (non-streaming)
        records = feishu_client.list_records()
        
        if not records:
            return jsonify({
                'status': 'success',
                'message': 'No eligible records found',
                'total': 0,
                'processed': 0,
                'failed': 0
            }), 200
        
        total = len(records)
        logger.info(f"Found {total} eligible records to process")
        
        futures = {}
        for record in records:
            future = executor.submit(pdf_processor.process_record, record)
            futures[future] = record.record_id
        
        # Collect results
        processed = 0
        failed = 0
        failed_records = []
        
        for future in as_completed(futures):
            record_id = futures[future]
            try:
                success = future.result()
                if success:
                    processed += 1
                    logger.info(f"Record {record_id} processed successfully")
                else:
                    failed += 1
                    failed_records.append(record_id)
                    logger.warning(f"Record {record_id} processing failed")
            except Exception as e:
                failed += 1
                failed_records.append(record_id)
                logger.error(f"Record {record_id} processing error: {e}")
        
        # Cleanup temporary files
        cleanup_files()
        
        response = {
            'status': 'success',
            'message': f'Processed {processed} out of {total} records',
            'total': total,
            'processed': processed,
            'failed': failed,
            'failed_records': failed_records
        }
        
        logger.info(f"Translation complete: {processed}/{total} successful, {failed} failed")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in translate_all: {e}", exc_info=True)
        if stream_mode:
            # Return SSE stream for error case
            return Response(
                stream_with_context(_stream_error(str(e))),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500


@app.route('/translate/record', methods=['GET'])
def translate_record():
    """Process a single specific record.
    
    Query Parameters:
        record_id: The record ID to process
        
    Returns:
        JSON response with status information
    """
    try:
        record_id = request.args.get('record_id')
        
        if not record_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameter: record_id'
            }), 400
        
        logger.info(f"Starting translation for record {record_id}")
        
        # Ensure directories exist
        ensure_directories()
        
        # Get the specific record
        record = feishu_client.get_record_by_id(record_id)
        
        if not record:
            return jsonify({
                'status': 'error',
                'message': f'Record {record_id} not found'
            }), 404
        
        # Check if record is eligible
        fields = record.fields
        origin_field = fields.get(ORIGIN_COLUMN, {})
        target_file_field = fields.get(TARGET_FILE_COLUMN, {})
        target_context_field = fields.get(TARGET_CONTEXT_COLUMN, {})
        
        origin_has_value = origin_field and isinstance(origin_field, list) and len(origin_field) > 0
        target_file_empty = not target_file_field or not isinstance(target_file_field, list) or len(target_file_field) == 0
        target_context_empty = not target_context_field or (isinstance(target_context_field, str) and not target_context_field.strip())
        
        if not origin_has_value:
            return jsonify({
                'status': 'error',
                'message': f'Record {record_id} has no PDF file in origin column'
            }), 400
        
        if not (target_file_empty and target_context_empty):
            return jsonify({
                'status': 'error',
                'message': f'Record {record_id} already has target columns filled'
            }), 400
        
        # Process the record
        success = pdf_processor.process_record(record)
        
        # Cleanup temporary files
        cleanup_files()
        
        if success:
            logger.info(f"Record {record_id} processed successfully")
            return jsonify({
                'status': 'success',
                'message': f'Record {record_id} processed successfully',
                'record_id': record_id
            }), 200
        else:
            logger.warning(f"Record {record_id} processing failed")
            return jsonify({
                'status': 'error',
                'message': f'Record {record_id} processing failed',
                'record_id': record_id
            }), 500
        
    except Exception as e:
        logger.error(f"Error in translate_record: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint.
    
    Returns:
        JSON response indicating service health
    """
    return jsonify({
        'status': 'healthy',
        'service': 'PDF to MD Translation Service'
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Serve the example client HTML page.
    
    Returns:
        HTML page for testing the translation service
    """
    try:
        from pathlib import Path
        html_path = Path(__file__).parent / 'example_client.html'
        if html_path.exists():
            return html_path.read_text(encoding='utf-8'), 200, {'Content-Type': 'text/html'}
        else:
            return jsonify({
                'message': 'Example client HTML not found. Use /translate/all?stream=true for streaming API.'
            }), 404
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Ensure directories exist on startup
    ensure_directories()
    
    logger.info("Starting PDF to MD Translation Service")
    app.run(host='0.0.0.0', port=5000, debug=False)

