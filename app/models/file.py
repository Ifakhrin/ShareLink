from datetime import datetime
from app.models import db

class File(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfers.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    storage_path = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='UPLOADING', nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    downloaded_at = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'transfer_id': self.transfer_id,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'status': self.status,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'downloaded_at': self.downloaded_at.isoformat() if self.downloaded_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def __repr__(self):
        return f'<File {self.original_filename} ({self.status})>'
