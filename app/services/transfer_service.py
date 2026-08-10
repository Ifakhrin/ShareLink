import secrets
import string
from datetime import datetime, timedelta
from flask import current_app
from app.models import db, Transfer, File, User
from app.services.file_service import delete_physical_file
from app.services.log_service import log_action

def generate_transfer_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        part1 = ''.join(secrets.choice(chars) for _ in range(4))
        part2 = ''.join(secrets.choice(chars) for _ in range(5))
        part3 = ''.join(secrets.choice(chars) for _ in range(2))
        code = f"{part1}-{part2}-{part3}"
        if not Transfer.query.filter_by(transfer_code=code).first():
            return code

def create_transfer(sender_id, receiver_id, subject='(Tanpa Judul)', message=None):
    if sender_id == receiver_id:
        return None, "Pengirim dan penerima tidak boleh merupakan akun yang sama."

    receiver = User.query.get(receiver_id)
    if not receiver:
        return None, "Penerima file tidak ditemukan."

    # Validate subject
    if not subject or not subject.strip():
        return None, "Judul transfer wajib diisi."
    
    subject = subject.strip()
    if len(subject) > 150:
        return None, "Judul transfer maksimal 150 karakter."

    # Validate message
    if message:
        message = message.strip()
        if len(message) > 2000:
            return None, "Pesan pengantar maksimal 2.000 karakter."

    code = generate_transfer_code()
    transfer = Transfer(
        sender_id=sender_id,
        receiver_id=receiver_id,
        subject=subject,
        message=message if message else None,
        transfer_code=code,
        status='PENDING',
        total_files=0,
        total_size=0,
        created_at=datetime.utcnow()
    )
    db.session.add(transfer)
    db.session.commit()

    log_action('FILE_UPLOAD_STARTED', user_id=sender_id, transfer_id=transfer.id, details=f"Judul: {subject} | Penerima: {receiver.username}")
    return transfer, None

def finalize_transfer(transfer_id):
    transfer = Transfer.query.get(transfer_id)
    if not transfer:
        return None, "Transfer tidak ditemukan."

    files = File.query.filter_by(transfer_id=transfer_id).all()
    if not files:
        db.session.delete(transfer)
        db.session.commit()
        return None, "Transfer gagal: tidak ada file yang diunggah."

    total_size = sum(f.file_size for f in files)
    transfer.total_files = len(files)
    transfer.total_size = total_size

    exp_hours = current_app.config['FILE_EXPIRATION_HOURS']
    transfer.expires_at = datetime.utcnow() + timedelta(hours=exp_hours)
    transfer.status = 'AVAILABLE'

    for f in files:
        f.status = 'AVAILABLE'

    db.session.commit()

    log_action('FILE_UPLOADED', user_id=transfer.sender_id, transfer_id=transfer.id,
               details=f"Transfer {transfer.transfer_code} ({len(files)} file, {total_size / (1024*1024):.2f} MB)")

    return transfer, None

def cancel_transfer(transfer_id, user_id, is_admin=False):
    transfer = Transfer.query.get(transfer_id)
    if not transfer:
        return False, "Transfer tidak ditemukan."

    if not is_admin and transfer.sender_id != user_id:
        return False, "Anda tidak memiliki hak akses untuk membatalkan transfer ini."

    if transfer.status in ['CANCELLED', 'EXPIRED', 'COMPLETED', 'DELETED']:
        return False, f"Transfer sudah dalam status {transfer.status} dan tidak dapat dibatalkan."

    transfer.status = 'CANCELLED'
    transfer.cancelled_at = datetime.utcnow()

    # Physically delete files
    for file_record in transfer.files:
        if file_record.status not in ['DELETED', 'CANCELLED']:
            delete_physical_file(file_record)
            file_record.status = 'CANCELLED'
            file_record.deleted_at = datetime.utcnow()

    db.session.commit()

    log_action('TRANSFER_CANCELLED', user_id=user_id, transfer_id=transfer.id, details="Transfer dibatalkan pengirim/admin")
    return True, "Transfer berhasil dibatalkan."

def cleanup_expired_transfers():
    """
    Service function to check and clean up expired transfers and delete their physical files.
    Can be run via CLI or triggered periodically.
    """
    now = datetime.utcnow()
    expired_transfers = Transfer.query.filter(
        Transfer.status.in_(['AVAILABLE', 'DOWNLOADING', 'PENDING']),
        Transfer.expires_at.isnot(None),
        Transfer.expires_at <= now
    ).all()

    cleaned_count = 0
    for transfer in expired_transfers:
        transfer.status = 'EXPIRED'
        for f in transfer.files:
            if f.status not in ['DELETED', 'EXPIRED']:
                delete_physical_file(f)
                f.status = 'EXPIRED'
                f.deleted_at = now

        log_action('TRANSFER_EXPIRED', user_id=None, transfer_id=transfer.id, details=f"Transfer expired pada {transfer.expires_at}")
        cleaned_count += 1

    if cleaned_count > 0:
        db.session.commit()

    return cleaned_count

def admin_delete_transfer(transfer_id, admin_id):
    transfer = Transfer.query.get(transfer_id)
    if not transfer:
        return False, "Transfer tidak ditemukan."

    transfer.status = 'DELETED'
    for f in transfer.files:
        delete_physical_file(f)
        f.status = 'DELETED'
        f.deleted_at = datetime.utcnow()

    db.session.commit()
    log_action('FILE_DELETED', user_id=admin_id, transfer_id=transfer.id, details="Penghapusan manual oleh Admin")
    return True, "Transfer berhasil dihapus oleh admin."
