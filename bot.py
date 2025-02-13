import telebot
import firebase_admin
from firebase_admin import credentials, db
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import os

# Загрузка токенов
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

cred = credentials.Certificate("./serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://valentine-a2e19-default-rtdb.firebaseio.com/"
})

# Словарь для хранения состояния пользователя
user_data = {}
blacklist_session = set()

RULES = "\nПравила использования:\n1) Не выставлять себя за других\n2) Не писать гадости, а только любовные записки\n3) Не использовать бота для других целей\n"

def is_blacklisted(user_id):
    blacklist_ref = db.reference("blacklist").get()
    return str(user_id) in blacklist_ref if blacklist_ref else False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if is_blacklisted(user_id):
        bot.send_message(user_id, "❌ Вам запрещено использовать этого бота.")
        return
    
    user_data[user_id] = {}
    bot.send_message(user_id, f"Привет! Добро пожаловать в бота для отправки валентинок! {RULES}\nКак тебя зовут?")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_id = message.chat.id
    user_data[user_id]['name'] = message.text
    bot.send_message(user_id, "Какая у тебя фамилия?")
    bot.register_next_step_handler(message, get_surname)

def get_surname(message):
    user_id = message.chat.id
    user_data[user_id]['surname'] = message.text
    bot.send_message(user_id, "Какой у тебя класс? (например: 10)")
    bot.register_next_step_handler(message, get_class)

def get_class(message):
    user_id = message.chat.id
    user_data[user_id]['class'] = message.text
    bot.send_message(user_id, "Какая буква у твоего класса? (одна буква, например: А)")
    bot.register_next_step_handler(message, validate_class_letter)

def validate_class_letter(message):
    user_id = message.chat.id
    class_letter = message.text.strip().upper()
    if len(class_letter) == 1 and class_letter.isalpha():
        user_data[user_id]['class_letter'] = class_letter
        save_user(user_id, user_data[user_id])
        bot.send_message(user_id, "✅ Спасибо! Я записал твои данные.", reply_markup=ReplyKeyboardRemove())
        send_search_button(user_id)
    else:
        bot.send_message(user_id, "❌ Ошибка: Введите только одну букву.")
        bot.register_next_step_handler(message, validate_class_letter)

def save_user(user_id, data):
    ref = db.reference("users")
    ref.child(str(user_id)).set({
        "name": data["name"],
        "surname": data["surname"],
        "class": data["class"],
        "class_letter": data["class_letter"]
    })

def send_search_button(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.add(KeyboardButton("🔍 Найти пользователя"))
    markup.add(KeyboardButton("⚠ Отправить жалобу"))

    if str(user_id) == "1413003857":
        markup.add(KeyboardButton("Blacklist"))
    
    bot.send_message(user_id, "Что хочешь сделать дальше?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔍 Найти пользователя")
def ask_for_class(message):
    bot.send_message(message.chat.id, "Введите номер класса (например: 10):")
    bot.register_next_step_handler(message, ask_for_class_letter)

def ask_for_class_letter(message):
    user_id = message.chat.id
    user_data[user_id] = {'class': message.text}
    bot.send_message(user_id, "Введите букву класса (например: А):")
    bot.register_next_step_handler(message, search_users_by_class)

def search_users_by_class(message):
    user_id = message.chat.id
    user_data[user_id]['class_letter'] = message.text.strip().upper()
    class_num = user_data[user_id]['class']
    class_letter = user_data[user_id]['class_letter']

    users_ref = db.reference("users").get()
    if users_ref:
        matching_users = [
            (uid, user_info) for uid, user_info in users_ref.items()
            if user_info.get("class") == class_num and user_info.get("class_letter", "").upper() == class_letter
        ]
        if matching_users:
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for uid, user_info in matching_users:
                markup.add(KeyboardButton(f"{user_info['name']} {user_info['surname']} ({uid})"))
            bot.send_message(user_id, "Выберите пользователя:", reply_markup=markup)
            bot.register_next_step_handler(message, ask_for_valentine)
        else:
            bot.send_message(user_id, "❌ Пользователи этого класса не найдены.")
    else:
        bot.send_message(user_id, "База данных пока пустая.")

if __name__ == "__main__":
    bot.infinity_polling()
