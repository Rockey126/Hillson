import telebot
from telebot import types
import requests
import sqlite3
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

def add_referral(referred_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO referrals (referred_id) VALUES (?)", (referred_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

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
    btn_refer = types.InlineKeyboardButton("🔗 Referral", callback_data="btn_refer")
    btn_buy = types.InlineKeyboardButton("💰 Buy Credits", callback_data="btn_buy")
    markup.add(btn_search)
    markup.add(btn_profile, btn_refer)
    markup.add(btn_buy)
    return markup

def join_markup():
    markup = types.InlineKeyboardMarkup()
    btn_join = types.InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USER.replace('@', '')}")
    btn_check = types.InlineKeyboardButton("🔄 Check Join Status", callback_data="check_join")
    markup.add(btn_join)
    markup.add(btn_check)
    return markup

# --- HELPERS ---
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    
    if get_credits(uid) is None:
        update_credits(uid, 10, is_new=True)
        if len(args) > 1 and args[1].isdigit():
            referrer_id = int(args[1])
            if referrer_id != uid:
                if add_referral(uid):
                    update_credits(referrer_id, 1) # +1 Credit per refer
                    try:
                        bot.send_message(referrer_id, "🎁 Aapko **1 Referral Credit** mila!")
                    except: pass

    if not is_user_joined(uid):
        bot.send_message(message.chat.id, f"⚠️ **Join Required!**\nJoin {CHANNEL_USER} to use the bot.", reply_markup=join_markup())
        return

    bot.send_message(message.chat.id, f"👋 Welcome! Owner: **{OWNER_NAME}**", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    uid = call.from_user.id
    if call.data == "check_join":
        if is_user_joined(uid):
            bot.answer_callback_query(call.id, "✅ Success!")
            bot.edit_message_text(f"👋 Welcome! Owner: **{OWNER_NAME}**", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
        else:
            bot.answer_callback_query(call.id, "❌ Join first!", show_alert=True)
    elif call.data == "btn_search":
        bot.send_message(call.message.chat.id, "🔢 **Ab wo 10-digit number bhejein.**")
    elif call.data == "btn_profile":
        bal = get_credits(uid)
        bot.edit_message_text(f"👤 **Profile**\nID: `{uid}`\nBalance: `{bal}` Credits", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    elif call.data == "btn_refer":
        ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.edit_message_text(f"🔗 **Your Referral Link**\n\n`{ref_link}`\n\n🎁 **Reward:** 1 Credit per friend!", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
    elif call.data == "btn_buy":
        bot.send_message(call.message.chat.id, f"💳 **Buy Credits**\nUPI: `{UPI_ID}`\nPrice: ₹10 = 50 Credits\nScreenshot Admin ko bhejein.")

@bot.message_handler(commands=['add'])
def admin_add(message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            update_credits(int(parts[1]), int(parts[2]))
            bot.reply_to(message, "✅ Credits Added Successfully.")
        except:
            bot.reply_to(message, "❌ Use: `/add UserID Amount` ")

@bot.message_handler(func=lambda message: message.text.isdigit() and len(message.text) >= 10)
def handle_search(message):
    uid = message.from_user.id
    if not is_user_joined(uid):
        bot.send_message(message.chat.id, "⚠️ Join First!", reply_markup=join_markup())
        return
    if get_credits(uid) < 2:
        bot.reply_to(message, "❌ Low Balance! 2 credits required per search.")
        return

    bot.send_message(message.chat.id, "🔍 Searching...")
    try:
        response = requests.get(f"https://username-brzb.vercel.app/get-info?phone={number}", timeout=15)
        data = response.json()
        if data.get("status") == True and data.get("results") and len(data["results"]) > 0:
            update_credits(uid, -2) # -2 Credits per search
            res = data["results"][0]
            details = (
                f"✅ **Details Found**\n━━━━━━━━━━━━━━━━━━\n"
                f"👤 Name: `{res.get('name', 'N/A')}`\n"
                f"👨‍👦 Father: `{res.get('father_name', 'N/A')}`\n"
                f"📱 Mobile: `{res.get('mobile', 'N/A')}`\n"
                f"📲 Alt Mobile: `{res.get('alt_mobile', 'N/A')}`\n"
                f"🆔 ID Number: `{res.get('id_number', 'N/A')}`\n"
                f"📍 Address: `{res.get('address', 'N/A')}`\n━━━━━━━━━━━━━━━━━━\n"
                f"💰 Balance: {get_credits(uid)} credits"
            )
            bot.reply_to(message, details, parse_mode="Markdown", reply_markup=main_menu())
        else:
            bot.reply_to(message, "❌ No record found.")
    except Exception as e:
        bot.reply_to(message, "⚠️ API Error! Please try again later.")

if __name__ == "__main__":
    init_db()
    keep_alive()
    bot.infinity_polling()
