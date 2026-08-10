"""
Development Database Seeder for ShareLink Internal File Transfer System.
WARNING: These credentials are strictly for local development and testing.
DO NOT use these credentials in production environments!
"""

from app import create_app
from app.models import db, User

def seed_database():
    app = create_app()
    with app.app_context():
        print("Creating database tables...")
        db.create_all()

        users_data = [
            {
                'username': 'admin',
                'password': 'Admin123!',
                'name': 'System Administrator',
                'role': 'admin'
            },
            {
                'username': 'user1',
                'password': 'User123!',
                'name': 'User One (Budi)',
                'role': 'user'
            },
            {
                'username': 'user2',
                'password': 'User123!',
                'name': 'User Two (Siti)',
                'role': 'user'
            }
        ]

        for udata in users_data:
            existing = User.query.filter_by(username=udata['username']).first()
            if not existing:
                u = User(
                    username=udata['username'],
                    name=udata['name'],
                    role=udata['role']
                )
                u.set_password(udata['password'])
                db.session.add(u)
                print(f"Created user: {udata['username']} ({udata['role']})")
            else:
                print(f"User already exists: {udata['username']}")

        db.session.commit()
        print("\n==================================================")
        print("DEVELOPMENT SEEDING COMPLETED SUCCESSFULLY")
        print("==================================================")
        print("WARNING: These default credentials are for local development ONLY!")
        print("Admin:  username: admin  | password: Admin123!")
        print("User 1: username: user1  | password: User123!")
        print("User 2: username: user2  | password: User123!")
        print("==================================================\n")

if __name__ == '__main__':
    seed_database()
