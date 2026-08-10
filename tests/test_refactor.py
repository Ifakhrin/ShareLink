import io
import pytest
from app.models import db, User, Transfer, File

def login(client, username, password):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=False)

def test_acceptance_1_admin_login_redirect_and_dashboard(client):
    """TEST 1: Login as admin redirects to /admin and shows Admin Dashboard without Kirim File."""
    res = login(client, 'admin', 'Admin123!')
    assert res.status_code == 302
    assert '/admin' in res.location

    res_admin = client.get('/admin', follow_redirects=True)
    assert res_admin.status_code == 200
    assert b'Dashboard Administrator' in res_admin.data
    assert b'Kirim File Baru' not in res_admin.data
    assert b'File Masuk' not in res_admin.data

def test_acceptance_2_user_login_redirect_and_dashboard(client):
    """TEST 2: Login as user redirects to /dashboard and shows Kirim File, File Masuk, File Terkirim."""
    res = login(client, 'user1', 'User123!')
    assert res.status_code == 302
    assert '/dashboard' in res.location

    res_dash = client.get('/dashboard', follow_redirects=True)
    assert res_dash.status_code == 200
    assert b'Kirim File Baru' in res_dash.data
    assert b'File Masuk' in res_dash.data
    assert b'File Terkirim' in res_dash.data

def test_acceptance_3_admin_access_send_rejected(client):
    """TEST 3: Admin opening /send is rejected with 403 Forbidden."""
    login(client, 'admin', 'Admin123!')
    res = client.get('/send', follow_redirects=True)
    assert res.status_code == 403

def test_acceptance_4_admin_access_inbox_rejected(client):
    """TEST 4: Admin opening /inbox is rejected with 403 Forbidden."""
    login(client, 'admin', 'Admin123!')
    res = client.get('/inbox', follow_redirects=True)
    assert res.status_code == 403

def test_acceptance_5_user_access_admin_rejected(client):
    """TEST 5: Normal user opening /admin is rejected with 403 Forbidden."""
    login(client, 'user1', 'User123!')
    res = client.get('/admin', follow_redirects=True)
    assert res.status_code == 403

def test_acceptance_6_admin_creates_new_user(client, app):
    """TEST 6: Admin creates a new user account successfully."""
    login(client, 'admin', 'Admin123!')
    res = client.post('/admin/users/create', data={
        'name': 'New Staff',
        'username': 'newstaff',
        'password': 'Password123!',
        'role': 'user'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'berhasil dibuat' in res.data

    with app.app_context():
        u = User.query.filter_by(username='newstaff').first()
        assert u is not None
        assert u.name == 'New Staff'
        assert u.role == 'user'
        assert u.is_active is True

def test_acceptance_7_new_user_login_redirects_to_user_dashboard(client, app):
    """TEST 7: Newly created user logs in and is redirected to /dashboard."""
    # First admin creates user
    login(client, 'admin', 'Admin123!')
    client.post('/admin/users/create', data={
        'name': 'New Staff 2',
        'username': 'newstaff2',
        'password': 'Password123!',
        'role': 'user'
    })
    client.get('/logout')

    # Now new user logs in
    res = login(client, 'newstaff2', 'Password123!')
    assert res.status_code == 302
    assert '/dashboard' in res.location

def test_acceptance_8_admin_views_transfers_metadata(client, app):
    """TEST 8: Admin views /admin/transfers and sees metadata of all transfers."""
    # User 1 sends file to User 2
    login(client, 'user1', 'User123!')
    client.post('/send', data={'receiver_id': 3, 'subject': 'Meta Test Subject', 'files': (io.BytesIO(b'metadata test'), 'meta.txt')})
    client.get('/logout')

    # Admin views /admin/transfers
    login(client, 'admin', 'Admin123!')
    res = client.get('/admin/transfers')
    assert res.status_code == 200
    assert b'meta.txt' in res.data or b'user1' in res.data or b'user2' in res.data

def test_acceptance_9_admin_not_in_recipient_dropdown(client, app):
    """TEST 9: Admin account does NOT appear in recipient list on /send."""
    login(client, 'user1', 'User123!')
    res = client.get('/send')
    assert res.status_code == 200
    # Admin username is 'admin'
    assert b'@admin' not in res.data

def test_acceptance_10_user_cannot_access_user_management(client):
    """TEST 10: User trying to access /admin/users gets 403 Forbidden."""
    login(client, 'user1', 'User123!')
    res = client.get('/admin/users', follow_redirects=True)
    assert res.status_code == 403
