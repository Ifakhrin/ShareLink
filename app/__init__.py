from flask import Flask, render_template, jsonify, request
from app.config import Config
from app.models import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    with app.app_context():
        import os
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'users' in inspector.get_table_names():
                u_cols = [c['name'] for c in inspector.get_columns('users')]
                if 'is_active' not in u_cols:
                    db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
                    db.session.commit()

            if 'transfers' in inspector.get_table_names():
                t_cols = [c['name'] for c in inspector.get_columns('transfers')]
                if 'subject' not in t_cols:
                    db.session.execute(text("ALTER TABLE transfers ADD COLUMN subject VARCHAR(150) NOT NULL DEFAULT '(Tanpa Judul)'"))
                    db.session.commit()
                if 'message' not in t_cols:
                    db.session.execute(text("ALTER TABLE transfers ADD COLUMN message TEXT"))
                    db.session.commit()
            db.create_all()
        except Exception as e:
            pass

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    # CLI Command for cleanup
    @app.cli.command("cleanup-expired")
    def cleanup_command():
        from app.services.transfer_service import cleanup_expired_transfers
        with app.app_context():
            count = cleanup_expired_transfers()
            print(f"Cleanup complete. {count} expired transfer(s) processed.")

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Forbidden', 'message': 'Akses ditolak.'}), 403
        return render_template('base.html', title="403 Forbidden", error_code="403", error_message="Akses Ditolak. Anda tidak memiliki wewenang untuk membuka halaman atau fitur ini."), 403

    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Not Found', 'message': 'Resource tidak ditemukan.'}), 404
        return render_template('base.html', title="404 Not Found", error_code="404", error_message="Halaman atau data transfer yang Anda cari tidak ditemukan."), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        msg = "Ukuran file melebihi batas maksimum server (Maksimal 1 GB per file / 2 GB total per transfer)."
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Payload Too Large', 'message': msg}), 413
        return render_template('base.html', title="File Terlalu Besar", error_code="413", error_message=msg), 413

    @app.errorhandler(500)
    def internal_error(error):
        msg = "Terjadi kesalahan pada server. Silakan coba beberapa saat lagi."
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Internal Server Error', 'message': msg}), 500
        return render_template('base.html', title="500 Internal Error", error_code="500", error_message=msg), 500

    return app
