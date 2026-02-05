from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import psycopg2
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE_URL = os.environ.get('DATABASE_URL')
active_sessions = {}

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS notes
                     (name TEXT PRIMARY KEY, password TEXT, content TEXT)''')
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()

init_db()

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/notes/create', methods=['POST'])
def create():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    if not name or not password:
        return {'error': 'Fill all fields'}, 400
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT name FROM notes WHERE name = %s', (name,))
        if c.fetchone():
            conn.close()
            return {'error': 'Note already exists'}, 400
        
        c.execute('INSERT INTO notes VALUES (%s, %s, %s)', (name, password, ''))
        conn.commit()
        conn.close()
        return {'success': True}
    except Exception as e:
        conn.close()
        return {'error': str(e)}, 500

@app.route('/api/notes/login', methods=['POST'])
def login():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT password, content FROM notes WHERE name = %s', (name,))
        row = c.fetchone()
        conn.close()
        
        if not row or row[0] != password:
            return {'error': 'Wrong name or password'}, 401
        
        return {'content': row[1]}
    except Exception as e:
        conn.close()
        return {'error': str(e)}, 500

@socketio.on('join_note')
def on_join(data):
    note_name = data['name']
    password = data['password']
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('SELECT password, content FROM notes WHERE name = %s', (note_name,))
        row = c.fetchone()
        conn.close()
        
        if not row or row[0] != password:
            emit('error', {'message': 'Invalid credentials'})
            return
        
        join_room(note_name)
        
        if note_name not in active_sessions:
            active_sessions[note_name] = {'content': row[1], 'users': 0}
        
        active_sessions[note_name]['users'] += 1
        
        emit('content_update', {'content': active_sessions[note_name]['content']})
        
        emit('user_joined', {'users': active_sessions[note_name]['users']}, room=note_name, skip_sid=True)
        
    except Exception as e:
        conn.close()
        emit('error', {'message': str(e)})

@socketio.on('content_change')
def on_content_change(data):
    note_name = data['name']
    content = data['content']
    
    if note_name in active_sessions:
        active_sessions[note_name]['content'] = content
    
    emit('content_update', {'content': content}, room=note_name, skip_sid=True)

@socketio.on('leave_note')
def on_leave(data):
    note_name = data['name']
    
    leave_room(note_name)
    
    if note_name in active_sessions:
        active_sessions[note_name]['users'] -= 1
        
        if active_sessions[note_name]['users'] <= 0:
            conn = get_db()
            c = conn.cursor()
            try:
                c.execute('UPDATE notes SET content = %s WHERE name = %s', 
                         (active_sessions[note_name]['content'], note_name))
                conn.commit()
                conn.close()
                del active_sessions[note_name]
            except Exception as e:
                conn.close()
                print(f"Error saving note: {e}")
        else:
            emit('user_left', {'users': active_sessions[note_name]['users']}, room=note_name)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=3000)
