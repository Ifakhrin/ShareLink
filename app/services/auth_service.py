from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, jsonify
from app.models import User

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user and user.is_active:
            return user
        elif user and not user.is_active:
            # Sesi user nonaktif -> clear session
            session.clear()
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not get_current_user():
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Unauthorized', 'message': 'Silakan login terlebih dahulu.'}), 401
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    """
    Decorator restricting route strictly to role == 'user'.
    Blocks unauthenticated users (401/redirect) and admins (403).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Unauthorized', 'message': 'Silakan login terlebih dahulu.'}), 401
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if current_user.role != 'user':
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Forbidden', 'message': 'Admin tidak diperkenankan mengakses layanan transfer pengguna.'}), 403
            abort(403)

        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator restricting route strictly to role == 'admin'.
    Blocks unauthenticated users (401/redirect) and normal users (403).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Unauthorized', 'message': 'Silakan login terlebih dahulu.'}), 401
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_admin:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Forbidden', 'message': 'Akses ditolak. Membutuhkan role admin.'}), 403
            abort(403)

        return f(*args, **kwargs)
    return decorated_function

def authenticate_user(username, password):
    if not username or not password:
        return None, "Username dan password tidak boleh kosong."
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return None, "Username atau password salah."
    if not user.is_active:
        return None, "Akun Anda telah dinonaktifkan oleh Administrator. Silakan hubungi admin."
    return user, None
