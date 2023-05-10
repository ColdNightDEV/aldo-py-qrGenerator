from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SECRET_KEY"] = "abc"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    first_name = db.Column(db.String(250), nullable=False)
    surname = db.Column(db.String(250), nullable=False)
    ref_username = db.Column(db.String(250), unique=True, nullable=False)
    phone_no = db.Column(db.String(20), unique=True, nullable=False)
    state = db.Column(db.String(250), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    local_govt = db.Column(db.String(250), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    next_of_kin = db.Column(db.String(250), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        first_name = request.form.get("first_name")
        surname = request.form.get("surname")
        ref_username = request.form.get("ref_username")
        phone_no = request.form.get("phone_no")
        state = request.form.get("state")
        date_of_birth = datetime.strptime(
            request.form.get("date_of_birth"), "%d %B %Y").date()
        local_govt = request.form.get("local_govt")
        gender = request.form.get("gender")
        next_of_kin = request.form.get("next_of_kin")

        user = Users.query.filter_by(
            username=username, phone_no=phone_no).first()
        if user:
            return "Account with details like this exist already!!"

        new_user = Users(username=username, password=password, first_name=first_name, surname=surname, ref_username=ref_username, phone_no=phone_no,
                         state=state, date_of_birth=date_of_birth, local_govt=local_govt, gender=gender, next_of_kin=next_of_kin)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("sign_up.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Users.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for("home"))

        return "Invalid username or password"

    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/")
def home():
    if current_user.is_authenticated:
        return render_template("dashboard.html", username=current_user.username, date_of_birth=current_user.date_of_birth)
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    if current_user.is_authenticated:
        return render_template("dashboard.html", username=current_user.username)
    return "<h1>You are not logged in</h1>"


if __name__ == "__main__":
    app.run()
