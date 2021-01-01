from aiogram.dispatcher.filters.state import State, StatesGroup

class Regestration(StatesGroup):
    waiting_for_greet = State()
    waiting_for_level = State()
    waiting_for_time = State()
    waiting_for_user_time = State()

class Learning_words(StatesGroup):
    waiting_for_option = State()
    #for revisng by eng word:
    waiting_for_word_translation = State()
    waiting_for_confirmation = State()  #for confirmation incorrect word
    #for revisng by translation:
    waiting_for_eng_word = State()
    waiting_for_confirmation_2 = State()

class Second_revision(StatesGroup):
    waiting_for_confirmation = State()

class Adding_words(StatesGroup):
    waiting_for_words = State()
    waiting_for_user_translation = State()


class Settings(StatesGroup):
    in_settings = State()
    level_change_confirmation = State()
    waiting_for_level = State()
    reload_confirmation = State()

class Admin_functions(StatesGroup):
    waiting_for_mailing_text = State()