import sys
import os
from app import create_app
from app.models import db
from app.services.transfer_service import cleanup_expired_transfers

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Ensure upload storage folder exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        # Ensure database tables exist
        db.create_all()

    if len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
        with app.app_context():
            count = cleanup_expired_transfers()
            print(f"[CLEANUP] Manual cleanup finished. {count} expired transfer(s) processed.")
    else:
        print("Starting ShareLink Internal File Transfer System on http://127.0.0.1:5000")
        app.run(host='127.0.0.1', port=5000, debug=True)
