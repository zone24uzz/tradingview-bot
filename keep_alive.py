from flask import Flask, jsonify, request, send_from_directory
from threading import Thread
import os
from flask_cors import CORS

from db import user_data_store, admins, save_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "webapp", "dist")

app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")
CORS(app)

@app.route('/')
def home():
    if os.path.exists(os.path.join(app.static_folder, 'index.html')):
        return send_from_directory(app.static_folder, 'index.html')
    return "Bot is alive and running! (dist folder not found)"

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return "Not found", 404

@app.route('/api/stats', methods=['GET'])
def get_stats():
    users = len(user_data_store)
    pro_users = sum(1 for d in user_data_store.values() if d.get("is_pro"))
    active_monitors = sum(len(d.get("monitoring", {})) for d in user_data_store.values())
    return jsonify({"users": users, "pro": pro_users, "active_monitors": active_monitors})

@app.route('/api/admins', methods=['GET', 'POST'])
def manage_admins():
    if request.method == 'POST':
        data = request.json
        admin_id = str(data.get("admin_id"))
        permissions = data.get("permissions", [])
        name = data.get("name", "Yangi Admin")
        
        admins[admin_id] = {"name": name, "permissions": permissions}
        save_db()
        return jsonify({"success": True})
    
    return jsonify(admins)

@app.route('/api/admins/<admin_id>', methods=['DELETE'])
def remove_admin(admin_id):
    if admin_id in admins:
        del admins[admin_id]
        save_db()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify(user_data_store)

@app.route('/api/users/<user_id>/pro', methods=['POST'])
def toggle_pro(user_id):
    if user_id in user_data_store:
        user_data_store[user_id]["is_pro"] = request.json.get("is_pro", False)
        save_db()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/api/broadcast', methods=['POST'])
def broadcast_message():
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"success": False, "error": "No text"}), 400
    
    import requests
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    
    success_count = 0
    for uid in user_data_store.keys():
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            res = requests.post(url, json={"chat_id": uid, "text": text, "parse_mode": "HTML"})
            if res.status_code == 200:
                success_count += 1
        except: pass
        
    return jsonify({"success": True, "count": success_count})

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
