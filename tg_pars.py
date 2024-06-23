# To change the category for the bot, it is important to change the words in the "category_main" and "category" 
# Change the token of the new chat
# Create a new database to store keys and users for a specific bot of a specific category
# After creating the database - mark the name on page 59 (engine = create_engine('sqlite:///marketing_base.db', echo=True)) - replace sqlite:///new_name.db

import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import create_engine, Column, Integer, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from aiohttp import ClientSession
import subprocess
import json
import sqlite3
import hashlib

# The main category of vacancies
category_main = 'Маркетинг'
category = ['Маркетинг', 'Marketing']
# TOKEN
TOKEN = '7372220700:AAESVJJv4Y4rD8flkUsKY-N1g0kKcnkAJ_c'

# Logging setup
logging.basicConfig(level=logging.INFO)

# Bot setup
bot = Bot(token=TOKEN)
dp_aiogram = Dispatcher(bot=bot)

# Database setup
Base = declarative_base()

# Association table for many-to-many relationship between User and Keywords
user_keywords_association = Table(
    'user_keywords', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('keyword_id', Integer, ForeignKey('keywords_in_chat.id'))
)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Text, unique=True, nullable=False)
    user_name = Column(Text, unique=False, nullable=True)
    first_name = Column(Text, unique=False, nullable=True)
    last_name = Column(Text, unique=False, nullable=True)
    keywords = relationship("Keyword", secondary=user_keywords_association, back_populates="users")

class Keyword(Base):
    __tablename__ = 'keywords_in_chat'
    id = Column(Integer, primary_key=True)
    keyword = Column(Text, unique=False, nullable=False)
    users = relationship("User", secondary=user_keywords_association, back_populates="keywords")
    
engine = create_engine('sqlite:///marketing_base.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

# Create tables
Base.metadata.create_all(engine)

# create keyboard
key_keys = types.InlineKeyboardButton(text='Ключи', callback_data='keys')
key_vacancies = types.InlineKeyboardButton(text='Поиск вакансий', callback_data='vacancies')

main_menu_builder = types.InlineKeyboardMarkup(inline_keyboard=[
    [key_keys],
    [key_vacancies]
])

# saving states
class States(StatesGroup):
    add_keyword = State()
    delete_keyword = State()

# Dictionary for storing tasks for sending vacancies to users
user_tasks = {}
# Dictionary for storing submitted vacancies (by hashes for each user)
user_sent_posts = {}

# hande the command /start
@dp_aiogram.message(Command('start'))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    user_name = message.from_user.first_name
    user_last_name = message.from_user.last_name

    # stopin active task if we have
    if user_id in user_tasks:
        user_tasks[user_id].cancel()
        del user_tasks[user_id]

    await state.clear()
    user = session.query(User).filter_by(user_id=user_id).first()
    if not user:
        user = User(user_id=user_id, user_name=username, first_name=user_name, last_name=user_last_name)
        session.add(user)
        session.commit()
    await message.answer(f'Здравствуйте, {message.from_user.first_name}! Я ваш бот для мониторинга вакансий в категории {category_main}. \
        Вы также можете добавить ключевые слова, нажав на кнопку - <b>Ключи</b>, чтобы я отбирал вакансии более точно. \
        Если вы хотите, чтобы я присылал список вакансий автоматически, нажмите на <b>Поиск вакансий</b>.', \
                            parse_mode='HTML', reply_markup=main_menu_builder)

######################################################### KEYS #########################################################
# menu for keys
@dp_aiogram.callback_query(lambda c: c.data == 'keys')
async def process_keys(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    keyboard = []
    for keyword in user.keywords:
        keyboard.append([types.InlineKeyboardButton(text=keyword.keyword, callback_data=f'keyword_{keyword.id}')])
    keyboard.append([
        types.InlineKeyboardButton(text="\U00002795 Добавить слово", callback_data='add_keyword'),
        types.InlineKeyboardButton(text="\U00002796 Удалить слово", callback_data='delete_keyword')
    ])
    keyboard.append([types.InlineKeyboardButton(text="\U00002B05 Назад", callback_data='main_menu')])
    inline_kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback_query.message.edit_text('Ключи:', reply_markup=inline_kb)
    await state.clear()

# add key and save in database
@dp_aiogram.callback_query(lambda c: c.data == 'add_keyword')
async def add_keyword(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text('Введите ключевое слово для добавления:')
    await state.set_state(States.add_keyword)

@dp_aiogram.message(States.add_keyword)
async def process_add_keyword(message: types.Message, state: FSMContext):
    keyword_text = message.text
    user_id = message.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    keyword = session.query(Keyword).filter_by(keyword=keyword_text).first()
    if not keyword:
        keyword = Keyword(keyword=keyword_text)
    user.keywords.append(keyword)
    session.commit()
    await message.answer(f'Ключевое слово "{keyword_text}" добавлено.', reply_markup=main_menu_builder)
    await state.clear()

# delete key and delete from db
@dp_aiogram.callback_query(lambda c: c.data == 'delete_keyword')
async def delete_keyword(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    keyboard = []
    for keyword in user.keywords:
        keyboard.append([types.InlineKeyboardButton(text=keyword.keyword, callback_data=f'delete_{keyword.id}')])
    keyboard.append([types.InlineKeyboardButton(text="\U00002B05 Назад", callback_data='main_menu')])
    inline_kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback_query.message.edit_text('Выберите ключевое слово для удаления:', reply_markup=inline_kb)
    await state.set_state(States.delete_keyword)

@dp_aiogram.callback_query(lambda c: c.data.startswith('delete_'))
async def process_keyword_deletion(callback_query: types.CallbackQuery, state: FSMContext):
    keyword_id = int(callback_query.data.split('_')[1])
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    keyword_entry = session.query(Keyword).filter_by(id=keyword_id).first()
    if keyword_entry in user.keywords:
        user.keywords.remove(keyword_entry)
        session.commit()
        await callback_query.message.answer(f'Ключевое слово "{keyword_entry.keyword}" удалено.', reply_markup=main_menu_builder)
    else:
        await callback_query.message.answer(f'Ключевое слово не найдено.', reply_markup=main_menu_builder)
    await state.clear()

############################################ PARSING ###########################################################################
@dp_aiogram.callback_query(lambda c: c.data == 'vacancies')
async def process_vacancies(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    user_keywords = [keyword.keyword.lower() for keyword in user.keywords]

    await callback_query.message.answer('Начинаю поиск вакансий...')
    # Создаем задачу и сохраняем ее
    task = asyncio.create_task(check_and_send_posts(callback_query.message.chat.id, user_keywords))
    user_tasks[user_id] = task
    await task

# save post in txt file
async def collect_posts(channel):
    posts = []
    try:
        with open(f"{channel}.txt") as file:
            lines = file.readlines()
        for line in lines:
            data = json.loads(line)
            links = [link for link in data['outlinks'] if channel not in link]
            post_content = str(data['content']) + '\n\n' + ' '.join(links)
            posts.append(post_content)
    except Exception as e:
        print(f"Error reading posts for channel {channel}: {e}")
    return posts

# upload post from our txt file
async def upload_posts(num_posts, channel):
    try:
        command = f"snscrape --max-results {num_posts} --jsonl telegram-channel {channel} > {channel}.txt"
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running snscrape for channel {channel}: {e}")

# take channel from our database
async def get_channels():
    conn = sqlite3.connect('base.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_username FROM chats")
    channels = cursor.fetchall()
    conn.close()
    return [channel[0] for channel in channels]

def hash_post(post):
    return hashlib.sha256(post.encode()).hexdigest()

# control and send post to user
async def check_and_send_posts(chat_id, user_keywords):
    channels = await get_channels()
    user_id = chat_id  # Assuming chat_id is the same as user_id for simplicity
    if user_id not in user_sent_posts:
        user_sent_posts[user_id] = set()
    while True:
        for channel in channels:
            try:
                await upload_posts(1, channel)  # Upload the latest post
                posts = await collect_posts(channel)
                for post in posts:
                    post_lower = post.lower()  # Convert post to lowercase
                    post_hash = hash_post(post_lower)  # Compute hash of the post

                    if post_hash in user_sent_posts[user_id]:
                        continue  # Skip if post has already been sent to this user

                    all_keywords = category + user_keywords
                    for key in all_keywords:
                        key_lower = key.lower()  # Convert keyword to lowercase
                        if key_lower in post_lower:
                            await bot.send_message(chat_id, post)  # Send the post if it contains the keyword
                            user_sent_posts[user_id].add(post_hash)  # Mark post as sent for this user
                            break
            except Exception as e:
                print(f"Error processing channel {channel}: {e}")
        await asyncio.sleep(60)  # stoping for 60 sec before next control

# ---------------------------------------------------------------------------------------------------------

@dp_aiogram.callback_query(lambda c: c.data == 'main_menu')
async def main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text('Главное меню', reply_markup=main_menu_builder)
    await state.clear()

async def main():
    await dp_aiogram.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
