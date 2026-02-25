import os
import sqlite3
import subprocess
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

# --- НАСТРОЙКИ ---
TOKEN = "8710913470:AAFqTQKgjaMcY2d_7zKPfg_DUah5Xw4pVYA"
ADMIN_ID = 856643486  # Твой ID
FFMPEG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
# Ссылка на твой будущий Mini App (пока можно использовать заглушку для теста)
WEB_APP_URL = "https://certonlive-spec.github.io/choza/" 

PHOTO, NAME, DESC, PRICE = range(4)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('choza_shop.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, desc TEXT, price TEXT, photo_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)''')
    conn.commit()
    conn.close()

# --- ЛОГИКА КРУЖКОВ (ЧОZA) ---
async def convert_to_circle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🎬 ЧОZA колдует кружок...")
    input_path = f"v_{update.effective_user.id}.mp4"
    output_path = f"c_{update.effective_user.id}.mp4"
    try:
        file = await update.message.video.get_file()
        await file.download_to_drive(input_path)
        cmd = [FFMPEG_PATH, '-y', '-i', input_path, '-vf', "crop='min(iw,ih):min(iw,ih)',scale=640:640", 
               '-t', '60', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', output_path]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(output_path, 'rb') as f: 
            await update.message.reply_video_note(f)
        await msg.delete()
    except Exception as e: 
        await update.message.reply_text(f"❌ Ошибка видео: {e}")
    finally:
        for p in [input_path, output_path]: 
            if os.path.exists(p): os.remove(p)

# --- АДМИНКА: ДОБАВЛЕНИЕ ТОВАРОВ ---
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("Отправь ФОТО нового букета для Mini App:")
    return PHOTO

async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("Введите НАЗВАНИЕ:")
    return NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_name'] = update.message.text
    await update.message.reply_text("Введите ОПИСАНИЕ:")
    return DESC

async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_desc'] = update.message.text
    await update.message.reply_text("Введите ЦЕНУ:")
    return PRICE

async def add_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('choza_shop.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, desc, price, photo_id) VALUES (?, ?, ?, ?)",
                   (context.user_data['new_name'], context.user_data['new_desc'], update.message.text, context.user_data['new_photo']))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Товар в базе! Он появится в Mini App.")
    return ConversationHandler.END

# --- ОБРАБОТКА ЗАКАЗА ИЗ MINI APP ---
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.effective_message.web_app_data.data)
    product_name = data.get("product", "Неизвестный товар")
    
    # Уведомление админу
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🛍 **НОВЫЙ ЗАКАЗ!**\n\nКлиент: @{update.effective_user.username}\nТовар: {product_name}"
    )
    # Ответ клиенту
    await update.message.reply_text(f"Спасибо за заказ! Мы скоро свяжемся с вами для уточнения доставки букета '{product_name}'.")

# --- КОМАНДА СТАРТ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌸 Открыть Магазин (Mini App)", web_app_info=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("📦 Мои заказы", callback_data='my_orders')]
    ]
    await update.message.reply_text(
        "Привет! Я бот ЧОZA.\n\n🎬 Отправь мне видео — сделаю кружок.\n🌸 Нажми кнопку ниже, чтобы выбрать букет!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Сборка обработчиков
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", admin_start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, add_photo)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_finish)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    app.add_handler(MessageHandler(filters.VIDEO, convert_to_circle))

    print("🚀 ЧОZA Mini App Bot запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

