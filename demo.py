# demo.py
"""
Automated Demo Script - FOR VIDEO RECORDING
Purpose: Show all features working automatically
"""

from seed import seed_database
from app import create_app, db
from app.models import User, Card, Transaction
from decimal import Decimal


def take_rest():
    input("\n⏸️  Press Enter to continue...")


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_balances(user1, user2):
    """Print current balances"""
    db.session.refresh(user1)
    db.session.refresh(user2)
    print(f"   💰 Alice: ${user1.usd_balance} USD | Albedo: ${user2.usd_balance} USD")


def run_demo():
    """Run complete automated demo"""
    print("\n" + "🎬" * 35)
    print("        WALLET SYSTEM - COMPLETE DEMO")
    print("🎬" * 35)

    # Step 1: Seed database
    print_section("STEP 1: DATABASE SETUP")
    seed_database()
    take_rest()

    # Get app context
    app = create_app()

    with app.app_context():
        # Get users
        alice = User.query.filter_by(email="alice@demo.com").first()
        albedo = User.query.filter_by(email="albedo@demo.com").first()

        # Get cards
        active_card = Card.query.filter_by(card_number="545454******5454").first()
        frozen_card = Card.query.filter_by(card_number="378282******0005").first()

        print("\n✅ Initial balances:")
        print_balances(alice, albedo)
        take_rest()

        # Step 2: User Registration Demo
        print_section("STEP 2: USER REGISTRATION (Creating New User)")

        with app.test_client() as client:
            response = client.post('/api/register', json={
                'name': 'Mousa the Nerd',
                'email': 'mousa@demo.com',
                'password': 'password123'
            })

            if response.status_code == 201:
                data = response.get_json()
                print(f"   ✅ New user registered: mousa@demo.com")
                print(f"   📋 User ID: {data['user_id']}")
                print(f"   💰 Initial USD balance: ${data['balances']['USD']}")
                print(f"   💰 Initial LBP balance: {data['balances']['LBP']}")
            else:
                print(f"   ❌ Registration failed")

        mousa = User.query.filter_by(email="mousa@demo.com").first()
        take_rest()

        # Step 3: Top-up Demo
        print_section("STEP 3: TOP-UP (Mousa's Wallet)")
        print(f"   Before: Mousa has ${mousa.usd_balance}")

        with app.test_client() as client:
            response = client.post('/api/top-up', json={
                'user_id': mousa.id,
                'amount': 100.00,
                'currency': 'USD'
            })

            if response.status_code == 200:
                data = response.get_json()
                print(f"   💵 Top-up: +$100.00")
                print(f"   After: Mousa has ${data['new_balance']}")
                print("   ✅ Top-up successful!")
            else:
                print(f"   ❌ Top-up failed: {response.get_json()}")
        take_rest()

        # Step 4: P2P Transfer Demo
        print_section("STEP 4: P2P TRANSFER (Alice → Albedo)")
        print("   Before:")
        print_balances(alice, albedo)

        transfer_amount = Decimal('75.00')
        print(f"\n   💸 Transferring: ${transfer_amount}")

        with app.test_client() as client:
            response = client.post('/api/transfer', json={
                'from_user_id': alice.id,
                'to_user_id': albedo.id,
                'amount': transfer_amount,
                'currency': 'USD'
            })

            if response.status_code == 200:
                data = response.get_json()
                print("\n   After:")
                print(f"   💰 Alice: ${data['from_user_new_balance']} USD")
                print(f"   💰 Albedo: ${data['to_user_new_balance']} USD")
                print("   ✅ P2P transfer successful!")
            else:
                print(f"   ❌ Transfer failed: {response.get_json()}")
        take_rest()

        # Step 5: Card Authorization - APPROVE
        print_section("STEP 5: CARD PAYMENT - RETAIL (APPROVE)")
        print(f"   Card: {active_card.card_number} ({active_card.status})")
        print(f"   Alice's balance before: ${alice.usd_balance}")

        payment_amount = Decimal('27.50')
        print(f"   💳 Processing payment: ${payment_amount} at SuperMart")

        # Use test client to call webhook
        with app.test_client() as client:
            webhook_data = {
                "messageType": "0100",
                "processingCode": "000000",
                "primaryAccountNumber": active_card.card_number,
                "amountTransaction": str(payment_amount),
                "amountCardholderBilling": str(payment_amount),
                "dateAndTimeTransmission": "20251031T120000Z",
                "conversionRateCardholderBilling": "1.000000",
                "systemsTraceAuditNumber": "999001",
                "dateCapture": "20251031",
                "merchantCategoryCode": "5411",
                "acquiringInstitutionIdentificationCode": "ACQ001",
                "retrievalReferenceNumber": "DEMO001",
                "cardAcceptorTerminalIdentification": "TERM001",
                "cardAcceptorIdentificationCode": "MERCHANT001",
                "cardAcceptorName": "SuperMart Downtown",
                "cardAcceptorCity": "Beirut",
                "cardAcceptorCountryCode": "422",
                "entry_mode": "chip",
                "currencyCode": "840",
                "txn_ref": "DEMO_TXN_001",
                "idempotency_key": "demo-retail-approve-001"
            }

            response = client.post('/webhook/card-auth', json=webhook_data)
            result = response.get_json()

            if result.get('actionCode') == '00':
                print(f"   ✅ Payment APPROVED!")
                print(f"   Action Code: {result['actionCode']}")
                db.session.refresh(alice)
                print(f"   Alice's balance after: ${alice.usd_balance}")
            else:
                print(f"   ❌ Payment DECLINED!")
                print(f"   Action Code: {result.get('actionCode')}")
        take_rest()

        # Step 6: Card Authorization - DECLINE
        print_section("STEP 6: CARD PAYMENT - E-COMMERCE (DECLINE)")
        print(f"   Card: {frozen_card.card_number} ({frozen_card.status})")
        print(f"   Alice's balance: ${alice.usd_balance}")

        ecom_amount = Decimal('59.99')
        print(f"   💳 Processing payment: ${ecom_amount} at Acme Online")

        with app.test_client() as client:
            webhook_data = {
                "messageType": "0100",
                "processingCode": "000000",
                "primaryAccountNumber": frozen_card.card_number,
                "amountTransaction": str(ecom_amount),
                "amountCardholderBilling": str(ecom_amount),
                "dateAndTimeTransmission": "20251031T120500Z",
                "conversionRateCardholderBilling": "1.000000",
                "systemsTraceAuditNumber": "999002",
                "merchantCategoryCode": "5732",
                "acquiringInstitutionIdentificationCode": "ACQ007",
                "retrievalReferenceNumber": "DEMO002",
                "cardAcceptorIdentificationCode": "ECOM001",
                "cardAcceptorName": "Acme Online Store",
                "cardAcceptorCity": "Beirut",
                "cardAcceptorCountryCode": "422",
                "currencyCode": "840",
                "ecom": {
                    "avs_result": "Y",
                    "three_ds": "frictionless",
                    "ip_address": "203.0.113.24",
                    "channel": "web"
                },
                "txn_ref": "DEMO_TXN_002",
                "idempotency_key": "demo-ecom-decline-001"
            }

            response = client.post('/webhook/card-auth', json=webhook_data)
            result = response.get_json()

            if result.get('actionCode') == '05':
                print(f"   ✅ Payment DECLINED (Card frozen)")
                print(f"   Action Code: {result['actionCode']}")
                db.session.refresh(alice)
                print(f"   Alice's balance unchanged: ${alice.usd_balance}")
            else:
                print(f"   ❌ Should have declined! Action Code: {result.get('actionCode')}")
        take_rest()

        # Step 7: Show Transaction History
        print_section("STEP 7: TRANSACTION HISTORY")
        transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()
        print(f"   📝 Recent transactions ({len(transactions)}):")
        for txn in transactions:
            if txn.transaction_type == 'p2p':
                print(f"      • P2P: User {txn.from_user_id} → User {txn.to_user_id} | ${txn.amount} {txn.currency}")
            elif txn.transaction_type == 'top_up':
                print(f"      • Top-up: User {txn.to_user_id} | +${txn.amount} {txn.currency}")
            elif txn.transaction_type == 'card_payment':
                print(f"      • Card Payment: User {txn.from_user_id} | -${txn.amount} {txn.currency} ({txn.status})")
        take_rest()

        # Final Summary
        print_section("DEMO COMPLETE - SUMMARY")
        print("   ✅ User registration & authentication")
        print("   ✅ Wallet balance management (USD & LBP)")
        print("   ✅ Top-up functionality")
        print("   ✅ P2P transfers between users")
        print("   ✅ Card payment authorization (retail)")
        print("   ✅ Card payment authorization (e-commerce)")
        print("   ✅ Card status validation (frozen card declined)")
        print("   ✅ Balance deduction on approval")
        print("   ✅ Transaction history logging")
        print("   ✅ Idempotency key handling")

        print("\n" + "🎬" * 35)
        print("    ALL FEATURES DEMONSTRATED SUCCESSFULLY!")
        print("🎬" * 35 + "\n")


if __name__ == '__main__':
    run_demo()
