from flask import Flask, request, jsonify, send_from_directory
import json
import os
import datetime

app = Flask(__name__)

ACCOUNT_FILE = "accounts.json"
RECORD_DIR = "records"
os.makedirs(RECORD_DIR, exist_ok=True)

# 初始化帳號資料
if not os.path.exists(ACCOUNT_FILE):
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "_sand_gold": "a36557153",
            "xuun_02": "weche2305"
        }, f, ensure_ascii=False, indent=2)

def load_accounts():
    with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_accounts(accounts):
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if username == "admin" and password == "1234":
        return jsonify({"status": "admin"})
    accounts = load_accounts()
    if accounts.get(username) == password:
        return jsonify({"status": "user"})
    return jsonify({"status": "error"}), 401

@app.route("/accounts", methods=["GET"])
def get_accounts():
    accounts = load_accounts()
    return jsonify(list(accounts.keys()))

@app.route("/add_account", methods=["POST"])
def add_account():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"message": "帳號與密碼不可為空"}), 400

    accounts = load_accounts()
    if username in accounts:
        return jsonify({"message": "帳號已存在"}), 400

    accounts[username] = password
    save_accounts(accounts)
    return jsonify({"message": f"✅ 成功新增帳號 {username}"}), 200

@app.route("/delete_account", methods=["POST"])
def delete_account():
    data = request.json
    username = data.get("username", "").strip()

    if username == "admin":
        return jsonify({"message": "❌ 無法刪除管理員帳號"}), 403

    accounts = load_accounts()
    if username not in accounts:
        return jsonify({"message": "帳號不存在"}), 404

    del accounts[username]
    save_accounts(accounts)
    return jsonify({"message": f"🗑️ 已刪除帳號 {username}"}), 200

@app.route("/send_dm", methods=["POST"])
def send_dm():
    data = request.json
    username = data.get("username")
    post_url = data.get("post_url")
    message = data.get("message")
    count = int(data.get("count", 5))

    if not all([username, post_url, message]):
        return jsonify({"status": "error", "message": "缺少必要欄位"}), 400

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(RECORD_DIR, f"{username}_log.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] 模擬私訊 {count} 人，訊息：{message}\n")

    return jsonify({"status": "success", "message": f"已記錄私訊 {count} 人內容"})

@app.route("/log/<username>")
def get_log(username):
    path = os.path.join("records", f"{username}_log.txt")
    if not os.path.exists(path):
        return "尚無紀錄", 404
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

