from fastapi import FastAPI
import requests
import sqlite3
from send_func import *
from interf_func import *
from cover_book import *
from config import telegram_api_url, DB_NAME

app = FastAPI()
user_states = {}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS categories ( 
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category_id INTEGER,
    telegram_file_id TEXT,
    UNIQUE(title, author),
    FOREIGN KEY (category_id) REFERENCES categories (id))''')
    conn.commit()
    conn.close()
init_db()


@app.post('/webhook')
def receive_update(data: dict):
    if 'callback_query' in data:
        chat_id = data['callback_query']['message']['chat']['id']
        message_id = data['callback_query']['message']['message_id']
        callback_data = data['callback_query']['data']
        if callback_data.startswith('setcat_'):
            parts = callback_data.split('_')
            book_id = int(parts[1])
            category_id = int(parts[2])

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('''UPDATE books SET category_id = ? WHERE id = ?''', (category_id, book_id))
            conn.commit()
            conn.close()

            url = f'{telegram_api_url}/editMessageText'
            payload = {'chat_id': chat_id, 'message_id': message_id, 'text': "Раздел успешно назначен"}
            requests.post(url, json = payload)

        elif callback_data == 'back_to_catalog':
            reply_markup = create_catalog()
            url = f'{telegram_api_url}/editMessageText'
            payload = {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': reply_markup}
            send_message(chat_id, 'Выбери раздел:\n', reply_markup)
            requests.post(url, json = payload)

        elif callback_data.startswith('addcat_'):
            book_id = int(callback_data.split('_')[1])
            user_states[chat_id] = {'action': 'waiting_for_new_category', 'book_id': book_id}
            url = f'{telegram_api_url}/editMessageText'
            payload = {'chat_id': chat_id, 'message_id': message_id, 'text': 'Напиши название нового раздела: '}
            requests.post(url, json = payload)

        elif callback_data.startswith('selcat_'):
            category_id = int(callback_data.split('_')[1])
            url = f'{telegram_api_url}/editMessageText'
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('''SELECT id, title, author, telegram_file_id FROM books WHERE category_id = ?''', (category_id,))
            books = cursor.fetchall()
            cursor.execute('''SELECT name FROM categories WHERE id = ?''', (category_id, ))
            category_name = cursor.fetchone()[0]
            conn.close()
            if books:
                reply_text = f'Книги в разделе: {category_name}\n\n'
                for index, book in enumerate(books, start = 1):
                    book_id = book[0]
                    book_name = book[1]
                    book_author = book[2]
                    book_file_id = book[3]
                    reply_text += f'{index}. {book_name} - {book_author}\n'
                    if book_file_id:
                        reply_text += f'Получить: /get_{book_id}\n\n'
                    else:
                        reply_text += 'Файла книги еще нет в базе.\n\n'
                inline_keyboard = [[{'text': 'Назад', 'callback_data': 'back_to_catalog'}]]
                reply_markup = {'inline_keyboard': inline_keyboard}
                send_message(chat_id, reply_text, reply_markup)
                payload = {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': reply_markup}
                requests.post(url, json = payload)
            else:
                reply_text = 'В этом разделе пока нет книг.\n'
                send_message(chat_id, reply_text)
                payload = {'chat_id': chat_id, 'message_id': message_id}
                requests.post(url, json = payload)
        elif callback_data == 'ai_reject':
            file_id = user_states[chat_id]['file_id']
            user_states[chat_id] = {'action': 'waiting_for_author', 'file_id': file_id}
            send_message(chat_id,
                         '\nФайл загружен, напиши автора в форме: Иванов А. А.; и напиши название (двумя разными сообщениями), если его нет то оставь "-"\n\n')
        elif callback_data == 'ai_confirm':
            author = user_states[chat_id]['author']
            title = user_states[chat_id]['title']
            file_id = user_states[chat_id]['file_id']
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO books (author, title, telegram_file_id) VALUES (?, ?, ?)''', (author, title, file_id, ))
                book_id = cursor.lastrowid
                cursor.execute('''SELECT id, name FROM categories''')
                categories = cursor.fetchall()

                conn.commit()
                conn.close()

                inline_keyboard = []
                for cat in categories:
                    button = [{'text': cat[1], 'callback_data': f"setcat_{book_id}_{cat[0]}"}]
                    inline_keyboard.append(button)
                inline_keyboard.append([{"text": "➕ Создать свой раздел", "callback_data": f"addcat_{book_id}"}])
                reply_markup = {"inline_keyboard": inline_keyboard}
                send_message(chat_id, f"Книга {title} успешно сохранена, выбери раздел: ",
                             reply_markup)

            except sqlite3.IntegrityError:
                send_message(chat_id, f"Книга {title} уже есть в библиотеке")
        return {'status': 'ok'}


    if 'message' in data:
        chat_id = data['message']['chat']['id']

        if 'document' in data['message']:
            file_id = data['message']['document']['file_id']
            file_size = data['message']['document'].get('file_size', 0)
            if file_size < 20*1024*1024:
                try:
                    send_message(chat_id, 'Сканирую обложку...\n\n')
                    save_path = download_pdf(file_id)
                    pages_path = extract_cover_images(save_path)
                    book_data = analyze_covers_with_ai(pages_path)
                    title = book_data['title']
                    author = book_data['author']
                    user_states[chat_id] = {'action': 'waiting_for_ai_confirmation',
                                            'file_id': file_id,
                                            'title': title,
                                            'author': author}
                    inline_keyboard = [[{'text': '✅ Верно, выбрать раздел',
                                        'callback_data': 'ai_confirm'}], [{'text': '❌ Ошибка, введу сам',
                                                                         'callback_data': 'ai_reject'}]]
                    reply_markup = {'inline_keyboard': inline_keyboard}
                    send_message(chat_id, f'Мы распознали обложку: Автор: {author}, Название: {title}; Все верно? \n\n',
                                 reply_markup)
                    os.remove(save_path)

                    return {'status': 'ok'}
                except Exception as e:
                    send_message(chat_id, 'ИИ не справился с распознанием обложки, введи автора вручную.\n\n')
                    user_states[chat_id] = {
                        'action': 'waiting_for_author',
                        'file_id': file_id,
                        'author': None
                    }
                    print(f'Ошибка: {e}\n\n')
                    send_message(chat_id,
                                 '\nФайл загружен, напиши автора в форме: Иванов А. А.; и напиши название (двумя разными сообщениями), если его нет то оставь "-"\n\n')
                    return {'status': 'ok'}
            else:
                send_message(chat_id, 'Размер файла слишком большой для анализа обложки, введи название и автора вручную. \n\n')
                user_states[chat_id] = {
                    'action': 'waiting_for_author',
                    'file_id': file_id,
                    'author': None
                }
                send_message(chat_id,
                             '\nФайл загружен, напиши автора в форме: Иванов А. А.; и напиши название (двумя разными сообщениями), если его нет то оставь "-"\n\n')
                return {'status': 'ok'}

        text = data['message'].get('text', '')
        if not text:
            return {'status': 'ok'}

        if chat_id in user_states:
            if user_states[chat_id].get('action') == 'waiting_for_new_category':
                new_category_name = text.strip()
                book_id = user_states[chat_id]['book_id']

                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()

                try:
                    cursor.execute('''INSERT INTO categories (name) VALUES (?)''', (new_category_name,))
                    new_cat_id = cursor.lastrowid
                    cursor.execute('''UPDATE books SET category_id = ? WHERE id = ?''', (new_cat_id, book_id,))
                    conn.commit()
                    send_message(chat_id, f'Создан новый раздел: {new_category_name} и книга добавлена в него.')
                except sqlite3.IntegrityError:
                    cursor.execute('''SELECT id FROM categories WHERE name = ?''', (new_category_name,))
                    exist_cat_id = cursor.fetchone()[0]
                    cursor.execute('''UPDATE books SET category_id = ? WHERE id = ?''', (exist_cat_id, book_id,))
                    conn.commit()
                    send_message(chat_id, f'Раздел {new_category_name} уже существует, книга добавлена в него.')
                conn.close()
                del user_states[chat_id]
                return {'status': 'ok'}

            if chat_id in user_states and user_states[chat_id].get('action') == 'waiting_for_author':
                author_name = text.strip()
                user_states[chat_id]['author'] = author_name
                user_states[chat_id]['action'] = 'waiting_for_title'
                send_message(chat_id, 'Автор принят теперь напиши название: \n')
                return {'status': 'ok'}

            if user_states[chat_id].get('action') == 'waiting_for_title':
                title_name = text.strip()
                send_message(chat_id, 'Название записано.\n\n')
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute('''INSERT INTO books (title, author, telegram_file_id) VALUES (?, ?, ?)''',
                                   (title_name, user_states[chat_id]['author'], user_states[chat_id]['file_id']))
                    book_id = cursor.lastrowid
                    cursor.execute('''SELECT id, name FROM categories''')
                    categories = cursor.fetchall()

                    conn.commit()
                    conn.close()

                    inline_keyboard = []
                    for cat in categories:
                        button = [{'text': cat[1], 'callback_data': f"setcat_{book_id}_{cat[0]}"}]
                        inline_keyboard.append(button)
                    inline_keyboard.append([{"text": "➕ Создать свой раздел", "callback_data": f"addcat_{book_id}"}])
                    reply_markup = {"inline_keyboard": inline_keyboard}
                    send_message(chat_id, f"Книга {title_name} успешно сохранена, выбери раздел: ",
                                 reply_markup)
                except sqlite3.IntegrityError:
                    send_message(chat_id, f"Книга {title_name} уже есть в библиотеке")
                del user_states[chat_id]
                return {'status': 'ok'}

            if user_states[chat_id]['action'] == 'waiting_for_search_query':
                url = f'{telegram_api_url}/editMessageText'
                search_text = data['message']['text'].strip()
                pattern = f'%{search_text}%'
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''SELECT id, title, author, telegram_file_id FROM books
                WHERE title LIKE ? OR author LIKE ?''', (pattern, pattern,))
                books = cursor.fetchall()
                conn.close()
                reply_text = 'Найденные книги: \n\n'
                if books:
                    for index, book in enumerate(books, start=1):
                        book_id = book[0]
                        book_name = book[1]
                        book_author = book[2]
                        book_file_id = book[3]
                        reply_text += f'{index}. {book_name} - {book_author}\n'
                        if book_file_id:
                            reply_text += f'Получить: /get_{book_id}\n\n'
                        else:
                            reply_text += 'Файла книги еще нет в базе.\n\n'
                    send_message(chat_id, reply_text)
                else:
                    send_message(chat_id, 'По твоему запросу книг не найдено. \n\n')
                del user_states[chat_id]
                return {'status': 'ok'}

        elif text == '/start':
            keyboard = {
                'keyboard': [
                    [{'text': '📚 Каталог книг'}, {'text': '🔎 Поиск'},
                     {'text': 'ℹ️ О библиотеке'}]
                ], 'resize_keyboard': True
            }
            send_message(chat_id, 'Добро пожаловать в библиотеку!', keyboard)

        elif text == '📚 Каталог книг':
            reply_markup = create_catalog()
            send_message(chat_id, 'Выбери раздел:\n', reply_markup)
            return {'status': 'ok'}

        elif text == '🔎 Поиск':
            user_states[chat_id] = {'action': 'waiting_for_search_query'}
            send_message(chat_id, 'Введи название книги или фамилию автора: \n\n')
            return {'status': 'ok'}

        elif text.startswith('/get_'):
            book_id_str = text[5:]
            if book_id_str.isdigit():
                book_id = int(book_id_str)
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''SELECT telegram_file_id, title FROM books WHERE id = ?''', (book_id,))
                book_data = cursor.fetchone()
                conn.close()
                if book_data and book_data[0]:
                    file_id = book_data[0]
                    book_title = book_data[1]

                    send_message(chat_id, f'Книга {book_title} загружается...')
                    send_document(chat_id, file_id)
                else:
                    send_message('Книга не найдена!')
        else:
            send_message(chat_id, 'Пожалуйста воспользуйтесь меню ниже, или напишите /start')
    return {'status': 'ok'}




