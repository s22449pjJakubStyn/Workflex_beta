from functools import wraps

from flask import Flask, render_template, request, redirect, session, url_for
from forms import RegistrationEmployeeForm, RegistrationEmployerForm

import firebase_admin
from firebase_admin import credentials, firestore, auth

import os

import mail as mail

from flask_mail import Message, Mail

# Inicjalizacja aplikacji Flask
app = Flask(__name__)

app.secret_key = os.urandom(24)

# Inicjalizacja Firebase
cred = credentials.Certificate("key.json")  # Ścieżka do klucza prywatnego Firebase
firebase_admin.initialize_app(cred)
db = firestore.client()

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587  # or the appropriate port number
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'firmex.zgloszenia@gmail.com'
app.config['MAIL_PASSWORD'] = 'ufbdtexftqzsdmcg'
app.config['SECRET_KEY'] = os.urandom(24)

mail = Mail(app)


# Strona główna
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register_main')
def register_main():
    return render_template('register_main.html')


@app.route('/login_main')
def login_main():
    return render_template('login_main.html')


# Rejestracja użytkownika
@app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():
    form = RegistrationEmployeeForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        name = form.name.data
        surname = form.surname.data
        phone = form.phone.data
        status = 'Active'

        try:
            # Utwórz użytkownika w Firebase Authentication
            user = auth.create_user(email=email, password=password)

            # Wyślij link weryfikacyjny na adres e-mail użytkownika
            verification_link = auth.generate_email_verification_link(email)

            # Ustaw dane użytkownika w bazie danych Firestore
            doc_ref = db.collection('Employee').document(user.uid)
            doc_ref.set({
                'user_id': user.uid,
                'first_name': name,
                'last_name': surname,
                'email': email,
                'phone': phone,
                'status': status,
            })

            msg = Message('Email verification', sender='your_email@example.com', recipients=[email])
            msg.body = f'Your email verification link: {verification_link}'
            mail.send(msg)

            # Przekierowanie na stronę z komunikatem o wysłaniu linku weryfikacyjnego
            return redirect(url_for('sent_verification', email=email))
        except Exception as e:
            return str(e)
    return render_template('register_employee.html', form=form)


# Rejestracja użytkownika
@app.route('/register_employer', methods=['GET', 'POST'])
def register_employer():
    form = RegistrationEmployerForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        name = form.name.data
        phone = form.phone.data
        status = 'Active'

        try:
            # Utwórz użytkownika w Firebase Authentication
            user = auth.create_user(email=email, password=password)

            # Wyślij link weryfikacyjny na adres e-mail użytkownika
            verification_link = auth.generate_email_verification_link(email)

            # Ustaw dane użytkownika w bazie danych Firestore
            doc_ref = db.collection('Company').document(user.uid)
            doc_ref.set({
                'user_id': user.uid,
                'first_name': name,
                'email': email,
                'phone': phone,
                'status': status,
            })

            msg = Message('Email verification', sender='your_email@example.com', recipients=[email])
            msg.body = f'Your email verification link: {verification_link}'
            mail.send(msg)

            # Przekierowanie na stronę z komunikatem o wysłaniu linku weryfikacyjnego
            return redirect(url_for('sent_verification', email=email))
        except Exception as e:
            return str(e)
    return render_template('register_employer.html', form=form)


def email_exists_in_database(f):
    @wraps(f)
    def decorated_function(email):
        try:
            user = auth.get_user_by_email(email)
            return f(email)
        except auth.UserNotFoundError:
            if request.referrer:
                return redirect(request.referrer)
            else:
                return redirect(url_for(
                    'index'))  # lub dowolna inna strona, gdy nie ma informacji o stronie, z której przyszedł użytkownik

    return decorated_function


def email_verified_in_database(f):
    @wraps(f)
    def decorated_function(email):
        try:
            user = auth.get_user_by_email(email)
            if user.email_verified:
                return redirect(url_for('index'))
            else:
                return f(email)
        except auth.UserNotFoundError:
            return redirect(url_for('index'))

    return decorated_function


@app.route('/sent_verification/<email>', methods=['GET'])
@email_verified_in_database
def sent_verification(email):
    return render_template('verification_sent.html', email=email)


# Logowanie użytkownika
@app.route('/login_employee', methods=['GET', 'POST'])
def login_employee():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Wykorzystaj Firebase Admin SDK do logowania użytkownika
        try:
            user = auth.get_user_by_email(email)
            if user.email_verified:
                session['user'] = {
                    'email': email,
                    'uid': user.uid
                }
                return redirect('/profile')
            else:
                return render_template('verification_sent.html', email=email)
        except Exception as e:
            return str(e)
    return render_template('login_employee.html')


# Logowanie użytkownika
@app.route('/login_employer', methods=['GET', 'POST'])
def login_employer():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Wykorzystaj Firebase Admin SDK do logowania użytkownika
        try:
            user = auth.get_user_by_email(email)
            if user.email_verified:
                session['user'] = {
                    'email': email,
                    'uid': user.uid
                }
                return redirect('/profile')
            else:
                return render_template('verification_sent.html', email=email)
        except Exception as e:
            return str(e)
    return render_template('login_employer.html')


@app.route('/password_reset', methods=['GET', 'POST'])
def password_reset():
    if request.method == 'POST':
        email = request.form['email']

        try:
            user = auth.get_user_by_email(email)

            reset_link = auth.generate_password_reset_link(email)

            if user.email_verified:
                msg = Message('Password reset link', sender='your_email@example.com', recipients=[email])
                msg.body = f'Your password reset link: {reset_link}'
                mail.send(msg)
                return render_template('reset_link.html', email=email, user=user)
            else:
                return render_template('index.html')
        except Exception as e:
            return str(e)
    return render_template('password_reset.html')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated_function


@app.route('/profile')
@login_required
def profile():
    if 'user' in session:
        user = session['user']
        return render_template('profile.html', user=user)
    return redirect('/login')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login_main')


if __name__ == '__main__':
    app.run(debug=True)
