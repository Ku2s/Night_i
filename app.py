from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_clé_secrète'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Utilisation de SQLite à des fins de démonstration
db = SQLAlchemy(app)
login_manager = LoginManager(app)

# Modèle SQLAlchemy pour la base de données des utilisateurs
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

# Fonction de chargement de l'utilisateur
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


@app.route('/')
def home():
    if current_user.is_authenticated:
        return 'Bienvenue !!!'
    else:
        return render_template('setup_login.html')  # Ajoutez un modèle pour définir le compte

@app.route('/setup_password', methods=['GET', 'POST'])
def setup_password():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Vérifiez si l'utilisateur existe déjà dans la base de données
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return 'Nom d\'utilisateur déjà pris. Choisissez en un autre.'

        # Créez un nouvel utilisateur avec le mot de passe haché
        new_user = User(username=username, password_hash=generate_password_hash(password, method='sha256'))
        db.session.add(new_user)
        db.session.commit()

        # Connectez automatiquement le nouvel utilisateur
        login_user(new_user)

        return 'Mot de passe initial configuré avec succès !'

    return render_template('setup_password.html')

# Page de login
@app.route('/login')
def login():
    # Remplacez cette logique par votre propre logique d'authentification
    user = User(user_id=1)
    login_user(user)
    return  '''
    <p>Connecté !</p>
    <p><a href="/protected">Accéder au site</a></p>
    <p><a href="/logout">Déconnexion</a></p>
    '''

# Page protégée (accessible uniquement après connexion)
@app.route('/protected')
@login_required
def protected():
    return f'''
    <p>Bienvenue, {current_user.id} !</p>
    <p>Ici c'est secret</p>
    <p><a href="/logout">Déconnexion</a></p>
    '''

# Page de logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'Déconnecté avec succès !'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
