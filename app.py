from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, current_user, login_user, login_required, logout_user
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, send, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'salutjesuisuneclé'
app.config['SESSION_TYPE'] = 'filesystem'

app.config['SESSION_PERMANENT'] = True
socketio = SocketIO(app, manage_session=False)

# Connexion à la BD
conn = sqlite3.connect('db.sqlite', check_same_thread=False)
login_manager = LoginManager(app)
login_manager.init_app(app)

class Compte(UserMixin):
    def __init__(self, user_id, nom, prenom, mail, pseudo, mot_de_passe_hash):
        self.id = user_id
        self.nom = nom
        self.prenom = prenom
        self.mail = mail
        self.pseudo = pseudo
        self.mot_de_passe_hash = mot_de_passe_hash
    
    def get_id(self):
        return str(self.pseudo)

def utilisateur_existant(pseudo):
    cursor = conn.cursor()
    cursor.execute("SELECT pseudo FROM Compte WHERE pseudo = ?", (pseudo,))
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
    if user_data:
        cursor.close()
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
            return redirect(url_for('index'))

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
            return redirect(url_for('index'))
        else:
            return 'Échec de l\'authentification. Vérifiez vos informations de connexion.'
    else:
        return render_template('log_in.html')

utilisateurs_connectes = set()

@app.route('/index', methods=['GET','POST'])
@login_required
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        utilisateurs_connectes.add(current_user.pseudo)
        print(f"{utilisateurs_connectes}")
        socketio.emit('join_connected_list', list(utilisateurs_connectes))


@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        utilisateurs_connectes.remove(current_user.pseudo)
        socketio.emit('join_connected_list', list(utilisateurs_connectes))

@socketio.on('join_room')
@login_required
def join(data):
    if isinstance(data, dict): 
        room_id = data.get('room_id')
        join_room(room_id)
        print(f'L utilisateur {current_user.pseudo} s est connecté à la room {room_id}')
        affichage_connection = f'{current_user.pseudo} s\'est connecté'
        send({"msg":affichage_connection}, room=room_id)
        return render_template('message.html', room_id = room_id)
    else:
        print("Erreur de room")


@app.route('/message', methods=['GET','POST'])
@login_required
def pageMess():
    room_id = request.args.get('room_id')
    return render_template('message.html', room_id = room_id)

@socketio.on('message_event')
@login_required
def sendMessage(data):
    message = data['message']
    room_id = data['room_id']
    print(f"Serveur: message reçu de {current_user.pseudo} pour la room {room_id}: {message}")
    send({"msg" :message}, room=room_id)
    print(f'Serveur: message envoyé à la room {room_id}')

@app.route('/log_out', methods=['GET'])
@login_required
def log_out():
    logout_user()
    flash('Déconnecté avec succès !', 'sucess')
    return render_template('sign_in.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)