import telebot
from datetime import date, datetime, timedelta
import sqlite3
import re
import random
import threading
import time

# ========== ТВОЙ ЛИЧНЫЙ КЛЮЧ К МАГИИ ==========
TOKEN = "8661510660:AAFtmqPyMq3qZEdBOdGWlbOndCBXfV7HohE"
bot = telebot.TeleBot(TOKEN)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  birthday TEXT,
                  last_congrat TEXT)''')
    conn.commit()
    conn.close()

def save_birthday(user_id, birthday_str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, birthday, last_congrat) VALUES (?, ?, ?)",
              (user_id, birthday_str, None))
    conn.commit()
    conn.close()

def get_birthday(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT birthday FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def update_last_congrat(user_id, today):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_congrat = ? WHERE user_id = ?", (today, user_id))
    conn.commit()
    conn.close()

def get_last_congrat(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT last_congrat FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_users():
    """Получить всех пользователей с их днями рождения"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id, birthday FROM users WHERE birthday IS NOT NULL")
    results = c.fetchall()
    conn.close()
    return results

# ========== ФУНКЦИЯ ПОДСЧЁТА ДНЕЙ ==========
def days_until(month, day):
    today = date.today()
    target = date(today.year, month, day)
    if target < today:
        target = date(today.year + 1, month, day)
    return (target - today).days

# ========== ФУНКЦИЯ ДЛЯ ЕЖЕДНЕВНЫХ НАПОМИНАНИЙ ==========
def send_daily_reminders():
    """Проверяет всех пользователей и отправляет напоминания тем, у кого ДР через <= 30 дней"""
    print(f"🕒 Запуск ежедневной проверки в {datetime.now().strftime('%H:%M:%S')}")
    
    users = get_all_users()
    today = date.today()
    
    for user_id, birthday_str in users:
        try:
            # Разбираем дату рождения
            day, month = map(int, birthday_str.split('.'))
            
            # Считаем дни до ДР
            days_left = days_until(month, day)
            
            # Если ДР через 30 дней или меньше (и не 0, потому что 0 - это сегодня)
            if 1 <= days_left <= 30:
                # Отправляем напоминание
                bot.send_message(
                    user_id, 
                    f"⏰ **НАПОМИНАНИЕ** ⏰\n\n"
                    f"🎂 До твоего дня рождения осталось **{days_left}** дней!\n"
                    f"Успей подготовить подарки и торт! 🎁🎂"
                )
                print(f"✅ Напоминание отправлено пользователю {user_id} (осталось {days_left} дней)")
            elif days_left == 0:
                # Сегодня ДР - поздравление уже сработает через обычный обработчик
                pass
        except Exception as e:
            print(f"❌ Ошибка при отправке напоминания пользователю {user_id}: {e}")
    
    print(f"✅ Ежедневная проверка завершена")

# ========== ПЛАНИРОВЩИК ==========
def scheduler():
    """Запускает ежедневные напоминания в 9:00"""
    while True:
        now = datetime.now()
        # Вычисляем время до следующего 9:00
        next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        
        sleep_seconds = (next_run - now).total_seconds()
        print(f"⏰ Следующая рассылка напоминаний в {next_run.strftime('%H:%M:%S %d.%m.%Y')}")
        
        time.sleep(sleep_seconds)
        send_daily_reminders()

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "друг"
    bot.send_message(message.chat.id, 
f"""🌟 Привет, {name}! 

👇 Жми на кнопки внизу 👇

Теперь я буду напоминать тебе о ДР за 30 дней! 🎯""", 
    reply_markup=main_keyboard())

def main_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        telebot.types.KeyboardButton("🎄 До НГ"),
        telebot.types.KeyboardButton("☀️ До лета"),
        telebot.types.KeyboardButton("🎂 Мой ДР"),
        telebot.types.KeyboardButton("📅 Установить ДР"),
        telebot.types.KeyboardButton("❓ Помощь")
    ]
    keyboard.add(*buttons)
    return keyboard

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id,
"""❓ **КАК ПОЛЬЗОВАТЬСЯ:**

🎄 До НГ - сколько дней до Нового года
☀️ До лета - сколько дней до лета
🎂 Мой ДР - сколько до твоего дня рождения
📅 Установить ДР - запомнить дату (потом напиши ДД.ММ)

📌 **НОВАЯ ФИЧА:** Каждый день в 9:00 я присылаю напоминание, если до твоего ДР осталось 30 дней или меньше!""", 
    parse_mode="Markdown", reply_markup=main_keyboard())

# ========== ОБРАБОТКА КНОПОК И ТЕКСТА ==========
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    text = message.text
    user_id = message.from_user.id
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    name = message.from_user.first_name or "друг"
    
    # ===== КНОПКА: До НГ =====
    if text == "🎄 До НГ":
        days = days_until(12, 31)
        bot.send_message(message.chat.id, f"🎄 До Нового года осталось {days} дней!", reply_markup=main_keyboard())
    
    # ===== КНОПКА: До лета =====
    elif text == "☀️ До лета":
        days = days_until(6, 1)
        bot.send_message(message.chat.id, f"☀️ До лета осталось {days} дней!", reply_markup=main_keyboard())
    
    # ===== КНОПКА: Мой ДР =====
    elif text == "🎂 Мой ДР":
        birthday_str = get_birthday(user_id)
        if not birthday_str:
            bot.send_message(message.chat.id, "❌ Сначала нажми «📅 Установить ДР» и введи дату (например 15.06)", reply_markup=main_keyboard())
            return
        
        day, month = map(int, birthday_str.split('.'))
        days = days_until(month, day)
        
        if days == 0:
            bot.send_message(message.chat.id, "🎉 СЕГОДНЯ ТВОЙ ДЕНЬ! ПОЗДРАВЛЯЮ! 🎂", reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, f"🎂 До твоего дня рождения {days} дней!", reply_markup=main_keyboard())
    
    # ===== КНОПКА: Установить ДР =====
    elif text == "📅 Установить ДР":
        msg = bot.send_message(message.chat.id, "📝 Напиши дату в формате ДД.ММ\nНапример: 15.06", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, process_birthday_step)
    
    # ===== КНОПКА: Помощь =====
    elif text == "❓ Помощь":
        help_command(message)
    
    # ===== ЕСЛИ ПРОСТО ТЕКСТ (НЕ КНОПКА) - ПРОВЕРЯЕМ ДР =====
    else:
        # Проверяем, может это дата (если человек нажал "Установить ДР" и вводит)
        if re.match(r'^\d{2}\.\d{2}$', text):
            try:
                day, month = map(int, text.split('.'))
                if 1 <= day <= 31 and 1 <= month <= 12:
                    save_birthday(user_id, text)
                    bot.send_message(message.chat.id, f"✅ Дата {text} сохранена!\nТеперь я буду напоминать о ДР заранее 🎯", reply_markup=main_keyboard())
                else:
                    bot.send_message(message.chat.id, "❌ Неправильная дата. Попробуй ещё раз /start", reply_markup=main_keyboard())
            except:
                bot.send_message(message.chat.id, "❌ Что-то не так. Нажми /start", reply_markup=main_keyboard())
        
        # Проверяем ДР для поздравления
        else:
            try:
                birthday_str = get_birthday(user_id)
                if birthday_str:
                    b_day, b_month = map(int, birthday_str.split('.'))
                    
                    if b_day == today.day and b_month == today.month:
                        last = get_last_congrat(user_id)
                        if last != today_str:
                            bot.send_message(message.chat.id, 
                                           f"🎉 С Днём Рождения, {name}! 🎂\nСчастья, здоровья, любви! 💝", 
                                           reply_markup=main_keyboard())
                            update_last_congrat(user_id, today_str)
            except:
                pass

# ===== ОТДЕЛЬНЫЙ ШАГ ДЛЯ УСТАНОВКИ ДР =====
def process_birthday_step(message):
    text = message.text
    user_id = message.from_user.id
    
    if re.match(r'^\d{2}\.\d{2}$', text):
        try:
            day, month = map(int, text.split('.'))
            if 1 <= day <= 31 and 1 <= month <= 12:
                save_birthday(user_id, text)
                bot.send_message(message.chat.id, f"✅ Дата {text} сохранена!\nТеперь я буду напоминать о ДР заранее 🎯", reply_markup=main_keyboard())
            else:
                bot.send_message(message.chat.id, "❌ Неправильная дата. Нажми /start", reply_markup=main_keyboard())
        except:
            bot.send_message(message.chat.id, "❌ Ошибка. Нажми /start", reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Формат ДД.ММ, например 15.06", reply_markup=main_keyboard())

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    init_db()
    
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=scheduler)
    scheduler_thread.daemon = True  # Поток завершится при остановке бота
    scheduler_thread.start()
    
    print("""
    ╔══════════════════════════════════╗
    ║   🚀 БОТ С НАПОМИНАНИЯМИ        ║
    ║   Ежедневная рассылка в 9:00    ║
    ║   За 30 дней до ДР              ║
    ╚══════════════════════════════════╝
    """)
    bot.infinity_polling()