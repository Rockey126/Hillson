import telebot
from telebot import types
import requests
import sqlite3
import os
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
BOT_TOKEN = '8097849910:AAGL557NBwfu2Inv7IjLwnrc-xvAHpzaiKk'
CHANNEL_ID = -1003896003068  
CHANNEL_USER = '@osintbyrockey' 
ADMIN_ID = 5768665344
OWNER_NAME = "Gurveer"
UPI_ID = "gurveer83@ptyes"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, credits INTEGER DEFAULT 10)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS referrals 
                      (referred_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def get_credits(user_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_credits(user_id, amount, is_new=False):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    if is_new:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, credits) VALUES (?, 10)", (user_id,))
    else:
        cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

# --- WEB SERVER FOR RENDER ---
@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- KEYBOARDS ---
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_search = types.InlineKeyboardButton("🔍 Start Search", callback_data="btn_search")
    btn_profile = types.InlineKeyboardButton("👤 Profile", callback_data="btn_profile")
    btn_buy = types.InlineKeyboardButton("💰 Buy Credits", callback_data="btn_buy")
    markup.add(btn_search)
    markup.add(btn_profile, btn_buy)
    return markup

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['add'])
def manual_add(message):
    """Usage: /add UserID Amount"""
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            target_id = int(parts[1])
            amount = int(parts[2])
            update_credits(target_id, amount)
            bot.reply_to(message, f"✅ Added {amount} credits to `{target_id}`. \nNew Balance: {get_credits(target_id)}")
            bot.send_message(target_id, f"🎁 Admin has added `{amount}` credits to your account!")
        except Exception as e:
            bot.reply_to(message, "❌ Format: `/add 12345678 50` ")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id == ADMIN_ID:
        msg_text = message.text.replace('/broadcast ', '')
        if msg_text == '/broadcast':
            bot.reply_to(message, "❌ Use: `/broadcast Message` ")
            return
        users = get_all_users()
        for user in users:
            try: bot.send_message(user, msg_text)
            except: pass
        bot.reply_to(message, "✅ Broadcast completed.")

# --- BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if get_credits(uid) is None:
        update_credits(uid, 10, is_new=True)
    bot.send_message(message.chat.id, f"👋 Welcome! Owner: **{OWNER_NAME}**", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    if call.data == "btn_search":
        bot.send_message(call.message.chat.id, "🔢 **Ab wo 10-digit number bhejein jiski details chahiye.**")
    elif call.data == "btn_profile":
        bal = get_credits(call.from_user.id)
        bot.edit_message_text(f"👤 **Profile**\nID: `{call.from_user.id}`\nBalance: `{bal}` credits", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    elif call.data == "btn_buy":
        bot.send_message(call.message.chat.id, f"💳 UPI ID: `{UPI_ID}`\nSend screenshot to Admin after payment.")

@bot.message_handler(func=lambda message: message.text.isdigit() and len(message.text) >= 10)
def handle_search(message):
    uid = message.from_user.id
    num = message.text.strip()
    
    # Check Credits
    current_bal = get_credits(uid)
    if current_bal < 2:
        bot.reply_to(message, "❌ Credits khatam! Refer karein ya Buy karein.")
        return

    bot.send_message(message.chat.id, "🔍 Searching...")
    try:
        res = requests.get(f"https://username-brzb.vercel.app/get-info?phone={num}").json()
        if res.get("status") and res.get("results"):
            update_credits(uid, -2)
            data = res["results"][0]
            
            # Detailed Result Message
            details = (
                f"✅ **Details Found**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 Name: `{data.get('name', 'N/A')}`\n"
                f"👨‍👦 Father: `{data.get('father_name', 'N/A')}`\n"
                f"📱 Mobile: `{data.get('mobile', 'N/A')}`\n"
                f"📲 Alt Mobile: `{data.get('alt_mobile', 'N/A')}`\n"
                f"🆔 ID Number: `{data.get('id_number', 'N/A')}`\n"
                f"📍 Address: `{data.get('address', 'N/A')}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💰 Balance: {get_credits(uid)} credits"
            )
            bot.reply_to(message, details, parse_mode="Markdown", reply_markup=main_menu())
        else:
            bot.reply_to(message, "❌ No record found.")
    except:
        bot.reply_to(message, "⚠️ API Server error!")

if __name__ == "__main__":
    init_db()
    keep_alive()
    bot.infinity_polling()
