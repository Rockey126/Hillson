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

def payment_keyboard():
    markup = types.InlineKeyboardMarkup()
    upi_url = f"upi://pay?pa={UPI_ID}&pn=OSINT_Bot&am=10&cu=INR"
    btn_pay = types.InlineKeyboardButton("📱 Pay via UPI App", url=upi_url)
    btn_verify = types.InlineKeyboardButton("✅ Submit UTR Number", callback_data="verify_payment")
    btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="back_home")
    markup.add(btn_pay)
    markup.add(btn_verify)
    markup.add(btn_back)
    return markup

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if get_credits(uid) is None:
        update_credits(uid, 10, is_new=True)

    msg = (
        f"👋 **Welcome to OSINT Bot!**\n\n"
        f"👤 Owner: **{OWNER_NAME}**\n"
        f"📢 Join: {CHANNEL_USER}\n\n"
        f"Use the buttons below to navigate."
    )
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id == ADMIN_ID:
        msg_text = message.text.replace('/broadcast ', '')
        if msg_text == '/broadcast':
            bot.reply_to(message, "❌ Use: `/broadcast Your Message`")
            return
        
        users = get_all_users()
        count = 0
        for user in users:
            try:
                bot.send_message(user, msg_text)
                count += 1
            except: pass
        bot.reply_to(message, f"✅ Sent to {count} users.")

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    uid = call.from_user.id
    
    if call.data == "btn_search":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔢 **Ab wo 10-digit number bhejein jiski details chahiye.**")
    
    elif call.data == "btn_profile":
        bot.answer_callback_query(call.id)
        credits = get_credits(uid)
        ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
        profile_msg = (
            f"👤 **Your Profile**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 User ID: `{uid}`\n"
            f"💰 Balance: `{credits}` Credits\n"
            f"🎁 Referral: `1 Credit / User`\n\n"
            f"🔗 **Your Referral Link:**\n`{ref_link}`"
        )
        bot.edit_message_text(profile_msg, call.message.chat.id, call.message.message_id, 
                              parse_mode="Markdown", reply_markup=main_menu())

    elif call.data == "btn_buy":
        bot.answer_callback_query(call.id)
        buy_msg = (
            f"💳 **Purchase Credits**\n\n"
            f"🆔 UPI: `{UPI_ID}`\n"
            f"💵 Price: ₹10 = 50 Credits\n\n"
            "1. Pay using UPI button.\n"
            "2. Send the 12-digit UTR number here."
        )
        bot.edit_message_text(buy_msg, call.message.chat.id, call.message.message_id, 
                              parse_mode="Markdown", reply_markup=payment_keyboard())
    
    elif call.data == "back_home":
        bot.answer_callback_query(call.id)
        start(call.message)

    elif call.data == "verify_payment":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "⌨️ **Enter your 12-digit UTR Number:**")
        bot.register_next_step_handler(msg, process_utr)

    elif call.data.startswith("adm_approve_"):
        target_uid = int(call.data.split("_")[2])
        update_credits(target_uid, 50)
        bot.send_message(target_uid, "🎉 **Payment Verified! 50 Credits added.**")
        bot.edit_message_text(f"✅ Approved User {target_uid}", call.message.chat.id, call.message.message_id)

def process_utr(message):
    utr = message.text.strip()
    if len(utr) == 12 and utr.isdigit():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"adm_approve_{message.from_user.id}"))
        bot.send_message(ADMIN_ID, f"🔔 **New Payment**\nUser: `{message.from_user.id}`\nUTR: `{utr}`", reply_markup=markup)
        bot.reply_to(message, "⏳ **UTR Verification under process.**")
    else:
        bot.reply_to(message, "❌ Invalid UTR.")

@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_search(message):
    uid = message.from_user.id
    num = message.text.strip()

    try:
        member = bot.get_chat_member(CHANNEL_ID, uid)
        if member.status not in ['member', 'administrator', 'creator']:
            bot.reply_to(message, f"⚠️ Join First: {CHANNEL_USER}")
            return
    except: pass

    if len(num) >= 10:
        if get_credits(uid) < 2:
            bot.reply_to(message, "❌ Low Balance!")
            return

        bot.send_message(message.chat.id, "🔍 Searching...")
        try:
            res = requests.get(f"https://username-brzb.vercel.app/get-info?phone={num}").json()
            if res.get("status") and res.get("results"):
                update_credits(uid, -2)
                data = res["results"][0]
                details = (
                    f"✅ **Details Found**\n━━━━━━━━━━━━━━━━━━\n"
                    f"👤 Name: `{data.get('name', 'N/A')}`\n"
                    f"📍 Address: `{data.get('address', 'N/A')}`\n━━━━━━━━━━━━━━━━━━\n"
                    f"💰 Balance: {get_credits(uid)} credits"
                )
                bot.reply_to(message, details, parse_mode="Markdown", reply_markup=main_menu())
            else:
                bot.reply_to(message, "❌ No record found.")
        except:
            bot.reply_to(message, "⚠️ API Error.")

if __name__ == "__main__":
    init_db()
    keep_alive()
    bot.infinity_polling()
