import os, sys, json, re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

import db, admins


BOT_TOCKEN = os.environ.get("BOT_TOCKEN")
BOT_ADMIN_ID = admins.ids

USER_COMMANDS = \
"""
Список команд:
/start - зарегистрироваться в игру
/advice - получить подсказку на задание
/help - справка по игре
"""
ADMIN_COMMANDS = \
"""

Список команд для администраторов
/gamestart - запустить игру для всех игроков. Новые игроки после запуска будут включены в игру автоматически
/gameover - завершить игру для всех игроков
/stat - получить статистику по игрокам
"""

# Настройки базы данных
DB_FILE = 'database.db'
if re.match("[0-9]{10}:[a-zA-Z0-9+\_]{35}", str(BOT_TOCKEN)) is None:
    print("Не найдена переменная с токеном бота!")
    sys.exit()

    # Инициализация бота
bot = Bot(token=BOT_TOCKEN)
loop = asyncio.get_event_loop()
dp = Dispatcher(bot, loop=loop, storage=MemoryStorage())

game_map_file_name = "game.json"
try:
    with open(game_map_file_name, "r", encoding="utf-8") as game_map_file:
        game_map = json.load(game_map_file)
except:
    print("Не найден файл с картой игры!")

#TODO добавить проверки на соответствия файла и количества баз

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    '''
    Функция обрабатывает команду /start. При вызове этой команды отправляет в личные сообщения пользователю
    приветственное сообщение
    '''
    answer_text = ""
    if str(message.from_user.id) in BOT_ADMIN_ID: 
        answer_text += f"Администратор не может участвовать в игре!\n{USER_COMMANDS}{ADMIN_COMMANDS}"
        await dp.bot.send_message(message.from_user.id, answer_text)
        return
    gamer = db.get_users(str(message.from_user.id))
    if len(gamer) == 0:
        answer_text = game_map['hello']
        db.create_user(str(message.from_user.id), message.from_user.full_name)
        if db.is_game_started() == True: 
            db.gamestart(str(message.from_user.id))
            db.level_up("1",message.from_user.id)
            await dp.bot.send_message(message.from_user.id,answer_text)
            await question(str(message.from_user.id))
            return
    else:
        answer_text = "Вы уже зарегистрированы в игре! Ждите начала!"

    await dp.bot.send_message(message.from_user.id,answer_text)

@dp.message_handler(commands=['gamestart'])
async def game_start_command(message: types.Message):
    '''
    Функция обрабатывает команду /gamestart и запускает игру
    '''
    answer_text = ""
    if str(message.from_user.id) not in BOT_ADMIN_ID:
        answer_text = "Команда доступна только администраторам"
        await dp.bot.send_message(message.from_user.id,answer_text)
        return
    
    if db.is_game_finished() == True:
        answer_text = "Игра уже была завершена!"
    elif db.is_game_started() == True:
        answer_text = "Игра уже запущена!"
    else:
        try:
            db.gamestart()
            db.level_up("1")
            await question()
            answer_text = "Игра успешно запущена!"
        except:
            answer_text = "Ошибка запуска игры!"
    await dp.bot.send_message(message.from_user.id,answer_text)

@dp.message_handler(commands=['gameover'])
async def game_over_command(message: types.Message):
    '''
    Функция обрабатывает команду /gameover и завершает игру
    '''
    answer_text = ""
    if str(message.from_user.id) not in BOT_ADMIN_ID:
        answer_text = "Команда доступна только администраторам"
        await dp.bot.send_message(message.from_user.id,answer_text)
        return
    
    if db.is_game_started() == False:
        answer_text = "Игра ещё не была запущена!"
    elif db.is_game_finished() == True:
        answer_text = "Игра уже была завершена!"
    else:
        try:
            db.gameover()
            await question()
            answer_text = "Игра успешно завершена!"
        except:
            answer_text = "Ошибка завершения игры!"
    await dp.bot.send_message(message.from_user.id,answer_text)

@dp.message_handler(commands=['advice'])
async def advice(message: types.Message):
    '''
    Функция обрабатывает команду /advice и даёт игроку подсказку
    '''
    answer = ""
    if not db.is_game_started() or db.is_game_finished():
        answer += "Сейчас игра не идёт и команда не доступна"
        await dp.bot.send_message(message.from_user.id, answer)
        return
    gamer = await get_gamer(db.get_users(str(message.from_user.id))[0])
    advice_text = game_map['stages'][gamer['stage']]['helper']
    answer += f"Подсказка: {advice_text}\n"
    answer += "Не забывайте, что использование подсказок учитывается в статистике"
    db.helper_count(gamer['user_id'], str(int(gamer['helpers'])+1))
    await dp.bot.send_message(gamer['user_id'], answer)

@dp.message_handler(commands=['stat'])
async def get_stat(message: types.Message):
    font_path = "RobotoMono-Italic-VariableFont_wght.ttf"
    font = ImageFont.truetype(font_path, 14)
    if str(message.from_user.id) not in BOT_ADMIN_ID:
        answer_text = "Команда доступна только администраторам"
        await dp.bot.send_message(message.from_user.id,answer_text)
        return
    
    users = db.get_users()
    if len(users)==0 or not db.is_game_started: 
        await dp.bot.send_message(message.from_user.id, "Статистика недоступна")
        return
    # Расчет времени между датами started и finished
    processed_data = []
    for row in users:
        gamer = await get_gamer(row)
        # Парсинг дат
        try:
            started_dt = datetime.strptime(gamer['started'], '%Y-%m-%d %H:%M:%S')
            finished_dt = datetime.strptime(gamer['finished'], '%Y-%m-%d %H:%M:%S')
            # Расчет разницы во времени
            time_diff = finished_dt - started_dt
        except:
            time_diff = ""
        processed_data.append((gamer['full_name'], str(time_diff), gamer['stage'], gamer['helpers']))

    
    # Создание изображения
    img_height = 30 * (len(processed_data) + 1) + 10  # Увеличиваем высоту, чтобы добавить место для заголовка
    img = Image.new('RGB', (1000, img_height), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    # Добавление заголовков столбцов
    headers = [await add_space("Имя", 50), await add_space("Время", 12), 
               await add_space("На точке", 12), await add_space("Число подсказок", 13)]
    header_text = " | ".join(headers)
    d.text((10, 10), header_text, fill=(0, 0, 0), font=font)

    # Добавление данных под заголовками
    data_start_y = 40  # Начинаем выводить данные ниже заголовка
    for i, (full_name, time_diff, stage, helpers) in enumerate(processed_data):
        fn_col = await add_space(full_name, 50)
        td_col = await add_space(time_diff,12)
        st_col = await add_space(stage,12)
        hl_col = await add_space(str(helpers),13)
        row_text = f'{fn_col} | {td_col} | {st_col} | {hl_col}'
        d.text((10, data_start_y + 30 * i), row_text, fill=(0, 0, 0), font=font)

    # Сохранение изображения
    img.save('data_image.png')

    with open('data_image.png', 'rb') as photo:
        await message.reply_photo(photo, caption='Статистика по игре')
    

@dp.message_handler()
async def gamer_answer(message: types.Message):
    '''
    Функция обрабатывает текст входящего сообщения
    '''
    answer = ""
    if str(message.from_user.id) in BOT_ADMIN_ID: 
        answer += f"{USER_COMMANDS}{ADMIN_COMMANDS}"
        await dp.bot.send_message(message.from_user.id, answer)
        return
    users = db.get_users(message.from_user.id)
    if len(users)==0:
        answer += "Для участия в игре введите команду /start"
        await dp.bot.send_message(message.from_user.id, answer)
        return 
    gamer = await get_gamer(users[0])
    is_last_stage = gamer['stage'] == game_map['stages']['count']
    next_stage = str(int(gamer['stage'])+1)
    if not db.is_game_started(gamer['user_id']):
        answer = f"Вы зарегистрированы в игре, но она ещё не начата! Подождите получения задания\n\n{USER_COMMANDS}"
        await dp.bot.send_message(gamer['user_id'], answer)
        return
    if db.is_game_started(gamer['user_id']) and not db.is_game_finished(gamer['user_id']):
        if message.text.lower() == game_map['stages'][gamer['stage']]['answer'].lower():
            answer = "Правильный ответ!\n"
            if is_last_stage:
                db.gameover(gamer['user_id'])
                gamer = await get_gamer(db.get_users(str(message.from_user.id))[0])
                answer += \
                f"""Вы закончили игру!
Время старта: {str(gamer["started"])}
Время финиша: {str(gamer["finished"])}
Подсказок: {str(gamer["helpers"])}
                """
                await dp.bot.send_message(gamer['user_id'], answer)
                return
            answer += "Следующее задание:\n"
            answer += game_map['stages'][next_stage]['question']
            db.level_up(next_stage, gamer['user_id'])
            await dp.bot.send_message(gamer['user_id'], answer)
            return
        else:
            answer += "Неверный ответ! Попробуй ещё раз\n"
            answer += game_map['stages'][gamer['stage']]['question']
            await dp.bot.send_message(gamer['user_id'], answer)
            return
    if db.is_game_finished():
        answer += "Игра завершена! За статистикой обратитесь к организатору"
        await dp.bot.send_message(gamer['user_id'], answer)
        return
        
async def question(user_id:str = ""):
    gamer_ids = []
    if user_id=="": 
        for user in db.get_users():
            gamer_ids.append(user[0])  #'user_id'
    else: 
        try:
            gamer_ids.append(int(user_id))
        except: 
            print("Указан неверный ID пользователя")
            return
    for idstr in gamer_ids:
        gamer = db.get_users(idstr)[0]
        ids = gamer[0]  #'user_id'
        stage = gamer[2]  #'stage'
        question_text = game_map['stages'][stage]['question']
        await dp.bot.send_message(ids, question_text)

async def get_gamer(row):
    gamer = {
        "user_id": row[0],
        "started": row[1],
        "stage": row[2],
        "finished": row[3],
        "helpers": row[4],
        "full_name": row[5]
    }
    return gamer

async def add_space(text:str, lenght:int):
    while len(text)<lenght:
        text += " "
    return text

if __name__ == '__main__':
    db.create_table_users()
    from aiogram import executor
    # Запуск планировщика задач (cron)
    #dp.loop.create_task(scheduled_actions())
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)