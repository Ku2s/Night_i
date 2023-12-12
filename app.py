from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'salutjesuisuneclé'

# Connexion à la BD
conn = sqlite3.connect('db.sqlite', check_same_thread=False)
login_manager = LoginManager(app)

class Compte(UserMixin):
    def __init__(self, user_id, nom, prenom, mail, pseudo, mot_de_passe_hash):
        self.id = user_id
        self.nom = nom
        self.prenom = prenom
        self.mail = mail
        self.pseudo = pseudo
        self.mot_de_passe_hash = mot_de_passe_hash

# Fonction de chargement de l'utilisateur
@login_manager.user_loader
def load_user(user_id):
    # Utilisez une requête SQL pour obtenir les informations de l'utilisateur à partir de la base de données
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Compte WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()

    if user_data:
        return Compte(*user_data)

@app.route('/')
def home():
    if current_user.is_authenticated:
        return 'Bienvenue !!!'
    else:
        return render_template('sign_in.html') 

@app.route('/sign_in', methods=['POST'])
def sign_in():
    if request.method == 'POST':

        name = request.form['prenom']
        last_name = request.form['nom']
        mail = request.form['mail']
        username = request.form['pseudo']
        password = request.form['mot_de_passe_hash']

        # Vérif de pseudo
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Compte WHERE pseudo = ?", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            cursor.close()
            return 'Nom d\'utilisateur déjà pris. Choisissez en un autre.'
        
        # Insertion du nouveau compte dans la BD
        hashed_password = generate_password_hash(password)
        print(f"Mdp haché: {hashed_password};")
        cursor.execute("INSERT INTO Compte (nom, prenom, mail, pseudo, mot_de_passe_hash) VALUES (?, ?, ?, ?, ?)",
                       (last_name, name, mail, username, hashed_password))
        conn.commit()
        cursor.close()

        # Connectez automatiquement le nouvel utilisateur
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Compte WHERE pseudo = ?", (username,))
        new_user_data = cursor.fetchone()
        cursor.close()

        if new_user_data:
            new_user = Compte(*new_user_data)
            login_user(new_user)
            return render_template('index.html')

    return render_template('sign_in.html')

@app.route('/log_in', methods=['GET','POST'])
def log_in():
    if request.method == 'POST':
        pseudo = request.form['pseudo']
        mdp = request.form['mot_de_passe']

        # Vérifiez dans la base de données si l'utilisateur existe et si le mot de passe est correct
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Compte WHERE pseudo = ?", (pseudo,))
        user_data = cursor.fetchone()
        cursor.close()

        if user_data and check_password_hash(user_data[5], mdp):
            user = Compte(*user_data)
            login_user(user)
            return render_template('index.html')
        else:
            return 'Échec de l\'authentification. Vérifiez vos informations de connexion.'
    else :
        return render_template('log_in.html')

@app.route('/index', methods=['GET'])
@login_required
def index():
    return render_template('index.html')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return 'Déconnecté avec succès !'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
