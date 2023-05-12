import requests
import dotenv
from flask import Flask, request, jsonify
from config import ApplicationConfig
from models import db, User


app = Flask(__name__)
app.config.from_object(ApplicationConfig)

PAYSTACK_SECRET_KEY = "sk_test_9080fa15f69abfac244cb0f461282c7f25ca2751"

@app.route('/pay', methods=['POST'])
def initialize_payment():
    try:
        data = request.get_json()
        amount = data.get('amount')
        email = data.get('email')
        reference = data.get('reference')

        if not amount or not email or not reference:
            return jsonify({'error': 'Missing required parameters'}), 400
        try:
            amount = int(amount)
        except ValueError:
            return jsonify({'error': 'Invalid amount'}), 400

        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
            }
        payload = {
            'amount': amount * 100, # Paystack expects amount in kobo (multiply by 100 for naira)
            'email': email,
            'reference': reference
        }
        response = requests.post('https://api.paystack.co/transaction/initialize', json=payload, headers=headers)
        data = response.json()
        authorization_url = data.get('data', {}).get('authorization_url')
        access_code = data.get('data', {}).get('access_code')
    
        return jsonify({'authorization_url': authorization_url, 'access_code': access_code})

    except Exception as e:
        print('Error initializing payment:', str(e))
    return jsonify({'error': 'An error occurred while initializing payment'}), 500

@app.route('/verify')
def verify_payment():
    try:
        reference = request.args.get('reference')

        if not reference:
            return jsonify({'error': 'Missing payment reference'}), 400

        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}'
            }
        response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
        data = response.json()

        status = data.get('data', {}).get('status')
        amount = data.get('data', {}).get('amount')
        email = data.get('data', {}).get('customer', {}).get('email')

        if status == 'success':
            # Payment was successful
            # Do something with the successful payment
            return jsonify({'status': 'success', 'amount': amount, 'email': email})
        else:
            # Payment was not successful
            # Handle failed payment
            return jsonify({'status': 'failed', 'amount': amount, 'email': email})

    except Exception as e:
        print('Error verifying payment:', str(e))
        return jsonify({'error': 'An error occurred while verifying payment'}), 500

if __name__ == '__main__':
    app.run(debug=True)