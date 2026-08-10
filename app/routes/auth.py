from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import db
from app.services.auth_service import authenticate_user, get_current_user, login_required
from app.services.log_service import log_action

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    current_user = get_current_user()
    if current_user:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user, err = authenticate_user(username, password)
        if user:
            session.clear()
            session['user_id'] = user.id
            log_action('LOGIN', user_id=user.id, details=f"User {user.username} logged in successfully")
            flash(f'Selamat datang kembali, {user.name}!', 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            # Role-based redirect
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
        else:
            flash(err or 'Username atau password salah.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    user = get_current_user()
    if user:
        session.clear()
        flash('Anda telah berhasil keluar.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    current_user = get_current_user()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        new_password = request.form.get('new_password', '')

        if not name:
            flash('Nama tidak boleh kosong.', 'danger')
            return redirect(url_for('auth.profile'))

        current_user.name = name

        if new_password:
            if len(new_password) < 6:
                flash('Password baru minimal 6 karakter.', 'danger')
                return redirect(url_for('auth.profile'))
            current_user.set_password(new_password)
            log_action('PASSWORD_RESET', user_id=current_user.id, details="User updated their own password")

        db.session.commit()
        log_action('USER_UPDATED', user_id=current_user.id, details="User updated profile details")
        flash('Profil berhasil diperbarui.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('profile.html', current_user=current_user)
