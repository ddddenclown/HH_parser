import logging
import requests
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

TOKEN = 'token'

params = {
    'text': 'backend',  # ключевое слово
    'area': 88,         # код региона: 88 – Казань
    'per_page': 10,
    'page': 0
}

sent_vacancies_file = 'sent_vacancies.json'

def load_sent_vacancies():
    if os.path.exists(sent_vacancies_file):
        try:
            with open(sent_vacancies_file, 'r') as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            print("Файл повреждён, создаём новый.")
            return set()
    return set()

def save_sent_vacancies(sent_ids):
    with open(sent_vacancies_file, 'w') as f:
        json.dump(list(sent_ids), f)

def fetch_new_vacancies():
    sent_ids = load_sent_vacancies()
    new_vacancies = []
    response = requests.get('https://api.hh.ru/vacancies', params=params)
    response.raise_for_status()
    data = response.json()
    for vacancy in data['items']:
        if vacancy['id'] not in sent_ids:
            new_vacancies.append(vacancy)
            sent_ids.add(vacancy['id'])
    save_sent_vacancies(sent_ids)
    return new_vacancies

user_vacancies = {}

# Обработчик команды /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Отправь /check, чтобы посмотреть новые вакансии.")

# Обработчик команды /check
async def check(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        vacancies = fetch_new_vacancies()
        if not vacancies:
            await update.message.reply_text("Нет новых вакансий.")
        else:
            user_vacancies[chat_id] = vacancies
            vacancy = vacancies[0]
            keyboard = [[InlineKeyboardButton("Следующая вакансия", callback_data="next_1")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = (f"Вакансия 1:\n"
                    f"Название: {vacancy['name']}\n"
                    f"Ссылка: {vacancy['alternate_url']}")
            await update.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        await update.message.reply_text("Ошибка при получении вакансий.")
        print(e)

async def next_vacancy(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    try:
        _, index_str = query.data.split("_")
        index = int(index_str)
    except Exception as e:
        index = 1

    vacancies = user_vacancies.get(chat_id, [])
    if index < len(vacancies):
        vacancy = vacancies[index]
        keyboard = [[InlineKeyboardButton("Следующая вакансия", callback_data=f"next_{index+1}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (f"Вакансия {index+1}:\n"
                f"Название: {vacancy['name']}\n"
                f"Ссылка: {vacancy['alternate_url']}")
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await query.edit_message_text(text="Больше новых вакансий нет.")

def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CallbackQueryHandler(next_vacancy, pattern=r'^next_'))

    application.run_polling()

if __name__ == '__main__':
    main()
