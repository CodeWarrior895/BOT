import telebot
import firebase_admin
from firebase_admin import credentials, db
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove




# Загрузка токенов
BOT_TOKEN = "7047755384:AAHrX_-Ca7iRs0IQnyJ9T2ft4dD7yFz-yDo"
bot = telebot.TeleBot(BOT_TOKEN)

# Подключение к Firebase
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
    class_letter = message.text.strip()
    if len(class_letter) == 1 and class_letter.isalpha():
        user_data[user_id]['class_letter'] = class_letter.upper()
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

    if(str(user_id) == "1413003857"):
        markup.add(KeyboardButton("Blacklist"))
    
    bot.send_message(user_id, "Что хочешь сделать дальше?", reply_markup=markup)

# Функция отправки жалоб
@bot.message_handler(func=lambda message: message.text == "⚠ Отправить жалобу")
def ask_for_complaint(message):
    bot.send_message(message.chat.id, "Опишите вашу жалобу:")
    bot.register_next_step_handler(message, save_complaint)


@bot.message_handler(func=lambda message: message.text == "Blacklist")
def blacklist(message):
    bot.send_message(message.chat.id, "Blacklist the user:")
    bot.register_next_step_handler(message, blacklist_user)

def blacklist_user(message):
    user_id = message.text.strip()
    ref = db.reference("blacklist")
    ref.child(str(user_id)).set(True)
    blacklist_session.add(user_id)
    bot.send_message(message.chat.id, f"✅ Пользователь {user_id} добавлен в черный список.")
    user_id = message.chat.id
    send_search_button(user_id)

    

def save_complaint(message):
    user_id = message.chat.id
    complaint_text = message.text
    complaints_ref = db.reference("complaints")
    complaints_ref.push({
        "user_id": user_id,
        "complaint": complaint_text
    })
    bot.send_message(user_id, "✅ Ваша жалоба отправлена.")

    user_id = message.chat.id
    send_search_button(user_id)

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
        matching_users = []
        for uid, user_info in users_ref.items():
            if user_info.get("class") == class_num and user_info.get("class_letter").upper() == class_letter:
                matching_users.append((uid, user_info))

        if matching_users:
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for uid, user_info in matching_users:
                button = KeyboardButton(f"{user_info['name']} {user_info['surname']} ({uid})")
                markup.add(button)
            bot.send_message(user_id, "Выберите пользователя:", reply_markup=markup)
            bot.register_next_step_handler(message, ask_for_valentine)
        else:
            bot.send_message(user_id, "❌ Пользователи этого класса не найдены.")
    else:
        bot.send_message(user_id, "База данных пока пустая.")



def ask_for_valentine(message):
    selected_text = message.text
    user_id = message.chat.id
    selected_uid = selected_text.split(" (")[1].rstrip(")") if " (" in selected_text else None
    
    if selected_uid:
        user_data[user_id]['recipient_id'] = selected_uid
        bot.send_message(user_id, "✍ Напишите вашу валентинку:")
        bot.register_next_step_handler(message, send_valentine)
    else:
        bot.send_message(user_id, "❌ Ошибка: Некорректный выбор пользователя.")

def send_valentine(message):
    user_id = message.chat.id
    recipient_id = user_data[user_id].get('recipient_id')
    valentine_text = message.text
    
    if recipient_id:
        bot.send_message(int(recipient_id), "❤️❤️ Вам пришла анонимная валентинка: ❤️❤️")
        bot.send_message(int(recipient_id), valentine_text)
        bot.send_message(user_id, "✅ Валентинка отправлена анонимно!")
    else:
        bot.send_message(user_id, "❌ Ошибка: Получатель не найден.")
    
    user_id = message.chat.id
    send_search_button(user_id)


if __name__ == "__main__":
    bot.infinity_polling()
