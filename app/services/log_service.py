import logging
from datetime import datetime
from app.models import db, TransferLog, User

# Configure standard logger
logger = logging.getLogger('sharelink')
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def log_action(action, user_id=None, transfer_id=None, details=None):
    """
    Record an action in transfer_logs DB table and console log.
    Actions:
    - LOGIN
    - FILE_UPLOAD_STARTED
    - FILE_UPLOADED
    - DOWNLOAD_STARTED
    - DOWNLOAD_COMPLETED
    - DOWNLOAD_FAILED
    - TRANSFER_CANCELLED
    - TRANSFER_EXPIRED
    - FILE_DELETED
    """
    try:
        log_entry = TransferLog(
            transfer_id=transfer_id,
            user_id=user_id,
            action=action,
            created_at=datetime.utcnow(),
            details=details
        )
        db.session.add(log_entry)
        db.session.commit()

        username = 'System'
        if user_id:
            user = User.query.get(user_id)
            if user:
                username = user.username

        logger.info(f"{action} | user={username} | transfer={transfer_id or 'N/A'} | details={details or ''}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to record transfer log: {e}")
