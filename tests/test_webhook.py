# tests/test_webhook.py
"""
Tests for card authorization webhook
Run with: pytest tests/test_webhook.py -v
"""
import pytest
from decimal import Decimal
from app import create_app, db
from app.models import User, Card, Transaction


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
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_user_with_card(app):
    """Create test user with card"""
    with app.app_context():
        user = User(
            email='test@example.com',
            name='Test User',
            usd_balance=Decimal('500.00'),
            lbp_balance=Decimal('750000.00')
        )
        user.set_password('password')
        db.session.add(user)
        db.session.flush()

        active_card = Card(
            user_id=user.id,
            card_number='545454******5454',
            type='virtual',
            status='active'
        )

        frozen_card = Card(
            user_id=user.id,
            card_number='424242******4242',
            type='physical',
            status='frozen'
        )

        db.session.add_all([active_card, frozen_card])
        db.session.commit()

        return user.id, active_card.card_number, frozen_card.card_number


class TestCardAuthorizationApprove:
    """Test card authorization approval scenarios"""

    def test_retail_payment_approve(self, client, test_user_with_card, app):
        """Test successful retail (card-present) payment"""
        user_id, active_card_number, _ = test_user_with_card

        webhook_data = {
            "messageType": "0100",
            "processingCode": "000000",
            "primaryAccountNumber": active_card_number,
            "amountTransaction": "27.50",
            "amountCardholderBilling": "27.50",
            "dateAndTimeTransmission": "20251026T130415Z",
            "conversionRateCardholderBilling": "1.000000",
            "systemsTraceAuditNumber": "847392",
            "dateCapture": "20251026",
            "merchantCategoryCode": "5411",
            "acquiringInstitutionIdentificationCode": "ACQ001",
            "retrievalReferenceNumber": "012345678901",
            "cardAcceptorTerminalIdentification": "T98765",
            "cardAcceptorIdentificationCode": "MRC123",
            "cardAcceptorName": "SuperMart Downtown",
            "cardAcceptorCity": "Beirut",
            "cardAcceptorCountryCode": "422",
            "entry_mode": "chip",
            "currencyCode": "840",
            "txn_ref": "TEST_TXN_001",
            "idempotency_key": "test-retail-001"
        }

        response = client.post('/webhook/card-auth', json=webhook_data)

        assert response.status_code == 200
        data = response.get_json()

        # Check approval
        assert data['messageType'] == '2110'
        assert data['actionCode'] == '00'  # Approved
        assert data['primaryAccountNumber'] == active_card_number

        # Check balance was deducted
        with app.app_context():
            user = User.query.get(user_id)
            assert float(user.usd_balance) == 472.50  # 500 - 27.50

    def test_ecommerce_payment_approve(self, client, test_user_with_card, app):
        """Test successful e-commerce (card-not-present) payment"""
        user_id, active_card_number, _ = test_user_with_card

        webhook_data = {
            "messageType": "0100",
            "processingCode": "000000",
            "primaryAccountNumber": active_card_number,
            "amountTransaction": "59.99",
            "amountCardholderBilling": "59.99",
            "dateAndTimeTransmission": "20251026T130703Z",
            "conversionRateCardholderBilling": "1.000000",
            "systemsTraceAuditNumber": "847393",
            "merchantCategoryCode": "5732",
            "acquiringInstitutionIdentificationCode": "ACQ007",
            "retrievalReferenceNumber": "012345678902",
            "cardAcceptorIdentificationCode": "ECM456",
            "cardAcceptorName": "Acme Online",
            "cardAcceptorCity": "Beirut",
            "cardAcceptorCountryCode": "422",
            "currencyCode": "840",
            "ecom": {
                "avs_result": "Y",
                "three_ds": "frictionless",
                "ip_address": "203.0.113.24",
                "channel": "web"
            },
            "txn_ref": "TEST_TXN_002",
            "idempotency_key": "test-ecom-001"
        }

        response = client.post('/webhook/card-auth', json=webhook_data)

        assert response.status_code == 200
        data = response.get_json()

        assert data['actionCode'] == '00'  # Approved

        # Check balance was deducted
        with app.app_context():
            user = User.query.get(user_id)
            assert float(user.usd_balance) == 440.01  # 500 - 59.99


class TestCardAuthorizationDecline:
    """Test card authorization decline scenarios"""

    def test_decline_frozen_card(self, client, test_user_with_card):
        """Test payment declined due to frozen card"""
        _, _, frozen_card_number = test_user_with_card

        webhook_data = {
            "messageType": "0100",
            "processingCode": "000000",
            "primaryAccountNumber": frozen_card_number,
            "amountTransaction": "50.00",
            "amountCardholderBilling": "50.00",
            "dateAndTimeTransmission": "20251026T130415Z",
            "conversionRateCardholderBilling": "1.000000",
            "systemsTraceAuditNumber": "847394",
            "merchantCategoryCode": "5411",
            "acquiringInstitutionIdentificationCode": "ACQ001",
            "retrievalReferenceNumber": "012345678903",
            "cardAcceptorIdentificationCode": "MRC123",
            "cardAcceptorName": "Test Store",
            "cardAcceptorCity": "Beirut",
            "cardAcceptorCountryCode": "422",
            "currencyCode": "840",
            "txn_ref": "TEST_TXN_003",
            "idempotency_key": "test-frozen-001"
        }

        response = client.post('/webhook/card-auth', json=webhook_data)

        assert response.status_code == 200
        data = response.get_json()

        assert data['actionCode'] == '05'  # Declined
        assert data['approvalCode'] == '000000'  # Failure code

    def test_decline_insufficient_funds(self, client, test_user_with_card, app):
        """Test payment declined due to insufficient balance"""
        user_id, active_card_number, _ = test_user_with_card

        webhook_data = {
            "messageType": "0100",
            "processingCode": "000000",
            "primaryAccountNumber": active_card_number,
            "amountTransaction": "600.00",  # More than user has
            "amountCardholderBilling": "600.00",
            "dateAndTimeTransmission": "20251026T130415Z",
            "conversionRateCardholderBilling": "1.000000",
            "systemsTraceAuditNumber": "847395",
            "merchantCategoryCode": "5411",
            "acquiringInstitutionIdentificationCode": "ACQ001",
            "retrievalReferenceNumber": "012345678904",
            "cardAcceptorIdentificationCode": "MRC123",
            "cardAcceptorName": "Test Store",
            "cardAcceptorCity": "Beirut",
            "cardAcceptorCountryCode": "422",
            "currencyCode": "840",
            "txn_ref": "TEST_TXN_004",
            "idempotency_key": "test-insufficient-001"
        }

        response = client.post('/webhook/card-auth', json=webhook_data)

        assert response.status_code == 200
        data = response.get_json()

        assert data['actionCode'] == '05'  # Declined

        # Check balance was NOT deducted
        with app.app_context():
            user = User.query.get(user_id)
            assert float(user.usd_balance) == 500.00  # Unchanged

    def test_decline_card_not_found(self, client):
        """Test payment declined due to non-existent card"""
        webhook_data = {
            "messageType": "0100",
            "processingCode": "000000",
            "primaryAccountNumber": "999999******9999",  # Doesn't exist
            "amountTransaction": "50.00",
            "amountCardholderBilling": "50.00",
            "dateAndTimeTransmission": "20251026T130415Z",
            "conversionRateCardholderBilling": "1.000000",
            "systemsTraceAuditNumber": "847396",
            "merchantCategoryCode": "5411",
            "acquiringInstitutionIdentificationCode": "ACQ001",
            "retrievalReferenceNumber": "012345678905",
            "cardAcceptorIdentificationCode": "MRC123",
            "cardAcceptorName": "Test Store",
            "cardAcceptorCity": "Beirut",
            "cardAcceptorCountryCode": "422",
            "currencyCode": "840",
            "txn_ref": "TEST_TXN_005",
            "idempotency_key": "test-notfound-001"
        }

        response = client.post('/webhook/card-auth', json=webhook_data)

        assert response.status_code == 200
        data = response.get_json()

        assert data['actionCode'] == '05'  # Declined


class TestIdempotency:
    """Test idempotency key handling"""

    def test_idempotency_same_request_twice(self, client, test_user_with_card, app):
        """Test that same idempotency key doesn't process twice"""
        user_id, active_card_number, _ = test_user_with_card

        webhook_data = {
            "messageType": "0100",
            "processingCode": "000000",
            "primaryAccountNumber": active_card_number,
            "amountTransaction": "30.00",
            "amountCardholderBilling": "30.00",
            "dateAndTimeTransmission": "20251026T130415Z",
            "conversionRateCardholderBilling": "1.000000",
            "systemsTraceAuditNumber": "847397",
            "merchantCategoryCode": "5411",
            "acquiringInstitutionIdentificationCode": "ACQ001",
            "retrievalReferenceNumber": "012345678906",
            "cardAcceptorIdentificationCode": "MRC123",
            "cardAcceptorName": "Test Store",
            "cardAcceptorCity": "Beirut",
            "cardAcceptorCountryCode": "422",
            "currencyCode": "840",
            "txn_ref": "TEST_TXN_006",
            "idempotency_key": "test-idempotency-001"
        }

        # First request
        response1 = client.post('/webhook/card-auth', json=webhook_data)
        assert response1.status_code == 200

        with app.app_context():
            user = User.query.get(user_id)
            balance_after_first = float(user.usd_balance)
            assert balance_after_first == 470.00  # 500 - 30

        # Second request with SAME idempotency key
        response2 = client.post('/webhook/card-auth', json=webhook_data)
        assert response2.status_code == 200

        # Balance should NOT change again
        with app.app_context():
            user = User.query.get(user_id)
            assert float(user.usd_balance) == 470.00  # Still 470, not 440

        # Check only ONE transaction was created
        with app.app_context():
            transactions = Transaction.query.filter_by(
                reference_id="test-idempotency-001"
            ).all()
            assert len(transactions) == 1
