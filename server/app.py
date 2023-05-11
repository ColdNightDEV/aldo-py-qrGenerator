from flask import Flask, request, jsonify, session, redirect, url_for
from flask_bcrypt import Bcrypt
from flask_session import Session
from config import ApplicationConfig
from models import db, User
import qrcode
from io import BytesIO
import requests
import base64

app = Flask(__name__)
app.config.from_object(ApplicationConfig)

bcrypt = Bcrypt(app)
server_session = Session(app)
db.init_app(app)

with app.app_context():
    db.create_all()


@app.route('/@me')
def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "unauthorized"}), 401

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    response = {
        "id": user.id,
        "email": user.email,
        "qr_code": user.qr_code,
        "paid": user.paid,
        "payment_reference": user.payment_reference  # Include the payment_reference in the response
    }

    return jsonify(response)


@app.route("/register", methods=["POST"])
def register_user():
    email = request.json["email"]
    password = request.json["password"]

    user_exists = User.query.filter_by(email=email).first() is not None

    if user_exists:
        return jsonify({"error": "A user with these credentials already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(password)

    # Generate the qr code
    data = email
    img = qrcode.make(data)
    buffer = BytesIO()
    img.save(buffer)
    img_str = base64.b64encode(buffer.getvalue()).decode()

    new_user = User(email=email, password=hashed_password, qr_code=img_str, paid=False)  # Set paid to False

    db.session.add(new_user)
    db.session.commit()

    response = {
        "id": new_user.id,
        "email": new_user.email,
        "qr_code": new_user.qr_code,
        "paid": new_user.paid,
        "payment_reference": new_user.payment_reference  # Include the payment_reference in the response
    }

    return jsonify(response)


@app.route("/login", methods=["POST"])
def login_user():
    email = request.json["email"]
    password = request.json["password"]

    user = User.query.filter_by(email=email).first()

    if user is None:
        return jsonify({"error": "Unauthorized"}), 401

    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Unauthorized"}), 401

    session["user_id"] = user.id

    response = {
        "id": user.id,
        "email": user.email,
        "qr_code": user.qr_code,
        "paid": user.paid,
        "payment_reference": user.payment_reference  # Include the payment_reference in the response
    }

    return jsonify(response)


@app.route("/pay/<user_id>", methods=["POST"])
def pay_for_qr_code(user_id):
    # Retrieve the user from the database
    PAYSTACK_SECRET_KEY = "sk_test_9080fa15f69abfac244cb0f461282c7f25ca2751"
    user = User.query.filter_by(id=user_id).first()

    # Check if the user exists
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        # Make a payment request to Paystack API to initiate payment
        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            json={
                'amount': 5000,  # Specify the payment amount
                'email': user.email,  # Provide the user's email
                'metadata': {
                    'user_id': user.id,  # Include the user_id in metadata
                },
                'callback_url': f"https://loacalhost:5000/pay/{user_id}/verify"  # Set the callback URL
            },
            headers={
                'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',  # Set your Paystack secret key here
                'Content-Type': 'application/json',
            }
        )

        data = response.json()
        authorization_url = data['data']['authorization_url']
        payment_reference = data['data']['reference']

        # Update the user's payment reference in the database
        user.payment_reference = payment_reference
        db.session.commit()

        return jsonify({"authorization_url": authorization_url})

    except Exception as e:
        print('Payment initiation failed:', str(e))
        return jsonify({"error": "Payment initiation failed"}), 500
    
    


@app.route("/pay/<user_id>/verify", methods=["GET"])
def verify_payment(user_id):
    PAYSTACK_SECRET_KEY = "sk_test_9080fa15f69abfac244cb0f461282c7f25ca2751"

    # Retrieve the payment reference and transaction reference from the query parameters
    payment_reference = request.args.get("reference")
    transaction_reference = request.args.get("trxref")

    # Check if the payment reference or transaction reference is missing
    if not payment_reference or not transaction_reference:
        return jsonify({"error": "Payment reference or transaction reference missing"}), 400

    # Make a request to the Paystack API to verify the payment
    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{payment_reference}",
        headers={
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
    )

    # Check the response status code
    if response.status_code != 200:
        return jsonify({"error": "Payment verification failed"}), 400

    # Retrieve the verification result from the response
    verification_data = response.json()

    # Check if the payment was successful
    if verification_data["data"]["status"] == "success":
        # Retrieve the user from the database based on the user ID
        user = User.query.filter_by(id=user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Update the user's payment status if the payment is successful
        user.paid = True
        db.session.commit()

        response = {
            "paid": user.paid,
            "payment_reference": user.payment_reference,
            "transaction_reference": transaction_reference
        }

        return jsonify(response)

    return jsonify({"paid": False})


# @app.route("/verify_payment", methods=["POST"])
# def verify_payment():
#     PAYSTACK_SECRET_KEY = "sk_test_9080fa15f69abfac244cb0f461282c7f25ca2751"
    
#     try:
#         # Retrieve the payment reference from the request
#         payment_reference = request.json.get("payment_reference")

#         # Make a request to the Paystack API to verify the payment
#         response = requests.get(
#             f"https://api.paystack.co/transaction/verify/{payment_reference}",
#             headers={
#                 "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
#                 "Content-Type": "application/json",
#             }
#         )

#         # Check the response status code
#         if response.status_code != 200:
#             return jsonify({"error": "Payment verification failed"}), 400

#         # Retrieve the verification result from the response
#         verification_data = response.json()

#         # Check if the payment was successful
#         if verification_data["data"]["status"] == "success":
#             # Retrieve the user from the database based on the payment reference
#             user = User.query.filter_by(payment_reference=payment_reference).first()

#             if not user:
#                 return jsonify({"error": "User not found"}), 404

#             # Update the user's payment status if the payment is successful
#             user.paid = True
#             db.session.commit()

#             response = {
#                 "paid": user.paid,
#                 "payment_reference": user.payment_reference
#             }

#             return jsonify(response)

#         return jsonify({"paid": False})

#     except Exception as e:
#         print('Payment verification failed:', str(e))
#         return jsonify({"error": "Payment verification failed"}), 500


if __name__ == "__main__":
    app.run(debug=True)