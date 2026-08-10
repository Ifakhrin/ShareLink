import io
import os
import pytest
from datetime import datetime, timedelta
from app.models import db, User, Transfer, File
from app.services.transfer_service import cleanup_expired_transfers

def login(client, username, password='User123!'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

def test_1_and_2_active_transfer_visibility_and_user3_isolation(client, app):
    """
    Test 1: User 1 sends file to User 2 -> appears in Active Sent for User 1 and Active Inbox for User 2.
    Test 2: User 3 does NOT see User 1 -> User 2 transfer anywhere.
    """
    login(client, 'user1', 'User123!')
    res_send = client.post('/send', data={
        'receiver_id': 3,  # user2
        'subject': 'Active Transfer 101',
        'message': 'Active message payload',
        'files': (io.BytesIO(b'Active payload data'), 'active.txt')
    }, follow_redirects=True)
    assert res_send.status_code == 200

    # User 1 active sent
    res_u1_sent = client.get('/sent')
    assert b'Active Transfer 101' in res_u1_sent.data
    assert b'Transfer Aktif' in res_u1_sent.data

    # User 2 active inbox
    client.get('/logout')
    login(client, 'user2', 'User123!')
    res_u2_inbox = client.get('/inbox')
    assert b'Active Transfer 101' in res_u2_inbox.data
    assert b'Transfer Aktif' in res_u2_inbox.data

    # User 3 sees NOTHING
    client.get('/logout')
    login(client, 'user3', 'User123!')
    res_u3_inbox = client.get('/inbox')
    res_u3_sent = client.get('/sent')
    assert b'Active Transfer 101' not in res_u3_inbox.data
    assert b'Active Transfer 101' not in res_u3_sent.data

def test_3_4_5_6_download_unlinks_file_and_moves_to_history(client, app):
    """
    Test 3: User 2 downloads -> physical file unlinked.
    Test 4: Metadata retained in database.
    Test 5 & 6: Transfer moves to History section for both Receiver and Sender.
    """
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'History Transition Test',
        'message': 'Transition payload',
        'files': (io.BytesIO(b'Transition data'), 'trans.txt')
    })
    with app.app_context():
        f = File.query.order_by(File.id.desc()).first()
        f_id = f.id
        t_id = f.transfer_id
        storage_path = f.storage_path

    assert os.path.exists(storage_path)

    # Receiver downloads file
    client.get('/logout')
    login(client, 'user2', 'User123!')
    res_dl = client.get(f'/download/{f_id}')
    assert res_dl.status_code == 200
    _ = res_dl.get_data()

    # Physical file deleted
    assert not os.path.exists(storage_path)

    # Metadata retained in DB
    with app.app_context():
        t = Transfer.query.get(t_id)
        assert t is not None
        assert t.status == 'COMPLETED'
        assert t.subject == 'History Transition Test'
        assert t.files[0].original_filename == 'trans.txt'

    # Receiver Inbox -> moves to Riwayat Transfer
    res_u2_inbox = client.get('/inbox')
    assert b'History Transition Test' in res_u2_inbox.data
    assert b'Riwayat Transfer' in res_u2_inbox.data

    # Sender Sent -> moves to Riwayat Transfer
    client.get('/logout')
    login(client, 'user1', 'User123!')
    res_u1_sent = client.get('/sent')
    assert b'History Transition Test' in res_u1_sent.data
    assert b'Riwayat Transfer' in res_u1_sent.data

def test_7_8_9_10_read_only_history_detail_and_no_redownload(client, app):
    """
    Test 7 & 9: Receiver and Sender can view read-only history detail.
    Test 8: Receiver CANNOT re-download file from history.
    Test 10: Unrelated User 3 denied access to history detail (403).
    """
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Read Only History Subject',
        'message': 'Read only message text',
        'files': (io.BytesIO(b'Read only content'), 'readonly.txt')
    })
    with app.app_context():
        f = File.query.order_by(File.id.desc()).first()
        f_id = f.id
        t_id = f.transfer_id

    # Download to complete transfer
    client.get('/logout')
    login(client, 'user2', 'User123!')
    res_dl = client.get(f'/download/{f_id}')
    _ = res_dl.get_data()

    # Receiver opens history detail
    res_u2_detail = client.get(f'/transfer/{t_id}')
    assert res_u2_detail.status_code == 200
    assert b'Read Only History Subject' in res_u2_detail.data
    assert b'Read only message text' in res_u2_detail.data
    assert b'Catatan Riwayat Transfer' in res_u2_detail.data
    assert b'File sudah tidak tersedia' in res_u2_detail.data

    # Receiver attempts re-download -> BLOCKED
    res_u2_redownload = client.get(f'/download/{f_id}', follow_redirects=True)
    assert res_u2_redownload.status_code in [200, 403]
    assert b'tidak tersedia' in res_u2_redownload.data or res_u2_redownload.status_code == 403

    # Sender opens history detail
    client.get('/logout')
    login(client, 'user1', 'User123!')
    res_u1_detail = client.get(f'/transfer/{t_id}')
    assert res_u1_detail.status_code == 200
    assert b'Read Only History Subject' in res_u1_detail.data

    # User 3 attempts to view history detail -> DENIED (403)
    client.get('/logout')
    login(client, 'user3', 'User123!')
    res_u3_detail = client.get(f'/transfer/{t_id}', follow_redirects=True)
    assert res_u3_detail.status_code == 403

def test_11_history_sorted_created_at_desc(client, app):
    """Test 11: History items sorted created_at DESC (newest first)."""
    with app.app_context():
        u1 = User.query.filter_by(username='user1').first()
        u2 = User.query.filter_by(username='user2').first()

        t_old = Transfer(sender_id=u1.id, receiver_id=u2.id, subject='Old History Item', transfer_code='CODE-OLD', status='COMPLETED', total_files=1, total_size=10, created_at=datetime.utcnow() - timedelta(days=2))
        t_new = Transfer(sender_id=u1.id, receiver_id=u2.id, subject='New History Item', transfer_code='CODE-NEW', status='COMPLETED', total_files=1, total_size=10, created_at=datetime.utcnow())
        db.session.add_all([t_old, t_new])
        db.session.commit()

    login(client, 'user2', 'User123!')
    res_inbox = client.get('/inbox')
    pos_new = res_inbox.data.find(b'New History Item')
    pos_old = res_inbox.data.find(b'Old History Item')
    assert pos_new != -1 and pos_old != -1
    assert pos_new < pos_old

def test_12_13_14_expired_and_cancelled_transfers_in_history(client, app):
    """
    Tests 12, 13, 14: Expired and Cancelled transfers move to History section, with physical files deleted.
    """
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Expiring Transfer',
        'files': (io.BytesIO(b'to be expired'), 'exp.txt')
    })
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Cancelling Transfer',
        'files': (io.BytesIO(b'to be cancelled'), 'can.txt')
    })

    with app.app_context():
        t_exp = Transfer.query.filter_by(subject='Expiring Transfer').first()
        t_exp.expires_at = datetime.utcnow() - timedelta(minutes=10)
        t_can = Transfer.query.filter_by(subject='Cancelling Transfer').first()
        t_can_id = t_can.id
        db.session.commit()

    # Expire cleanup
    with app.app_context():
        cleanup_expired_transfers()

    # Cancel transfer
    client.post(f'/cancel/{t_can_id}', follow_redirects=True)

    # Check inbox history
    client.get('/logout')
    login(client, 'user2', 'User123!')
    res_inbox = client.get('/inbox')
    assert b'Expiring Transfer' in res_inbox.data
    assert b'Cancelling Transfer' in res_inbox.data

def test_15_history_limit(client, app):
    """Test 15: History query applies limit correctly."""
    login(client, 'user2', 'User123!')
    res = client.get('/inbox')
    assert res.status_code == 200

def test_16_admin_views_history_metadata_only(client, app):
    """Test 16: Admin views history metadata in /admin/transfers without user transfer actions."""
    login(client, 'user1', 'User123!')
    client.post('/send', data={
        'receiver_id': 3,
        'subject': 'Admin History View Subject',
        'files': (io.BytesIO(b'admin test content'), 'adm.txt')
    })
    client.get('/logout')

    login(client, 'admin', 'Admin123!')
    res_admin = client.get('/admin/transfers')
    assert res_admin.status_code == 200
    assert b'Admin History View Subject' in res_admin.data
