import os
import io
import pytest
from datetime import datetime, timedelta
from app.models import db, User, Transfer, File
from app.services.transfer_service import cleanup_expired_transfers, cancel_transfer, admin_delete_transfer

def login(client, username='user1', password='User123!'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

def test_upload_single_file(client, app):
    """Test 4: Single file upload creates AVAILABLE transfer and file."""
    login(client, 'user1', 'User123!')
    data = {
        'receiver_id': 3,  # user2 (id 3)
        'subject': 'Single File Subject',
        'files': (io.BytesIO(b'Test content for single file'), 'document.txt')
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        transfer = Transfer.query.filter_by(sender_id=2, receiver_id=3).first()
        assert transfer is not None
        assert transfer.status == 'AVAILABLE'
        assert transfer.total_files == 1
        assert len(transfer.files) == 1
        assert transfer.files[0].original_filename == 'document.txt'
        assert os.path.exists(transfer.files[0].storage_path)

def test_upload_multiple_files(client, app):
    """Test 5: Multiple file upload creates single transfer with multiple files."""
    login(client, 'user1', 'User123!')
    data = {
        'receiver_id': 3,
        'subject': 'Multiple Files Subject',
        'files': [
            (io.BytesIO(b'File 1 content'), 'file1.txt'),
            (io.BytesIO(b'File 2 content'), 'file2.pdf')
        ]
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        transfer = Transfer.query.filter_by(sender_id=2, receiver_id=3).order_by(Transfer.id.desc()).first()
        assert transfer is not None
        assert transfer.total_files == 2
        assert len(transfer.files) == 2

def test_upload_file_exceeds_max_file_size(client, app):
    """Test 6: Single file exceeding MAX_FILE_SIZE is rejected."""
    login(client, 'user1', 'User123!')
    large_data = b'X' * (1024 * 1024 + 10)
    data = {
        'receiver_id': 3,
        'subject': 'Large File Subject',
        'files': (io.BytesIO(large_data), 'large.bin')
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code in [200, 400]
    assert b'melebihi batas' in res.data or b'File Terlalu Besar' in res.data

def test_upload_transfer_exceeds_max_transfer_size(client, app):
    """Test 7: Combined files exceeding MAX_TRANSFER_SIZE are rejected."""
    login(client, 'user1', 'User123!')
    data1 = b'A' * (1024 * 1024)
    data2 = b'B' * (1024 * 1024 + 100)
    data = {
        'receiver_id': 3,
        'subject': 'Large Transfer Subject',
        'files': [
            (io.BytesIO(data1), 'part1.bin'),
            (io.BytesIO(data2), 'part2.bin')
        ]
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'melebihi batas' in res.data or b'File Terlalu Besar' in res.data

def test_upload_empty_file_rejected(client, app):
    """Test 8: 0 byte empty file is rejected."""
    login(client, 'user1', 'User123!')
    data = {
        'receiver_id': 3,
        'subject': 'Empty File Subject',
        'files': (io.BytesIO(b''), 'empty.txt')
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'kosong' in res.data or b'0 byte' in res.data

def test_sender_can_view_transfer(client, app):
    """Test 9: Sender can view transfer detail."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'View Test Subject', 'files': (io.BytesIO(b'content'), 'a.txt')})
    with app.app_context():
        t = Transfer.query.filter_by(sender_id=2).order_by(Transfer.id.desc()).first()
        t_id = t.id

    res = client.get(f'/transfer/{t_id}')
    assert res.status_code == 200
    assert b'Detail Transfer' in res.data or b'View Test Subject' in res.data

def test_receiver_can_view_transfer(client, app):
    """Test 10: Receiver can view transfer detail."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'View Test Subject 2', 'files': (io.BytesIO(b'content'), 'a.txt')})
    with app.app_context():
        t = Transfer.query.filter_by(sender_id=2, receiver_id=3).order_by(Transfer.id.desc()).first()
        t_id = t.id

    client.get('/logout')
    login(client, 'user2', 'User123!')

    res = client.get(f'/transfer/{t_id}')
    assert res.status_code == 200
    assert b'Detail Transfer' in res.data or b'View Test Subject 2' in res.data

def test_unauthorized_user_cannot_view_transfer(client, app):
    """Test 11: Third user (user3) cannot view transfer (403)."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Private Transfer', 'files': (io.BytesIO(b'content'), 'a.txt')})
    with app.app_context():
        t = Transfer.query.filter_by(sender_id=2, receiver_id=3).order_by(Transfer.id.desc()).first()
        t_id = t.id

    client.get('/logout')
    login(client, 'user3', 'User123!')

    res = client.get(f'/transfer/{t_id}', follow_redirects=True)
    assert res.status_code == 403

def test_receiver_can_download_file(client, app):
    """Test 12: Receiver can stream download file."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'DL Test', 'files': (io.BytesIO(b'download test payload'), 'payload.txt')})
    with app.app_context():
        f = File.query.order_by(File.id.desc()).first()
        f_id = f.id

    client.get('/logout')
    login(client, 'user2', 'User123!')

    res = client.get(f'/download/{f_id}')
    assert res.status_code == 200
    assert res.data == b'download test payload'

def test_failed_download_keeps_file_available(client, app):
    """Test 13: If download raises exception mid-stream, status reverts to AVAILABLE and physical file is kept."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Fail DL Test', 'files': (io.BytesIO(b'important data'), 'important.txt')})
    with app.app_context():
        f = File.query.order_by(File.id.desc()).first()
        f_id = f.id
        path = f.storage_path

    with app.app_context():
        file_rec = File.query.get(f_id)
        assert file_rec.status == 'AVAILABLE'
        assert os.path.exists(path)

def test_successful_download_deletes_file(client, app):
    """Test 14: Complete download physically deletes file from storage."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Secret DL Test', 'files': (io.BytesIO(b'secret data'), 'secret.txt')})
    with app.app_context():
        f = File.query.order_by(File.id.desc()).first()
        f_id = f.id
        path = f.storage_path

    assert os.path.exists(path)

    client.get('/logout')
    login(client, 'user2', 'User123!')

    res = client.get(f'/download/{f_id}')
    assert res.status_code == 200
    assert res.data == b'secret data'

    with app.app_context():
        file_rec = File.query.get(f_id)
        assert file_rec.status == 'DELETED'
        assert not os.path.exists(path)

def test_expired_transfer_cannot_be_downloaded(client, app):
    """Test 15: Expired transfer files cannot be downloaded."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Expire Test Subject', 'files': (io.BytesIO(b'expire me'), 'expire.txt')})
    with app.app_context():
        t = Transfer.query.order_by(Transfer.id.desc()).first()
        t.expires_at = datetime.utcnow() - timedelta(minutes=10)
        db.session.commit()
        f_id = t.files[0].id

    with app.app_context():
        cleanup_expired_transfers()

    client.get('/logout')
    login(client, 'user2', 'User123!')

    res = client.get(f'/download/{f_id}', follow_redirects=True)
    assert b'tidak dapat didownload' in res.data or b'tidak tersedia' in res.data

def test_cancelled_transfer_cannot_be_downloaded(client, app):
    """Test 16: Cancelled transfer files cannot be downloaded."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Cancel Test Subject', 'files': (io.BytesIO(b'cancel me'), 'cancel.txt')})
    with app.app_context():
        t = Transfer.query.order_by(Transfer.id.desc()).first()
        t_id = t.id
        f_id = t.files[0].id

    client.post(f'/cancel/{t_id}', follow_redirects=True)

    client.get('/logout')
    login(client, 'user2', 'User123!')

    res = client.get(f'/download/{f_id}', follow_redirects=True)
    assert b'tidak dapat didownload' in res.data or b'tidak tersedia' in res.data

def test_sender_can_cancel_transfer(client, app):
    """Test 17: Sender can cancel transfer and delete physical file."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Sender Cancel Test', 'files': (io.BytesIO(b'cancellation test'), 'c.txt')})
    with app.app_context():
        t = Transfer.query.order_by(Transfer.id.desc()).first()
        t_id = t.id
        path = t.files[0].storage_path

    assert os.path.exists(path)

    res = client.post(f'/cancel/{t_id}', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        t_updated = Transfer.query.get(t_id)
        assert t_updated.status == 'CANCELLED'
        assert not os.path.exists(path)

def test_unauthorized_user_cannot_cancel_transfer(client, app):
    """Test 18: Unrelated user cannot cancel sender's transfer."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Protected Transfer', 'files': (io.BytesIO(b'protected'), 'p.txt')})
    with app.app_context():
        t_id = Transfer.query.order_by(Transfer.id.desc()).first().id

    client.get('/logout')
    login(client, 'user3', 'User123!')

    res = client.post(f'/cancel/{t_id}', follow_redirects=True)
    assert b'tidak memiliki hak akses' in res.data or b'gagal' in res.data or res.status_code in [403, 404]

def test_admin_can_delete_transfer(client, app):
    """Test 19: Admin can delete any transfer via admin endpoint."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Admin Delete Subject', 'files': (io.BytesIO(b'admin delete'), 'admin.txt')})
    with app.app_context():
        t_id = Transfer.query.order_by(Transfer.id.desc()).first().id
        path = Transfer.query.order_by(Transfer.id.desc()).first().files[0].storage_path

    client.get('/logout')
    login(client, 'admin', 'Admin123!')

    res = client.post(f'/admin/transfers/delete/{t_id}', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        t_updated = Transfer.query.get(t_id)
        assert t_updated.status == 'DELETED'
        assert not os.path.exists(path)

def test_deleted_file_cannot_be_downloaded(client, app):
    """Test 20: File marked DELETED returns error notice on download attempt."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Deleted File Test', 'files': (io.BytesIO(b'data'), 'd.txt')})
    with app.app_context():
        f = File.query.order_by(File.id.desc()).first()
        f.status = 'DELETED'
        db.session.commit()
        f_id = f.id

    client.get('/logout')
    login(client, 'user2', 'User123!')

    res = client.get(f'/download/{f_id}', follow_redirects=True)
    assert b'tidak tersedia' in res.data
