from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import uuid

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
            RoomMember.is_active=True
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
        created_by = User.query.get(session['user_id'])
        room_code = str(uuid.uuid4())[:8]
        new_room = ChatRoom(room_name=room_name, room_code=room_code, created_by=created_by.id)
        db.session.add(new_room)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('/user/create_room.html')
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password, is_admin=True).first()
        if user:
            session['admin_id'] = user.id
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid admin credentials"
    return render_template('/admin/admin_login.html')
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    users= User.query.all()
    rooms = ChatRoom.query.all()
    return render_template('/admin/admin_dashboard.html', rooms=rooms, users=users)
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    RoomMember.is_active=False
    return redirect(url_for('home'))
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
