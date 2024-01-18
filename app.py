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
            workplace_ref = doc_ref.collection('Workplace').document('default')
            workplace_ref.set({})

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
                return redirect(url_for('login_main'))
            else:
                return f(email)
        except auth.UserNotFoundError:
            return redirect(url_for('index'))

    return decorated_function


@app.route('/sent_verification/<email>', methods=['GET'])
@email_verified_in_database
def sent_verification(email):
    return render_template('verification_sent.html', email=email)


# Moduł logowania pracownika
@app.route('/login_employee', methods=['GET', 'POST'])
def login_employee():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Wykorzystaj Firebase Admin SDK do logowania użytkownika
        try:
            user = auth.get_user_by_email(email)
            if is_employee(email):
                if user.email_verified:
                    session['user'] = {
                        'email': email,
                        'uid': user.uid,
                        'role': 'Employee'
                    }
                    return redirect('/employee_main_page')
                else:
                    return render_template('verification_sent.html', email=email)
            else:
                return render_template('login_employee.html', error_message='Próbowałeś zalogować się na konto firmy.')
        except Exception as e:
            return str(e)
    return render_template('login_employee.html')


# Moduł logowania pracodawcy
@app.route('/login_employer', methods=['GET', 'POST'])
def login_employer():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Wykorzystaj Firebase Admin SDK do logowania użytkownika
        try:
            user = auth.get_user_by_email(email)
            if is_employer(email):
                if user.email_verified:
                    session['user'] = {
                        'email': email,
                        'uid': user.uid,
                        'role': 'Employee'
                    }
                    return redirect('/employer_main_page')
                else:
                    return render_template('verification_sent.html', email=email)
            else:
                return render_template('login_employer.html',
                                       error_message='Próbowałeś zalogować się na konto pracownika.')
        except Exception as e:
            return str(e)
    return render_template('login_employer.html')


# Funkcje pomocnicze sprawdzające rolę użytkownika
def is_employee(email):
    # Sprawdź, czy email należy do pracownika w Firebase (np. w kolekcji "Employee")
    # Zwróć True, jeśli należy do pracownika, w przeciwnym razie False
    # Poniżej znajdziesz przykładową implementację, którą trzeba dostosować do swojej bazy danych
    employee_docs = db.collection('Employee').where('email', '==', email).stream()
    return any(employee.exists for employee in employee_docs)


def is_employer(email):
    # Sprawdź, czy email należy do pracownika w Firebase (np. w kolekcji "Employee")
    # Zwróć True, jeśli należy do pracownika, w przeciwnym razie False
    # Poniżej znajdziesz przykładową implementację, którą trzeba dostosować do swojej bazy danych
    employer_docs = db.collection('Company').where('email', '==', email).stream()
    return any(employer.exists for employer in employer_docs)


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


@app.route('/employee_main_page')
@login_required
def employee_main_page():
    if 'user' in session:
        user = session['user']
        return render_template('employee_main_page.html', user=user)
    return redirect('/login')


@app.route('/employer_main_page')
@login_required
def employer_main_page():
    if 'user' in session:
        user = session['user']
        return render_template('employer_main_page.html', user=user)
    return redirect('/login')


@app.route('/teams', methods=['GET', 'POST'])
@login_required
def teams():
    error_message = None
    team_names = []

    try:
        employer_uid = session.get('user', {}).get('uid')
        teams_ref = db.collection('Company').document(employer_uid).collection('Workplace')
        teams = teams_ref.stream()

        # Pomijaj zespół o nazwie 'default' i sprawdzaj, czy istnieje pole 'Team name' i czy nie jest puste
        team_names = sorted([team.to_dict().get('Team name') for team in teams if
                             team.exists and team.to_dict().get('Team name') and team.to_dict().get(
                                 'Team name') != 'default'])
        app.logger.info("Team names retrieved: %s", team_names)

    except Exception as e:
        error_message = str(e)
        app.logger.warning("Failed to retrieve team names. Error message: %s", error_message)

    return render_template('teams.html', team_names=team_names, error_message=error_message)


@app.route('/create_teams', methods=['GET', 'POST'])
@login_required
def create_teams():
    error_message = None

    if request.method == 'POST':
        app.logger.debug("Request received for /create_teams")  # Dodaj log debugowania
        team_name = request.form.get('team_name')
        team_acronim_name = request.form.get('team_acronim_name')
        team_description = request.form.get('team_description')
        team_adres_street = request.form.get('team_adres_street')
        team_adres_city = request.form.get('team_adres_city')
        team_adres_postal_code = request.form.get('team_adres_postal_code')
        team_phone = request.form.get('team_phone')
        try:
            employer_uid = session.get('user', {}).get('uid')
            team_id = team_name

            existing_team = db.collection('Company').document(employer_uid).collection(
                'Workplace').document(team_name).get()
            if existing_team.exists:
                error_message = 'Zespół o danej nazwie już istnieje.'
            else:
                doc_ref = db.collection('Company').document(employer_uid).collection('Workplace').document(team_id)
                doc_ref.set({
                    'Team name': team_name,
                    'Team acronim': team_acronim_name,
                    'Team description': team_description,
                    'Team street adress': team_adres_street,
                    'Team city address': team_adres_city,
                    'Team postal code address': team_adres_postal_code,
                    'Team phone number': team_phone,
                })
                app.logger.info("Team created: %s", team_name)  # Dodaj ten log

                return redirect(url_for('teams'))
        except Exception as e:
            error_message = str(e)
            app.logger.error("Error while creating team: %s", error_message)

    app.logger.warning("Form submission failed. Error message: %s", error_message)  # Dodaj ten log
    return render_template('teams.html', error_message=error_message)


@app.route('/team/<team_name>')
@login_required
def team_main_page(team_name):
    # Tutaj możesz dodać kod obsługujący stronę zespołu, np. pobieranie danych z bazy danych
    # i przekazanie ich do szablonu
    return render_template('team_main_page.html', team_name=team_name)


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login_main')


if __name__ == '__main__':
    app.run(debug=True)
