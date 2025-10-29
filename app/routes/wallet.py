# app/routes/wallet.py
from flask import request, jsonify
from app import db
from app.models import User, Transaction, Card
from decimal import Decimal


def init_wallet_routes(app):
    @app.route('/api/top-up', methods=['POST'])
    def top_up():
        try:
            data = request.get_json()

            # Validation
            if not data or not data.get('user_id') or not data.get('amount') or not data.get('currency'):
                return jsonify({'error': 'user_id, amount, and currency required'}), 400

            if data['currency'] not in ['USD', 'LBP']:
                return jsonify({'error': 'Currency must be USD or LBP'}), 400

            # SQL: SELECT * FROM users WHERE id = ?
            user = User.query.get(data['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 404

            amount = Decimal(str(data['amount']))
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400

            # SQL: UPDATE users SET usd_balance = usd_balance + ? WHERE id = ?
            # OR: UPDATE users SET lbp_balance = lbp_balance + ? WHERE id = ?
            user.credit(amount, data['currency'])

            # SQL: INSERT INTO transactions (from_user_id, to_user_id, amount, currency, transaction_type, status)
            # VALUES (NULL, ?, ?, ?, 'top_up', 'completed')
            transaction = Transaction(
                from_user_id=None,
                to_user_id=user.id,
                amount=amount,
                currency=data['currency'],
                transaction_type='top_up',
                status='completed'
            )

            db.session.add(transaction)
            db.session.commit()

            return jsonify({
                'message': 'Top-up successful',
                'new_balance': user.get_balance(data['currency'])
            }), 200

        except Exception as e:
            db.session.rollback()
            print(f"Top-up error: {str(e)}")
            return jsonify({'error': 'Top-up failed'}), 500

    @app.route('/api/transfer', methods=['POST'])
    def transfer():
        try:
            data = request.get_json()

            # Validation
            required = ['from_user_id', 'to_user_id', 'amount', 'currency']
            if not data or any(field not in data for field in required):
                return jsonify({'error': 'from_user_id, to_user_id, amount, and currency required'}), 400

            if data['currency'] not in ['USD', 'LBP']:
                return jsonify({'error': 'Currency must be USD or LBP'}), 400

            # SQL: SELECT * FROM users WHERE id IN (?, ?)
            from_user = User.query.get(data['from_user_id'])
            to_user = User.query.get(data['to_user_id'])

            if not from_user or not to_user:
                return jsonify({'error': 'One or both users not found'}), 404

            if from_user.id == to_user.id:
                return jsonify({'error': 'Cannot transfer to yourself'}), 400

            amount = Decimal(str(data['amount']))
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400

            # SQL: SELECT usd_balance FROM users WHERE id = ?
            # (or lbp_balance depending on currency)
            if not from_user.can_debit(amount, data['currency']):
                return jsonify({'error': 'Insufficient balance'}), 400

            # SQL: BEGIN TRANSACTION;
            # SQL: UPDATE users SET usd_balance = usd_balance - ? WHERE id = ?;
            # SQL: UPDATE users SET usd_balance = usd_balance + ? WHERE id = ?;
            # SQL: COMMIT;
            from_user.debit(amount, data['currency'])
            to_user.credit(amount, data['currency'])

            # SQL: INSERT INTO transactions (from_user_id, to_user_id, amount, currency, transaction_type, status)
            # VALUES (?, ?, ?, ?, 'p2p', 'completed')
            transaction = Transaction(
                from_user_id=from_user.id,
                to_user_id=to_user.id,
                amount=amount,
                currency=data['currency'],
                transaction_type='p2p',
                status='completed'
            )

            db.session.add(transaction)
            db.session.commit()

            return jsonify({
                'message': 'Transfer successful',
                'from_user_new_balance': from_user.get_balance(data['currency']),
                'to_user_new_balance': to_user.get_balance(data['currency'])
            }), 200

        except Exception as e:
            db.session.rollback()  # SQL: ROLLBACK;
            print(f"Transfer error: {str(e)}")
            return jsonify({'error': 'Transfer failed'}), 500

    @app.route('/api/create-card', methods=['POST'])
    def create_card():
        try:
            data = request.get_json()

            # Validation
            if not data or not data.get('user_id') or not data.get('card_number') or not data.get('type'):
                return jsonify({'error': 'user_id, card_number, and type required'}), 400

            if data['type'] not in ['physical', 'virtual']:
                return jsonify({'error': 'Type must be physical or virtual'}), 400

            # SQL: SELECT * FROM users WHERE id = ?
            user = User.query.get(data['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 404

            # SQL: INSERT INTO cards (user_id, card_number, type, status) VALUES (?, ?, ?, ?)
            card = Card(
                user_id=user.id,
                card_number=data['card_number'],
                type=data['type'],
                status='active'
            )

            db.session.add(card)
            db.session.commit()

            return jsonify({
                'message': 'Card created successfully',
                'card_id': card.id
            }), 201

        except Exception as e:
            db.session.rollback()
            print(f"Card creation error: {str(e)}")
            return jsonify({'error': 'Card creation failed'}), 500
