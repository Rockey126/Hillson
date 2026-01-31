import telebot
from telebot import types
import requests
import sqlite3
import os
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
BOT_TOKEN = '8097849910:AAGL557NBwfu2Inv7IjLwnrc-xvAHpzaiKk'
ADMIN_ID = 5768665344
UPI_ID = "gurveer83@ptyes"
CHANNEL_ID = -1003896003068
CHANNEL_USER = "@osintbyrockey"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# --- DATABASE LOGIC ---
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

# --- WEB SERVER FOR RENDER ---
@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- KEYBOARDS ---
def main_menu(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_search = types.InlineKeyboardButton("🔍 Start Search", callback_data="btn_search")
    btn_buy = types.InlineKeyboardButton("💰 Buy Credits", callback_data="btn_buy")
    markup.add(btn_search, btn_buy)
    return markup

def payment_keyboard():
    markup = types.InlineKeyboardMarkup()
    # Opens UPI Apps automatically with amount ₹10 as example
    upi_url = f"upi://pay?pa={UPI_ID}&pn=OSINT_Bot&am=10&cu=INR"
    btn_pay = types.InlineKeyboardButton("📱 Open UPI App (Pay ₹10)", url=upi_url)
    btn_verify = types.InlineKeyboardButton("✅ Submit UTR / Confirm", callback_data="verify_payment")
    btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="back_home")
    markup.add(btn_pay)
    markup.add(btn_verify, btn_back)
    return markup

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if get_credits(uid) is None:
        update_credits(uid, 10, is_new=True)

    msg = (
        f"👋 **Welcome to ROCKEY OSINT Bot**\n\n"
        f"💰 Balance: {get_credits(uid)} Credits\n"
        f"📢 Join: {CHANNEL_USER}\n\n"
        f"Click the buttons below to start."
    )
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    uid = call.from_user.id
    
    if call.data == "btn_search":
        bot.send_message(call.message.chat.id, "🔢 **Please send the 10-digit number to search.**")
    
    elif call.data == "btn_buy":
        buy_msg = (
            f"💳 **Purchase Credits**\n\n"
            f"💵 Price: **₹100 = 50 Credits**\n"
            f"🆔 UPI: `{UPI_ID}`\n\n"
            f"1. Pay using the button below.\n"
            f"2. Copy the 12-digit UTR from your receipt.\n"
            f"3. Click 'Submit UTR' to get credited."
        )
        bot.edit_message_text(buy_msg, call.message.chat.id, call.message.message_id, 
                              parse_mode="Markdown", reply_markup=payment_keyboard())
    
    elif call.data == "verify_payment":
        msg = bot.send_message(call.message.chat.id, "⌨️ **Enter your 12-digit UTR Number:**")
        bot.register_next_step_handler(msg, process_utr)
        
    elif call.data == "back_home":
        start(call.message)

    elif call.data.startswith("adm_approve_"):
# Admin clicks Approve
        target_uid = int(call.data.split("_")[2])
        update_credits(target_uid, 50) # Adding 50 credits
        bot.send_message(target_uid, "🎉 **Payment Verified! 50 Credits added.**")
        bot.edit_message_text(f"✅ User {target_uid} Approved.", call.message.chat.id, call.message.message_id)

def process_utr(message):
    utr = message.text.strip()
    if len(utr) == 12 and utr.isdigit():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"adm_approve_{message.from_user.id}"))
        bot.send_message(ADMIN_ID, f"🔔 **New Payment**\nUser: `{message.from_user.id}`\nUTR: `{utr}`", reply_markup=markup)
        bot.reply_to(message, "⏳ **UTR Sent for verification! Wait 5-10 mins.**")
    else:
        bot.reply_to(message, "❌ Invalid UTR. Must be 12 digits.")

@bot.message_handler(func=lambda message: message.text.isdigit())
def search_logic(message):
    uid = message.from_user.id
    num = message.text.strip()
    
    # Check credits
    bal = get_credits(uid)
    if bal < 2:
        bot.reply_to(message, "❌ Low Balance! Buy credits first.")
        return

    # Mock API call
    bot.send_message(message.chat.id, "🔍 Searching...")
    api_url = f"https://username-brzb.vercel.app/get-info?phone={num}"
    try:
        res = requests.get(api_url).json()
        if res.get("status") and res.get("results"):
            update_credits(uid, -2)
            data = res["results"][0]
            bot.reply_to(message, f"👤 Name: {data.get('name')}\n📍 Address: {data.get('address')}")
        else:
            bot.reply_to(message, "❌ Not Found.")
    except:
        bot.reply_to(message, "⚠️ API Error.")

# --- START ---
if name == "__main__":
    init_db()
    keep_alive() # Starts Flask on port 8080
    print("Bot is running...")
    bot.infinity_polling()