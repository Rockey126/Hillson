import telebot
import requests
import json

# ==============================
# CONFIG
# ==============================

BOT_TOKEN = "8280681654:AAHBYcWu6PusYYKezEWKwIcviya4zQeCxqk"
bot = /addcredit 5768665344 100

OWNER_ID = 5768665344  # ✅ Fixed Owner ID

DATA_FILE = "users.json"

SEARCH_COST = 2        # ✅ Per Search Cost = 2 Credits
REFERRAL_REWARD = 1    # ✅ Per Referral Reward = 1 Credit


# ==============================
# DATABASE FUNCTIONS
# ==============================

def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(uid):
    users = load_users()
    if str(uid) not in users:
        users[str(uid)] = {"credits": 0, "referred": False}
        save_users(users)
    return users


# ==============================
# START COMMAND + REFERRAL
# ==============================

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    users = get_user(uid)

    args = message.text.split()

    # Referral Logic
    if len(args) > 1:
        ref_id = args[1]

        if ref_id != str(uid) and users[str(uid)]["referred"] == False:
            all_users = load_users()

            if ref_id in all_users:
                all_users[ref_id]["credits"] += REFERRAL_REWARD
                users[str(uid)]["referred"] = True

                save_users(all_users)

                bot.send_message(
                    ref_id,
                    f"🎉 New Referral Joined!\n+{REFERRAL_REWARD} Credit Added!"
                )

    bot.reply_to(
        message,
        "👋 Welcome!\n\n"
        "📌 Search Number Using:\n"
        "/search 9876543210\n\n"
        f"💳 Each search costs {SEARCH_COST} credits.\n\n"
        "🧾 Commands:\n"
        "/balance - Check Credits\n"
        "/refer - Get Referral Link\n"
        "/buy - Buy Credits\n"
        "/search - Search Phone Number"
    )


# ==============================
# BALANCE COMMAND
# ==============================

@bot.message_handler(commands=["balance"])
def balance(message):
    uid = message.from_user.id
    users = load_users()

    credits = users.get(str(uid), {}).get("credits", 0)
    bot.reply_to(message, f"💳 Your Balance: {credits} Credits")


# ==============================
# REFERRAL COMMAND
# ==============================

@bot.message_handler(commands=["refer"])
def refer(message):
    uid = message.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={uid}"

    bot.reply_to(
        message,
        f"🎁 Referral Link:\n{link}\n\n"
        f"✅ Earn {REFERRAL_REWARD} Credit Per Referral!"
    )


# ==============================
# BUY COMMAND
# ==============================

@bot.message_handler(commands=["buy"])
def buy(message):
    bot.reply_to(
        message,
        "💰 Buy Credits Option:\n\n"
        "📌 Contact Owner:\n"
        "@rockeyxjoker\n\n"
        "Available Packs:\n"
        "10 Credits = ₹50\n"
        "50 Credits = ₹200\n"
        "100 Credits = ₹350"
    )


# ==============================
# OWNER ADD CREDIT COMMAND
# ==============================

@bot.message_handler(commands=["addcredit"])
def addcredit(message):

    # ✅ Only Owner Allowed
    if int(message.from_user.id) != OWNER_ID:
        return bot.reply_to(message, "🚫 Only Owner can use this command!")

    try:
        _, user_id, amount = message.text.split()
        user_id = str(user_id)
        amount = int(amount)

        users = load_users()

        if user_id not in users:
            users[user_id] = {"credits": 0, "referred": False}

        users[user_id]["credits"] += amount
        save_users(users)

        bot.reply_to(
            message,
            f"✅ Added {amount} Credits to User {user_id}"
        )

    except:
        bot.reply_to(
            message,
            "❌ Usage:\n/addcredit userID amount\n\nExample:\n/addcredit 123456789 10"
        )


# ==============================
# SEARCH COMMAND
# ==============================

@bot.message_handler(commands=["search"])
def search_command(message):
    uid = message.from_user.id
    users = load_users()

    if str(uid) not in users:
        users[str(uid)] = {"credits": 0, "referred": False}
        save_users(users)

    # Check Credits
    if users[str(uid)]["credits"] < SEARCH_COST:
        return bot.reply_to(
            message,
            f"❌ Not enough credits!\nEach search costs {SEARCH_COST} credits.\nUse /buy to purchase."
        )

    try:
        _, number = message.text.split()

        if not (number.isdigit() and len(number) >= 10):
            return bot.reply_to(message, "🚫 Invalid number!\nUse: /search 9876543210")

        bot.send_message(message.chat.id, "🔍 Searching Database...")

        api_url = f"https://username-brzb.vercel.app/get-info?phone={number}"
        response = requests.get(api_url, timeout=10)
        data = response.json()

        if data.get("status") == True and data.get("results"):

            res = data["results"][0]

            # Deduct Credits (2 credits per search)
            users[str(uid)]["credits"] -= SEARCH_COST
            save_users(users)

            # ✅ Details With Alternative Number Added
            details = (
                f"✅ Details Found\n\n"
                f"👤 Name: {res.get('name', 'N/A')}\n"
                f"👨‍👦 Father: {res.get('father_name', 'N/A')}\n"
                f"📍 Address: {res.get('address', 'N/A')}\n"
                f"📱 Mobile: {res.get('mobile', 'N/A')}\n"
                f"📞 Alternative: {res.get('alt_number', 'N/A')}\n"
                f"🌐 Circle: {res.get('circle', 'N/A')}\n\n"
                f"💳 Remaining Credits: {users[str(uid)]['credits']}"
            )

            bot.reply_to(message, details)

        else:
            bot.reply_to(message, "❌ No records found.")

    except:
        bot.reply_to(message, "❌ Usage:\n/search 9876543210")


# ==============================
# BLOCK RANDOM MESSAGES
# ==============================

@bot.message_handler(func=lambda message: True)
def fallback(message):
    bot.reply_to(
        message,
        "📌 Please use:\n/search 9876543210\n\n"
        "To check credits:\n/balance"
    )


# ==============================
# RUN BOT
# ==============================

print("🤖 Bot Started Successfully...")
bot.infinity_polling()
