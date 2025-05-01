from flask import Flask, request, jsonify, send_from_directory
import json
import random
from datetime import datetime
from pathlib import Path
import os
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# 預設帳號密碼（可被覆蓋）
USERNAME = "_sand_gold"
PASSWORD = "a36557153"

# 訊息清單
messages = [
    "最近有再操作娛樂城嗎?",
    "百家最近打得如何",
    "賽特最近打得如何",
]

# 建立紀錄資料夾
RECORD_DIR = Path("records")
RECORD_DIR.mkdir(exist_ok=True)

def get_sent_file(username):
    return RECORD_DIR / f"sent_users_{username}.json"

def load_sent_users(username):
    sent_file = get_sent_file(username)
    if sent_file.exists():
        with open(sent_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_sent_users(username, users):
    sent_file = get_sent_file(username)
    with open(sent_file, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False)

def send_dm(post_url, username=USERNAME, password=PASSWORD, messages_override=None, limit=5):
    result_log = []
    sent_users = load_sent_users(username)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()

        # 登入 IG
        page.goto("https://www.instagram.com/accounts/login/")
        page.wait_for_selector("input[name='username']")
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")
        page.wait_for_timeout(8000)
        # 登入成功與否判斷
        if "login" in page.url or "challenge" in page.url:
            print("❗ 登入失敗，仍在登入頁面")
            return [{"status": "error", "message": "登入失敗，請確認帳號密碼或帳號是否被驗證擋住"}]
        else:
            print(f"✅ 登入成功：{username}")
        try:
            page.click("text=稍後再說")
        except:
            pass

        # 前往貼文
        try:
            page.goto(post_url, timeout=30000)
            page.wait_for_timeout(3000)
            page.keyboard.press("Home")
            page.wait_for_timeout(1000)
            try:
                like_btn = (
                    page.locator("span:has-text('個讚')").first or
                    page.locator("span:has-text('人都說讚')").first or
                    page.locator("span:has-text('likes')").first or
                    page.locator("div:has-text('個讚')").first or
                    page.locator("div:has-text('人都說讚')").first or
                    page.locator("div:has-text('likes')").first or
                    page.locator("button:has-text('個讚')").first or
                    page.locator("button:has-text('人都說讚')").first or
                    page.locator("button:has-text('likes')").first or
                    page.locator("span:has-text('和其他')").first
                )
                if like_btn:
                    like_btn.click()
                else:
                    return [{"status": "error", "message": "❗ 找不到『個讚』按鈕，可能沒人按讚或 UI 已變"}]
            except:
                return [{"status": "error", "message": "❗ 找不到『個讚』按鈕，可能沒人按讚或 UI 已變"}]
            page.wait_for_timeout(2000)
        except Exception as e:
            return [{"status": "error", "message": f"無法載入貼文或打開按讚清單：{e}"}]

        # 抓用戶
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(300)
        elements = page.query_selector_all("div[role='dialog'] a[href^='/']")
        usernames = list(set([el.inner_text() for el in elements if el.inner_text() and el.inner_text() not in sent_users]))

        # 私訊流程
        for target_user in usernames[:limit]:
            page.goto(f"https://www.instagram.com/{target_user}/")
            page.wait_for_timeout(2000)

            try:
                follow_btn = page.query_selector("text=追蹤")
                if follow_btn and follow_btn.inner_text() == "追蹤":
                    print(f"👉 已追蹤過：{target_user}，不重複追蹤")
                else:
                    print(f"✔️ 無需追蹤：{target_user}")
            except:
                pass

            try:
                msg_btn = page.query_selector("text=發送訊息") or page.query_selector("text=Message")
                if msg_btn:
                    msg_btn.click(force=True)
                else:
                    more_btn = page.query_selector("svg[aria-label='選項'], svg[aria-label='更多選項'], svg[aria-label='Options']")
                    if more_btn:
                        more_btn.click()
                        page.wait_for_timeout(1000)
                        page.click("text=發送訊息", force=True)
                    else:
                        result_log.append({"user": target_user, "status": "❌ 找不到發送訊息按鈕"})
                        continue

                page.wait_for_timeout(2000)
                try:
                    msg_box = page.wait_for_selector("div[contenteditable='true']", timeout=5000)
                except:
                    result_log.append({"user": target_user, "status": "❗ 找不到輸入框（可能對陌生人封鎖私訊）"})
                    continue

                msg = random.choice(messages_override) if messages_override else random.choice(messages)
                msg_box.type(msg)
                msg_box.press("Enter")
                sent_users.append(target_user)
                save_sent_users(username, sent_users)
                result_log.append({"user": target_user, "status": "✅ 已私訊", "message": msg})
            except Exception as e:
                result_log.append({"user": target_user, "status": f"❌ 發送失敗：{e}"})

        browser.close()
    return result_log

@app.route("/records/<path:filename>")
def get_record_file(filename):
    return send_from_directory(RECORD_DIR, filename)

@app.route("/send_dm", methods=["POST"])
def handle_dm():
    data = request.json
    post_url = data.get("post_url")
    username = data.get("username", USERNAME)
    password = data.get("password", PASSWORD)
    messages_override = data.get("messages")
    limit = int(data.get("limit", 5))
    if not post_url:
        return jsonify({"error": "請提供貼文連結 post_url"}), 400
    result = send_dm(post_url, username=username, password=password, messages_override=messages_override, limit=limit)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
