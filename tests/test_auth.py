import pytest
from flask import session

def test_login_success(client):
    """Test 1: Login succeeds with correct credentials."""
    res = client.post('/login', data={'username': 'user1', 'password': 'User123!'}, follow_redirects=True)
    assert res.status_code == 200
    assert b'Selamat datang' in res.data or b'Dashboard' in res.data
    with client.session_transaction() as sess:
        assert sess.get('user_id') is not None

def test_login_failure(client):
    """Test 2: Login fails with invalid credentials."""
    res = client.post('/login', data={'username': 'user1', 'password': 'wrongpassword'}, follow_redirects=True)
    assert res.status_code == 200
    assert b'Username atau password salah' in res.data
    with client.session_transaction() as sess:
        assert sess.get('user_id') is None

def test_unauthenticated_dashboard_redirect(client):
    """Test 3: Unauthenticated user is redirected when accessing dashboard."""
    res = client.get('/dashboard', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location
