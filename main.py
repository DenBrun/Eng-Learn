import asyncio
import logging
from datetime import datetime
from typing import Text
import aiogram
from aiogram.types import update
#from aiogram.dispatcher.filters import state
#from aiogram.dispatcher.filters import filters

#from attr import dataclass

import pytz
tz = pytz.timezone('Europe/Kiev')

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types.message import ContentType


import config
import keyboards as kb
import states
from db import DB, User, Word, Translator

db = DB()

#api_key = 'tr6v1Y7P2KibUWpv8LbXS707rxKcTcs8Dk62P3MDoia9'
#api_url = 'https://api.eu-gb.language-translator.watson.cloud.ibm.com/instances/0702e292-360c-4d11-9490-88fe47e4d4ca'

#translator = Translator(api_url, api_key)


global users
users = db.getAllUsers()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=config.API_TOKEN)
memory_storage = MemoryStorage()
dp = Dispatcher(bot, storage=memory_storage)


@dp.message_handler(commands=['start'], state="*")
async def send_welcome(message: types.Message, state=FSMContext):
    if db.getUser(message.from_user.id) != None:
        await message.answer('Для перезавантаження відкрий налаштування бота', reply_markup=kb.main_kb)
        await state.finish()
        return

    await message.answer("Hello!")
    await message.answer("Я — твій вчитель англійської в телеграмі")
    await message.answer("Використовуй кнопки для спілкування зі мною 👇👌", reply_markup=kb.greet_kb)

    await states.Regestration.waiting_for_greet.set()

@dp.message_handler(state=states.Regestration.waiting_for_greet)
async def ask_level(message: types.Message, state: FSMContext):
    await message.answer("Для початку вибери свій рівень 😉", reply_markup=kb.levels_kb)
    await states.Regestration.waiting_for_level.set()
    await state.update_data(update_time=False)


@dp.message_handler(state=states.Regestration.waiting_for_level)
async def ask_time(message: types.Message, state: FSMContext, content_types=types.ContentTypes.TEXT):
    if message.text not in kb.available_levels:
        await message.reply("Вибери рівень за допомогою клавіатури.")
        return
    await state.update_data(level=message.text)
    await message.answer('Great, коли тобі буде зручно вивчати слова? 📖', reply_markup=kb.time_kb)
    await states.Regestration.waiting_for_time.set()


@dp.message_handler(state=states.Regestration.waiting_for_time)
async def end_registration(message: types.Message, state: FSMContext, content_types=types.ContentType.TEXT):
    if message.text not in kb.available_time:
        await message.reply('Вибери за допомогою клавіатури.')
        return
    elif message.text == 'Інший час':
        await message.answer('О котрій займаємось?')
        await states.Regestration.waiting_for_user_time.set()
        return
    user_data = await state.get_data()
    if user_data['update_time'] == False:
        db.addUser(message.from_user, kb.available_levels.index(user_data['level']) + 1, message.text)
    else:
        db.updateTime(message.from_user.id, message.text)

    await state.finish()
    await message.answer('OK, good luck)', reply_markup=kb.main_kb)
    global users
    users = db.getAllUsers()

@dp.message_handler(state=states.Regestration.waiting_for_user_time)
async def end_registration_receive_user_time(message: types.Message, state: FSMContext, \
    content_types=types.ContentType.TEXT):

    user_data = await state.get_data()

    try:
        message.text.strip().split(':')[1] == message.text.strip().split(':')[1]
        #db.addUser(message.from_user, kb.available_levels.index(user_data['level']) + 1, message.text)
        tz.localize(datetime.strptime(message.text, "%H:%M"), is_dst=None).time().isoformat()
    except:
        await message.reply('Не розумію тебе 🤷‍♂️ Введи час\nПриклад: 22:00')
        return
    

    if user_data['update_time'] == False:
        db.addUser(message.from_user, kb.available_levels.index(user_data['level']) + 1, message.text)
    else:
        db.updateTime(message.from_user.id, message.text)
    

    await state.finish()
    await message.answer('OK, good luck)', reply_markup=kb.main_kb)
    global users
    users = db.getAllUsers()






@dp.message_handler(lambda message: message.text == kb.available_main_kb[0])
async def start_learning_words(message: types.Message, state: FSMContext, \
    content_types=types.ContentType.TEXT):

    user = db.getUser(message.from_user.id)

    if user == None:
        await message.answer('Щось пішло не так 😕, перезавантаж бота в налаштуваннях')
        return

    last_word = db.getLastWord(message)

    
    if db.getWord(last_word + 5, user.table) == None:
        await message.answer("Вітаю!!! 🎉🎉🎉")
        await message.answer("Ти пройшов всі слова на своєму рівні 👍")
        await message.answer("Вибирай наступний рівнь в налаштуваннях)")
        return


    word = db.getWord(last_word + 1 , user.table)

    await message.answer("Let's go! ✊")
    await message.answer("Вибирай нові слова, щоб додати їх для вивчення 😉")

    await word.send_new_word(message)

    await states.Learning_words.waiting_for_option.set()
    
    async with state.proxy() as data:
        data['words'] = [word]
        data['user'] = user


@dp.message_handler(state=states.Learning_words.waiting_for_option, text=[kb.availabe_learning_kb[0], kb.availabe_learning_kb[1]])
async def getting_learning_option(message:types.Message, state:FSMContext): 
    async with state.proxy() as data:
        if message.text == kb.availabe_learning_kb[1]:
            last_word = data['words'][-1]
            del data['words'][-1]
            await message.answer('Окей, пропустимо це слово 😉')
        else:

            if len(data['words'])>=5:
                db.addNewLearning(data)

                await message.answer('Perfect 👍')
                await message.answer('Тепер постарайся згадати значення пройдених слів')
                await message.answer('Вибирай відповідь з клавіатури 👇')
                
                data['revising_words'] = data['words'].copy()

                revising_word = data['revising_words'][0]
                await revising_word.send_revising_quiz(message, data)

                await states.Learning_words.waiting_for_word_translation.set()
                return


            last_word = data['words'][-1]

        word = db.getWord(last_word.word_id + 1 , data['user'].table)

        await word.send_new_word(message)
        data['words'].append(word)

        
@dp.message_handler(state=states.Learning_words.waiting_for_word_translation)
async def revise_learned_words(message:types.Message, state=FSMContext):
    async with state.proxy() as data:

        words_translations = []
        for word in data['words']:
            words_translations.append(word.translation)

        if message.text not in words_translations:
            await message.answer('Не розумію тебе 🤷‍♂️ Використовуй кнопки 👇😉')
            return
        

        if message.text == data['revising_words'][0].translation:
            await message.answer('Right 👍')
            del data['revising_words'][0]

            if len(data['revising_words']) == 0:
                await message.answer('Awesome 👍')
                if len(data['words']) == 5:
                    text = 'Ти закріпив 5 слів'
                else:
                    text = 'Ти закріпив слова'
                await message.answer(text, reply_markup=kb.main_kb)
                await state.finish()
                return

            revising_word = data['revising_words'][0]

            await revising_word.send_revising_quiz(message, data)

            
        else:
            revising_word = data['revising_words'][0]
            await revising_word.send_revision_for_incorrect(message)
            
            del data['revising_words'][0]
            data['revising_words'].append(revising_word)
            await states.Learning_words.waiting_for_confirmation.set()
            

        
@dp.message_handler(state=states.Learning_words.waiting_for_confirmation, content_types=ContentType.ANY)
async def send_next_word_after_confimation(message: types.Message, state=FSMContext):
    async with state.proxy() as data:
        revising_word = data['revising_words'][0]
        await revising_word.send_revising_quiz(message, data)

        await states.Learning_words.waiting_for_word_translation.set()

@dp.message_handler(state=states.Learning_words.waiting_for_confirmation_2, content_types=ContentType.ANY)
async def send_next_word_after_confimation_2(message: types.Message, state=FSMContext):
    async with state.proxy() as data:
        revising_word = data['revising_words'][0]
        await revising_word.send_revising_quiz_2(message, data)

        await states.Learning_words.waiting_for_eng_word.set()





@dp.message_handler(text = [kb.availabe_learning_kb[2], kb.cancel_button], state='*')
async def go_to_main_menu(message:types.Message, state=FSMContext):
    await message.answer('Окей, чекаю тебе в будь-який час ✨', reply_markup=kb.main_kb)
    await state.finish()



@dp.message_handler(state=states.Learning_words.waiting_for_eng_word)
async def revise_learned_words_type2(message:types.Message, state=FSMContext):
    async with state.proxy() as data:
        eng_words = []
        for word in data['words']:
            eng_words.append(word.eng_word)

        if message.text not in eng_words:
            await message.answer('Не розумію тебе 🤷‍♂️ Використовуй кнопки 👇😉')
            return
        
        if message.text == data['revising_words'][0].eng_word:
            await data['revising_words'][0].send_voice(message)
            await message.answer('Right 👍')
            del data['revising_words'][0]

            if len(data['revising_words']) == 0:
                await message.answer('Awesome 👍')
                await message.answer('Ти закріпив 5 слів', reply_markup=kb.main_kb)
                await state.finish()
                return

            revising_word = data['revising_words'][0]

            await revising_word.send_revising_quiz_2(message, data)

            
        else:
            revising_word = data['revising_words'][0]
            await revising_word.send_revision_for_incorrect(message)
            
            del data['revising_words'][0]
            data['revising_words'].append(revising_word)
            await states.Learning_words.waiting_for_confirmation_2.set()



@dp.callback_query_handler(state=states.Second_revision.waiting_for_confirmation)
async def process_callback_confirmation(callback_query: types.CallbackQuery, state=FSMContext):

    await bot.answer_callback_query(callback_query.id)

    if callback_query.data == 'true':
        await bot.edit_message_text(text='Повторення пройдених слів 📘', chat_id=callback_query.message.chat.id, 
                                message_id=callback_query.message.message_id, reply_markup=kb.ReplyKeyboardMarkup())
        
        await callback_query.message.answer('Вибирай відповідь з клавіатури 👇')
                
        async with state.proxy() as data:
            data['revising_words'] = data['words'].copy()
            revising_word = data['revising_words'][0]
            await revising_word.send_revising_quiz(callback_query, data)

        await states.Learning_words.waiting_for_word_translation.set()

    else:
        async with state.proxy() as data:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=data['prev_m_id'])
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await state.finish()



@dp.callback_query_handler()
async def process_callback_button(callback_query: types.CallbackQuery, state=FSMContext):
    await bot.answer_callback_query(callback_query.id)

    user = db.getUser(callback_query.from_user.id)

    if callback_query.data in ['true', 'false']:
        return

    stage = callback_query.data.split('_')[0]
    w_id = callback_query.data.split('_')[1]
    table = callback_query.data.split('_')[2]


    if table != user.table_id and table != 'u':
        await callback_query.message.answer('❌ Ти не можеш повторити слова із минулого рівня')
        return

    if table == 'u':
        global_table = 'user_words'
        from_table = 'user_words'
    else:
        global_table = 'all'
        from_table = user.table

    if user.keyboards_data[global_table][stage][w_id]['usd'] == True:
        prev_message = await callback_query.message.answer('Ти вже вивчив цей набір слів ✅')
        await callback_query.message.answer('Повторити знову?', reply_markup=kb.confirmation_kb)
        async with state.proxy() as data:
            data['words'] = user.keyboards_data[global_table][stage][w_id]['words'].copy()
            for i in range(len(data['words'])):
                data['words'][i] = db.getWord(data['words'][i], user.table)
            data['prev_m_id'] = prev_message.message_id
        await states.Second_revision.waiting_for_confirmation.set()
        return

    

    async with state.proxy() as data:
        data['words'] = user.keyboards_data[global_table][stage][w_id]['words'].copy()

        for word in range(len(data['words'])):
            data['words'][word] = db.getWord(data['words'][word], from_table)

        data['revising_words'] = data['words'].copy()

        revising_word = data['revising_words'][0]

        await bot.send_message(callback_query.from_user.id, 'Тепер постарайся згадати значення пройдених слів')
        await bot.send_message(callback_query.from_user.id, 'Вибирай відповідь з клавіатури 👇')

        if stage == '1' or stage == '3':
            await revising_word.send_revising_quiz(callback_query, data)
            await states.Learning_words.waiting_for_word_translation.set()
        else:
            await revising_word.send_revising_quiz_2(callback_query, data)
            await states.Learning_words.waiting_for_eng_word.set()

        
        
    user.move_next_stage(stage, w_id, global_table)
    






@dp.message_handler(text=[kb.available_main_kb[2]])
async def start_adding_words(message: types.Message):
    await message.answer('Додай власні слова у персональний словник 🙌', reply_markup=kb.cancel_kb)
    await message.answer('Відправ мені список англійських слів через кому')
    await states.Adding_words.waiting_for_words.set()


async def detect(text, alphabet=set('abcdefghijklmnopqrstuvwxyz,')):
    return not alphabet.isdisjoint(text.lower())

@dp.message_handler(state=states.Adding_words.waiting_for_words)
async def confirm_user_words(message:types.Message, state=FSMContext):
    text = message.text.lower()

    if not await detect(text):
        await message.reply('Введіть слова на англійській мові', reply_markup=kb.cancel_kb)
        return
    
    words:list = []

    text = text.split(',')

    for i in text:
        if len(i) == 0:
            await message.reply('Перевір правильність написання')
            return

    if len(text) < 3:
        await message.answer('📕 Введи мінімум три слова')
        return

    for i in range(len(text)):
        text[i] = text[i].strip().capitalize()
        words.append(Word(eng_word=text[i].capitalize()))
        
    
    async with state.proxy() as data:
        data['words'] = words.copy()
        data['i'] = 0
        data['user'] = db.getUser(message.from_user.id)
        word:Word = data['words'][0]

    await bot.send_message(text=f'📖 Напиши переклад для слова *{word.eng_word}*', parse_mode='Markdown',
                                chat_id=message.chat.id, reply_markup=kb.InlineKeyboardMarkup())

    await states.Adding_words.waiting_for_user_translation.set()
        
  

@dp.message_handler(state = states.Adding_words.waiting_for_user_translation)
async def add_user_translation(message:types.Message, state=FSMContext):

    translation = message.text.capitalize()
    
    async with state.proxy() as data:
        data['words'][data['i']].translation = translation
        word = data['words'][data['i']]

        await message.answer(text=f'📙 *{word.eng_word}* – {word.translation}', parse_mode='Markdown')

        if data['i'] + 1 <= len(data['words']) - 1:
            data['i'] += 1
        else:

            await states.Learning_words.waiting_for_word_translation.set()

            _words = db.addNewUserWords(data['words'], data['user'])
                
            data['words'] = _words

            await message.answer('Тепер постарайся згадати значення пройдених слів')
            await message.answer('Вибирай відповідь з клавіатури 👇')
                            
            data['revising_words'] = data['words'].copy()

            revising_word = data['revising_words'][0]

            await revising_word.send_revising_quiz(message, data)

            return

        
        word = data['words'][data['i']]

        await bot.send_message(text=f'📖 Напиши переклад для слова *{word.eng_word}*', parse_mode='Markdown',
                                    chat_id=message.chat.id, reply_markup=kb.InlineKeyboardMarkup())



@dp.message_handler(text=[kb.available_main_kb[1]])
async def get_progress(message:types.Message):
    user:User = db.getUser(message.from_user.id)
    all_learned, in_5_days, practice_days, continious = user.get_progress()
    await message.answer(f'📚 Словниковий запас: +{all_learned} слів\n📊 Нових слів за 5 днів: +{in_5_days} слів\n\
📅 Днів практики: {practice_days}\n🏆 Безперервна серія: {continious}')



@dp.message_handler(text=[kb.available_main_kb[4]])
async def settings(message:types.Message):
    await message.answer('Налаштування ⚙️', reply_markup=kb.settings_kb)
    await message.answer('Вибирай з клавіатури')
    await states.Settings.in_settings.set()




@dp.message_handler(state=states.Settings.in_settings, text=[kb.available_settings_kb[0]])
async def change_time(message:types.Message, state=FSMContext):
    await state.update_data(level=kb.available_levels[int(db.getUser(message.from_user.id).table_id) - 1], update_time=True)
    await message.answer('Great, коли тобі буде зручно вивчати слова? 📖', reply_markup=kb.time_kb)
    await states.Regestration.waiting_for_time.set()



@dp.message_handler(state=states.Settings.in_settings, text=[kb.available_settings_kb[1]])
async def change_level(message:types.Message):
    level=kb.available_levels[int(db.getUser(message.from_user.id).table_id) - 1]
    await message.answer(f'Твій рівень – {level}')
    await message.answer('Увага!')
    await message.answer('Після зміни рівня весь минулий прогрес буде недоступний ❌')
    await message.answer('Підтвердити ?', reply_markup=kb.confirmation_kb)
    await states.Settings.level_change_confirmation.set()



@dp.callback_query_handler(state=states.Settings.level_change_confirmation)
async def confirmation_level_changing(c:types.CallbackQuery, state=FSMContext):
    await bot.answer_callback_query(c.id)
    await bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=kb.InlineKeyboardMarkup())
    if c.data == 'true':
        await c.message.answer("Вибери свій рівень 😉", reply_markup=kb.levels_kb)
        await states.Settings.waiting_for_level.set()
    else:
        await c.message.answer('Ok', reply_markup=kb.main_kb)
        await state.finish()  


@dp.message_handler(state=states.Settings.waiting_for_level)
async def get_level(message: types.Message, state: FSMContext, content_types=types.ContentTypes.TEXT):
    if message.text not in kb.available_levels:
        await message.reply("Вибери рівень за допомогою клавіатури.")
        return

    db.updateLevel(message.from_user.id, message.text)
    await message.answer(f'Great! Твій новий рівень – {message.text}', reply_markup=kb.main_kb)
    await state.finish()
    global users
    users = db.getAllUsers()



@dp.message_handler(state=states.Settings.in_settings, text=[kb.available_settings_kb[2]])
async def reload_bot_confirmation(message:types.Message):
    await message.answer('Увага!')
    await message.answer('Після перезавантаження весь минулий прогрес буде недоступний ❌')
    await message.answer('Підтвердити ?', reply_markup=kb.confirmation_kb)
    await states.Settings.reload_confirmation.set()



@dp.callback_query_handler(state=states.Settings.reload_confirmation)
async def reload_bot(c:types.CallbackQuery, state=FSMContext):
    await bot.answer_callback_query(c.id) 
    await bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=kb.InlineKeyboardMarkup())
    if c.data == 'true':
        db.remove_user(c.from_user.id)
        await send_welcome(c.message)
    else:
        await c.message.answer('Ok', reply_markup=kb.main_kb)
        await state.finish()  


@dp.message_handler(state=states.Settings.in_settings, text=[kb.available_settings_kb[3]])
async def support(message:types.Message):
    await message.answer('Great 💪')
    await message.answer(f'Якщо у тебе проблеми з ботом, або якщо ти маєш ідеї щодо його покращення, напиши про це \
[розробнику](tg://user?id=663493008) 👨🏼‍💻\n\nТвій id: `{message.from_user.id}`', parse_mode='markdown')


@dp.message_handler(state=states.Settings.in_settings, text=[kb.available_settings_kb[4]])
async def main_menu(message:types.Message, state=FSMContext):
    await message.answer('Головне меню ✅', reply_markup=kb.main_kb)
    await state.finish()


@dp.message_handler(text=[kb.available_main_kb[3]])
async def soon(message:types.Message):
    await message.answer('Скоро... ✨')


@dp.message_handler(commands=['clear'])
async def clear(message: types.Message):
    await message.answer('Keyboards cleared', reply_markup=kb.ReplyKeyboardRemove())    


@dp.message_handler(commands=['a'])
async def test(message: types.Message):
    await send_revision(db.getUser(message.from_user.id))


@dp.message_handler(commands=['send_all'])
async def send_all(message: types.Message):
    if message.from_user.id != config.admin_id:
        return
    await message.answer('Enter text')
    await states.Admin_functions.waiting_for_mailing_text.set()

@dp.message_handler(state=states.Admin_functions.waiting_for_mailing_text)
async def mail_text(message: types.Message, state=FSMContext):
    text = message.text
    if text == '/cancel':
        await state.finish()
        await message.answer('Canceled')
        return

    global users
    for user in users:
        try:
            await bot.send_message(user.user_id, text)
        except aiogram.utils.exceptions.BotBlocked:
            print(f'Error: {user.first_name} ({user.user_id}) has blocked bot')
            db.remove_user(user.user_id)
    await message.answer('Finished')
    await state.finish()


@dp.message_handler(content_types=ContentType.ANY)
async def handle_all_in_main(message:types.Message):
    await message.answer('Не розумію тебе 🤷‍♂️ Використовуй кнопки 👇😉', reply_markup=kb.main_kb)


@dp.message_handler(content_types=ContentType.ANY, state='*')
async def handle_any_stuff(message: types.Message, state=FSMContext):
    keyboard = None

    if await state.get_state() == 'Learning_words:waiting_for_option':
        keyboard = kb.learning_kb

    await message.answer('Не розумію тебе 🤷‍♂️ Використовуй кнопки 👇😉', reply_markup=keyboard)
    

async def send_revision(user:User):
    keyboards = kb.get_periods_inline_kb(user)

    if keyboards == None:
        await bot.send_message(user.user_id, '👋 Час додати нові слова у твій словниковий запас\n\n✅ Натискай кнопку "Вчити слова"')
        return
    
    await bot.send_message(user.user_id, "💪 Час повторити слова\n\n\
Повертайся до цього повідомлення будь-коли та запускай тренування – кнопки активні завжди.\n\nПовторюй слова вивчені в ці періоди. \
В дужках вказано стадію вивчення.\n📘 – Слова з твого рівня\n📕 – Слова з персонального словника\n\n\
Які із них ти ще пам'ятаєш? 👇", reply_markup=keyboards)


async def periodic(sleep_for):
    global users
    while True:
        for user in users:
            if await user.check_learning_time() == True:
                try:
                    await send_revision(db.getUser(user.user_id))
                except aiogram.utils.exceptions.BotBlocked:
                    print(f'Error: {user.first_name} ({user.user_id}) has blocked bot')
                    db.remove_user(user.user_id)

        await asyncio.sleep(sleep_for)
            


if __name__ == '__main__':
    #executor.start_polling(dp, skip_updates=True)
    dp.loop.create_task(periodic(30))
    executor.start_polling(dp, skip_updates=True)
