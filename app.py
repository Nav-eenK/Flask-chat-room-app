from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SECRET_KEY'] = 'chattysecretkey'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(100))
    room_code = db.Column(db.String(10), unique=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)

class RoomMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_active = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=="POST":
        username=request.form['username']
        password=request.form['password']
        user=User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id']=user.id
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials"
    return render_template('/auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method=="POST":
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        if User.query.filter_by(username=username).first():
            return "Username already exists"
        if User.query.filter_by(email=email).first():
            return "Email already registered"
        new_user=User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('/auth/register.html')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user=User.query.get(session['user_id'])
    return render_template('/user/dashboard.html', user=user)

@app.route('/create_room', methods=['GET', 'POST'])
def create_room():
    if request.method == 'POST':
        room_name = request.form['room_name']
        return redirect(url_for('dashboard'))
    return render_template('/user/create_room.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
