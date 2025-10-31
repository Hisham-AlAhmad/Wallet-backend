# app/routes/webhook.py
from flask import request, jsonify
from app import db
from app.models import User, Card, Transaction
from decimal import Decimal
from datetime import datetime


def init_webhook_routes(app):
    @app.route('/webhook/card-auth', methods=['POST'])
    def card_authorization():
        """
        Bank sends card payment requests here
        We approve/decline based on card status and user balance
        """
        try:
            bank_data = request.get_json()
            print("Bank webhook received:", bank_data)

            # STEP 1: Check idempotency FIRST (before any processing)
            idempotency_key = bank_data.get('idempotency_key')
            if idempotency_key:
                existing = Transaction.query.filter_by(reference_id=idempotency_key).first()
                if existing:
                    # Already processed - return cached response
                    if existing.status == 'completed':
                        return jsonify(create_approve_response(bank_data, existing.sender, existing.currency)), 200
                    else:
                        return jsonify(create_decline_response(bank_data, "Previously declined")), 200

            # STEP 2: Find the card
            card = Card.query.filter_by(card_number=bank_data['primaryAccountNumber']).first()

            # STEP 3: Validation checks
            if not card:
                return jsonify(create_decline_response(bank_data, "Card not found")), 200

            if not card.is_active():
                return jsonify(create_decline_response(bank_data, "Card not active")), 200

            user = card.user
            amount = Decimal(str(bank_data['amountTransaction']))
            currency = 'USD' if bank_data['currencyCode'] == '840' else 'LBP'

            if not user.can_debit(amount, currency):
                return jsonify(create_decline_response(bank_data, "Insufficient funds")), 200

            # STEP 4: APPROVE - debit user
            user.debit(amount, currency)

            # STEP 5: Create transaction with idempotency_key
            transaction = Transaction(
                from_user_id=user.id,
                to_user_id=None,
                card_id=card.id,
                amount=amount,
                currency=currency,
                transaction_type='card_payment',
                status='completed',
                reference_id=idempotency_key  # ← Store the idempotency key!
            )

            db.session.add(transaction)
            db.session.commit()

            # STEP 6: Return approval response
            return jsonify(create_approve_response(bank_data, user, currency)), 200

        except Exception as e:
            db.session.rollback()
            print(f"Webhook error: {str(e)}")
            return jsonify(create_decline_response(bank_data, "System error")), 200

    def create_approve_response(bank_data, user, currency):
        """Create APPROVED response for bank"""
        return {
            "messageType": "2110",
            "primaryAccountNumber": bank_data['primaryAccountNumber'],
            "processingCode": bank_data['processingCode'],
            "amountTransaction": bank_data['amountTransaction'],
            "amountCardholderBilling": bank_data['amountCardholderBilling'],
            "dateAndTimeTransmission": bank_data['dateAndTimeTransmission'],
            "conversionRateCardholderBilling": bank_data['conversionRateCardholderBilling'],
            "systemsTraceAuditNumber": bank_data['systemsTraceAuditNumber'],
            "dateCapture": bank_data.get('dateCapture'),
            "merchantCategoryCode": bank_data['merchantCategoryCode'],
            "acquiringInstitutionIdentificationCode": bank_data['acquiringInstitutionIdentificationCode'],
            "retrievalReferenceNumber": bank_data['retrievalReferenceNumber'],
            "cardAcceptorTerminalIdentification": bank_data.get('cardAcceptorTerminalIdentification'),
            "cardAcceptorIdentificationCode": bank_data['cardAcceptorIdentificationCode'],
            "cardAcceptorName": bank_data['cardAcceptorName'],
            "cardAcceptorCity": bank_data['cardAcceptorCity'],
            "cardAcceptorCountryCode": bank_data['cardAcceptorCountryCode'],
            "actionCode": "00",  # 00 = Approved
            "approvalCode": "123456",  # Mock approval code
            "additionalAmounts": [
                {
                    "accountType": "00",
                    "amountType": "02",
                    "currencyCode": bank_data['currencyCode'],
                    "currencyMinorUnit": "2",
                    "amountSign": "C",
                    "value": str(int(user.get_balance(currency) * 100)).zfill(12)  # Balance in minor units
                }
            ]
        }

    def create_decline_response(bank_data, reason):
        """Create DECLINED response for bank"""
        response = {
            "messageType": "2110",
            "primaryAccountNumber": bank_data['primaryAccountNumber'],
            "processingCode": bank_data['processingCode'],
            "amountTransaction": bank_data['amountTransaction'],
            "amountCardholderBilling": bank_data['amountCardholderBilling'],
            "dateAndTimeTransmission": bank_data['dateAndTimeTransmission'],
            "conversionRateCardholderBilling": bank_data['conversionRateCardholderBilling'],
            "systemsTraceAuditNumber": bank_data['systemsTraceAuditNumber'],
            "dateCapture": bank_data.get('dateCapture'),
            "merchantCategoryCode": bank_data['merchantCategoryCode'],
            "acquiringInstitutionIdentificationCode": bank_data['acquiringInstitutionIdentificationCode'],
            "retrievalReferenceNumber": bank_data['retrievalReferenceNumber'],
            "cardAcceptorTerminalIdentification": bank_data.get('cardAcceptorTerminalIdentification'),
            "cardAcceptorIdentificationCode": bank_data['cardAcceptorIdentificationCode'],
            "cardAcceptorName": bank_data['cardAcceptorName'],
            "cardAcceptorCity": bank_data['cardAcceptorCity'],
            "cardAcceptorCountryCode": bank_data['cardAcceptorCountryCode'],
            "actionCode": "05",  # 05 = Decline
            "approvalCode": "000000",  # 000000 on failure
            "additionalAmounts": [
                {
                    "accountType": "00",
                    "amountType": "02",
                    "currencyCode": bank_data['currencyCode'],
                    "currencyMinorUnit": "2",
                    "amountSign": "C",
                    "value": "000000000000"  # Zero balance on decline
                }
            ]
        }
        print(f"Payment declined: {reason}")
        return response
