from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import psycopg
import os
from datetime import datetime
import uuid

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set")
    conn = psycopg.connect(DATABASE_URL, connect_timeout=5)
    return conn

def init_db():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS rooms
                     (name TEXT PRIMARY KEY, password TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS posts
                     (id TEXT PRIMARY KEY, room_name TEXT, content TEXT, created_at TIMESTAMP, FOREIGN KEY(room_name) REFERENCES rooms(name) ON DELETE CASCADE)''')
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization skipped: {e}")
        pass

try:
    init_db()
except:
    print("Could not initialize database on startup")

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/rooms/create', methods=['POST'])
def create_room():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    if not name or not password:
        return {'error': 'Fill all fields'}, 400
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT name FROM rooms WHERE name = %s', (name,))
        if c.fetchone():
            conn.close()
            return {'error': 'Room already exists'}, 400
        
        c.execute('INSERT INTO rooms VALUES (%s, %s)', (name, password))
        conn.commit()
        conn.close()
        return {'success': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}, 500

@app.route('/api/rooms/login', methods=['POST'])
def login_room():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT password FROM rooms WHERE name = %s', (name,))
        row = c.fetchone()
        
        if not row or row[0] != password:
            conn.close()
            return {'error': 'Wrong name or password'}, 401
        
        c.execute('SELECT id, content, created_at FROM posts WHERE room_name = %s ORDER BY created_at ASC', (name,))
        posts = [{'id': p[0], 'content': p[1], 'created_at': p[2].isoformat()} for p in c.fetchall()]
        conn.close()
        
        return {'posts': posts}
    except Exception as e:
        conn.close()
        return {'error': str(e)}, 500

@socketio.on('join_room')
def on_join(data):
    room_name = data['name']
    password = data['password']
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT password FROM rooms WHERE name = %s', (room_name,))
        row = c.fetchone()
        conn.close()
        
        if not row or row[0] != password:
            emit('error', {'message': 'Invalid credentials'})
            return
        
        join_room(room_name)
        emit('user_joined', {'room': room_name}, room=room_name, skip_sid=True)
        
    except Exception as e:
        conn.close()
        emit('error', {'message': str(e)})

@socketio.on('post_message')
def on_post_message(data):
    room_name = data['room']
    content = data['content']
    
    post_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO posts (id, room_name, content, created_at) VALUES (%s, %s, %s, %s)',
                 (post_id, room_name, content, created_at))
        conn.commit()
        conn.close()
        
        emit('new_post', {
            'id': post_id,
            'content': content,
            'created_at': created_at
        }, room=room_name)
        
    except Exception as e:
        conn.close()
        emit('error', {'message': str(e)})

@socketio.on('delete_post')
def on_delete_post(data):
    room_name = data['room']
    post_id = data['id']
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM posts WHERE id = %s AND room_name = %s', (post_id, room_name))
        conn.commit()
        conn.close()
        
        emit('post_deleted', {'id': post_id}, room=room_name)
        
    except Exception as e:
        conn.close()
        emit('error', {'message': str(e)})

@socketio.on('clear_room')
def on_clear_room(data):
    room_name = data['room']
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM posts WHERE room_name = %s', (room_name,))
        conn.commit()
        conn.close()
        
        emit('room_cleared', {}, room=room_name)
        
    except Exception as e:
        conn.close()
        emit('error', {'message': str(e)})

@socketio.on('leave_room')
def on_leave_room(data):
    room_name = data['room']
    leave_room(room_name)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 3000)), allow_unsafe_werkzeug=True)
