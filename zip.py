import os
import zipfile

import telebot
from telebot import types

TOKEN = "TOKEN"
bot = telebot.TeleBot(TOKEN)

# ==== СПИСОК РАЗРЕШЕННЫХ ID ====
ALLOWED_USERS = [123456789, 123456789, 123456789]

user_data = {}


# ====== Проверка доступа ======
def is_allowed(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.send_message(message.chat.id, "⛔ Sizga bu botdan foydalanishga ruxsat berilmagan.")
        return False
    return True


# ====== /start ======
@bot.message_handler(commands=['start'])
def start(message):
    if not is_allowed(message):
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📂 Fayllarni siqish"))
    bot.send_message(
        message.chat.id,
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "📦 Men sizning fayllaringizni qabul qilib, ularni <b>.zip</b> formatida siqib beradigan botman.\n\n"
        "👇 Quyidagi tugmadan foydalaning:",
        parse_mode="HTML",
        reply_markup=markup
    )
    user_data[message.chat.id] = {"files": [], "zip_name": None, "caption": None, "pending_media_group": {}}


# ====== Кнопка "Fayllarni siqish" ======
@bot.message_handler(func=lambda message: message.text == "📂 Fayllarni siqish")
def ask_zip_name(message):
    if not is_allowed(message):
        return

    user_data[message.chat.id] = {"files": [], "zip_name": None, "caption": None, "pending_media_group": {}}
    bot.send_message(message.chat.id, "✍️ <b>Zip fayl nomini kiriting:</b>", parse_mode="HTML")
    bot.register_next_step_handler(message, set_zip_name)


def set_zip_name(message):
    if not is_allowed(message):
        return

    chat_id = message.chat.id
    user_data[chat_id]["zip_name"] = message.text.strip()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✅ Tayyor"))
    bot.send_message(
        chat_id,
        "📤 <b>Endi fayllarni yuboring.</b>\n\n"
        "💡 Agar hammasini yuborib bo'lsangiz, '✅ Tayyor' tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=markup
    )


# ====== Функция сохранения файла ======
def save_file(chat_id, file_id, file_name):
    folder = f"temp_{chat_id}"
    if not os.path.exists(folder):
        os.makedirs(folder)

    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    file_path = os.path.join(folder, file_name)
    with open(file_path, "wb") as f:
        f.write(downloaded_file)

    user_data[chat_id]["files"].append(file_path)


# ====== Обработка альбомов (media_group) ======
@bot.message_handler(content_types=['photo', 'video', 'document'],
                     func=lambda message: message.media_group_id is not None)
def handle_media_group(message):
    if not is_allowed(message):
        return

    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {"files": [], "zip_name": None, "caption": None, "pending_media_group": {}}

    group_id = message.media_group_id
    if group_id not in user_data[chat_id]["pending_media_group"]:
        user_data[chat_id]["pending_media_group"][group_id] = []

    user_data[chat_id]["pending_media_group"][group_id].append(message)

    if len(user_data[chat_id]["pending_media_group"][group_id]) == 1:
        import threading
        threading.Timer(1.0, process_media_group, args=(chat_id, group_id)).start()


def process_media_group(chat_id, group_id):
    messages = user_data[chat_id]["pending_media_group"].pop(group_id, [])
    if not messages:
        return

    caption = None
    for i, msg in enumerate(messages):
        if msg.caption and not caption:
            caption = msg.caption

        if msg.content_type == 'photo':
            file_id = msg.photo[-1].file_id
            file_name = f"group_{group_id}_{i}.jpg"
        elif msg.content_type == 'video':
            file_id = msg.video.file_id
            file_name = msg.video.file_name or f"group_{group_id}_{i}.mp4"
        elif msg.content_type == 'document':
            file_id = msg.document.file_id
            file_name = msg.document.file_name
        else:
            continue

        save_file(chat_id, file_id, file_name)

    if caption:
        user_data[chat_id]["caption"] = caption
        create_and_send_zip(chat_id)
    else:
        bot.send_message(
            chat_id,
            f"✅ <b>{len(messages)}</b> ta fayl qabul qilindi.\n📥 Yana yuboring yoki '✅ Tayyor' tugmasini bosing.",
            parse_mode="HTML"
        )


# ====== Обработка одиночных файлов ======
@bot.message_handler(content_types=['document', 'photo', 'video', 'audio', 'voice', 'video_note', 'sticker', 'animation'])
def handle_files(message):
    if not is_allowed(message):
        return

    chat_id = message.chat.id
    if message.media_group_id:
        return

    if chat_id not in user_data:
        user_data[chat_id] = {"files": [], "zip_name": None, "caption": None, "pending_media_group": {}}

    if message.content_type == 'document':
        file_id = message.document.file_id
        file_name = message.document.file_name
    elif message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_name = f"photo_{len(user_data[chat_id]['files'])}.jpg"
    elif message.content_type == 'video':
        file_id = message.video.file_id
        file_name = message.video.file_name or f"video_{len(user_data[chat_id]['files'])}.mp4"
    elif message.content_type == 'audio':
        file_id = message.audio.file_id
        file_name = message.audio.file_name or f"audio_{len(user_data[chat_id]['files'])}.mp3"
    elif message.content_type == 'voice':
        file_id = message.voice.file_id
        file_name = f"voice_{len(user_data[chat_id]['files'])}.ogg"
    elif message.content_type == 'video_note':
        file_id = message.video_note.file_id
        file_name = f"videonote_{len(user_data[chat_id]['files'])}.mp4"
    elif message.content_type == 'sticker':
        file_id = message.sticker.file_id
        file_name = f"sticker_{len(user_data[chat_id]['files'])}.webp"
    elif message.content_type == 'animation':
        file_id = message.animation.file_id
        file_name = message.animation.file_name or f"gif_{len(user_data[chat_id]['files'])}.mp4"
    else:
        bot.send_message(chat_id, "⚠️ Bu fayl turini qo'llab-quvvatlay olmayman.")
        return

    save_file(chat_id, file_id, file_name)
    bot.send_message(chat_id, "📥 Fayl qabul qilindi. Yana yuboring yoki '✅ Tayyor' tugmasini bosing.")


@bot.message_handler(func=lambda message: message.text == "✅ Tayyor")
def ask_caption(message):
    if not is_allowed(message):
        return

    chat_id = message.chat.id
    if not user_data.get(chat_id) or len(user_data[chat_id]["files"]) == 0:
        bot.send_message(chat_id, "⚠️ Avval hech bo'lmaganda bitta fayl yuboring.")
        return
    bot.send_message(chat_id, "📝 <b>Zip fayl uchun izoh (caption) yozing:</b>", parse_mode="HTML")
    bot.register_next_step_handler(message, set_caption)


def set_caption(message):
    if not is_allowed(message):
        return

    chat_id = message.chat.id
    user_data[chat_id]["caption"] = message.text
    create_and_send_zip(chat_id)


def create_and_send_zip(chat_id):
    zip_name = user_data[chat_id]["zip_name"] or "files"
    caption = user_data[chat_id]["caption"]
    files = user_data[chat_id]["files"]

    zip_path = f"{zip_name}.zip"

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))

    with open(zip_path, 'rb') as zf:
        bot.send_document(chat_id, zf, caption=caption)

    for file in files:
        os.remove(file)
    folder = f"temp_{chat_id}"
    if os.path.exists(folder):
        os.rmdir(folder)
    os.remove(zip_path)

    user_data[chat_id] = {"files": [], "zip_name": None, "caption": None, "pending_media_group": {}}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📂 Fayllarni siqish"))
    bot.send_message(chat_id, "🎉 <b>Hammasi tayyor!</b>\n♻️ Fayllar tozalandi, endi yangi siqishni boshlashingiz mumkin.",
                     parse_mode="HTML", reply_markup=markup)


bot.polling(none_stop=True)
