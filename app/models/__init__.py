from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from app.models.user import User
from app.models.transfer import Transfer
from app.models.file import File
from app.models.transfer_log import TransferLog

__all__ = ['db', 'User', 'Transfer', 'File', 'TransferLog']
