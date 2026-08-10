import os
import shutil
import tempfile
import pytest
from app import create_app
from app.models import db, User, Transfer, File, TransferLog
from app.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key-12345'
    WTF_CSRF_ENABLED = False
    MAX_FILE_SIZE = 1048576  # 1 MB for fast testing
    MAX_TRANSFER_SIZE = 2097152  # 2 MB for fast testing

@pytest.fixture
def temp_storage():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def app(temp_storage):
    TestConfig.UPLOAD_FOLDER = temp_storage
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()

        # Create test users
        admin = User(username='admin', name='Admin', role='admin')
        admin.set_password('Admin123!')

        user1 = User(username='user1', name='User One', role='user')
        user1.set_password('User123!')

        user2 = User(username='user2', name='User Two', role='user')
        user2.set_password('User123!')

        user3 = User(username='user3', name='User Three', role='user')
        user3.set_password('User123!')

        db.session.add_all([admin, user1, user2, user3])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
