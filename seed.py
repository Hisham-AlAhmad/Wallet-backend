# seed.py
"""
Database Seeding Script
Purpose: Create fresh test data for development/demo
Run with: python seed.py
"""
from app import create_app, db
from app.models import User, Card, Transaction
from decimal import Decimal


def seed_database():
    """Create test users and cards"""
    app = create_app()

    with app.app_context():
        print("🚀 SEEDING DATABASE")
        print("=" * 60)

        # Clear existing data
        print("🗑️  Clearing existing data...")
        db.session.query(Transaction).delete()
        db.session.query(Card).delete()
        db.session.query(User).delete()
        db.session.commit()

        print("👥 Creating users...")

        # User 1 - Alice (wealthy, has cards)
        user1 = User(
            email="alice@demo.com",
            name="Alice the Witch",
            usd_balance=Decimal('500.00'),
            lbp_balance=Decimal('7500000.00')
        )
        user1.set_password("password123")
        db.session.add(user1)

        # User 2 - Albedo (moderate balance, no cards)
        user2 = User(
            email="albedo@demo.com",
            name="Albedo the Alchemist",
            usd_balance=Decimal('250.00'),
            lbp_balance=Decimal('3750000.00')
        )
        user2.set_password("password123")
        db.session.add(user2)

        db.session.commit()

        print("💳 Creating cards...")

        # Alice's active virtual card
        card1 = Card(
            user_id=user1.id,
            card_number="545454******5454",
            type="virtual",
            status="active"
        )
        db.session.add(card1)

        # Alice's active physical card
        card2 = Card(
            user_id=user1.id,
            card_number="424242******4242",
            type="physical",
            status="active"
        )
        db.session.add(card2)

        # Alice's frozen card (for decline testing)
        card3 = Card(
            user_id=user1.id,
            card_number="378282******0005",
            type="virtual",
            status="frozen"
        )
        db.session.add(card3)

        db.session.commit()

        print("\n✅ SEED COMPLETED!")
        print("=" * 60)
        print("📊 CREATED DATA:")
        print("=" * 60)

        print(f"\n👤 {user1.name} (ID: {user1.id})")
        print(f"   Email: {user1.email}")
        print(f"   Password: password123")
        print(f"   USD: ${user1.usd_balance} | LBP: {user1.lbp_balance:,}")
        print(f"   Cards: {Card.query.filter_by(user_id=user1.id).count()}")

        print(f"\n👤 {user2.name} (ID: {user2.id})")
        print(f"   Email: {user2.email}")
        print(f"   Password: password123")
        print(f"   USD: ${user2.usd_balance} | LBP: {user2.lbp_balance:,}")
        print(f"   Cards: {Card.query.filter_by(user_id=user2.id).count()}")

        print("\n💳 CARDS:")
        print("-" * 60)
        for card in Card.query.all():
            print(f"   {card.card_number} - {card.type} ({card.status}) → User {card.user_id}")

        print("\n" + "=" * 60)
        print("✅ The data is Ready! --- seed.py ends here.")
        print("=" * 60 + "\n")


if __name__ == '__main__':
    seed_database()
