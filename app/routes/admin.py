from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, User, Transfer, TransferLog
from app.services.auth_service import admin_required, get_current_user
from app.services.transfer_service import admin_delete_transfer, cleanup_expired_transfers
from app.services.log_service import log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    cleanup_expired_transfers()
    current_user = get_current_user()

    total_users = User.query.filter_by(role='user').count()
    active_users = User.query.filter_by(role='user', is_active=True).count()
    total_transfers = Transfer.query.count()
    active_transfers = Transfer.query.filter(Transfer.status.in_(['AVAILABLE', 'DOWNLOADING', 'PENDING'])).count()
    completed_transfers = Transfer.query.filter_by(status='COMPLETED').count()
    expired_transfers = Transfer.query.filter_by(status='EXPIRED').count()

    recent_logs = TransferLog.query.order_by(TransferLog.created_at.desc()).limit(10).all()

    return render_template(
        'admin/dashboard.html',
        current_user=current_user,
        total_users=total_users,
        active_users=active_users,
        total_transfers=total_transfers,
        active_transfers=active_transfers,
        completed_transfers=completed_transfers,
        expired_transfers=expired_transfers,
        recent_logs=recent_logs
    )

@admin_bp.route('/users')
@admin_required
def users():
    current_user = get_current_user()
    user_list = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', current_user=current_user, users=user_list)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    current_user = get_current_user()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')

        # Restrict role creation to 'user' for normal admin form
        if role != 'user':
            role = 'user'

        if not name or not username or not password:
            flash('Seluruh field (Nama, Username, Password) wajib diisi.', 'danger')
            return redirect(url_for('admin.create_user'))

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash(f"Username '{username}' sudah digunakan.", 'danger')
            return redirect(url_for('admin.create_user'))

        new_user = User(
            name=name,
            username=username,
            role=role,
            is_active=True
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        log_action('USER_CREATED', user_id=current_user.id, details=f"Created user: {username} ({name})")
        flash(f"Pengguna baru '{username}' berhasil dibuat.", 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', current_user=current_user, edit_user=None)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    current_user = get_current_user()
    target_user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip().lower()

        if not name or not username:
            flash('Nama dan Username tidak boleh kosong.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        existing = User.query.filter(User.username == username, User.id != user_id).first()
        if existing:
            flash(f"Username '{username}' sudah digunakan oleh pengguna lain.", 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))

        target_user.name = name
        target_user.username = username
        db.session.commit()

        log_action('USER_UPDATED', user_id=current_user.id, details=f"Updated user ID {user_id}: {username}")
        flash(f"Data pengguna '{username}' berhasil diperbarui.", 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', current_user=current_user, edit_user=target_user)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    current_user = get_current_user()
    target_user = User.query.get_or_404(user_id)

    if target_user.id == current_user.id:
        flash('Anda tidak dapat menonaktifkan akun sendiri.', 'danger')
        return redirect(url_for('admin.users'))

    target_user.is_active = not target_user.is_active
    db.session.commit()

    status_str = "diaktifkan" if target_user.is_active else "dinonaktifkan"
    action_type = "USER_ENABLED" if target_user.is_active else "USER_DISABLED"
    
    log_action(action_type, user_id=current_user.id, details=f"User {target_user.username} {status_str}")
    flash(f"Akun pengguna '{target_user.username}' berhasil {status_str}.", 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    current_user = get_current_user()
    target_user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '')

    if not new_password or len(new_password) < 6:
        flash('Password baru minimal 6 karakter.', 'danger')
        return redirect(url_for('admin.users'))

    target_user.set_password(new_password)
    db.session.commit()

    log_action('PASSWORD_RESET', user_id=current_user.id, details=f"Admin reset password for user: {target_user.username}")
    flash(f"Password pengguna '{target_user.username}' berhasil di-reset.", 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/transfers')
@admin_required
def transfers():
    cleanup_expired_transfers()
    current_user = get_current_user()
    transfer_list = Transfer.query.order_by(Transfer.created_at.desc()).all()
    return render_template('admin/transfers.html', current_user=current_user, transfers=transfer_list)

@admin_bp.route('/transfers/delete/<int:transfer_id>', methods=['POST'])
@admin_required
def delete_transfer(transfer_id):
    current_user = get_current_user()
    success_flag, message = admin_delete_transfer(transfer_id, current_user.id)
    if success_flag:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin.transfers'))

@admin_bp.route('/logs')
@admin_required
def logs():
    current_user = get_current_user()
    log_list = TransferLog.query.order_by(TransferLog.created_at.desc()).limit(200).all()
    return render_template('admin/logs.html', current_user=current_user, logs=log_list)
