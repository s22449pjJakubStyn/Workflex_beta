from functools import wraps

from flask import Flask, render_template, request, redirect, session, url_for, jsonify
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
            workplace_ref = doc_ref.collection('Workplace').document('default')
            workplace_ref.set({})
            cal_ref = doc_ref.collection('Calendar').document('default')
            cal_ref.set({})

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
    if 'user' in session and is_employer():
        return redirect('/login_employer')
    if 'user' in session and is_employee():
        return redirect('/login_employee')

    else:
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
                    if 'redirected_from_verification' in session:
                        del session['redirected_from_verification']
                        return redirect('/login_employee')
                    else:
                        return redirect('/employee_main_page')
                else:
                    # Jeśli mail nie jest zweryfikowany, ustaw zmienną sesyjną
                    # 'redirected_from_verification' i przekieruj na verification_sent.html
                    session['redirected_from_verification'] = True
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
                    if 'redirected_from_verification' in session:
                        del session['redirected_from_verification']
                        return redirect('/login_employer')
                    else:
                        return redirect('/employer_main_page')
                else:
                    session['redirected_from_verification'] = True
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
    team_data = []

    try:
        employer_uid = session.get('user', {}).get('uid')
        teams_ref = db.collection('Company').document(employer_uid).collection('Workplace')
        teams = teams_ref.stream()

        # Pobierz nazwy zespołów i ich identyfikatory
        for team in teams:
            if team.exists:
                team_dict = team.to_dict()
                team_name = team_dict.get('TeamName')
                team_uid = team.id  # Pobierz identyfikator zespołu
                if team_name and team_name != 'default':
                    team_data.append({'name': team_name, 'uid': team_uid})

    except Exception as e:
        error_message = str(e)

    return render_template('teams.html', team_data=team_data, error_message=error_message)


@app.route('/create_teams', methods=['GET', 'POST'])
@login_required
def create_teams():
    error_message = None
    team_names = []  # Zainicjuj pustą listę

    if request.method == 'POST':
        app.logger.debug("Request received for /create_teams")  # Dodaj log debugowania
        team_name = request.form.get('team_name')
        team_acronim_name = request.form.get('team_acronim_name')
        team_description = request.form.get('team_description')
        team_adres_street = request.form.get('team_adres_street')
        team_adres_city = request.form.get('team_adres_city')
        team_adres_postal_code = request.form.get('team_adres_postal_code')
        team_phone = request.form.get('team_phone')
        start_hour = request.form.get('start_hour')
        end_hour = request.form.get('end_hour')
        try:
            employer_uid = session.get('user', {}).get('uid')

            existing_team = db.collection('Company').document(employer_uid).collection(
                'Workplace').document(team_name).get()
            if existing_team.exists:
                error_message = 'Zespół o danej nazwie już istnieje.'
            else:
                doc_ref = db.collection('Company').document(employer_uid).collection('Workplace').document()
                doc_ref.set({
                    'TeamName': team_name,
                    'TeamAcronim': team_acronim_name,
                    'TeamDescription': team_description,
                    'TeamStreetAdress': team_adres_street,
                    'TeamCityAddress': team_adres_city,
                    'TeamPostalCodeAddress': team_adres_postal_code,
                    'TeamPhoneNumber': team_phone,
                    'TeamStartShiftHour': start_hour,
                    'TeamEndShiftHour': end_hour,
                })
                employess_ref = doc_ref.collection('Employess').document('default')
                employess_ref.set({})
                app.logger.info("Team created: %s", team_name)  # Dodaj ten log

                return redirect(url_for('teams'))
        except Exception as e:
            error_message = str(e)
            app.logger.error("Error while creating team: %s", error_message)

    # Jeśli wystąpił błąd lub zespół istniał, pobierz listę zespołów
    try:
        employer_uid = session.get('user', {}).get('uid')
        teams_ref = db.collection('Company').document(employer_uid).collection('Workplace')
        teams = teams_ref.stream()

        # Pomijaj zespół o nazwie 'default' i sprawdzaj, czy istnieje pole 'Team name' i czy nie jest puste
        team_names = sorted([team.to_dict().get('TeamName') for team in teams if
                             team.exists and team.to_dict().get('TeamName') and team.to_dict().get(
                                 'TeamName') != 'default'])

    except Exception as e:
        error_message = str(e)

    app.logger.warning("Form submission failed. Error message: %s", error_message)  # Dodaj ten log
    return render_template('teams.html', error_message=error_message, team_names=team_names)


@app.route('/team/<team_name>?<team_uid>')
@login_required
def team_main_page(team_name, team_uid=None):
    # Tutaj możesz dodać kod obsługujący stronę zespołu, np. pobieranie danych z bazy danych
    # i przekazanie ich do szablonu
    return render_template('team_main_page.html', team_name=team_name, team_uid=team_uid)


@app.route('/team/<team_name>?<team_uid>/employees')
def team_employees(team_name, team_uid=None):
    error_message = None
    employees_data = []

    try:
        employer_uid = session.get('user', {}).get('uid')
        employees_ref = db.collection('Company').document(employer_uid).collection('Workplace').document(
            team_uid).collection('Employess')
        employees = employees_ref.stream()

        for employee_doc in employees:
            if employee_doc.id == 'default':
                continue
            employee_id = employee_doc.get('EmployeeID')

            # Pobierz dane pracownika na podstawie identyfikatora
            company_employee_ref = db.collection('Employee').document(employee_id)
            company_employee_data = company_employee_ref.get().to_dict()

            # Dodaj dane pracownika do listy
            if company_employee_data:
                employees_data.append(company_employee_data)

    except Exception as e:
        error_message = str(e)
        print("Error retrieving data:", e)  # Dodaj print dla błędu

    print("Employees data:", employees_data)  # Dodaj print dla listy danych pracowników
    return render_template('team_employees.html', team_name=team_name, team_uid=team_uid, employees_data=employees_data,
                           error_message=error_message)


@app.route('/team/<team_name>/<team_uid>/employees?<employee_id>')
@login_required
def team_employees_main_page(team_name, team_uid=None, employee_id=None):
    error_message = None
    employee_data = None

    try:
        # Pobierz dane pracownika na podstawie identyfikatora
        company_employee_ref = db.collection('Employee').document(employee_id)
        employee_data = company_employee_ref.get().to_dict()
    except Exception as e:
        error_message = str(e)
        print("Error retrieving data:", e)

    # Przekazanie danych pracownika jako kontekst do szablonu
    return render_template('team_employees_main_page.html', team_name=team_name, team_uid=team_uid,
                           employee_data=employee_data, error_message=error_message)


@app.route('/team/<team_name>/<team_uid>/employees/<employee_name>?<employee_id>/preferences')
@login_required
def team_employees_preferences(team_name, team_uid=None, employee_name=None, employee_id=None):
    error_message = None
    employee_preferences = {}
    employee_data = None
    try:
        company_employee_ref = db.collection('Employee').document(employee_id)
        employee_data = company_employee_ref.get().to_dict()

        # Pobierz wszystkie miejsca pracy pracownika
        employee_workplaces_ref = db.collection('Employee').document(employee_id) \
            .collection('Workplace').stream()

        for doc in employee_workplaces_ref:
            if doc.id == 'default':
                continue
            workplace_data = doc.to_dict()
            workplace_id = workplace_data.get('WorkplaceID')

            # Jeśli WorkplaceID odpowiada team_uid, pobierz preferencje pracownika
            if workplace_id == team_uid:
                employee_preferences_ref = db.collection('Employee').document(employee_id) \
                    .collection('Workplace').document(doc.id) \
                    .collection('Preferences').document('PreferencesValues')

                employee_preferences_data = employee_preferences_ref.get().to_dict()

                if employee_preferences_data:
                    min_shift = employee_preferences_data.get('MinShiftLength')
                    max_shift = employee_preferences_data.get('MaxShiftLength')

                    if min_shift is not None:
                        employee_preferences['MinShiftLength'] = min_shift
                    if max_shift is not None:
                        employee_preferences['MaxShiftLength'] = max_shift
                else:
                    print("No preferences found for employee:", employee_id)
                break  # Przerwij pętlę po znalezieniu odpowiedniego miejsca pracy

    except Exception as e:
        error_message = str(e)
        print(f"Error retrieving data: {e}")

    return render_template('team_employees_preferences.html', employee_name=employee_name,
                           employee_preferences=employee_preferences, team_name=team_name, team_uid=team_uid,
                           employee_data=employee_data, error_message=error_message)


@app.route('/team/<team_name>?<team_uid>/settings', methods=['GET', 'POST'])
def team_setings(team_name, team_uid=None):
    error_message = None
    team_data = {}

    try:
        employer_uid = session.get('user', {}).get('uid')
        team_ref = db.collection('Company').document(employer_uid).collection('Workplace').document(
            team_uid)
        team_settings = team_ref.get().to_dict()

        # Dodaj dane zespołu do słownika
        if team_settings:
            team_data = team_settings

        if request.method == 'POST':
            # Pobierz dane z formularza
            team_name = request.form.get('team_name')
            team_acronim = request.form.get('team_acronim')
            team_description = request.form.get('team_description')
            team_phone_number = request.form.get('team_phone_number')
            team_city_address = request.form.get('team_city_address')
            team_street_address = request.form.get('team_street_address')
            team_postal_code_address = request.form.get('team_postal_code_address')
            team_start_shift_hour = request.form.get('team_start_shift_hour')
            team_end_shift_hour = request.form.get('team_end_shift_hour')

            # Aktualizuj dane zespołu w bazie danych
            team_ref.update({
                'TeamName': team_name,
                'TeamAcronim': team_acronim,
                'TeamDescription': team_description,
                'TeamPhoneNumber': team_phone_number,
                'TeamCityAddress': team_city_address,
                'TeamStreetAdress': team_street_address,
                'TeamPostalCodeAddress': team_postal_code_address,
                'TeamStartShiftHour': team_start_shift_hour,
                'TeamEndShiftHour': team_end_shift_hour
            })

            # Zaktualizuj dane w słowniku
            team_data['TeamName'] = team_name
            team_data['TeamAcronim'] = team_acronim
            team_data['TeamDescription'] = team_description
            team_data['TeamPhoneNumber'] = team_phone_number
            team_data['TeamCityAddress'] = team_city_address
            team_data['TeamStreetAdress'] = team_street_address
            team_data['TeamPostalCodeAddress'] = team_postal_code_address
            team_data['TeamStartShiftHour'] = team_start_shift_hour
            team_data['TeamEndShiftHour'] = team_end_shift_hour

    except Exception as e:
        error_message = str(e)
        print("Error retrieving data:", e)  # Dodaj print dla błędu

    print("Team data:", team_data)  # Dodaj print dla danych zespołu
    return render_template('team_settings.html', team_name=team_name, team_uid=team_uid, team_data=team_data,
                           error_message=error_message)


@app.route('/searcher', methods=['GET'])
@login_required
def searcher():
    try:
        query = request.args.get('query', '').lower()

        # Sprawdź, czy zapytanie jest puste
        if not query:
            return jsonify({'employees': []})

        # Pobierz wszystkich pracowników
        employees_ref = db.collection('Employee')
        query_result = employees_ref.where('email', '>=', query).where('email', '<=', query + u'\uf8ff').stream()

        # Utwórz listę pracowników spełniających kryteria
        employees = [{'email': employee.get('email'), 'employee_id': employee.id, 'name': employee.get('first_name'),
                      'surname': employee.get('last_name'), 'phone': employee.get('phone')} for employee in
                     query_result]

        return jsonify({'employees': employees})

    except Exception as e:
        error_message = str(e)
        app.logger.error("Error during search: %s", error_message)
        return jsonify({'error': error_message})


@app.route('/employer_settings', methods=['GET', 'POST'])
def employer_settings():
    error_message = None
    employer_data = {}

    try:
        employer_uid = session.get('user', {}).get('uid')
        employer_ref = db.collection('Company').document(employer_uid)
        employer_settings = employer_ref.get().to_dict()

        # Dodaj dane zespołu do słownika
        if employer_settings:
            employer_data = employer_settings

        if request.method == 'POST':
            # Pobierz dane z formularza
            name = request.form.get('name')
            phone = request.form.get('phone')
            status = request.form.get('status')

            # Aktualizuj dane zespołu w bazie danych
            employer_ref.update({
                'first_name': name,
                'phone': phone,
                'status': status,
            })

            # Zaktualizuj dane w słowniku
            employer_data['first_name'] = name
            employer_data['phone'] = phone
            employer_data['status'] = status

    except Exception as e:
        error_message = str(e)
        print("Error retrieving data:", e)  # Dodaj print dla błędu

    return render_template('employer_settings.html', employer_data=employer_data,
                           error_message=error_message)


def send_invitation_email(to_email, selected_teams):
    subject = 'Zaproszenie do zespołów'
    body = f"Witaj! Zostałeś zaproszony do zespołów: {', '.join(selected_teams)}."

    msg = Message(subject=subject, recipients=[to_email], body=body)
    mail.send(msg)


# Endpoint employee_searched z dodaną funkcją wysyłania e-maila
# Endpoint employee_searched z bezpośrednim wysłaniem e-maila
@app.route('/employee_searched/<employee_uid>', methods=['GET', 'POST'])
@login_required
def employee_searched(employee_uid):
    try:
        if request.method == 'POST':
            print("Endpoint 'employee_searched' został wywołany po kliknięciu przycisku.")

            # Jeśli formularz został wysłany, pobierz dane z formularza (zespoły, do których zaprosić pracownika)
            selected_teams = request.form.getlist('teams')

            # Tutaj możesz wykonać odpowiednie akcje, np. zapisując wybrane zespoły w bazie danych
            # ...

            # Pobierz dane pracownika z bazy danych
            employee_ref = db.collection('Employee').document(employee_uid)
            employee_data = employee_ref.get().to_dict()

            # Wyślij zaproszenie e-mailowe
            subject = 'Zaproszenie do zespołów'
            body = f"Witaj! Zostałeś zaproszony do zespołów: {', '.join(selected_teams)}."
            msg = Message(subject=subject, recipients=[employee_data['email']], body=body)
            mail.send(msg)

            # Przekieruj użytkownika z powrotem do strony z danymi pracownika
            return redirect(url_for('employee_invited', employee_uid=employee_uid))

        # Pobierz dane pracownika z bazy danych
        employee_ref = db.collection('Employee').document(employee_uid)
        employee_data = employee_ref.get().to_dict()

        team_names = []

        employer_uid = session.get('user', {}).get('uid')
        teams_ref = db.collection('Company').document(employer_uid).collection('Workplace')
        teams = teams_ref.stream()

        team_names = sorted([team.to_dict().get('Team name') for team in teams if
                             team.exists and team.to_dict().get('Team name') and team.to_dict().get(
                                 'Team name') != 'default'])

        # Przekazujemy dane pracownika i zespoły do szablonu
        return render_template('employee_searched.html', employee_data=employee_data, team_names=team_names)

    except Exception as e:
        error_message = str(e)
        app.logger.error("Error during employee search: %s", error_message)
        return jsonify({'error': error_message})


@app.route('/employee_invited/<employee_uid>', methods=['GET'])
@login_required
def employee_invited(employee_uid):
    app.logger.info("Endpoint 'employee_invited' został odwiedzony.")
    # Tutaj możesz dodać logikę dla strony, na którą użytkownik zostanie przekierowany po wysłaniu zaproszenia
    return render_template('employee_invited.html', employee_uid=employee_uid)


@app.route('/employees_teams', methods=['GET', 'POST'])
@login_required
def employees_teams():
    error_message = None
    team_data = []

    try:
        employee_uid = session.get('user', {}).get('uid')
        employee_workplaces_ref = db.collection('Employee').document(employee_uid).collection('Workplace')
        employee_workplaces = employee_workplaces_ref.stream()

        for workplace_doc in employee_workplaces:
            if workplace_doc.id == 'default':
                continue
            company_id = workplace_doc.get('CompanyID')
            workplace_id = workplace_doc.get('WorkplaceID')

            company_workplace_ref = db.collection('Company').document(company_id).collection('Workplace').document(
                workplace_id)
            company_workplace_data = company_workplace_ref.get().to_dict()

            team_name = company_workplace_data.get('TeamName')
            team_uid = company_workplace_ref.id  # Pobierz identyfikator zespołu
            if team_name:
                team_data.append({'name': team_name, 'uid': team_uid})

    except Exception as e:
        error_message = str(e)
        print(f"Error retrieving data: {e}")

    return render_template('employees_teams.html', team_data=team_data, error_message=error_message)


@app.route('/employee_team/<team_name>?<team_uid>')
@login_required
def employee_teams_main_page(team_name, team_uid=None):

    return render_template('employee_teams_main_page.html', team_name=team_name, team_uid=team_uid)


@app.route('/employee_team/<team_name>?<team_uid>/team_information')
@login_required
def employees_team_information(team_name, team_uid=None):
    error_message = None
    team_data = {'name': team_name}  # Inicjalizacja danych zespołu
    # team_uid = request.args.get('team_uid')
    try:
        # Pobierz team_uid z parametru URL

        employee_uid = session.get('user', {}).get('uid')
        employee_workplaces_ref = db.collection('Employee').document(employee_uid).collection('Workplace')
        employee_workplaces = employee_workplaces_ref.stream()

        for workplace_doc in employee_workplaces:
            if workplace_doc.id == 'default':
                continue
            company_id = workplace_doc.get('CompanyID')
            workplace_id = workplace_doc.get('WorkplaceID')

            company_workplace_ref = db.collection('Company').document(company_id).collection('Workplace').document(
                workplace_id)
            company_workplace_data = company_workplace_ref.get().to_dict()

            # Sprawdź, czy to jest właściwy zespół na podstawie team_uid
            if team_uid == company_workplace_ref.id:
                team_data['acronim'] = company_workplace_data.get('TeamAcronim')
                team_data['city'] = company_workplace_data.get('TeamCityAddress')
                team_data['street'] = company_workplace_data.get('TeamStreetAdress')
                team_data['postal_code'] = company_workplace_data.get('TeamPostalCodeAddress')
                team_data['description'] = company_workplace_data.get('TeamDescription')
                team_data['phone'] = company_workplace_data.get('TeamPhoneNumber')
                team_data['start'] = company_workplace_data.get('TeamStartShiftHour')
                team_data['end'] = company_workplace_data.get('TeamEndShiftHour')

    except Exception as e:
        error_message = str(e)
        print(f"Error retrieving data: {e}")

    return render_template('employees_team_information.html', team_data=team_data, team_name=team_name, team_uid=team_uid,
                           error_message=error_message)


@app.route('/employee_team/<team_name>?<team_uid>/preferences', methods=['GET', 'POST'])
@login_required
def employee_preferences(team_name, team_uid=None):
    error_message = None
    preferences_data = {}

    try:
        employee_uid = session.get('user', {}).get('uid')
        workplace_ref = db.collection('Employee').document(employee_uid).collection('Workplace')
        workplace_docs = workplace_ref.stream()

        # Iteracja przez dokumenty w podkolekcji Workplace
        for doc in workplace_docs:
            preferences_ref = doc.reference.collection('Preferences').document(
                'PreferencesValues')  # Zastąp 'uid' odpowiednim identyfikatorem dokumentu
            preferences_doc = preferences_ref.get()

            # Sprawdź, czy dokument preferencji istnieje i pobierz jego dane
            if preferences_doc.exists:
                preferences_data = preferences_doc.to_dict()
                break  # Zatrzymaj iterację po znalezieniu pierwszego dokumentu preferencji

        if request.method == 'POST':
            min_shift_length = request.form.get('min_shift_length')
            max_shift_length = request.form.get('max_shift_length')

            # Aktualizuj dane preferencji pracownika w bazie danych
            preferences_ref.update({
                'MinShiftLength': min_shift_length,
                'MaxShiftLength': max_shift_length
            })

            # Zaktualizuj dane w preferencjach
            preferences_data['MinShiftLength'] = min_shift_length
            preferences_data['MaxShiftLength'] = max_shift_length

    except Exception as e:
        error_message = str(e)

    return render_template('employee_team_preferences.html', preferences_data=preferences_data, team_name=team_name, team_uid=team_uid,
                           error_message=error_message)


@app.route('/employee_calendar')
@login_required
def employee_calendar():
    return render_template('employee_calendar_main_page.html')


@app.route('/create_time_block', methods=['GET', 'POST'])
@login_required
def create_time_block():
    error_message = None
    # time_block = []  # Zainicjuj pustą listę

    if request.method == 'POST':
        app.logger.debug("Request received for /create_time_block")  # Dodaj log debugowania
        start_date = request.form.get('start_date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        event_description = request.form.get('event_description')
        repeat_event = request.form.get('repeat_event')
        repeat_options = request.form.getlist('repeat_options[]')
        if repeat_options:
            repeating = ', '.join(repeat_options)
        else:
            repeating = None  # Lub inna wartość, jeśli nie ma zaznaczonych opcji
        try:
            employee_uid = session.get('user', {}).get('uid')
            block_id = start_date

            doc_ref = db.collection('Employee').document(employee_uid).collection('Calendar').document(block_id)
            doc_ref.set({
                'Start date': start_date,
                'Start time': start_time,
                'End time': end_time,
                'Event description': event_description,
                'Is repeating?': repeat_event,
                'Repeating': repeating,
            })
            app.logger.info("Time block created: %s", start_date)  # Dodaj ten log

            return redirect(url_for('employee_calendar'))
        except Exception as e:
            error_message = str(e)
            app.logger.error("Error while creating time block: %s", error_message)

    return render_template('employee_calendar_main_page.html', error_message=error_message)


@app.route('/employee_settings', methods=['GET', 'POST'])
def employee_settings():
    error_message = None
    employee_data = {}

    try:
        employee_uid = session.get('user', {}).get('uid')
        employee_ref = db.collection('Employee').document(employee_uid)
        employee_settings = employee_ref.get().to_dict()

        # Dodaj dane zespołu do słownika
        if employee_settings:
            employee_data = employee_settings

        if request.method == 'POST':
            # Pobierz dane z formularza
            name = request.form.get('name')
            surname = request.form.get('surname')
            phone = request.form.get('phone')
            status = request.form.get('status')

            # Aktualizuj dane zespołu w bazie danych
            employee_ref.update({
                'first_name': name,
                'last_name': surname,
                'phone': phone,
                'status': status,
            })

            # Zaktualizuj dane w słowniku
            employee_data['first_name'] = name
            employee_data['last_name'] = surname
            employee_data['phone'] = phone
            employee_data['status'] = status

    except Exception as e:
        error_message = str(e)
        print("Error retrieving data:", e)  # Dodaj print dla błędu

    return render_template('employee_settings.html', employee_data=employee_data,
                           error_message=error_message)


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login_main')


if __name__ == '__main__':
    app.run(debug=True)
