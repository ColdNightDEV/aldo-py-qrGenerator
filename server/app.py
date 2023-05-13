from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from flask_session import Session
from config import ApplicationConfig
from models import db, User, Referral
import qrcode
from io import BytesIO
import requests
import string
import random
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

    referred_users = User.query.join(Referral, Referral.referred_id == User.id).filter(Referral.referrer_id == user.id).all()

    response = {
        "id": user.id,
        "email": user.email,
        "qr_code": user.qr_code,
        "paid": user.paid,
        "payment_reference": user.payment_reference,
        "referred_user_emails": [referred_user.email for referred_user in referred_users],
        "referred_user_ids": [referred_user.id for referred_user in referred_users]
    }

    return jsonify(response)



def generate_referral_id():
    characters = string.ascii_letters + string.digits
    referral_id = ''.join(random.choices(characters, k=8))
    existing_user = User.query.filter_by(referral_id=referral_id).first()
    if existing_user:
        return generate_referral_id()  # Regenerate if the referral ID already exists
    return referral_id


@app.route("/register", methods=["POST"])
def register_user():
    email = request.json["email"]
    password = request.json["password"]
    first_name = request.json["first_name"]
    last_name = request.json["last_name"]
    phone_number = request.json["phone_number"]
    state_of_origin = request.json["state_of_origin"]
    date_of_birth = request.json["date_of_birth"]
    local_government = request.json["local_government"]
    gender = request.json["gender"]
    next_of_kin = request.json["next_of_kin"]
    referral_code = request.json.get("referral_code", None)  # Optional field, set to None if not provided

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

    referral_id = generate_referral_id()

    # Create the referral link
    referral_link = f"http://localhost:5000/invite/{referral_id}"

    new_user = User(
        email=email,
        password=hashed_password,
        qr_code=img_str,
        paid=False,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        state_of_origin=state_of_origin,
        date_of_birth=date_of_birth,
        local_government=local_government,
        gender=gender,
        next_of_kin=next_of_kin,
        referral_code=referral_code,
        referral_id=referral_id
    )

    db.session.add(new_user)
    db.session.commit()

    response = {
        "id": new_user.id,
        "email": new_user.email,
        "qr_code": new_user.qr_code,
        "paid": new_user.paid,
        "payment_reference": new_user.payment_reference,
        "first_name": new_user.first_name,
        "last_name": new_user.last_name,
        "phone_number": new_user.phone_number,
        "state_of_origin": new_user.state_of_origin,
        "date_of_birth": new_user.date_of_birth,
        "local_government": new_user.local_government,
        "gender": new_user.gender,
        "next_of_kin": new_user.next_of_kin,
        "referral_code": new_user.referral_code,
        "referral_id": referral_id,
        "referral_link": referral_link
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
                'callback_url': f"https://localhost:5000/pay/{user_id}/verify"  # Set the callback URL
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
        user = User.query.get(user_id)

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

    # Return a response indicating the payment was not successful
    return jsonify({"paid": False})


@app.route("/invite/<referral_id>", methods=["GET", "POST"])
def handle_referral_registration(referral_id):
    # Check if the referral ID exists
    referrer = User.query.filter_by(referral_id=referral_id).first()
    if not referrer:
        return jsonify({"error": "Invalid referral ID"}), 404

    if request.method == "GET":
        return jsonify({"referrer_id": referrer.id}), 200

    # Parse request data for new user registration
    email = request.json.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Check if the email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already exists"}), 409

    password = request.json.get("password")
    first_name = request.json.get("first_name")
    last_name = request.json.get("last_name")
    phone_number = request.json.get("phone_number")
    state_of_origin = request.json.get("state_of_origin")
    date_of_birth = request.json.get("date_of_birth")
    local_government = request.json.get("local_government")
    gender = request.json.get("gender")
    next_of_kin = request.json.get("next_of_kin")

    # Create the new user
    new_user = User(
        email=email,
        password=password,
        qr_code=None,
        paid=False,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        state_of_origin=state_of_origin,
        date_of_birth=date_of_birth,
        local_government=local_government,
        gender=gender,
        next_of_kin=next_of_kin,
        referral_code=None,
        referral_id=None
    )

    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    # Record referral if referrer exists
    referral = Referral(referrer_id=referrer.id, referred_id=new_user.id)
    db.session.add(referral)
    db.session.commit()

    # Update the referral information for the referrer
    referrer.referrals_made.append(referral)
    db.session.commit()

    response = {
        "id": new_user.id,
        "email": new_user.email,
        # Other user attributes
        "referrer_id": referrer.id
    }

    return jsonify(response), 200




if __name__ == "__main__":
    app.run(debug=True)