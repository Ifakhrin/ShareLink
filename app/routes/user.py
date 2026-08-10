from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, abort
from app.models import User, Transfer, File
from app.services.auth_service import user_required, get_current_user
from app.services.file_service import validate_file, save_uploaded_file, generate_file_stream_response
from app.services.transfer_service import create_transfer, finalize_transfer, cancel_transfer, cleanup_expired_transfers

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@user_required
def dashboard():
    cleanup_expired_transfers()
    current_user = get_current_user()

    active_incoming = Transfer.query.filter(
        Transfer.receiver_id == current_user.id,
        Transfer.status.in_(['PENDING', 'AVAILABLE', 'DOWNLOADING'])
    ).order_by(Transfer.created_at.desc()).all()

    history_incoming = Transfer.query.filter(
        Transfer.receiver_id == current_user.id,
        Transfer.status.in_(['COMPLETED', 'EXPIRED', 'CANCELLED', 'DELETED'])
    ).order_by(Transfer.created_at.desc()).limit(20).all()

    active_sent = Transfer.query.filter(
        Transfer.sender_id == current_user.id,
        Transfer.status.in_(['PENDING', 'AVAILABLE', 'DOWNLOADING'])
    ).order_by(Transfer.created_at.desc()).all()

    history_sent = Transfer.query.filter(
        Transfer.sender_id == current_user.id,
        Transfer.status.in_(['COMPLETED', 'EXPIRED', 'CANCELLED', 'DELETED'])
    ).order_by(Transfer.created_at.desc()).limit(20).all()

    return render_template(
        'user/dashboard.html',
        current_user=current_user,
        active_incoming=active_incoming,
        history_incoming=history_incoming,
        active_sent=active_sent,
        history_sent=history_sent
    )

@user_bp.route('/inbox')
@user_required
def inbox():
    cleanup_expired_transfers()
    current_user = get_current_user()

    active_transfers = Transfer.query.filter(
        Transfer.receiver_id == current_user.id,
        Transfer.status.in_(['PENDING', 'AVAILABLE', 'DOWNLOADING'])
    ).order_by(Transfer.created_at.desc()).all()

    history_transfers = Transfer.query.filter(
        Transfer.receiver_id == current_user.id,
        Transfer.status.in_(['COMPLETED', 'EXPIRED', 'CANCELLED', 'DELETED'])
    ).order_by(Transfer.created_at.desc()).limit(50).all()

    return render_template(
        'user/inbox.html',
        current_user=current_user,
        active_transfers=active_transfers,
        history_transfers=history_transfers
    )

@user_bp.route('/sent')
@user_required
def sent():
    cleanup_expired_transfers()
    current_user = get_current_user()

    active_transfers = Transfer.query.filter(
        Transfer.sender_id == current_user.id,
        Transfer.status.in_(['PENDING', 'AVAILABLE', 'DOWNLOADING'])
    ).order_by(Transfer.created_at.desc()).all()

    history_transfers = Transfer.query.filter(
        Transfer.sender_id == current_user.id,
        Transfer.status.in_(['COMPLETED', 'EXPIRED', 'CANCELLED', 'DELETED'])
    ).order_by(Transfer.created_at.desc()).limit(50).all()

    return render_template(
        'user/sent.html',
        current_user=current_user,
        active_transfers=active_transfers,
        history_transfers=history_transfers
    )

@user_bp.route('/send', methods=['GET', 'POST'])
@user_required
def send():
    current_user = get_current_user()

    if request.method == 'POST':
        receiver_id = request.form.get('receiver_id', type=int)
        if not receiver_id:
            msg = "Pilih penerima file terlebih dahulu."
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('user.send'))

        # Check receiver is a valid active user and NOT admin
        receiver = User.query.get(receiver_id)
        if not receiver or receiver.role != 'user' or not receiver.is_active or receiver.id == current_user.id:
            msg = "Penerima file tidak valid."
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('user.send'))

        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not subject:
            msg = "Judul transfer wajib diisi."
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('user.send'))

        if len(subject) > 150:
            msg = "Judul transfer maksimal 150 karakter."
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('user.send'))

        if len(message) > 2000:
            msg = "Pesan pengantar maksimal 2.000 karakter."
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('user.send'))

        uploaded_files = request.files.getlist('files')
        if not uploaded_files or len(uploaded_files) == 0 or (len(uploaded_files) == 1 and not uploaded_files[0].filename):
            msg = "Pilih setidaknya satu file untuk dikirim."
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('user.send'))

        running_total_size = 0
        file_validations = []

        for f_storage in uploaded_files:
            if not f_storage.filename or f_storage.filename.strip() == '':
                continue
            is_valid, err, f_size = validate_file(f_storage, running_total_size)
            if not is_valid:
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': err}), 400
                flash(err, 'danger')
                return redirect(url_for('user.send'))
            running_total_size += f_size
            file_validations.append((f_storage, f_size))

        if not file_validations:
            msg = "Tidak ada file valid yang diunggah."
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redirect(url_for('user.send'))

        transfer, err = create_transfer(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            subject=subject,
            message=message
        )
        if err:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': err}), 400
            flash(err, 'danger')
            return redirect(url_for('user.send'))

        for f_storage, _ in file_validations:
            save_uploaded_file(f_storage, transfer.id)

        finalized_transfer, f_err = finalize_transfer(transfer.id)
        if f_err:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': f_err}), 500
            flash(f_err, 'danger')
            return redirect(url_for('user.send'))

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'redirect_url': url_for('user.transfer_detail', transfer_id=finalized_transfer.id)
            })

        flash(f'File berhasil dikirim ke {receiver.name}! Kode Transfer: {finalized_transfer.transfer_code}', 'success')
        return redirect(url_for('user.transfer_detail', transfer_id=finalized_transfer.id))

    # GET request: Recipient list MUST strictly filter role == 'user', is_active == True, id != current_user.id
    recipients = User.query.filter(
        User.id != current_user.id,
        User.role == 'user',
        User.is_active == True
    ).order_by(User.name.asc()).all()

    return render_template('user/send.html', current_user=current_user, recipients=recipients)

@user_bp.route('/transfer/<int:transfer_id>')
@user_required
def transfer_detail(transfer_id):
    cleanup_expired_transfers()
    current_user = get_current_user()
    transfer = Transfer.query.get_or_404(transfer_id)

    # Authorization: strictly Sender or Receiver!
    if transfer.sender_id != current_user.id and transfer.receiver_id != current_user.id:
        abort(403)

    return render_template('user/transfer_detail.html', current_user=current_user, transfer=transfer)

@user_bp.route('/download/<int:file_id>')
@user_required
def download(file_id):
    cleanup_expired_transfers()
    current_user = get_current_user()
    file_record = File.query.get_or_404(file_id)
    transfer = file_record.transfer

    # Authorization: strictly Receiver!
    if transfer.receiver_id != current_user.id:
        abort(403)

    if transfer.status in ['EXPIRED', 'CANCELLED', 'DELETED']:
        flash(f'Transfer ini telah berstatus {transfer.status} dan tidak dapat didownload lagi.', 'danger')
        return redirect(url_for('user.transfer_detail', transfer_id=transfer.id))

    if file_record.status in ['DELETED', 'DOWNLOADED', 'EXPIRED', 'CANCELLED']:
        flash('File sudah tidak tersedia lagi.', 'danger')
        return redirect(url_for('user.transfer_detail', transfer_id=transfer.id))

    response, err = generate_file_stream_response(file_record, current_user.id, current_app._get_current_object())
    if err:
        flash(err, 'danger')
        return redirect(url_for('user.transfer_detail', transfer_id=transfer.id))

    return response

@user_bp.route('/cancel/<int:transfer_id>', methods=['POST'])
@user_required
def cancel(transfer_id):
    current_user = get_current_user()
    success_flag, message = cancel_transfer(transfer_id, current_user.id, is_admin=False)

    if success_flag:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('user.transfer_detail', transfer_id=transfer_id))
