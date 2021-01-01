import sqlite3
import datetime
from aiogram import types, Bot
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
import json
from aiogram.types import audio
from attr import dataclass
#from gtts import gTTS 
import requests
import os

from ibm_watson import LanguageTranslatorV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from time import time

from aiogram.types import message
from requests.sessions import session
import keyboards as kb
import config
import pytz

tz = pytz.timezone('Europe/Kiev')

bot = Bot(token=config.API_TOKEN)

class User:
    def __init__(self, user_id, first_name, table_id, learning_time, learned_words, for_revision, keyboards_data):
        self.user_id = user_id
        self.first_name = first_name
        self.table_id = str(table_id)
        #datetime.datetime.strptime(learning_time, "%H:%M:%S")
        self.learning_time = tz.localize(datetime.datetime.strptime(learning_time, "%H:%M:%S"), is_dst=None).time()
        #self.learned_words = learned_words
        if for_revision == None or len(for_revision) == 0:
            self.for_revision = {'all':{"1":{}, "2":{}, "3":{}, "4":{}}, 'user_words':{"1":{}, "2":{}, "3":{}, "4":{}}}
        else:
            self.for_revision = json.loads(for_revision)

        self._sent = False

        if learned_words == None or len(learned_words) == 0:
            self.learned_words = {'all':[], 'user_words':[]}
        else:
            self.learned_words = json.loads(learned_words)


        if keyboards_data == None or len(keyboards_data) == 0:
            self.keyboards_data = {'all':{"1":{}, "2":{}, "3":{}, "4":{}}, 'user_words':{"1":{}, "2":{}, "3":{}, "4":{}}}
        else:
            self.keyboards_data = json.loads(keyboards_data)


        self.table = User.get_table(table_id)

    @staticmethod
    def get_table(table_id):
        if table_id == '1':
            return 'words_a1'
        elif table_id == '2':
            return 'words_a2'
        elif table_id == '3':
            return 'words_b1'
        elif table_id == '4':
            return 'words_b2'


    #def check....
    async def check_learning_time(self):
        _now = datetime.datetime.now(tz)

        if self.learning_time.hour == _now.hour and self.learning_time.minute == _now.minute:
            if self._sent == False:
                self._sent = True

                return True

        if self._sent == True:
            _difference = _now - datetime.timedelta(minutes=1)
            if _difference.time() > self.learning_time:
                self._sent = False
###########!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    def move_next_stage(self, stage, w_id, global_table):
        try:
            next_w_id = str(int(list(self.for_revision[global_table][str(int(stage) + 1)].keys())[-1]) + 1)
        except:
            next_w_id = '1'

        prev_learning = self.for_revision[global_table][stage].pop(w_id) 
        prev_learning_kb = self.keyboards_data[global_table][stage][w_id].copy()
        #prev_learning = self.for_revision['all'][stage][w_id].copy()
        self.keyboards_data[global_table][stage][w_id]['usd'] = True
        #next_id = 
        
        if int(stage) + 1 <= 4:
            self.for_revision[global_table][str(int(stage) + 1)][next_w_id] = prev_learning
            self.keyboards_data[global_table][str(int(stage) + 1)][next_w_id] = prev_learning_kb.copy()

        DB.execute(DB(), 'UPDATE users SET for_revision=:for_revision, kb_data=:kb_data WHERE id=:user_id', \
            {'for_revision': json.dumps(self.for_revision), 'kb_data': json.dumps(self.keyboards_data), 'user_id': self.user_id}, True)


    def get_progress(self):
        all_learned = len(self.learned_words['all']) * 5
        for learning in self.learned_words['user_words']:
            all_learned += len(learning['words'])

        if all_learned == 0:
            return 0, 0, 0, 0
        #date = tz.localize(datetime.datetime.now(), is_dst=None).strftime('%d.%m.%y')
        #learning_time = tz.localize(datetime.datetime.strptime(learning_time, "%H:%M:%S"), is_dst=None).time()
        now = datetime.datetime.now(tz)
        in_5_days = 0

        learnings_all = self.learned_words['all'].copy()
        learnings_all.reverse()

        #last_day = now - datetime.timedelta(days=5)

        for learning in learnings_all:
            learning_date = tz.localize(datetime.datetime.strptime(learning['date'], '%d.%m.%y'), is_dst=None)
            if now - learning_date < datetime.timedelta(days=6):
                in_5_days += 5
            else:
                break

        user_learnings = self.learned_words['user_words'].copy()
        user_learnings.reverse()

        for learning in user_learnings:
            learning_date = tz.localize(datetime.datetime.strptime(learning['date'], '%d.%m.%y'), is_dst=None)
            if now - learning_date < datetime.timedelta(days=6):
                in_5_days += len(learning['words'])
            else:
                break

        learning_dates = []
        for learning in learnings_all:
            date = datetime.datetime.strptime(learning['date'], '%d.%m.%y')
            if date not in learning_dates:
                learning_dates.append(date)

        for learning in user_learnings:
            date = datetime.datetime.strptime(learning['date'], '%d.%m.%y')
            if date not in learning_dates:
                learning_dates.append(date)

        learning_dates.sort(reverse=True)

        practice_days = len(learning_dates)
        
        if now - tz.localize(learning_dates[0]) > datetime.timedelta(days=1):
            continious = 0
        else:
            continious = 1
            for i in range(1, len(learning_dates)):
                if learning_dates[i - 1] - learning_dates[i] > datetime.timedelta(days=1):
                    break
                else:
                    continious += 1

        return all_learned, in_5_days, practice_days, continious



class Word:
    def __init__(self, word_id=None, eng_word=None, translation=None, pronunciation=None, file_id=None, table=None):
        self.word_id = word_id
        self.eng_word = eng_word
        self.translation = translation
        self.pronunciation = pronunciation
        self.file_id = file_id
        self.table = table


    async def send_new_word(self, message:types.Message):
        await bot.send_message(message.from_user.id, f'📖 *{self.eng_word}* – {self.translation}', parse_mode='Markdown', reply_markup=kb.learning_kb)
        await self.send_voice(message)
    

    async def send_voice(self, message:types.Message):
        if self.file_id != None and len(self.file_id) > 0:
            await bot.send_voice(message.from_user.id, self.file_id)
        else:

            audio = types.InputFile(self.pronunciation)    
            msg = await bot.send_voice(message.from_user.id, audio)
            file_id = msg.voice.file_id
            DB.execute(DB(), f'UPDATE {self.table} SET File_id=:file_id WHERE Word_id =:word_id', 
                        {"file_id":file_id, "word_id":self.word_id},
                        commit=True)


    async def send_revising_quiz(self, message:types.Message, data):
        await bot.send_message(message.from_user.id, f'*{self.eng_word}*', parse_mode='Markdown', 
                            reply_markup=kb.get_revising_kb(data['words'], data['revising_words'][0]))
        await self.send_voice(message)

    #for 2 and 4 stage:
    async def send_revising_quiz_2(self, message:types.Message, data):
        await bot.send_message(message.from_user.id, f'*{self.translation}*', parse_mode='Markdown', 
                            reply_markup=kb.get_revising_kb_2(data['words'], data['revising_words'][0]))
        


    async def send_revision_for_incorrect(self, message:types.Message):
        await message.answer('Не зовсім 🤔')
        await bot.send_message(message.from_user.id, f'*{self.eng_word}* – {self.translation}', parse_mode='Markdown', 
                            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).row(KeyboardButton('Зрозумів, йдемо далі ✊')))
        await self.send_voice(message)



class DB:

    def execute(self, query, params={}, commit=False):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute(query, params)
        if commit:
            conn.commit()

        result = c.fetchall()    
        conn.close()
        return result


    def getUser(self, user_id):
        result = self.execute('select * from users where id=:user_id', {"user_id":user_id})
        if result:
            result = result[0]
            return User(result[0], result[1], result[2], result[3], result[4], result[5], result[6])
        else:
            return None


    def getAllUsers(self):
        result = self.execute('select * from users')

        users = []

        for user in result:
            users.append(User(user[0], user[1], user[2], user[3], user[4], user[5], user[6]))
            
        return users



    def addUser(self, tg_user: types.User, level='', learning_time=''):
            #learning_datetime = datetime.datetime.strptime(learning_time, "%H:%M")
        self.execute('insert or ignore into users(id, first_name, level, learning_time, reg_data) values(:id, :first_name, :level, :learning_time, :reg_data)', {
            "id": tg_user.id,
            "first_name": tg_user.first_name,
            "level": level,
            "learning_time": tz.localize(datetime.datetime.strptime(learning_time, "%H:%M"), is_dst=None).time().isoformat(),
                #"learning_time": datetime.datetime.strptime(learning_time, "%H:%M").time().strftime("%H:%M"),
                #"learning_time": datetime.datetime.strptime(learning_time, "%H:%M").time().isoformat(timespec='minutes'),
            "reg_data": tz.localize(datetime.datetime.now(), is_dst=None).isoformat()
        }, True)


    
    def updateTime(self, user_id, learning_time):
        self.execute('UPDATE users SET learning_time =:learning_time WHERE id=:user_id',
        {'learning_time':tz.localize(datetime.datetime.strptime(learning_time, "%H:%M"), is_dst=None).time().isoformat(),
        'user_id':user_id}, True)


    def updateLevel(self, user_id, new_level):
        user = self.getUser(user_id)
        learned = user.learned_words
        for_revision = user.for_revision
        kb_data = user.keyboards_data

        learned['all'] = []
        for_revision['all'] = {"1":{}, "2":{}, "3":{}, "4":{}}
        kb_data['all'] = {"1":{}, "2":{}, "3":{}, "4":{}}
        self.execute("UPDATE users SET level =:new_level, learned_words=:learned, for_revision=:for_revision, kb_data=:kb_data WHERE id=:user_id",
        {'new_level':kb.available_levels.index(new_level) + 1,'learned': json.dumps(learned), 
        'for_revision':json.dumps(for_revision), 'kb_data':json.dumps(kb_data), 'user_id':user_id}, True)


    def remove_user(self, user_id):
        self.execute("DELETE FROM users WHERE id=:user_id", {'user_id':user_id}, True)


    def getLastWord(self, message: types.Message):

        user = self.getUser(message.from_user.id)

        if user == None:
            return None

        if user.learned_words['all'] == [] or len(user.learned_words) == 0:
            return 0

        words_info = user.learned_words
        
        last_word = words_info["all"][-1]["words"][-1]
        
        return last_word
        


    def getWord(self, word_id, table):
        
        result = self.execute(f'select * from {table} where Word_id=:word_id', {"word_id": word_id})

        if result:
            result = result[0]
            return Word(result[0], result[1], result[2], result[3], result[4], table)
        else:
            return None



    def getWordId(self, eng_word, translation, table):
        result = self.execute(f'select Word_id from {table} where Word=:word AND Translation=:translation', 
                                {"word": eng_word, "translation":translation})
        if result:

            return result[0][0]
        else:
            return None



    def addNewLearning(self, data, user_words=False):
        user:User = data['user']

        words_numbers = []
        for word in data['words']:
            words_numbers.append(word.word_id)
        
        date = tz.localize(datetime.datetime.now(), is_dst=None).strftime('%d.%m.%y')

        learned_words = user.learned_words

        new_learning = {'date':date, 'words':words_numbers}
        new_kb_data = {'usd':False, 'words':words_numbers}
        
        if user_words == True:
            table = 'user_words'
        else:
            table = 'all'

        learned_words[table].append(new_learning)
        learned_json = json.dumps(learned_words)

        try:
            next_kb_id = str(int(list(user.keyboards_data[table]['1'].keys())[-1]) + 1)
        except IndexError:
            next_kb_id = '1'

        kb_data = user.keyboards_data
        kb_data[table]['1'][next_kb_id] = new_kb_data
        kb_json = json.dumps(kb_data)

        for_revision = user.for_revision
        for_revision[table]['1'][next_kb_id] = new_learning
        revision_json = json.dumps(for_revision)



        self.execute('UPDATE users SET learned_words=:learned_words, for_revision=:for_revision, kb_data=:kb_data WHERE id=:user_id', \
            {'learned_words':learned_json, 'for_revision':revision_json, 'kb_data': kb_json, 'user_id': user.user_id}, True)

        #{"all":{"1": "1":{"date":"05.09.20", "words":[1, 2, 3, 4, 5]}}}}

    def addNewUserWords(self, words, user:User):
        _words:list = []

        for word in words:
            filename = os.path.join('User_words_pronunciation/', word.eng_word + '.mp3')

            if not os.path.exists(filename):
                audio = Translator.get_audio(word.eng_word)
                with open(filename, 'wb') as _file:
                    _file.write(audio)

            word.pronunciation = filename
            word_id = self.getWordId(word.eng_word, word.translation, table='user_words')

            if word_id == None:
                self.execute('INSERT INTO user_words(Word, Translation, Pronunciation) VALUES (:word, :translation, :pronunciation)',
                                    {'word':word.eng_word, 'translation':word.translation, 'pronunciation':word.pronunciation}, commit=True)

                word_id = self.getWordId(word.eng_word, word.translation, table='user_words')

            _words.append(Word(word_id, word.eng_word, word.translation, word.pronunciation, table='user_words'))


        data = {'user': user, 'words':_words}
        self.addNewLearning(data, user_words=True)    

        return data['words']



    def addNewKbData(self, data, user:User):
        data_json = json.dumps(data)
        self.execute('UPDATE users SET keyboards_data=:keyboards_data WHERE id=:user_id', \
            {'keyboards_data':data_json,'user_id': user.user_id}, True)






class Translator:
    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key
        authenticator = IAMAuthenticator(api_key)
        self.language_translator = LanguageTranslatorV3(
            version='2018-05-01',
            authenticator=authenticator
        )
        self.language_translator.set_service_url(url)

    def translate(self, text, lang='en-uk'):
        translation = self.language_translator.translate(
            text=text,
            model_id=lang).get_result()
        return translation['translations'][0]['translation']

    @staticmethod
    def get_audio(text):
        r = requests.get(f'http://translate.google.com/translate_tts?ie=UTF-8&total=1&idx=0&textlen=32&client=tw-ob&q={text}&tl=En-gb')
        return r.content