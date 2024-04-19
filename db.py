import logging
import sqlite3
from sqlite3 import Error
import pathlib
from datetime import datetime


# Логгирование
logging.basicConfig(
    filename="feedback.log",
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger()


# Создание и подключение базы данных
def sql_connection():
    path = pathlib.Path(__file__).parent.absolute()
    try:
        con = sqlite3.connect(str(path) + "/database.db")
        return con
    except Error:
        print(Error)
        return False


def execute(request):
    '''
    Функция выполняет заданный SQL запрос в базу данных
    '''
    con = sql_connection()
    if not con:
        return False

    try:
        cur = con.cursor()
        with con:
            records = cur.execute(request).fetchall()
        con.commit()
    finally:
        con.close()
    return records

def create_table_users():
    '''
    Функция создаёт таблицу регистрации пользователей в групповых чатах:
    - user_id - идентификатор пользователя
    - started - когда пользователь начал игру
    - stage - номер станции, к которой он движется
    - finished - когда пользователь закончил игру
    '''

    query = """CREATE TABLE IF NOT EXISTS users (
user_id integer,
started datetime,
stage text default "0",
finished datetime,
helpers integer default 0,
full_name text)"""
    return execute(query)

def create_user(user_id:str, full_name:str):
    '''
    Функция записи в таблицу нового пользователя
    '''

    request = f"""
    INSERT INTO users (user_id, full_name)
    SELECT {user_id}, '{full_name.replace("'","")}'
    WHERE NOT EXISTS (
        SELECT 1 FROM users WHERE user_id = {user_id}
    );
    """
    return execute(request)

def get_users(user_id:str=""):
    '''
    Функция получения списка пользователей, зарегистрированных на игру
    '''
    condition = ""
    if user_id!="": condition = f"WHERE user_id = {user_id}"
    query = f"SELECT * FROM users {condition}"
    return execute(query)

""" def get_user(user_id:str):
    '''
    Функция получения одного пользователя
    '''
    query = f"SELECT * FROM users WHERE user_id={user_id}"
    return execute(query) """

def gamestart(user_id:str = ""):
    '''
    Функция записывает текущее время для всех или выбранного игрока как время начала игры
    '''
    condition = ""
    if user_id!="": condition = f"WHERE user_id = {user_id}"
    query = f"UPDATE users SET started = CURRENT_TIMESTAMP, stage = 0 {condition}"
    return execute(query)

def gameover(user_id:str = ""):
    '''
    Функция записывает текущее время для всех или выбранного игрока как время завершение игры
    '''
    condition = ""
    if user_id!="": condition = f"WHERE user_id = {user_id}"
    query = f"UPDATE users SET finished = CURRENT_TIMESTAMP {condition}"
    return execute(query)

def is_game_started(user_id:str = ""):
    '''
    Функция проверяет начата ли игра (т.е. есть ли игроки, у которых started не null)
    '''
    condition = ""
    if user_id!="": condition = f"AND user_id = {user_id}"
    query = f"SELECT * FROM users WHERE started is not null {condition}"
    rows = execute(query)
    if len(rows)==0:
        return False
    else:
        return True
    
def is_game_finished(user_id:str = ""):
    '''
    Функция проверяет завершена ли игра (т.е. есть ли игроки, у которых finished не null)
    '''
    condition = ""
    if user_id!="": condition = f"AND user_id = {user_id}"
    query = f"SELECT * FROM users WHERE finished is not null {condition}"
    rows = execute(query)
    if len(rows)==0:
        return False
    else:
        return True

def level_up(stage:str, user_id:str=""):
    '''
    Функция изменяет уровень у игроков
    '''
    condition = ""
    if user_id!="": condition = f"WHERE user_id = {user_id}"
    query = f"UPDATE users SET stage = {stage} {condition}"
    return execute(query)

def helper_count(user_id:str, count_helpers:str):
    '''
    Функция добавляет значение счётчика для игроков
    '''
    query = f"UPDATE users SET helpers = {count_helpers} WHERE user_id = {user_id}"
    return execute(query)

