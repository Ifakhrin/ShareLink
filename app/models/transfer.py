from datetime import datetime
from app.models import db

class Transfer(db.Model):
    __tablename__ = 'transfers'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(150), nullable=False, default='(Tanpa Judul)')
    message = db.Column(db.Text, nullable=True)
    transfer_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='PENDING', nullable=False)
    total_files = db.Column(db.Integer, default=0, nullable=False)
    total_size = db.Column(db.BigInteger, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_transfers', lazy=True))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_transfers', lazy=True))
    files = db.relationship('File', backref='transfer', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('TransferLog', backref='transfer', lazy=True)

    @property
    def is_expired(self):
        if self.expires_at and datetime.utcnow() >= self.expires_at and self.status == 'AVAILABLE':
            return True
        return False

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.name if self.sender else None,
            'receiver_id': self.receiver_id,
            'receiver_name': self.receiver.name if self.receiver else None,
            'subject': self.subject,
            'message': self.message,
            'transfer_code': self.transfer_code,
            'status': self.status,
            'total_files': self.total_files,
            'total_size': self.total_size,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f'<Transfer {self.transfer_code} ({self.status})>'
