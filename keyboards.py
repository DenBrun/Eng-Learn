from aiogram import types
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random

from aiogram.types import callback_query
from db import User, DB
from datetime import datetime, timedelta
import pytz

tz = pytz.timezone('Europe/Kiev')


hi_but = KeyboardButton('Привіт! 👋')
greet_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(hi_but)

#keyboard for choosing level
available_levels = ['Beginner', 'Pre-intermediate', 'Intermediate', 'Upper-Intermediate']
levels_kb = ReplyKeyboardMarkup(resize_keyboard=True)
for i in available_levels:
    levels_kb.add(KeyboardButton(i))

#kb for choosing time
available_time = ['8:00', '10:00', '13:00', '15:00', '18:00', '20:00', 'Інший час']
time_kb = ReplyKeyboardMarkup(resize_keyboard=True).row(
    KeyboardButton('8:00'), KeyboardButton('10:00'), KeyboardButton('13:00')
).row(
    KeyboardButton('15:00'), KeyboardButton('18:00'), KeyboardButton('20:00')
).add('Інший час')

#main keyboard
available_main_kb = ['Вчити слова 📚', 'Мій прогрес 📈', 'Додати слова 📝', 'Вчити тему 📙', 'Налаштування ⚙️']
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
for i in available_main_kb:
    if i =='Вчити тему 📙':
        main_kb.row(KeyboardButton(i), KeyboardButton('Налаштування ⚙️'))
        break
    main_kb.add(KeyboardButton(i))


available_settings_kb = ['Змінити час навчання 🕓', 'Змінити рівень 📊', 'Перезавантажити бота ⚙️', 
                                                    'Підтримка 🛠', 'Головне меню 🖥']
settings_kb = ReplyKeyboardMarkup(resize_keyboard=True)
for i in available_settings_kb:
    if i == 'Перезавантажити бота ⚙️':
        settings_kb.row(KeyboardButton(i), KeyboardButton('Підтримка 🛠')).add(KeyboardButton('Головне меню 🖥'))
        break
    settings_kb.add(KeyboardButton(i))


#1 learning keyboard
availabe_learning_kb = ['Вчити ✅', 'Я це знаю 😎', 'Зупинити вправу 🏁']
learning_kb = ReplyKeyboardMarkup(resize_keyboard=True)
for i in availabe_learning_kb:
    learning_kb.add(KeyboardButton(i))

def get_revising_kb(all_words, correct_word):  #for 1/3 revizing quiz
    words = all_words.copy()

    kb_options = [correct_word]
    words.remove(correct_word)
    
    random.shuffle(words)

    kb_options.append(words[0])
    kb_options.append(words[1])

    random.shuffle(kb_options)
    
    revising_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for word in kb_options:
        revising_kb.add(KeyboardButton(word.translation))
    return revising_kb


def get_revising_kb_2(all_words, correct_word):  #for 2/4 revizing quiz
    words = all_words.copy()

    kb_options = [correct_word]
    words.remove(correct_word)
    
    random.shuffle(words)

    kb_options.append(words[0])
    kb_options.append(words[1])

    random.shuffle(kb_options)
    
    revising_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for word in kb_options:
        revising_kb.add(KeyboardButton(word.eng_word))
    return revising_kb

cancel_button = 'Скасувати 🏁'
cancel_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton(cancel_button))


#######__________Inline buttons__________#######


confirmation_kb = InlineKeyboardMarkup().row(InlineKeyboardButton('✅ Yes', callback_data=f'true'), 
                                            InlineKeyboardButton('❌ No', callback_data=f'false'))


def create_periods(global_table, stage, table_id, kb, for_revising, now):

    inline_kb = kb
    keyboard_buttons:list = []

    if table_id == 'u':
        emj = '📕 '
    else:
        emj = '📘 '

    for w_id in for_revising[global_table][stage]:

        learning_date = tz.localize(datetime.strptime(for_revising[global_table][stage][w_id]['date'], '%d.%m.%y'), is_dst=None)

        if now - timedelta(days=3) <= learning_date:
            keyboard_buttons.append(InlineKeyboardButton(f'{emj}Вчора та раніше 🙃 ({stage})', callback_data=f'{stage}_{w_id}_{table_id}'))
        elif now - timedelta(days=7) <= learning_date:
            keyboard_buttons.append(InlineKeyboardButton(f'{emj}3 дні назад та раніше 🤔 ({stage})', callback_data=f'{stage}_{w_id}_{table_id}'))
        elif now - timedelta(days=21) <= learning_date:
            keyboard_buttons.append(InlineKeyboardButton(f'{emj}Тиждень назад та раніше 🥵 ({stage})', callback_data=f'{stage}_{w_id}_{table_id}'))
        elif now - timedelta(days=30) <= learning_date:
            keyboard_buttons.append(InlineKeyboardButton(f'{emj}3 тижня назад та раніше 🤯 ({stage})', callback_data=f'{stage}_{w_id}_{table_id}'))
        else:
            keyboard_buttons.append(InlineKeyboardButton(f'{emj}Місяць назад та раніше 🥶 ({stage})', callback_data=f'{stage}_{w_id}_{table_id}'))


            #word_kb_id = int(list(keyboards_data['all'][stage].values()).index(learning['words'])) + 1



    keyboard_buttons.reverse()
    for button in keyboard_buttons:
        inline_kb.add(button)

    return inline_kb



def get_periods_inline_kb(user:User):
    table_id = user.table_id
    inline_kb = InlineKeyboardMarkup()
    for_revising = user.for_revision
    now = datetime.now(tz)

    keyboards_data:dict = user.keyboards_data
    for global_table in ['all', 'user_words']:

        if global_table == 'user_words':
            table_id = 'u'
        else:
            table_id = user.table_id
    
        if len(for_revising[global_table]['1']) > 0:
            inline_kb = create_periods(global_table, '1', table_id, inline_kb, for_revising, now)

        if len(for_revising[global_table]['2']) > 0:
            inline_kb = create_periods(global_table, '2', table_id, inline_kb, for_revising, now)

        if len(for_revising[global_table]['3']) > 0:
            inline_kb = create_periods(global_table, '3', table_id, inline_kb, for_revising, now)

        if len(for_revising[global_table]['4']) > 0:
            inline_kb = create_periods(global_table, '4', table_id, inline_kb, for_revising, now)
        

    if len(for_revising['all']['1']) == 0 and len(for_revising['all']['2']) == 0 and \
                            len(for_revising['all']['3']) == 0 and len(for_revising['all']['4']) == 0 and\
                            len(for_revising['user_words']['1']) == 0 and len(for_revising['user_words']['2']) == 0 and \
                            len(for_revising['user_words']['3']) == 0 and len(for_revising['user_words']['4']) == 0:
        return None

    return inline_kb

    