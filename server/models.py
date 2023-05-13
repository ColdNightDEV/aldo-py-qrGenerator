from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4

db = SQLAlchemy()

def get_uuid():
    return uuid4().hex

class Referral(db.Model):
    __tablename__ = "Referrals"
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.String(32), db.ForeignKey("Users.id"), nullable=False)
    referred_id = db.Column(db.String(32), db.ForeignKey("Users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add the relationship backrefs
    referrer = db.relationship("User", foreign_keys=[referrer_id], backref=db.backref("referrer_referrals", lazy=True))
    referred = db.relationship("User", foreign_keys=[referred_id], backref=db.backref("referrals_received", lazy=True))

    def __init__(self, referrer_id, referred_id):
        self.referrer_id = referrer_id
        self.referred_id = referred_id


class Transaction(db.Model):
    __tablename__ = "Transactions"
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    user_id = db.Column(db.String(32), db.ForeignKey("Users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    # Add other relevant columns for the transaction

    def __init__(self, user_id, amount):
        self.user_id = user_id
        self.amount = amount


class User(db.Model):
    __tablename__ = "Users"
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    email = db.Column(db.String(345), unique=True)
    password = db.Column(db.Text, nullable=False)
    qr_code = db.Column(db.String(255))
    paid = db.Column(db.Boolean, default=False)
    payment_reference = db.Column(db.String(255), default=None)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    state_of_origin = db.Column(db.String(255))
    date_of_birth = db.Column(db.String(10))
    local_government = db.Column(db.String(255))
    gender = db.Column(db.String(10))
    next_of_kin = db.Column(db.String(255))
    referral_code = db.Column(db.String(255), default=None)
    referral_id = db.Column(db.String(255), default=None)

    # Define the referral_users relationship    
    referrals_made = db.relationship("Referral", foreign_keys=[Referral.referrer_id], backref=db.backref("referrer_user_relationship", lazy=True))
    referral_received = db.relationship("Referral", foreign_keys=[Referral.referred_id], backref=db.backref("referred_user_relationship", lazy=True, uselist=False))

    # Define the refUserPaid relationship
    refUserPaid = db.relationship("Transaction", backref="user")

    def __init__(self, email, password, qr_code, first_name, last_name, phone_number,
                 state_of_origin, date_of_birth, local_government, gender, next_of_kin,
                 referral_code=None, referral_id=None, paid=False):
        self.email = email
        self.password = password
        self.qr_code = qr_code
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.state_of_origin = state_of_origin
        self.date_of_birth = date_of_birth
        self.local_government = local_government
        self.gender = gender
        self.next_of_kin = next_of_kin
        self.referral_code = referral_code
        self.referral_id = referral_id
        self.paid = paid
