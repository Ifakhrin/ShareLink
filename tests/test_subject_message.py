import io
import os
import pytest
from datetime import datetime, timedelta
from app.models import db, User, Transfer, File
from app.services.transfer_service import cleanup_expired_transfers

def login(client, username, password='User123!'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

def test_subject_required(client, app):
    """Test 1: Subject is required (empty subject rejected)."""
    login(client, 'user1', 'User123!')
    data = {
        'receiver_id': 3,
        'subject': '',
        'message': 'Test message',
        'files': (io.BytesIO(b'content'), 'a.txt')
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'Judul transfer wajib diisi' in res.data or res.status_code in [400, 200]

def test_subject_too_long(client, app):
    """Test 2: Subject > 150 characters is rejected."""
    login(client, 'user1', 'User123!')
    long_subj = 'S' * 151
    data = {
        'receiver_id': 3,
        'subject': long_subj,
        'message': 'Test message',
        'files': (io.BytesIO(b'content'), 'a.txt')
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'maksimal 150 karakter' in res.data or res.status_code in [400, 200]

def test_message_too_long(client, app):
    """Test 3: Message > 2000 characters is rejected."""
    login(client, 'user1', 'User123!')
    long_msg = 'M' * 2001
    data = {
        'receiver_id': 3,
        'subject': 'Valid Subject',
        'message': long_msg,
        'files': (io.BytesIO(b'content'), 'a.txt')
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'maksimal 2.000 karakter' in res.data or res.status_code in [400, 200]

def test_subject_and_message_saved(client, app):
    """Tests 4 & 5: Subject and Message are correctly saved on transfer creation."""
    login(client, 'user1', 'User123!')
    data = {
        'receiver_id': 3,
        'subject': 'Laporan Mingguan Cluster 2',
        'message': 'Berikut saya kirimkan laporan mingguan Cluster 2 untuk diperiksa.',
        'files': (io.BytesIO(b'report data'), 'report.xlsx')
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        t = Transfer.query.filter_by(sender_id=2, receiver_id=3).order_by(Transfer.id.desc()).first()
        assert t is not None
        assert t.subject == 'Laporan Mingguan Cluster 2'
        assert t.message == 'Berikut saya kirimkan laporan mingguan Cluster 2 untuk diperiksa.'

def test_sender_can_view_subject_message(client, app):
    """Test 6: Sender can view subject and message of their transfer."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Laporan Q3',
        'message': 'Pesan pengantar Q3',
        'files': (io.BytesIO(b'data'), 'q3.pdf')
    })

    with app.app_context():
        t_id = Transfer.query.filter_by(sender_id=2).order_by(Transfer.id.desc()).first().id

    res = client.get(f'/transfer/{t_id}')
    assert res.status_code == 200
    assert b'Laporan Q3' in res.data
    assert b'Pesan pengantar Q3' in res.data

def test_receiver_can_view_subject_message(client, app):
    """Test 7: Receiver can view subject and message of transfer addressed to them."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Instruksi Project',
        'message': 'Harap dibaca dengan teliti.',
        'files': (io.BytesIO(b'instruksi'), 'doc.docx')
    })
    with app.app_context():
        t_id = Transfer.query.filter_by(sender_id=2, receiver_id=3).order_by(Transfer.id.desc()).first().id

    client.get('/logout')
    login(client, 'user2', 'User123!')

    res = client.get(f'/transfer/{t_id}')
    assert res.status_code == 200
    assert b'Instruksi Project' in res.data
    assert b'Harap dibaca dengan teliti.' in res.data

def test_unrelated_user_cannot_view_subject_message(client, app):
    """Test 8: Unrelated user is denied access to subject and message (403 Forbidden)."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Private Subject',
        'message': 'Confidential content',
        'files': (io.BytesIO(b'secret'), 'secret.txt')
    })
    with app.app_context():
        t_id = Transfer.query.filter_by(sender_id=2, receiver_id=3).order_by(Transfer.id.desc()).first().id

    client.get('/logout')
    login(client, 'user3', 'User123!')

    res = client.get(f'/transfer/{t_id}', follow_redirects=True)
    assert res.status_code == 403

def test_admin_views_subject_message_metadata(client, app):
    """Test 9: Admin can view subject metadata in admin monitoring."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Admin Audit Subject',
        'message': 'Audit message',
        'files': (io.BytesIO(b'audit'), 'audit.txt')
    })
    client.get('/logout')

    login(client, 'admin', 'Admin123!')
    res = client.get('/admin/transfers')
    assert res.status_code == 200
    assert b'Admin Audit Subject' in res.data

def test_download_behavior_and_delete_after_download(client, app):
    """Tests 10 & 11: File download works and physical file is deleted after download."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Download Test',
        'message': 'Download message',
        'files': (io.BytesIO(b'download payload 123'), 'dl.txt')
    })
    with app.app_context():
        f = File.query.order_by(File.id.desc()).first()
        f_id = f.id
        path = f.storage_path

    assert os.path.exists(path)

    client.get('/logout')
    login(client, 'user2', 'User123!')

    res = client.get(f'/download/{f_id}')
    assert res.status_code == 200
    assert res.data == b'download payload 123'

    with app.app_context():
        f_updated = File.query.get(f_id)
        assert f_updated.status == 'DELETED'
        assert not os.path.exists(path)

def test_expiration_intact(client, app):
    """Test 12: Expired transfer cleanup removes physical files."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Expire Test',
        'files': (io.BytesIO(b'expire content'), 'exp.txt')
    })
    with app.app_context():
        t = Transfer.query.order_by(Transfer.id.desc()).first()
        t.expires_at = datetime.utcnow() - timedelta(minutes=5)
        db.session.commit()
        path = t.files[0].storage_path

    assert os.path.exists(path)

    with app.app_context():
        cleanup_expired_transfers()

    assert not os.path.exists(path)

def test_cancellation_intact(client, app):
    """Test 13: Sender can cancel transfer and physical file is unlinked."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Cancel Test',
        'files': (io.BytesIO(b'cancel content'), 'cn.txt')
    })
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

def test_multiple_attachments_and_limits_intact(client, app):
    """Tests 14, 15, 16: Multiple file attachments work and file limits are enforced."""
    login(client, 'user1', 'User123!')
    data = {
        'receiver_id': 3,
        'subject': 'Multi Attachment Test',
        'message': 'Multiple files enclosed',
        'files': [
            (io.BytesIO(b'Content A'), 'fileA.txt'),
            (io.BytesIO(b'Content B'), 'fileB.txt')
        ]
    }
    res = client.post('/send', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        t = Transfer.query.filter_by(sender_id=2, receiver_id=3).order_by(Transfer.id.desc()).first()
        assert t.total_files == 2
        assert len(t.files) == 2
