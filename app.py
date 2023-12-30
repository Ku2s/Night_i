from flask import Flask, render_template, request
from flask_login import LoginManager, UserMixin, current_user, login_user, login_required, logout_user
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, send, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'salutjesuisuneclé'
socketio = SocketIO(app)

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

def utilisateur_existant(pseudo):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Compte WHERE pseudo = ?", (pseudo,))
    pseudo = cursor.fetchone()
    if pseudo:
        cursor.close()
        return True
    print('Echec de l''obtention des informations utilisateur')
    return False

# Fonction de chargement de l'utilisateur
@login_manager.user_loader
def load_user(pseudo):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Compte WHERE pseudo = ?", (pseudo,))
    user_data = cursor.fetchone()
    cursor.close()

    if user_data:
        return Compte(*user_data)

@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('index.html')
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
        if utilisateur_existant(username):
            return 'Nom d\'utilisateur déjà pris. Choisissez en un autre.'
        
        # Insertion du nouveau compte dans la BD
        cursor = conn.cursor()
        hashed_password = generate_password_hash(password)
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

        # Vérif des données dont le mdp dans la BD
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Compte WHERE pseudo = ?", (pseudo,))
        user_data = cursor.fetchone()
        cursor.close()

        if utilisateur_existant(pseudo) and check_password_hash(user_data[5], mdp):
            user = Compte(*user_data)
            login_user(user)
            return render_template('index.html')
        else:
            return 'Échec de l\'authentification. Vérifiez vos informations de connexion.'
    else:
        return render_template('log_in.html')

@app.route('/index', methods=['GET','POST'])
#@login_required
def index():
    if request.method == 'POST':
        pseudo_ami = request.form['pseudo_ami']
        if utilisateur_existant(pseudo_ami):
            return render_template('message.html', pseudo_ami=pseudo_ami)
        else:
            return 'Pseudo non valide'
    return render_template('index.html')


@socketio.on("message")
def sebrodcast ndMessage(data):
    pseudo_ami = data['pseudo_ami']
    message = data['message']
    print(f"Serveur: message reçu de{request.sid} pour {pseudo_ami}: {message}")
    send(message, room=pseudo_ami)
    print('Serveur: message envoyé')

@socketio.on('join')
def join(data):
    pseudo_ami = data['pseudo_ami']
    join_room(pseudo_ami)

    # Broadcast 
    send(["Un utilisateur vien de se connecter!"], room=pseudo_ami)

@app.route('/log_out', methods=['GET'])
#@login_required
def log_out():
    logout_user()
    return 'Déconnecté avec succès !'

if __name__ == '__main__':
    socketio.run(app)