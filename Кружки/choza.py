import os
import sqlite3
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler

# --- НАСТРОЙКИ ---
TOKEN = "8710913470:AAFqTQKgjaMcY2d_7zKPfg_DUah5Xw4pVYA"
ADMIN_ID = 856643486 # Твой ID
FFMPEG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')

# Состояния для добавления товара
PHOTO, NAME, DESC, PRICE = range(4)

# --- ИНИЦИАЛИЗАЦИЯ БД ---
def init_db():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS products 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, desc TEXT, price TEXT, photo_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, username TEXT)''')
    conn.commit()
    conn.close()

# --- ФУНКЦИИ АДМИНКИ ---

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("➕ Добавить товар", callback_data='add_item')],
        [InlineKeyboardButton("🗑 Удалить все товары", callback_data='clear_db')]
    ]
    await update.message.reply_text("🛠 Панель управления магазином:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- ПРОЦЕСС ДОБАВЛЕНИЯ ТОВАРА ---

async def add_item_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Отправьте ФОТО букета:")
    return PHOTO

async def add_item_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("Введите НАЗВАНИЕ букета:")
    return NAME

async def add_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_name'] = update.message.text
    await update.message.reply_text("Введите ОПИСАНИЕ:")
    return DESC

async def add_item_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_desc'] = update.message.text
    await update.message.reply_text("Введите ЦЕНУ (например, 3500 руб.):")
    return PRICE

async def add_item_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = update.message.text
    
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, desc, price, photo_id) VALUES (?, ?, ?, ?)",
                   (context.user_data['new_name'], context.user_data['new_desc'], price, context.user_data['new_photo']))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("✅ Товар успешно добавлен в каталог!")
    return ConversationHandler.END

# --- ВИТРИНА ДЛЯ КЛИЕНТОВ ---

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, desc, price, photo_id FROM products")
    items = cursor.fetchall()
    conn.close()

    if not items:
        await update.message.reply_text("Каталог пока пуст. Заходите позже! 🌸")
        return

    for name, desc, price, photo_id in items:
        caption = f"💐 *{name}*\n\n📝 {desc}\n\n💰 Цена: {price}"
        await update.message.reply_photo(photo=photo_id, caption=caption, parse_mode='Markdown')

# --- СТАРЫЙ ФУНКЦИОНАЛ (КРУЖКИ) ---

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
        with open(output_path, 'rb') as f: await update.message.reply_video_note(f)
        await msg.delete()
    except Exception as e: await update.message.reply_text(f"❌ Ошибка видео: {e}")
    finally:
        for p in [input_path, output_path]: 
            if os.path.exists(p): os.remove(p)

# --- ЗАПУСК ---

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Диалог добавления товара
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_item_start, pattern='add_item')],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, add_item_photo)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_name)],
            DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_desc)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_item_finish)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(CommandHandler("catalog", show_catalog))
    app.add_handler(add_conv)
    app.add_handler(MessageHandler(filters.VIDEO, convert_to_circle))
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Привет! /catalog - смотреть букеты, видео - сделать кружок.")))

    print("Бот запущен! Команды: /admin для тебя, /catalog для всех.")
    app.run_polling()

if __name__ == "__main__":
    main()