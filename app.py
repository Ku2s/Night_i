from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, current_user, login_user, login_required, logout_user
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, send, join_room, leave_room
from cryptography.fernet import Fernet
import time
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'salutjesuisuneclé'
app.config['SESSION_TYPE'] = 'filesystem'

KEY_FILE = 'encryption_key.key'
with open(KEY_FILE, 'rb') as key_file:
    cipher_key = key_file.read()
cipher = Fernet(cipher_key)
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

def room_existant(room_id):
    # Créer un curseur à l'intérieur de la fonction
    cursor = conn.cursor()
    cursor.execute("SELECT room_id FROM conversation WHERE room_id = ?", (room_id,))
    existing_room = cursor.fetchone()
    if existing_room:
        return True
    cursor.close()
    return False

def genere_message_id():
    timestamp = str(time.time()).encode('utf-8')
    message_hash = hashlib.md5(timestamp).hexdigest()
    return message_hash
    
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
    room_id = data.get('room_id')
    join_room(room_id)
    print(f'L utilisateur {current_user.pseudo} s est connecté à la room {room_id}')

    # Récupérer les anciens messages sauvegardés dans la base de données
    cursor = conn.cursor()
    cursor.execute("SELECT messages,sender, message_id FROM conversation WHERE room_id = ?", (room_id,))
    results = cursor.fetchall()
    #Envoyer les messages dans la room
    if results:
        for result in results:
            messages, sender, message_id = result

            # Traiter le cas où il y a plusieurs messages dans la chaîne
            individual_messages = messages.split('\n')

            for individual_message in individual_messages:
                if individual_message and sender and message_id:
                    decrypted_message = cipher.decrypt(individual_message.encode()).decode()
                    send({'message': decrypted_message, 'sender': sender, 'message_id': message_id}, room=request.sid)

    cursor.close()

    affichage_connection = f'{current_user.pseudo} s\'est connecté'
    send({'message':affichage_connection}, room=room_id)


@socketio.on('leave_room')
@login_required
def leave(data):
    room_id = data.get('room_id')
    if room_id:
        leave_room(room_id)
        print(f'{current_user.pseudo} a quitté la room {room_id}')
    else:
        flash('Echec lors de la déconnexion de la room')

@app.route('/message', methods=['GET','POST'])
@login_required
def pageMess():
    room_id = request.args.get('room_id')
    return render_template('message.html', room_id = room_id)

@socketio.on("sauv_mess")
def SAUVMESS(data):
    room_id = data['room_id']
    message = data['message']
    message_id = genere_message_id()
    # Cryptage du message
    encrypted_message = cipher.encrypt(message.encode()).decode()  
    # Assurez-vous de convertir le message en bytes avant le chiffrement
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO conversation (room_id, messages, sender, message_id) VALUES (?, ?, ?, ?)",
                        (room_id, encrypted_message, current_user.pseudo, message_id))
        # Sauvegarder les changements dans la BD
        conn.commit()
        decrypted_message = cipher.decrypt(encrypted_message.encode()).decode()
        send({'message':decrypted_message, 'message_id': message_id, 'sender':current_user.pseudo}, room=room_id)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()

@socketio.on("supprimer_message")
def suppMess(data):
    message_id = data['message_id']
    cursor = conn.cursor()
    cursor.execute("DELETE from conversation WHERE message_id = ?", (message_id,))
    cursor.close()
    socketio.emit("message_supp", {'message_id':message_id})


@app.route('/log_out', methods=['GET'])
@login_required
def log_out():
    logout_user()
    flash('Déconnecté avec succès !', 'sucess')
    return render_template('sign_in.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)