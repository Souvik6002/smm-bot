import telebot
import sqlite3
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8755105428:AAG2LDYhGgaZQzlcRgZRK8ooBR-5TTWWNU8"
ADMIN_ID = 8122066254
UPI_ID = "souvik6@fam"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# ========= DATABASE =========
conn = sqlite3.connect("ultimate_smm.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, name TEXT, price INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, service TEXT, link TEXT, qty INTEGER, status TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, utr TEXT, status TEXT)")
conn.commit()

# ========= STATE =========
user_state = {}
admin_state = {}

# ========= MENU =========
def user_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("💰 Balance", "📦 Services")
    m.add("💳 Add Money", "📊 Orders")
    return m

def admin_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("➕ Add Service")
    m.add("🔙 Back")
    return m

# ========= START =========
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.chat.id
    cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
    conn.commit()

    if uid == ADMIN_ID:
        bot.send_message(uid, "👑 Admin Panel", reply_markup=admin_menu())
    else:
        bot.send_message(uid,
        "🌟 *Premium SMM Panel* 🌟\n\n🚀 Fast • 💎 Reliable • ⚡ Instant\n\n👇 Choose option:",
        reply_markup=user_menu())

# ========= BALANCE =========
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(msg):
    cur.execute("SELECT balance FROM users WHERE user_id=?", (msg.chat.id,))
    bal = cur.fetchone()[0]
    bot.send_message(msg.chat.id, f"💰 Balance: ₹{bal}")

# ========= ADD MONEY =========
@bot.message_handler(func=lambda m: m.text == "💳 Add Money")
def add_money(msg):
    bot.send_message(msg.chat.id, f"💳 UPI: {UPI_ID}")

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Payment Done", callback_data="paid"))
    bot.send_message(msg.chat.id, "Click after payment:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "paid")
def paid(call):
    user_state[call.message.chat.id] = {"step": "amount"}
    bot.send_message(call.message.chat.id, "Enter Amount:")

# ========= USER FLOW =========
@bot.message_handler(func=lambda m: m.chat.id in user_state and m.chat.id not in admin_state)
def user_flow(msg):
    uid = msg.chat.id
    state = user_state[uid]

    # PAYMENT FLOW
    if state["step"] == "amount":
        state["amount"] = msg.text
        state["step"] = "utr"
        bot.send_message(uid, "Enter UTR:")
        return

    if state["step"] == "utr":
        try:
            amount = int(state["amount"])
        except:
            bot.send_message(uid, "Invalid amount")
            return

        utr = msg.text

        cur.execute("INSERT INTO payments(user_id,amount,utr,status) VALUES (?,?,?,?)",
                    (uid, amount, utr, "Pending"))
        conn.commit()

        pid = cur.lastrowid

        bot.send_message(uid, "⏳ Payment submitted for approval")

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"pay_ok_{pid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"pay_no_{pid}")
        )

        bot.send_message(
            ADMIN_ID,
            f"💰 *Payment Request*\n\n🆔 {pid}\n👤 {uid}\n💸 ₹{amount}\n🔢 {utr}",
            reply_markup=kb
        )

        user_state.pop(uid)
        return

    # ORDER FLOW
    if state["step"] == "platform":
        state["platform"] = msg.text
        state["step"] = "service"

        cur.execute("SELECT id,name FROM services WHERE platform=?", (msg.text,))
        rows = cur.fetchall()