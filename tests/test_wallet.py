# tests/test_wallet.py
"""
Tests for wallet operations (top-up, P2P transfers)
Run with: pytest tests/test_wallet.py -v
"""
import pytest
from decimal import Decimal
from app import create_app, db
from app.models import User, Transaction


@pytest.fixture
def app():
    """Create test app"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

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


@pytest.fixture
def test_users(app):
    """Create test users"""
    with app.app_context():
        user1 = User(
            email='alice@test.com',
            name='Alice',
            usd_balance=Decimal('100.00'),
            lbp_balance=Decimal('150000.00')
        )
        user1.set_password('password')

        user2 = User(
            email='bob@test.com',
            name='Bob',
            usd_balance=Decimal('50.00'),
            lbp_balance=Decimal('75000.00')
        )
        user2.set_password('password')

        db.session.add_all([user1, user2])
        db.session.commit()

        return user1.id, user2.id


class TestTopUp:
    """Test wallet top-up functionality"""

    def test_topup_usd_success(self, client, test_users):
        """Test successful USD top-up"""
        user_id = test_users[0]

        response = client.post('/api/top-up', json={
            'user_id': user_id,
            'amount': 50.00,
            'currency': 'USD'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Top-up successful'
        assert float(data['new_balance']) == 150.00  # 100 + 50

    def test_topup_lbp_success(self, client, test_users):
        """Test successful LBP top-up"""
        user_id = test_users[0]

        response = client.post('/api/top-up', json={
            'user_id': user_id,
            'amount': 50000.00,
            'currency': 'LBP'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert float(data['new_balance']) == 200000.00  # 150000 + 50000

    def test_topup_invalid_currency(self, client, test_users):
        """Test top-up with invalid currency"""
        user_id = test_users[0]

        response = client.post('/api/top-up', json={
            'user_id': user_id,
            'amount': 50.00,
            'currency': 'EUR'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Currency must be USD or LBP' in data['error']

    def test_topup_negative_amount(self, client, test_users):
        """Test top-up with negative amount"""
        user_id = test_users[0]

        response = client.post('/api/top-up', json={
            'user_id': user_id,
            'amount': -50.00,
            'currency': 'USD'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'positive' in data['error'].lower()

    def test_topup_nonexistent_user(self, client):
        """Test top-up for non-existent user"""
        response = client.post('/api/top-up', json={
            'user_id': 99999,
            'amount': 50.00,
            'currency': 'USD'
        })

        assert response.status_code == 404
        data = response.get_json()
        assert 'not found' in data['error'].lower()


class TestP2PTransfer:
    """Test peer-to-peer transfer functionality"""

    def test_transfer_usd_success(self, client, test_users):
        """Test successful USD transfer"""
        user1_id, user2_id = test_users

        response = client.post('/api/transfer', json={
            'from_user_id': user1_id,
            'to_user_id': user2_id,
            'amount': 25.00,
            'currency': 'USD'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Transfer successful'
        assert float(data['from_user_new_balance']) == 75.00  # 100 - 25
        assert float(data['to_user_new_balance']) == 75.00  # 50 + 25

    def test_transfer_lbp_success(self, client, test_users):
        """Test successful LBP transfer"""
        user1_id, user2_id = test_users

        response = client.post('/api/transfer', json={
            'from_user_id': user1_id,
            'to_user_id': user2_id,
            'amount': 50000.00,
            'currency': 'LBP'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert float(data['from_user_new_balance']) == 100000.00  # 150000 - 50000
        assert float(data['to_user_new_balance']) == 125000.00  # 75000 + 50000

    def test_transfer_insufficient_funds(self, client, test_users):
        """Test transfer with insufficient balance"""
        user1_id, user2_id = test_users

        response = client.post('/api/transfer', json={
            'from_user_id': user1_id,
            'to_user_id': user2_id,
            'amount': 200.00,  # User1 only has 100
            'currency': 'USD'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Insufficient balance' in data['error']

    def test_transfer_to_self(self, client, test_users):
        """Test transfer to same user"""
        user1_id = test_users[0]

        response = client.post('/api/transfer', json={
            'from_user_id': user1_id,
            'to_user_id': user1_id,
            'amount': 25.00,
            'currency': 'USD'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'yourself' in data['error'].lower()

    def test_transfer_invalid_currency(self, client, test_users):
        """Test transfer with invalid currency"""
        user1_id, user2_id = test_users

        response = client.post('/api/transfer', json={
            'from_user_id': user1_id,
            'to_user_id': user2_id,
            'amount': 25.00,
            'currency': 'GBP'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Currency must be USD or LBP' in data['error']

    def test_transfer_negative_amount(self, client, test_users):
        """Test transfer with negative amount"""
        user1_id, user2_id = test_users

        response = client.post('/api/transfer', json={
            'from_user_id': user1_id,
            'to_user_id': user2_id,
            'amount': -25.00,
            'currency': 'USD'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'positive' in data['error'].lower()

    def test_transfer_creates_transaction_record(self, client, test_users, app):
        """Test that transfer creates transaction record"""
        user1_id, user2_id = test_users

        response = client.post('/api/transfer', json={
            'from_user_id': user1_id,
            'to_user_id': user2_id,
            'amount': 25.00,
            'currency': 'USD'
        })

        assert response.status_code == 200

        # Check transaction was recorded
        with app.app_context():
            transaction = Transaction.query.filter_by(
                from_user_id=user1_id,
                to_user_id=user2_id
            ).first()

            assert transaction is not None
            assert float(transaction.amount) == 25.00
            assert transaction.currency == 'USD'
            assert transaction.transaction_type == 'p2p'
            assert transaction.status == 'completed'
