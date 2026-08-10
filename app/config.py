import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-sharelink-internal-system-38917491')
    
    db_path = os.environ.get('DATABASE_URL', 'sqlite:///' + str(BASE_DIR / 'instance' / 'app.db'))
    if db_path.startswith('sqlite:///') and not db_path.startswith('sqlite:////'):
        # Normalize sqlite path relative to BASE_DIR if needed
        rel_path = db_path.replace('sqlite:///', '')
        if not os.path.isabs(rel_path):
            db_path = f"sqlite:///{BASE_DIR / rel_path}"
            
    SQLALCHEMY_DATABASE_URI = db_path
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload limits (in bytes)
    # 1 GB per file = 1,073,741,824 bytes
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 1073741824))
    # 2 GB total per transfer = 2,147,483,648 bytes
    MAX_TRANSFER_SIZE = int(os.environ.get('MAX_TRANSFER_SIZE', 2147483648))
    
    FILE_EXPIRATION_HOURS = int(os.environ.get('FILE_EXPIRATION_HOURS', 24))
    
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'storage'))
    if not os.path.isabs(UPLOAD_FOLDER):
        UPLOAD_FOLDER = str(BASE_DIR / UPLOAD_FOLDER)
