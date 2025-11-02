# app/routes/auth.py
from flask import request, jsonify
from app import db
from app.models import User


def init_auth_routes(app):
    @app.route('/api/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()

            # Validation
            if not data or not data.get('name') or not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password required'}), 400

            # SQL: SELECT * FROM users WHERE email = ?
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'User already exists'}), 409

            # SQL: INSERT INTO users (email, name, usd_balance, lbp_balance, password_hash)
            # VALUES (?, ?, 0.0, 0.0, ?)
            # ORM: Create User object with parameters
            user = User(
                email=data['email'],
                name=data.get('name'),
                usd_balance=0.0,
                lbp_balance=0.0
            )
            user.set_password(data['password'])

            # db.session.add() = Stage the user for insertion (like git add)
            # SQL not executed yet - just added to transaction
            db.session.add(user)

            # db.session.commit() = Execute ALL staged operations atomically
            # SQL: BEGIN TRANSACTION;
            # SQL: INSERT INTO users ...; (actual execution)
            # SQL: COMMIT; (Commit + Push)
            db.session.commit()

            return jsonify({
                'message': 'User created successfully',
                'user_id': user.id,
                'balances': {
                    'USD': user.usd_balance,
                    'LBP': user.lbp_balance
                }
            }), 201

        except Exception as e:
            # db.session.rollback() = Cancel ALL staged operations
            # SQL: ROLLBACK; (if commit failed, undo everything)
            db.session.rollback()
            print(f"Register error: {str(e)}")
            return jsonify({'error': 'Registration failed'}), 500
