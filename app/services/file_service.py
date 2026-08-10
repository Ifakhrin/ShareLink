import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, Response, stream_with_context
from app.models import db, File, Transfer
from app.services.log_service import log_action, logger

def sanitize_filename(filename):
    if not filename:
        return "unnamed_file"
    cleaned = secure_filename(filename)
    if not cleaned:
        # Fallback if secure_filename stripped everything (e.g. non-ascii only)
        cleaned = f"file_{uuid.uuid4().hex[:8]}"
    return cleaned

def validate_file(file_storage, current_total_size=0):
    """
    Validates a single FileStorage instance.
    Returns (is_valid, error_message, file_size)
    """
    if not file_storage or not file_storage.filename or file_storage.filename.strip() == '':
        return False, "File tidak boleh kosong.", 0

    # Seek to end to get length, then seek back to 0
    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)

    if file_size == 0:
        return False, f"File '{file_storage.filename}' kosong (0 byte). Upload ditolak.", 0

    max_file_size = current_app.config['MAX_FILE_SIZE']
    if file_size > max_file_size:
        max_gb = max_file_size / (1024 * 1024 * 1024)
        return False, f"Ukuran file '{file_storage.filename}' ({file_size / (1024*1024):.1f} MB) melebihi batas maksimum {max_gb:.1f} GB per file.", file_size

    max_transfer_size = current_app.config['MAX_TRANSFER_SIZE']
    if current_total_size + file_size > max_transfer_size:
        max_t_gb = max_transfer_size / (1024 * 1024 * 1024)
        return False, f"Total ukuran transfer melebihi batas maksimum {max_t_gb:.1f} GB per transfer.", file_size

    return True, None, file_size

def save_uploaded_file(file_storage, transfer_id):
    """
    Saves uploaded file to configured upload storage directory with UUID stored_filename.
    Creates File record with status 'UPLOADING'.
    """
    orig_name = sanitize_filename(file_storage.filename)
    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)

    storage_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(storage_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}"
    storage_path = os.path.join(storage_dir, stored_name)

    file_storage.save(storage_path)

    file_record = File(
        transfer_id=transfer_id,
        original_filename=file_storage.filename,  # Original raw name preserved for display metadata
        stored_filename=stored_name,
        file_size=file_size,
        storage_path=storage_path,
        status='UPLOADING',
        uploaded_at=datetime.utcnow()
    )
    db.session.add(file_record)
    db.session.commit()

    return file_record

def delete_physical_file(file_record):
    """
    Removes the physical file from local storage if it exists.
    Returns True if removed or already absent.
    """
    try:
        if file_record.storage_path and os.path.exists(file_record.storage_path):
            os.remove(file_record.storage_path)
            logger.info(f"Physical file deleted: {file_record.storage_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting physical file {file_record.storage_path}: {e}")
        return False

def generate_file_stream_response(file_record, current_user_id, app_obj):
    """
    Streams file to recipient response and deletes physical file immediately upon successful completion.
    """
    storage_path = file_record.storage_path

    if not os.path.exists(storage_path):
        # File is physically missing
        file_record.status = 'DELETED'
        file_record.deleted_at = datetime.utcnow()
        db.session.commit()
        return None, "File fisik tidak ditemukan pada server storage."

    # Update statuses to DOWNLOADING
    file_record.status = 'DOWNLOADING'
    transfer = file_record.transfer
    if transfer.status == 'AVAILABLE':
        transfer.status = 'DOWNLOADING'
    db.session.commit()

    log_action('DOWNLOAD_STARTED', user_id=current_user_id, transfer_id=file_record.transfer_id, details=f"File: {file_record.original_filename}")

    def generate_and_cleanup():
        success = False
        try:
            with open(storage_path, 'rb') as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    yield chunk
            success = True
        except Exception as e:
            logger.error(f"Streaming error for file {file_record.id}: {e}")
            raise e
        finally:
            with app_obj.app_context():
                f_record = File.query.get(file_record.id)
                t_record = Transfer.query.get(file_record.transfer_id) if f_record else None

                if success and f_record:
                    # Download successful: AVAILABLE -> DOWNLOADING -> DOWNLOADED -> DELETED
                    f_record.status = 'DOWNLOADED'
                    f_record.downloaded_at = datetime.utcnow()
                    db.session.commit()

                    # Physically delete file
                    deleted = delete_physical_file(f_record)
                    if deleted:
                        f_record.status = 'DELETED'
                        f_record.deleted_at = datetime.utcnow()
                        db.session.commit()
                        log_action('DOWNLOAD_COMPLETED', user_id=current_user_id, transfer_id=f_record.transfer_id, details=f"File: {f_record.original_filename}")
                        log_action('FILE_DELETED', user_id=current_user_id, transfer_id=f_record.transfer_id, details=f"File: {f_record.original_filename} (Post-download cleanup)")
                else:
                    # Download failed or interrupted: status reverts to AVAILABLE!
                    if f_record and f_record.status == 'DOWNLOADING':
                        f_record.status = 'AVAILABLE'
                        if t_record and t_record.status == 'DOWNLOADING':
                            t_record.status = 'AVAILABLE'
                        db.session.commit()
                        log_action('DOWNLOAD_FAILED', user_id=current_user_id, transfer_id=f_record.transfer_id, details=f"File: {f_record.original_filename} (Connection interrupted)")

                # Check if all files in transfer are completed/deleted
                if t_record:
                    active_files = File.query.filter(
                        File.transfer_id == t_record.id,
                        File.status.in_(['AVAILABLE', 'DOWNLOADING', 'UPLOADING'])
                    ).count()
                    if active_files == 0 and t_record.status in ['AVAILABLE', 'DOWNLOADING']:
                        t_record.status = 'COMPLETED'
                        t_record.completed_at = datetime.utcnow()
                        db.session.commit()

    headers = {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': f'attachment; filename="{secure_filename(file_record.original_filename)}"',
        'Content-Length': str(file_record.file_size)
    }

    return Response(stream_with_context(generate_and_cleanup()), headers=headers), None
