import logging
import sqlite3
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# --- ২৪ ঘণ্টা অনলাইনে রাখার জন্য ---
from keep_alive import keep_alive  

# --- কনফিগারেশন ---
API_TOKEN = '7953880175:AAHqQiuPH24qJKNYcJzo-_FpBdCrt7Eaqto'
ADMIN_ID = 5550550932
ADMIN_GROUP_ID = -5046885109
PAYMENT_NUMBER = "01769990607"

# লগিং এবং মেমোরি
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# --- ডাটাবেস সেটআপ ---
conn = sqlite3.connect('shop_database.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, data TEXT, status TEXT DEFAULT 'unsold')''')
conn.commit()

# --- স্টেপ বা ধাপ ---
class BuyState(StatesGroup):
    waiting_for_quantity = State()
    waiting_for_confirm = State()

class ReplaceState(StatesGroup):
    waiting_for_complain = State()

class DepositState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_method = State()
    waiting_for_trx = State()

# --- বাটন ডিজাইন ---
def get_main_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    menu.add(KeyboardButton("🛒 Buy Mail"), KeyboardButton("💰 Deposit / Balance"))
    menu.add(KeyboardButton("📦 Stock Info"), KeyboardButton("🔄 Replacement"))
    menu.add(KeyboardButton("👤 Profile"), KeyboardButton("🆘 Support"))
    return menu

def get_cancel_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    menu.add(KeyboardButton("🔙 Cancel"))
    return menu

# --- ফাংশন শুরু ---
@dp.message_handler(commands=['start'], state="*")
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await message.reply(f"স্বাগতম {message.from_user.first_name}! \nপ্রফেশনাল ডিজিটাল শপে আপনাকে স্বাগতম।", reply_markup=get_main_menu())

# --- এডমিন স্টক এড ---
@dp.message_handler(commands=['addstock'])
async def add_stock(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.split(maxsplit=2)
        item_type = parts[1].lower()
        item_data = parts[2]
        items = item_data.split('\n')
        count = 0
        for item in items:
            if item.strip():
                cursor.execute("INSERT INTO stock (type, data) VALUES (?, ?)", (item_type, item.strip()))
                count += 1
        conn.commit()
        await message.reply(f"✅ {count}টি {item_type} মেইল স্টকে যুক্ত হয়েছে!")
    except: await message.reply("ভুল! সঠিক নিয়ম: /addstock edu email:pass")

# --- সাধারণ বাটন ---
@dp.message_handler(lambda message: message.text == "💰 Deposit / Balance")
async def check_balance_deposit(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("➕ Deposit Money", callback_data="start_deposit"))
    await message.reply(f"💰 **আপনার ব্যালেন্স:** {bal} TK\n\nআপনি কি ব্যালেন্স এড করতে চান?", parse_mode="Markdown", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "📦 Stock Info")
async def show_stock(message: types.Message):
    cursor.execute("SELECT COUNT(*) FROM stock WHERE type='edu' AND status='unsold'")
    edu = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stock WHERE type='hotmail' AND status='unsold'")
    hot = cursor.fetchone()[0]
    await message.reply(f"📦 **বর্তমান স্টক:**\n\n🔹 Edu Mail: `{edu}` pcs\n🔹 Hotmail: `{hot}` pcs", parse_mode="Markdown")

@dp.message_handler(lambda message: message.text == "👤 Profile")
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    await message.reply(f"👤 **User Profile**\n\n🆔 ID: `{user_id}`\n💰 Balance: {bal} TK", parse_mode="Markdown")

@dp.message_handler(lambda message: message.text == "🆘 Support")
async def support(message: types.Message):
    await message.reply(f"📞 হেল্পলাইনের জন্য এডমিনকে মেসেজ দিন: tg://user?id={ADMIN_ID}")

@dp.message_handler(lambda message: message.text == "🔙 Cancel", state="*")
@dp.message_handler(lambda message: message.text == "🔙 Main Menu", state="*")
async def back_home(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply("🏠 মেইন মেনু:", reply_markup=get_main_menu())

# --- 🚀 DEPOSIT SYSTEM ---

@dp.callback_query_handler(lambda c: c.data == 'start_deposit')
async def process_deposit_start(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    amount_kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    amount_kb.add("20 BDT", "50 BDT", "100 BDT", "500 BDT")
    amount_kb.add("🔙 Cancel")
    await bot.send_message(callback_query.from_user.id, "👇 কত টাকা ডিপোজিট করতে চান সিলেক্ট করুন:", reply_markup=amount_kb)
    await DepositState.waiting_for_amount.set()

@dp.message_handler(state=DepositState.waiting_for_amount)
async def process_deposit_amount(message: types.Message, state: FSMContext):
    if "Cancel" in message.text:
        await state.finish()
        await message.reply("বাতিল করা হয়েছে।", reply_markup=get_main_menu())
        return

    amount_str = message.text.replace(" BDT", "").replace("Tk", "").strip()
    try:
        amount = float(amount_str)
        if amount < 10: raise ValueError
    except:
        await message.reply("❌ ভুল অ্যামাউন্ট! সর্বনিম্ন ১০ টাকা।")
        return

    await state.update_data(deposit_amount=amount)

    method_kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    method_kb.add("bKash", "Nagad", "Rocket")
    method_kb.add("🔙 Cancel")

    await message.reply(f"✅ {amount} TK সিলেক্ট করেছেন।\n\n👇 পেমেন্ট মেথড সিলেক্ট করুন:", reply_markup=method_kb)
    await DepositState.waiting_for_method.set()

@dp.message_handler(state=DepositState.waiting_for_method)
async def process_deposit_method(message: types.Message, state: FSMContext):
    method = message.text.strip()

    if "Cancel" in method:
        await state.finish()
        await message.reply("বাতিল করা হয়েছে।", reply_markup=get_main_menu())
        return

    if method not in ["bKash", "Nagad", "Rocket"]:
        await message.reply("❌ ভুল মেথড! দয়া করে নিচের বাটন থেকে সিলেক্ট করুন।")
        return

    await state.update_data(method=method)

    # ডাটা লোড
    data = await state.get_data()
    amount = data['deposit_amount']

    msg = (
        f"📩 **Payment Info:**\n\n"
        f"💳 Method: **{method}**\n"
        f"📞 Number: `{PAYMENT_NUMBER}` (Personal)\n"
        f"💰 Amount: **{amount} TK**\n\n"
        f"⚠️ নিয়ম:\n১. এই নাম্বারে টাকা Send Money করুন।\n"
        f"২. এরপর আপনার **Sender Number** অথবা **TrxID** নিচে লিখে পাঠান:"
    )

    await message.reply(msg, parse_mode="Markdown", reply_markup=get_cancel_menu())
    await DepositState.waiting_for_trx.set()

@dp.message_handler(state=DepositState.waiting_for_trx)
async def process_deposit_complete(message: types.Message, state: FSMContext):
    if "Cancel" in message.text:
        await state.finish()
        await message.reply("বাতিল করা হয়েছে।", reply_markup=get_main_menu())
        return

    trx_info = message.text
    data = await state.get_data()
    amount = data['deposit_amount']
    method = data['method']
    user = message.from_user
    now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")

    receipt_msg = (
        f"⏳ **Deposit Pending!**\n\n"
        f"👤 User: {user.first_name}\n"
        f"💰 Amount: {amount} TK\n"
        f"💳 Method: {method}\n"
        f"📝 Info: `{trx_info}`\n\n"
        f"✅ রিকোয়েস্ট জমা হয়েছে। এডমিন চেক করে এপ্রুভ করবেন।"
    )
    await message.reply(receipt_msg, parse_mode="Markdown", reply_markup=get_main_menu())

    admin_kb = InlineKeyboardMarkup()
    admin_kb.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"appr:{user.id}:{amount}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"decl:{user.id}")
    )
    admin_msg = (
        f"🔔 **New Deposit Request!**\n\n"
        f"👤 User: {user.first_name} (@{user.username})\n"
        f"🆔 ID: `{user.id}`\n"
        f"💰 Amount: **{amount} TK**\n"
        f"💳 Method: {method}\n"
        f"📝 Info: `{trx_info}`\n"
        f"🕒 Time: {now}"
    )

    try:
        await bot.send_message(ADMIN_GROUP_ID, admin_msg, parse_mode="Markdown", reply_markup=admin_kb)
    except:
        await bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=admin_kb)

    await state.finish()

# --- এডমিন অ্যাকশন ---
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('appr:'))
async def approve_deposit(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID: 
        await callback_query.answer("⚠️ Only Admin!", show_alert=True)
        return

    _, user_id, amount = callback_query.data.split(':')
    user_id = int(user_id)
    amount = float(amount)

    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

    await bot.edit_message_text(f"✅ **Approved!**\nUser: `{user_id}`\nAdded: {amount} TK", 
                                chat_id=callback_query.message.chat.id, 
                                message_id=callback_query.message.message_id, 
                                parse_mode="Markdown")

    try: await bot.send_message(user_id, f"🎉 অভিনন্দন! আপনার {amount} TK ডিপোজিট এপ্রুভ হয়েছে।")
    except: pass

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('decl:'))
async def decline_deposit(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID: return

    _, user_id = callback_query.data.split(':')
    await bot.edit_message_text(f"❌ **Declined!**", chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    try: await bot.send_message(int(user_id), "❌ আপনার ডিপোজিট রিকোয়েস্ট বাতিল করা হয়েছে।")
    except: pass

# --- কেনাকাটা ---
@dp.message_handler(lambda message: message.text == "🛒 Buy Mail")
async def buy_start(message: types.Message):
    menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    menu.add(KeyboardButton("📧 Edu Mail (1.50 TK)"), KeyboardButton("🔥 Hotmail (1.50 TK)"))
    menu.add(KeyboardButton("🔙 Main Menu"))
    await message.reply("👇 কি কিনতে চান সিলেক্ট করুন:", reply_markup=menu)

@dp.message_handler(lambda message: "1.50 TK" in message.text)
async def process_buy_request(message: types.Message, state: FSMContext):
    item_type = 'edu' if 'Edu' in message.text else 'hotmail'
    cursor.execute("SELECT COUNT(*) FROM stock WHERE type=? AND status='unsold'", (item_type,))
    stock_count = cursor.fetchone()[0]
    if stock_count == 0:
        await message.reply(f"⚠️ দুঃখিত! এই মুহূর্তে **{item_type.upper()}** স্টক নেই।", parse_mode="Markdown")
        return
    await state.update_data(item_type=item_type, price=1.50)
    await message.reply(f"✅ স্টক আছে: {stock_count} টি।\nকয়টি কিনতে চান? সংখ্যা লিখুন:", reply_markup=get_cancel_menu())
    await BuyState.waiting_for_quantity.set()

@dp.message_handler(state=BuyState.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    if "Cancel" in message.text:
        await state.finish()
        await message.reply("বাতিল করা হয়েছে।", reply_markup=get_main_menu())
        return
    try:
        qty = int(message.text)
        if qty < 1: raise ValueError
    except:
        await message.reply("❌ ভুল সংখ্যা!")
        return
    data = await state.get_data()
    item_type = data['item_type']
    total_cost = qty * data['price']
    cursor.execute("SELECT COUNT(*) FROM stock WHERE type=? AND status='unsold'", (item_type,))
    if cursor.fetchone()[0] < qty:
        await message.reply(f"⚠️ পর্যাপ্ত স্টক নেই।")
        return
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone()[0] < total_cost:
        await message.reply(f"❌ ব্যালেন্স কম! প্রয়োজন: {total_cost} TK।", reply_markup=get_main_menu())
        await state.finish()
        return
    conf_kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    conf_kb.add("✅ Confirm", "❌ Cancel")
    await state.update_data(qty=qty, total_cost=total_cost)
    await message.reply(f"📝 **অর্ডার:** {qty}x {item_type}\n💰 **মোট:** {total_cost} TK\n\nনিশ্চিত?", parse_mode="Markdown", reply_markup=conf_kb)
    await BuyState.waiting_for_confirm.set()

@dp.message_handler(state=BuyState.waiting_for_confirm)
async def process_confirm(message: types.Message, state: FSMContext):
    if message.text == "✅ Confirm":
        data = await state.get_data()
        user_id = message.from_user.id
        try:
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (data['total_cost'], user_id))
            cursor.execute("SELECT id, data FROM stock WHERE type=? AND status='unsold' LIMIT ?", (data['item_type'], data['qty']))
            items = cursor.fetchall()
            msg_list = []
            for i, item in enumerate(items, 1):
                cursor.execute("UPDATE stock SET status='sold' WHERE id=?", (item[0],))
                raw = item[1]
                if ":" in raw:
                    e, p = raw.split(":", 1)
                    msg_list.append(f"📦 **Mail #{i}**\n📧 `{e.strip()}`\n🔑 `{p.strip()}`")
                else:
                    msg_list.append(f"📦 **Mail #{i}**\n`{raw}`")
            conn.commit()
            await message.reply(f"✅ সফল!\n\n" + "\n\n".join(msg_list), parse_mode="Markdown", reply_markup=get_main_menu())
        except:
            await message.reply("Error!")
    else:
        await message.reply("বাতিল করা হলো।", reply_markup=get_main_menu())
    await state.finish()

# --- রিপ্লেসমেন্ট ---
@dp.message_handler(lambda message: message.text == "🔄 Replacement")
async def replacement_start(message: types.Message):
    await message.reply("⚠️ সমস্যা বিস্তারিত লিখুন:", reply_markup=get_cancel_menu())
    await ReplaceState.waiting_for_complain.set()

@dp.message_handler(state=ReplaceState.waiting_for_complain)
async def process_complain(message: types.Message, state: FSMContext):
    if "Cancel" in message.text:
        await state.finish()
        await message.reply("বাতিল।", reply_markup=get_main_menu())
        return

    try: await bot.send_message(ADMIN_GROUP_ID, f"🚨 **Replacement Req**\nUser: `{message.from_user.id}`\nMsg: {message.text}", parse_mode="Markdown")
    except: await bot.send_message(ADMIN_ID, f"🚨 **Replacement Req**\nUser: `{message.from_user.id}`\nMsg: {message.text}", parse_mode="Markdown")

    await message.reply("✅ এডমিনকে জানানো হয়েছে।", reply_markup=get_main_menu())
    await state.finish()

if __name__ == '__main__':
    keep_alive()  # বট জাগিয়ে রাখার এলার্ম
    executor.start_polling(dp, skip_updates=True)