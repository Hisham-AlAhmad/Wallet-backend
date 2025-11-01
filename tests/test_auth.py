# tests/test_auth.py
"""
Tests for user authentication endpoints
Run with: pytest tests/test_auth.py -v
"""
import pytest
from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    """Create test app"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory test DB

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_db(app):
    """Reset database before AND after each test"""
    # Clear BEFORE test
    with app.app_context():
        from app.models import User, Card, Transaction
        db.session.query(Transaction).delete()
        db.session.query(Card).delete()
        db.session.query(User).delete()
        db.session.commit()

    yield  # Test runs here

    # Clear AFTER test
    with app.app_context():
        from app.models import User, Card, Transaction
        db.session.query(Transaction).delete()
        db.session.query(Card).delete()
        db.session.query(User).delete()
        db.session.commit()


class TestUserRegistration:
    """Test user registration endpoint"""

    def test_register_success(self, client, app):
        """Test successful user registration"""
        response = client.post('/api/register', json={
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'Test User'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'User created successfully'
        assert 'user_id' in data
        assert data['balances']['USD'] == '0.00'
        assert data['balances']['LBP'] == '0.00'

        # Verify user exists in database
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user is not None
            assert user.name == 'Test User'
            assert user.usd_balance == 0.0
            assert user.lbp_balance == 0.0

    def test_register_duplicate_email(self, client, app):
        """Test registration with duplicate email"""
        # Create first user
        client.post('/api/register', json={
            'email': 'test@example.com',
            'password': 'password123',
            'name': 'First User'
        })

        # Try to create second user with same email
        response = client.post('/api/register', json={
            'email': 'test@example.com',
            'password': 'different_password',
            'name': 'Second User'
        })

        assert response.status_code == 409
        data = response.get_json()
        assert 'already exists' in data['error'].lower()

    def test_register_missing_email(self, client):
        """Test registration without email"""
        response = client.post('/api/register', json={
            'password': 'password123',
            'name': 'Test User'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'required' in data['error'].lower()

    def test_register_missing_password(self, client):
        """Test registration without password"""
        response = client.post('/api/register', json={
            'email': 'test@example.com',
            'name': 'Test User'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'required' in data['error'].lower()

    def test_register_empty_request(self, client):
        """Test registration with empty request"""
        response = client.post('/api/register', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert 'required' in data['error'].lower()


class TestPasswordHashing:
    """Test password hashing functionality"""

    def test_password_is_hashed(self, app):
        """Test that passwords are hashed, not stored plainly"""
        with app.app_context():
            user = User(
                email='test@example.com',
                name='Test User',
                usd_balance=0.0,
                lbp_balance=0.0
            )
            user.set_password('my_password')
            db.session.add(user)
            db.session.commit()

            # Password should be hashed, not plain
            assert user.password_hash != 'my_password'
            assert len(user.password_hash) > 20  # Hashed passwords are long

    def test_password_check_correct(self, app):
        """Test checking correct password"""
        with app.app_context():
            user = User(
                email='test@example.com',
                name='Test User',
                usd_balance=0.0,
                lbp_balance=0.0
            )
            user.set_password('correct_password')
            db.session.add(user)
            db.session.commit()

            assert user.check_password('correct_password') == True

    def test_password_check_incorrect(self, app):
        """Test checking incorrect password"""
        with app.app_context():
            user = User(
                email='test@example.com',
                name='Test User',
                usd_balance=0.0,
                lbp_balance=0.0
            )
            user.set_password('correct_password')
            db.session.add(user)
            db.session.commit()

            assert user.check_password('wrong_password') == False
