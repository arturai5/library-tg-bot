import sqlite3
from config import DB_NAME

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