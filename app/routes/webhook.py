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
            print("Bank webhook received:", bank_data)  # For debugging

            # Find the card
            card = Card.query.filter_by(card_number=bank_data['primaryAccountNumber']).first()

            # Validation checks
            if not card:
                return create_decline_response(bank_data, "Card not found")

            if not card.is_active():
                return create_decline_response(bank_data, "Card not active")

            user = card.user
            amount = Decimal(str(bank_data['amountTransaction']))
            currency = 'USD' if bank_data['currencyCode'] == '840' else 'LBP'

            if not user.can_debit(amount, currency):
                return create_decline_response(bank_data, "Insufficient funds")

            # If all checks pass - APPROVE
            user.debit(amount, currency)

            # Create transaction record
            transaction = Transaction(
                from_user_id=user.id,
                to_user_id=None,  # Bank/merchant receives money
                card_id=card.id,
                amount=amount,
                currency=currency,
                transaction_type='card_payment',
                status='completed'
            )

            db.session.add(transaction)
            db.session.commit()

            return create_approve_response(bank_data, user, currency)

        except Exception as e:
            print(f"Webhook error: {str(e)}")
            return jsonify({'error': 'Authorization failed'}), 500

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
                    "currencyCode": "840",
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
                    "currencyCode": "840",
                    "currencyMinorUnit": "2",
                    "amountSign": "C",
                    "value": "000000000000"  # Zero balance on decline
                }
            ]
        }
        print(f"Payment declined: {reason}")
        return response
