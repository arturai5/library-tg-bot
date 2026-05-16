import sqlite3
from config import DB_NAME
import math
from database import count_books_in_category


def create_catalog():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, name FROM categories''')
    categories = cursor.fetchall()
    conn.close()
    if categories:
        inline_keyboard = []
        for cat in categories:
            button = [{'text': cat[1], 'callback_data': f'selcat_{cat[0]}'}]
            inline_keyboard.append(button)
    return {'inline_keyboard': inline_keyboard}

def create_inline_keyboard_pages(category_id, cur_page, count_books, limit):
    max_pages = math.ceil(count_books / limit)
    dict_result = []
    if max_pages:
        if cur_page > 1:
            dict_result.append({'text': '⬅️', 'callback_data': f'page_{category_id}_{cur_page - 1}'})
        else:
            dict_result.append({'text': '🔙Назад️', 'callback_data': 'back_to_catalog'})
        dict_result.append({'text': f'Страница {cur_page} из {max_pages}', 'callback_data': 'ignore'})
        if cur_page < max_pages:
            dict_result.append({'text': '➡️', 'callback_data': f'page_{category_id}_{cur_page + 1}'})
        result_list = [dict_result]
        if cur_page != 1:
            result_list.append([{'text': '🔙Назад', 'callback_data': 'back_to_catalog'}])
        return result_list
    else:
        return [[{'text': '🔙Назад', 'callback_data': 'back_to_catalog'}]]
