# app/routes/auth.py
from flask import request, jsonify
from app import db
from app.models import User


def init_auth_routes(app):
    @app.route('/api/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()

            # Basic validation
            if not data or not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email and password required'}), 400

            # Check if user exists
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'User already exists'}), 409

            # Create user with default balances
            user = User(
                email=data['email'],
                name=data.get('name', ''),
                usd_balance=0.0,
                lbp_balance=0.0
            )
            user.set_password(data['password'])

            db.session.add(user)
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
            db.session.rollback()
            return jsonify({'error': 'Registration failed'}), 500
