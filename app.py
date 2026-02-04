from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

notes = {}

@app.route('/api/notes/create', methods=['POST'])
def create():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    if not name or not password:
        return {'error': 'Fill all fields'}, 400
    
    if name in notes:
        return {'error': 'Note already exists'}, 400
    
    notes[name] = {'password': password, 'content': ''}
    return {'success': True}

@app.route('/api/notes/login', methods=['POST'])
def login():
    data = request.json
    name = data.get('name', '').strip()
    password = data.get('password', '')
    
    if name not in notes or notes[name]['password'] != password:
        return {'error': 'Wrong name or password'}, 401
    
    return {'content': notes[name]['content']}

@app.route('/api/notes/<name>', methods=['GET'])
def get_note(name):
    if name not in notes:
        return {'error': 'Note not found'}, 404
    return {'content': notes[name]['content']}

@app.route('/api/notes/<name>/save', methods=['POST'])
def save(name):
    data = request.json
    content = data.get('content', '')
    password = data.get('password', '')
    
    if name not in notes or notes[name]['password'] != password:
        return {'error': 'Wrong name or password'}, 401
    
    notes[name]['content'] = content
    return {'success': True}

if __name__ == '__main__':
    
    app.run(debug=True, host='0.0.0.0', port=3000)
