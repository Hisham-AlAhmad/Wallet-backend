# app/models.py
from app import db
from datetime import datetime
import hashlib

'''
# Think of it like writing and deploying code:

flask db init                        # Set up deployment pipeline (one time)

flask db migrate -m "Add users"      # Write the deployment script
                                     # ↑ Creates migration file with SQL instructions

flask db upgrade                     # RUN the deployment script  
                                     # ↑ Executes the SQL against your database
'''


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))

    # Balances directly on user (Option A)
    usd_balance = db.Column(db.Float, default=0.0, nullable=False)
    lbp_balance = db.Column(db.Float, default=0.0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    cards = db.relationship('Card', backref='user', lazy='dynamic')
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.from_user_id', backref='sender',
                                        lazy='dynamic')
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.to_user_id', backref='receiver',
                                            lazy='dynamic')

    def set_password(self, password):
        """Hash password using SHA-256"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def get_balance(self, currency):
        """Get balance for specific currency"""
        if currency == 'USD':
            return self.usd_balance
        elif currency == 'LBP':
            return self.lbp_balance
        else:
            return 0.0

    def can_debit(self, amount, currency):
        """Check if user has sufficient balance for debit"""
        balance = self.get_balance(currency)
        return balance >= amount > 0

    def debit(self, amount, currency):
        """Debit amount from user's balance"""
        if not self.can_debit(amount, currency):
            return False

        if currency == 'USD':
            self.usd_balance -= amount
        elif currency == 'LBP':
            self.lbp_balance -= amount
        return True

    def credit(self, amount, currency):
        """Credit amount to user's balance"""
        if amount <= 0:
            return False

        if currency == 'USD':
            self.usd_balance += amount
        elif currency == 'LBP':
            self.lbp_balance += amount
        return True


class Card(db.Model):
    __tablename__ = 'cards'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_number = db.Column(db.String(16), nullable=False)  # Store masked: "545454******5454"
    type = db.Column(db.Enum('physical', 'virtual', name='card_type'), nullable=False)
    status = db.Column(db.Enum('active', 'frozen', 'cancelled', name='card_status'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_active(self):
        return self.status == 'active'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null for top-ups
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=True)  # For card payments
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    transaction_type = db.Column(db.Enum('p2p', 'card_payment', 'top_up', name='transaction_type'))
    status = db.Column(db.Enum('pending', 'completed', 'failed', name='transaction_status'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reference_id = db.Column(db.String(50), unique=True)  # For idempotency

    # Index for common queries
    __table_args__ = (
        db.Index('idx_user_transactions', 'from_user_id', 'to_user_id'),
        db.Index('idx_transaction_created', 'created_at'),
    )
