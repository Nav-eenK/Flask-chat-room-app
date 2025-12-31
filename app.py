from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, emit
import uuid

# ---------------- APP SETUP ----------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chattysecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- MODELS ----------------

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


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    username = db.Column(db.String(150))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())


with app.app_context():
    db.create_all()

# ---------------- AUTH ROUTES ----------------

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        if User.query.filter_by(username=request.form['username']).first():
            return "Username already exists"

        if User.query.filter_by(email=request.form['email']).first():
            return "Email already registered"

        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=request.form['password']  # hash later
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('/auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            username=request.form['username'],
            password=request.form['password']
        ).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))

        return "Invalid credentials"

    return render_template('/auth/login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ---------------- USER ROUTES ----------------

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    rooms = ChatRoom.query.filter_by(is_active=True).all()

    return render_template(
        '/user/dashboard.html',
        user=user,
        rooms=rooms
    )



@app.route('/create_room', methods=['GET', 'POST'])
def create_room():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        room = ChatRoom(
            room_name=request.form['room_name'],
            room_code=str(uuid.uuid4())[:8],
            created_by=session['user_id']
        )
        db.session.add(room)
        db.session.commit()
        return redirect(url_for('chat_room', room_code=room.room_code))

    return render_template('/user/create_room.html')


@app.route('/chat/<room_code>')
def chat_room(room_code):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    room = ChatRoom.query.filter_by(room_code=room_code, is_active=True).first()
    if not room:
        return "Room not found"

    messages = Message.query.filter_by(room_id=room.id).order_by(Message.timestamp).all()

    return render_template(
        '/user/chat.html',
        room=room,
        messages=messages,
        username=session['username']
    )

# ---------------- SOCKET.IO EVENTS ----------------

@socketio.on('join')
def on_join(data):
    if 'username' not in session:
        return

    join_room(data['room'])
    emit(
        'status',
        {'msg': f"{session['username']} joined the room"},
        room=data['room']
    )


@socketio.on('leave')
def on_leave(data):
    if 'username' not in session:
        return

    leave_room(data['room'])
    emit(
        'status',
        {'msg': f"{session['username']} left the room"},
        room=data['room']
    )


@socketio.on('typing')
def on_typing(data):
    if 'username' not in session:
        return

    emit(
        'typing',
        {'username': session['username']},
        room=data['room'],
        include_self=False
    )


@socketio.on('send_message')
def handle_message(data):
    if 'user_id' not in session:
        return

    room = ChatRoom.query.filter_by(room_code=data['room'], is_active=True).first()
    if not room:
        return

    msg = Message(
        room_id=room.id,
        user_id=session['user_id'],
        username=session['username'],
        content=data['message']
    )

    db.session.add(msg)
    db.session.commit()

    emit(
        'receive_message',
        {
            'username': session['username'],
            'message': data['message']
        },
        room=data['room']
    )

# ---------------- ADMIN ROUTES ----------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        admin = User.query.filter_by(
            username=request.form['username'],
            password=request.form['password'],
            is_admin=True
        ).first()

        if admin:
            session['admin_id'] = admin.id
            return redirect(url_for('admin_dashboard'))

        return "Invalid admin credentials"

    return render_template('/admin/admin_login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    return render_template(
        '/admin/admin_dashboard.html',
        users=User.query.all(),
        rooms=ChatRoom.query.all()
    )

# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
