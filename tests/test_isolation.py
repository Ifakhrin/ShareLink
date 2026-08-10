import io
import pytest
from app.models import db, User, Transfer, File

def login(client, username, password='User123!'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

@pytest.fixture
def isolation_setup(app):
    """
    Creates Users:
    - User 1 (id 2, username 'user1')
    - User 2 (id 3, username 'user2')
    - User 3 (id 4, username 'user3')

    Creates Transfers:
    - T1: User 1 -> User 2
    - T2: User 2 -> User 1
    - T3: User 2 -> User 3
    - T4: User 3 -> User 1
    """
    with app.app_context():
        u1 = User.query.filter_by(username='user1').first()
        u2 = User.query.filter_by(username='user2').first()
        u3 = User.query.filter_by(username='user3').first()

        # Helper to create finished AVAILABLE transfer
        def make_t(sender, receiver, name):
            t = Transfer(sender_id=sender.id, receiver_id=receiver.id, subject=f"Subject {name}", transfer_code=f"CODE-{name}", status='AVAILABLE', total_files=1, total_size=100)
            db.session.add(t)
            db.session.commit()
            f = File(transfer_id=t.id, original_filename=f"{name}.txt", stored_filename=f"stored_{name}", file_size=100, storage_path=f"/dummy/{name}", status='AVAILABLE')
            db.session.add(f)
            db.session.commit()
            return t, f

        t1, f1 = make_t(u1, u2, 'T1_U1_to_U2')
        t2, f2 = make_t(u2, u1, 'T2_U2_to_U1')
        t3, f3 = make_t(u2, u3, 'T3_U2_to_U3')
        t4, f4 = make_t(u3, u1, 'T4_U3_to_U1')

        yield {
            'u1': u1, 'u2': u2, 'u3': u3,
            't1': t1, 't2': t2, 't3': t3, 't4': t4,
            'f1': f1, 'f2': f2, 'f3': f3, 'f4': f4
        }

def test_user1_isolation(client, isolation_setup):
    """
    User 1:
    - Sent: T1 only
    - Inbox: T2 and T4 only
    - Access T3 detail: DENIED (403)
    - Download T3 file: DENIED (403)
    - Cancel T3: DENIED (403)
    """
    login(client, 'user1', 'User123!')

    # Sent list
    res_sent = client.get('/sent')
    assert res_sent.status_code == 200
    assert b'T1_U1_to_U2' in res_sent.data
    assert b'T2_U2_to_U1' not in res_sent.data
    assert b'T3_U2_to_U3' not in res_sent.data
    assert b'T4_U3_to_U1' not in res_sent.data

    # Inbox list
    res_inbox = client.get('/inbox')
    assert res_inbox.status_code == 200
    assert b'T2_U2_to_U1' in res_inbox.data
    assert b'T4_U3_to_U1' in res_inbox.data
    assert b'T1_U1_to_U2' not in res_inbox.data
    assert b'T3_U2_to_U3' not in res_inbox.data

    t3_id = isolation_setup['t3'].id
    f3_id = isolation_setup['f3'].id

    # View T3 detail
    res_detail = client.get(f'/transfer/{t3_id}', follow_redirects=True)
    assert res_detail.status_code == 403

    # Download T3 file
    res_dl = client.get(f'/download/{f3_id}', follow_redirects=True)
    assert res_dl.status_code == 403

    # Cancel T3
    res_cancel = client.post(f'/cancel/{t3_id}', follow_redirects=True)
    assert res_cancel.status_code == 403

def test_user2_isolation(client, isolation_setup):
    """
    User 2:
    - Sent: T2 and T3
    - Inbox: T1
    - T4 not visible
    """
    login(client, 'user2', 'User123!')

    # Sent list
    res_sent = client.get('/sent')
    assert res_sent.status_code == 200
    assert b'T2_U2_to_U1' in res_sent.data
    assert b'T3_U2_to_U3' in res_sent.data
    assert b'T1_U1_to_U2' not in res_sent.data
    assert b'T4_U3_to_U1' not in res_sent.data

    # Inbox list
    res_inbox = client.get('/inbox')
    assert res_inbox.status_code == 200
    assert b'T1_U1_to_U2' in res_inbox.data
    assert b'T2_U2_to_U1' not in res_inbox.data
    assert b'T3_U2_to_U3' not in res_inbox.data
    assert b'T4_U3_to_U1' not in res_inbox.data

    t4_id = isolation_setup['t4'].id
    res_detail_t4 = client.get(f'/transfer/{t4_id}', follow_redirects=True)
    assert res_detail_t4.status_code == 403

def test_user3_isolation(client, isolation_setup):
    """
    User 3:
    - Sent: T4
    - Inbox: T3
    - T1 and T2 not visible
    """
    login(client, 'user3', 'User123!')

    # Sent list
    res_sent = client.get('/sent')
    assert res_sent.status_code == 200
    assert b'T4_U3_to_U1' in res_sent.data
    assert b'T1_U1_to_U2' not in res_sent.data
    assert b'T2_U2_to_U1' not in res_sent.data

    # Inbox list
    res_inbox = client.get('/inbox')
    assert res_inbox.status_code == 200
    assert b'T3_U2_to_U3' in res_inbox.data
    assert b'T1_U1_to_U2' not in res_inbox.data
    assert b'T2_U2_to_U1' not in res_inbox.data

    t1_id = isolation_setup['t1'].id
    res_t1 = client.get(f'/transfer/{t1_id}', follow_redirects=True)
    assert res_t1.status_code == 403

def test_admin_monitoring_sees_all(client, isolation_setup):
    """
    Admin sees all metadata in /admin/transfers
    """
    login(client, 'admin', 'Admin123!')

    res_admin = client.get('/admin/transfers')
    assert res_admin.status_code == 200
    assert b'T1_U1_to_U2' in res_admin.data
    assert b'T2_U2_to_U1' in res_admin.data
    assert b'T3_U2_to_U3' in res_admin.data
    assert b'T4_U3_to_U1' in res_admin.data
