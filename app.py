from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import os

app = Flask(**name**, static_folder=’.’, static_url_path=’’)
CORS(app)

DATABASE_URL = os.environ.get(‘DATABASE_URL’)

def get_db():
conn = psycopg2.connect(DATABASE_URL)
return conn

def init_db():
conn = get_db()
c = conn.cursor()
c.execute(’’‘CREATE TABLE IF NOT EXISTS notes
(name TEXT PRIMARY KEY, password TEXT, content TEXT)’’’)
conn.commit()
conn.close()

init_db()

@app.route(’/’)
def serve_index():
return send_from_directory(’.’, ‘index.html’)

@app.route(’/<path:path>’)
def serve_static(path):
return send_from_directory(’.’, path)

@app.route(’/api/notes/create’, methods=[‘POST’])
def create():
data = request.json
name = data.get(‘name’, ‘’).strip()
password = data.get(‘password’, ‘’)

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

@app.route(’/api/notes/login’, methods=[‘POST’])
def login():
data = request.json
name = data.get(‘name’, ‘’).strip()
password = data.get(‘password’, ‘’)

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

@app.route(’/api/notes/<name>’, methods=[‘GET’])
def get_note(name):
conn = get_db()
c = conn.cursor()
try:
c.execute(‘SELECT content FROM notes WHERE name = %s’, (name,))
row = c.fetchone()
conn.close()

    if not row:
        return {'error': 'Note not found'}, 404
    return {'content': row[0]}
except Exception as e:
    conn.close()
    return {'error': str(e)}, 500

@app.route(’/api/notes/<name>/save’, methods=[‘POST’])
def save(name):
data = request.json
content = data.get(‘content’, ‘’)
password = data.get(‘password’, ‘’)

conn = get_db()
c = conn.cursor()
try:
    c.execute('SELECT password FROM notes WHERE name = %s', (name,))
    row = c.fetchone()
    
    if not row or row[0] != password:
        conn.close()
        return {'error': 'Wrong name or password'}, 401
    
    c.execute('UPDATE notes SET content = %s WHERE name = %s', (content, name))
    conn.commit()
    conn.close()
    return {'success': True}
except Exception as e:
    conn.close()
    return {'error': str(e)}, 500

if **name** == ‘**main**’:
app.run(debug=True, host=‘0.0.0.0’, port=3000)