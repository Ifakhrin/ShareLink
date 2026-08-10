from datetime import datetime
from app.models import db

class TransferLog(db.Model):
    __tablename__ = 'transfer_logs'

    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('transfers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    details = db.Column(db.Text, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('activity_logs', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'transfer_id': self.transfer_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'action': self.action,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'details': self.details
        }

    def __repr__(self):
        return f'<TransferLog {self.action} at {self.created_at}>'
