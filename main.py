import re
import json
import os
import random
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatMemberStatus
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

# ================= CONFIGURATION =================
API_TOKEN_1 = "8726416871:AAEKluMhwL7k4eP0RkchwvF_f82VQmLgc3A" # @YukchiForwarder_Bot
API_TOKEN_2 = "8112720689:AAFR_KtcgUYH3vBlsFZcBRj4qH3SGCwI2Zo" # @YukchiForwarderorg_Bot

ADMINS = [6977836294, 8409259397]
REQUIRED_CHANNELS = ["@YukchiForwarder", "@YukchiForwarderPeople"]
TARGET_GROUPS = [-1003968416767, -1003775919755]
SUPPORT_SITE_URL = "https://yukchibot.vercel.app/" 

logging.basicConfig(level=logging.INFO)

bot1 = Bot(token=API_TOKEN_1)
dp1 = Dispatcher(storage=MemoryStorage())

bot2 = Bot(token=API_TOKEN_2)
dp2 = Dispatcher(storage=MemoryStorage())

# ================= JSON STORAGE (/tmp) =================
DRIVERS_FILE = "/tmp/drivers.json"
CURATORS_FILE = "/tmp/curators.json"
BANNED_FILE = "/tmp/banned.json"
LOADS_FILE = "/tmp/loads.json"
STATS_FILE = "/tmp/stats.json"

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"Xatolik {path}: {e}")

drivers_db = {int(k) if str(k).isdigit() else k: v for k, v in load_json(DRIVERS_FILE).items()}
curators_db = {int(k) if str(k).isdigit() else k: v for k, v in load_json(CURATORS_FILE).items()}
banned_users = {int(k) if str(k).isdigit() else k: v for k, v in load_json(BANNED_FILE).items()}
active_loads = {int(k) if str(k).isdigit() else k: v for k, v in load_json(LOADS_FILE).items()}
user_stats = {int(k) if str(k).isdigit() else k: v for k, v in load_json(STATS_FILE).items()}

class UserRoleState(StatesGroup):
    choosing_role = State()
    driver_get_name = State()
    driver_get_car = State()
    curator_get_name = State()
    curator_get_phone = State()
    load_text = State()
    accept_load_id = State()

class AdminState(StatesGroup):
    waiting_for_ban_target = State()
    waiting_for_unban_target = State()
    waiting_for_broadcast = State()

class ComplaintState(StatesGroup):
    waiting_for_complaint_text = State()

LINK_REGEX = r'(https?://[^\s]+|t\.me/[^\s]+|@[a-zA-Z0-9_]+)'
SPAM_WORDS = ["kanalga", "gruppaga", "o'ting", "murojaat", "arzon", "aksiya", "reklama", "lichkaga", "http", "t.me"]

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚛 Haydovchilar", callback_data="admin_list_drivers"), InlineKeyboardButton(text="📦 Kuratorlar", callback_data="admin_list_curators")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"), InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"), InlineKeyboardButton(text="✅ Bandan chiqarish", callback_data="admin_unban_user")]
    ])

async def check_subscriptions(user_id: int, bot_obj: Bot) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot_obj.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                return False
        except Exception:
            return False
    return True

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 1-Kanalga qo'shilish", url="https://t.me/YukchiForwarder")],
        [InlineKeyboardButton(text="📢 2-Kanalga qo'shilish", url="https://t.me/YukchiForwarderPeople")],
        [InlineKeyboardButton(text="🔄 Obunani tekshirish", callback_data="check_sub")]
    ])

async def track_user_activity(user: types.User, bot_name: str):
    user_stats[user.id] = {"name": user.full_name, "username": user.username or "yoq", "bots": [bot_name]}
    save_json(STATS_FILE, user_stats)

# ================= 1-BOT (Asosiy Yukchi Bot) =================
@dp1.message(F.text == "/start")
async def start_cmd_bot1(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    await track_user_activity(message.from_user, "@YukchiForwarder_Bot")

    if user_id in banned_users:
        await message.answer("⛔️ Siz botdan bloklangansiz!")
        return
    if user_id in ADMINS:
        await message.answer("👨‍💻 <b>Admin Boshqaruv Paneli:</b>", reply_markup=get_admin_keyboard())
        return
    
    if not await check_subscriptions(user_id, bot1):
        await message.answer("⚠️ <b>Botdan foydalanish uchun avval kanallarimizga obuna bo'ling:</b>", reply_markup=get_sub_keyboard())
        return

    if user_id in drivers_db:
        d = drivers_db[user_id]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Yukni qabul qilish (ID orqali)", callback_data="driver_accept_menu")],
            [InlineKeyboardButton(text="❌ Yukni bekor qilish", callback_data="driver_cancel_menu")],
            [InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL)]
        ])
        await message.answer(f"🚛 <b>Xush kelibsiz, haydovchi {d['name']}!</b>\nMashinangiz: {d['car']}", reply_markup=kb)
        return
    elif user_id in curators_db:
        c = curators_db[user_id]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Yangi yuk e'lon qilish", callback_data="curator_new_load")],
            [InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL)]
        ])
        await message.answer(f"📦 <b>Xush kelibsiz, kurator {c['name']}!</b>", reply_markup=kb)
        return

    role_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚛 Haydovchiman", callback_data="role_driver")],
        [InlineKeyboardButton(text="📦 Kuratoriman", callback_data="role_curator")]
    ])
    await message.answer("Assalomu alaykum! Rolingizni tanlang:", reply_markup=role_keyboard)
    await state.set_state(UserRoleState.choosing_role)

@dp1.callback_query(F.data == "check_sub")
async def check_sub_cb(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    if await check_subscriptions(call.from_user.id, bot1):
        role_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚛 Haydovchiman", callback_data="role_driver")],
            [InlineKeyboardButton(text="📦 Kuratoriman", callback_data="role_curator")]
        ])
        await call.message.edit_text("✅ Obuna tasdiqlandi! Rolingizni tanlang:", reply_markup=role_keyboard)
        await state.set_state(UserRoleState.choosing_role)
    else:
        await call.answer("❌ Hali hamma kanallarga qo'shilmadingiz!", show_alert=True)

@dp1.callback_query(F.data == "role_driver")
async def role_driver(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("👤 Ism-sharifingizni kiriting:")
    await state.set_state(UserRoleState.driver_get_name)

@dp1.message(UserRoleState.driver_get_name, F.text)
async def driver_name(message: types.Message, state: FSMContext):
    await state.update_data(d_name=message.text.strip())
    await message.answer("🚛 Mashinangiz nomini kiriting (masalan: Cobalt, Damas):")
    await state.set_state(UserRoleState.driver_get_car)

@dp1.message(UserRoleState.driver_get_car, F.text)
async def driver_car(message: types.Message, state: FSMContext):
    car = message.text.strip()
    data = await state.get_data()
    drivers_db[message.from_user.id] = {"name": data.get("d_name"), "car": car, "username": message.from_user.username or "yoq"}
    save_json(DRIVERS_FILE, drivers_db)
    await message.answer("✅ Haydovchi sifatida ro'yxatdan o'tdingiz! /start ni bosing.")
    await state.clear()

@dp1.callback_query(F.data == "role_curator")
async def role_curator(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("👤 Kuratorning to'liq ism-sharifini kiriting:")
    await state.set_state(UserRoleState.curator_get_name)

@dp1.message(UserRoleState.curator_get_name, F.text)
async def curator_name(message: types.Message, state: FSMContext):
    await state.update_data(c_name=message.text.strip())
    await message.answer("📞 Telefon raqamingizni kiriting (masalan: +998901234567):")
    await state.set_state(UserRoleState.curator_get_phone)

@dp1.message(UserRoleState.curator_get_phone, F.text)
async def curator_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.get_data()
    curators_db[message.from_user.id] = {"name": data.get("c_name"), "phone": phone, "username": message.from_user.username or "yoq"}
    save_json(CURATORS_FILE, curators_db)
    await message.answer("✅ Kurator muvaffaqiyatli ro'yxatdan o'tdi! /start bosing.")
    await state.clear()

@dp1.callback_query(F.data == "curator_new_load")
async def curator_new_load(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("📝 Yuk e'lonining matnini to'liq yuboring (Qayerdan, qayerga, narxi va hokazo):")
    await state.set_state(UserRoleState.load_text)

@dp1.message(UserRoleState.load_text, F.text)
async def load_text_save(message: types.Message, state: FSMContext):
    load_id = random.randint(1000, 9999)
    user = message.from_user
    curator = curators_db.get(user.id, {"name": user.full_name, "phone": "Mavjud emas"})
    load_content = message.text.strip()
    
    group_text = (
        f"📦 <b>YUK E'LONI (ID: #{load_id})</b>\n\n"
        f"{load_content}\n\n"
        f"──────────────────\n"
        f"👤 <b>Kurator:</b> {curator['name']}\n"
        f"🆔 <b>Yuk ID raqami:</b> <code>{load_id}</code>\n"
        f"🌐 <b>Support:</b> {SUPPORT_SITE_URL}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL)]
    ])
    
    for g in TARGET_GROUPS:
        try:
            await bot1.send_message(chat_id=g, text=group_text, reply_markup=kb)
        except:
            pass
            
    active_loads[load_id] = {
        "user_id": user.id,
        "curator_name": curator["name"],
        "curator_phone": curator["phone"],
        "text": load_content,
        "status": "faol",
        "driver_id": None
    }
    save_json(LOADS_FILE, active_loads)
    await message.answer(f"✅ Yukingiz guruhlarga muvaffaqiyatli tarqatildi!\n🆔 <b>Yuk ID raqami:</b> #{load_id}")
    await state.clear()

@dp1.callback_query(F.data == "driver_accept_menu")
async def driver_accept_menu(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer("📥 Qabul qilmoqchi bo'lgan yukning <b>ID raqamini</b> yuboring:")
    await state.set_state(UserRoleState.accept_load_id)

@dp1.message(UserRoleState.accept_load_id, F.text)
async def driver_accept_process(message: types.Message, state: FSMContext):
    txt = message.text.strip().replace("#", "")
    if not txt.isdigit():
        await message.answer("❌ Faqat raqamli ID kiriting:")
        return
    load_id = int(txt)
    load = active_loads.get(load_id)
    if not load or load["status"] != "faol":
        await message.answer("❌ Bunday faol yuk topilmadi yoki allaqachon olingan!")
        await state.clear()
        return
        
    driver = drivers_db.get(message.from_user.id)
    load["status"] = "olingan"
    load["driver_id"] = message.from_user.id
    save_json(LOADS_FILE, active_loads)
    
    try:
        await bot1.send_message(
            chat_id=load["user_id"],
            text=(
                f"✅ <b>Yukingizni haydovchi qabul qildi!</b>\n\n"
                f"🚛 <b>Haydovchi:</b> {driver['name']}\n"
                f"🚗 <b>Mashina:</b> {driver['car']}\n"
                f"📞 <b>Aloqa:</b> @{driver['username']}"
            )
        )
    except:
        pass
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Atmen qilish (Bekor qilish)", callback_data=f"cancel_load_{load_id}")]
    ])
    await message.answer(
        f"✅ Siz #{load_id} raqamli yukni muvaffaqiyatli qabul qildingiz!\n\n"
        f"📦 <b>Ma'lumot:</b> {load['text']}\n"
        f"📞 <b>Kurator raqami:</b> {load['curator_phone']}",
        reply_markup=kb
    )
    await state.clear()

@dp1.callback_query(F.data.startswith("cancel_load_"))
async def cancel_load_callback(call: types.CallbackQuery):
    await call.answer("Yuk bekor qilindi!")
    load_id = int(call.data.split("_")[-1])
    if load_id in active_loads:
        active_loads[load_id]["status"] = "faol"
        save_json(LOADS_FILE, active_loads)
    await call.message.edit_text("❌ Siz bu yukni bekor qildingiz.")

@dp1.callback_query(F.data == "driver_cancel_menu")
async def driver_cancel_menu(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer("❌ Bekor qilmoqchi bo'lgan yukingizning <b>ID raqamini</b> yuboring:")
    await state.set_state(UserRoleState.accept_load_id)

# ================= 2-BOT (Nazoratchi va Shikoyat Bot) =================
@dp2.message(F.text == "/start")
async def start_bot2(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    await track_user_activity(message.from_user, "@YukchiForwarderorg_Bot")

    if user_id in ADMINS:
        await message.answer("👨‍💻 <b>Nazoratchi Bot Admin Paneli:</b>", reply_markup=get_admin_keyboard())
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Shikoyat qilish", callback_data="comp_shikoyat"), InlineKeyboardButton(text="❓ Muammo bildirish", callback_data="comp_muammo")],
        [InlineKeyboardButton(text="🌐 Support Sayt", url=SUPPORT_SITE_URL)]
    ])
    await message.answer("🛡 <b>Nazoratchi va Shikoyat Boti</b>", reply_markup=kb)

@dp2.callback_query(F.data.in_({"comp_shikoyat", "comp_muammo"}))
async def comp_type(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(c_type="Shikoyat" if call.data == "comp_shikoyat" else "Muammo")
    await call.message.answer("📝 Matnni yuboring:")
    await state.set_state(ComplaintState.waiting_for_complaint_text)

@dp2.message(ComplaintState.waiting_for_complaint_text)
async def comp_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    for admin in ADMINS:
        try:
            await bot2.send_message(chat_id=admin, text=f"🚨 <b>{data.get('c_type')}</b>\nKimdan: {message.from_user.full_name}\nMatn: {message.text}")
        except: pass
    await message.answer("✅ Adminga yuborildi!")
    await state.clear()

# ================= UMUMIY ADMIN PANEL FUNKSIYALARI =================
async def admin_list_drivers(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS: return
    txt = "\n".join([f"👤 {d['name']} | 🚛 {d['car']} | @{d['username']}" for d in drivers_db.values()]) or "Haydovchilar yo'q"
    await call.message.answer(f"🚛 <b>Haydovchilar ro'yxati:</b>\n\n{txt}")

async def admin_list_curators(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS: return
    txt = "\n".join([f"👤 {c['name']} | 📞 {c['phone']} | @{c['username']}" for c in curators_db.values()]) or "Kuratorlar yo'q"
    await call.message.answer(f"📦 <b>Kuratorlar ro'yxati:</b>\n\n{txt}")

async def admin_stats(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS: return
    await call.message.answer(f"📊 <b>Statistika:</b>\n👥 Foydalanuvchilar: {len(user_stats)}\n🚛 Haydovchilar: {len(drivers_db)}\n📦 Kuratorlar: {len(curators_db)}")

async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS: return
    await call.message.answer("📢 Barcha foydalanuvchilarga yuboriladigan reklama matnini kiriting:")
    await state.set_state(AdminState.waiting_for_broadcast)

async def broadcast_process(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS: return
    count = 0
    for uid in user_stats.keys():
        try:
            await message.copy_to(chat_id=int(uid))
            count += 1
        except: pass
    await message.answer(f"✅ Reklama {count} ta foydalanuvchiga yetkazildi!")
    await state.clear()

async def ban_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS: return
    await call.message.answer("🚫 Ban qilinadigan foydalanuvchi ID raqamini yuboring:")
    await state.set_state(AdminState.waiting_for_ban_target)

async def ban_process(message: types.Message, state: FSMContext):
    if message.text.strip().isdigit():
        uid = int(message.text.strip())
        banned_users[uid] = "Blocked"
        save_json(BANNED_FILE, banned_users)
        await message.answer(f"✅ {uid} ban qilindi!")
    await state.clear()

async def unban_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS: return
    await call.message.answer("✅ Bandan chiqariladigan foydalanuvchi ID raqamini yuboring:")
    await state.set_state(AdminState.waiting_for_unban_target)

async def unban_process(message: types.Message, state: FSMContext):
    if message.text.strip().isdigit():
        uid = int(message.text.strip())
        if uid in banned_users: del banned_users[uid]
        save_json(BANNED_FILE, banned_users)
        await message.answer(f"✅ {uid} bandan chiqarildi!")
    await state.clear()

for dp_inst in [dp1, dp2]:
    @dp_inst.callback_query(F.data == "admin_list_drivers")
    async def ald(c: types.CallbackQuery): await call_answer_and_run(c, admin_list_drivers)
    @dp_inst.callback_query(F.data == "admin_list_curators")
    async def alc(c: types.CallbackQuery): await call_answer_and_run(c, admin_list_curators)
    @dp_inst.callback_query(F.data == "admin_stats")
    async def als(c: types.CallbackQuery): await call_answer_and_run(c, admin_stats)
    @dp_inst.callback_query(F.data == "admin_broadcast")
    async def bcs(c: types.CallbackQuery, s: FSMContext): await call_answer_and_run(c, lambda x: broadcast_start(x, s))
    @dp_inst.callback_query(F.data == "admin_ban_user")
    async def bns(c: types.CallbackQuery, s: FSMContext): await call_answer_and_run(c, lambda x: ban_start(x, s))
    @dp_inst.callback_query(F.data == "admin_unban_user")
    async def ubs(c: types.CallbackQuery, s: FSMContext): await call_answer_and_run(c, lambda x: unban_start(x, s))

async def call_answer_and_run(call: types.CallbackQuery, func):
    await call.answer()
    await func(call)

@dp1.message(AdminState.waiting_for_broadcast)
async def bcp(m: types.Message, s: FSMContext): await broadcast_process(m, s)
@dp1.message(AdminState.waiting_for_ban_target)
async def bnp(m: types.Message, s: FSMContext): await ban_process(m, s)
@dp1.message(AdminState.waiting_for_unban_target)
async def ubp(m: types.Message, s: FSMContext): await unban_process(m, s)

@dp2.message(AdminState.waiting_for_broadcast)
async def bcp2(m: types.Message, s: FSMContext): await broadcast_process(m, s)
@dp2.message(AdminState.waiting_for_ban_target)
async def bnp2(m: types.Message, s: FSMContext): await ban_process(m, s)
@dp2.message(AdminState.waiting_for_unban_target)
async def ubp2(m: types.Message, s: FSMContext): await unban_process(m, s)

# ================= FASTAPI WEBHOOKS =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/webhook/{token}")
async def webhook_handler(token: str, request: Request):
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot1 if token == API_TOKEN_1 else bot2})
    if token == API_TOKEN_1:
        await dp1.feed_update(bot1, update)
    elif token == API_TOKEN_2:
        await dp2.feed_update(bot2, update)
    return {"status": "ok"}

@app.get("/")
async def root(request: Request):
    base_url = str(request.base_url).rstrip("/")
    await bot1.set_webhook(f"{base_url}/webhook/{API_TOKEN_1}")
    await bot2.set_webhook(f"{base_url}/webhook/{API_TOKEN_2}")
    return {"status": "Botlar muvaffaqiyatli ishga tushdi va ulandi!"}
