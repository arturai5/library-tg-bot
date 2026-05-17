from fastapi import FastAPI, BackgroundTasks, Request
import requests
import sqlite3
from send_func import *
from interf_func import *
from cover_book import *
from config import telegram_api_url, DB_NAME, ADMIN_ID, CHANNEL_DUMP_ID
from database import *
from auto_uploader import process_dump_post
import math
import time




app = FastAPI()
user_states = {}
init_db()



def process_telegram_update(data: dict):
    print(f"📥 ПРИШЕЛ WEBHOOK! Ключи внутри: {list(data.keys())}")
    if 'callback_query' in data:
        chat_id = data['callback_query']['message']['chat']['id']
        message_id = data['callback_query']['message']['message_id']
        callback_data = data['callback_query']['data']
        if callback_data.startswith('setcat_'):
            parts = callback_data.split('_')
            book_id = int(parts[1])
            category_id = int(parts[2])
            update_book_category(category_id, book_id)
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
            limit = 5
            count_books = count_books_in_category(category_id)
            url = f'{telegram_api_url}/editMessageText'
            cur_page = 1
            offset = 0
            category_name, books = get_books_in_category_and_name_limit(category_id, limit, offset)
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
                reply_markup = {'inline_keyboard': create_inline_keyboard_pages(category_id, 1, count_books, limit)}
                send_message(chat_id, reply_text, reply_markup)
                payload = {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': reply_markup}
                requests.post(url, json = payload)
            else:
                reply_text = 'В этом разделе пока нет книг.\n'
                send_message(chat_id, reply_text)
                payload = {'chat_id': chat_id, 'message_id': message_id}
                requests.post(url, json=payload)

            # res_tup = get_books_in_category_and_name(category_id)
            # books = res_tup[1]
            # category_name = res_tup[0]
            # if books:
            #     reply_text = f'Книги в разделе: {category_name}\n\n'
            #     for index, book in enumerate(books, start = 1):
            #         book_id = book[0]
            #         book_name = book[1]
            #         book_author = book[2]
            #         book_file_id = book[3]
            #         reply_text += f'{index}. {book_name} - {book_author}\n'
            #         if book_file_id:
            #             reply_text += f'Получить: /get_{book_id}\n\n'
            #         else:
            #             reply_text += 'Файла книги еще нет в базе.\n\n'
            #     inline_keyboard = [[{'text': 'Назад', 'callback_data': 'back_to_catalog'}]]
            #     reply_markup = {'inline_keyboard': inline_keyboard}
            #     send_message(chat_id, reply_text, reply_markup)
            #     payload = {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': reply_markup}
            #     requests.post(url, json = payload)
            # else:
            #     reply_text = 'В этом разделе пока нет книг.\n'
            #     send_message(chat_id, reply_text)
            #     payload = {'chat_id': chat_id, 'message_id': message_id}
            #     requests.post(url, json = payload)
        elif callback_data == 'ai_reject':
            file_id = user_states[chat_id]['file_id']
            user_states[chat_id] = {'action': 'waiting_for_author', 'file_id': file_id}
            send_message(chat_id,
                         '\nФайл загружен, напиши автора в форме: Иванов А. А.; и напиши название (двумя разными сообщениями), если его нет то оставь "-"\n\n')
        elif callback_data == 'ai_confirm':
            if chat_id not in user_states or user_states[chat_id].get('action') != 'waiting_for_ai_confirmation':
                send_message(chat_id, 'Эта кнопка устарела, пожалуйста, загрузи книгу заново.')
                return {'status': 'ok'}
            author = user_states[chat_id]['author']
            title = user_states[chat_id]['title']
            file_id = user_states[chat_id]['file_id']
            tup_add_book = add_book(author, title, file_id)
            book_id = tup_add_book[0]
            categories = get_all_categories()
            if tup_add_book[1]:
                inline_keyboard = []
                for cat in categories:
                    button = [{'text': cat[1], 'callback_data': f"setcat_{book_id}_{cat[0]}"}]
                    inline_keyboard.append(button)
                inline_keyboard.append([{"text": "➕ Создать свой раздел", "callback_data": f"addcat_{book_id}"}])
                reply_markup = {"inline_keyboard": inline_keyboard}
                send_message(chat_id, f"Книга {title} успешно сохранена, выбери раздел: ",
                             reply_markup)

            else:
                send_message(chat_id, f"Книга {title} уже есть в библиотеке")
        elif callback_data.startswith('page_'):
            category_id = int(callback_data.split('_')[1])
            target_page = int(callback_data.split('_')[2])
            limit = 5
            offset = (target_page - 1) * limit
            count_books = count_books_in_category(category_id)
            category_name, books = get_books_in_category_and_name_limit(category_id, limit, offset)
            url = f'{telegram_api_url}/editMessageText'
            if books:
                reply_text = f'Книги в разделе: {category_name}\n\n'
                for index, book in enumerate(books, start = offset + 1):
                    book_id = book[0]
                    book_name = book[1]
                    book_author = book[2]
                    book_file_id = book[3]
                    reply_text += f'{index}. {book_name} - {book_author}\n'
                    if book_file_id:
                        reply_text += f'Получить: /get_{book_id}\n\n'
                    else:
                        reply_text += 'Файла книги еще нет в базе.\n\n'
                reply_markup = {'inline_keyboard': create_inline_keyboard_pages(category_id, target_page, count_books, limit)}
                send_message(chat_id, reply_text, reply_markup)
                payload = {'chat_id': chat_id, 'message_id': message_id, 'reply_markup': reply_markup}
                requests.post(url, json = payload)
            else:
                reply_text = 'В этом разделе пока нет книг.\n'
                send_message(chat_id, reply_text)
                payload = {'chat_id': chat_id, 'message_id': message_id}
                requests.post(url, json=payload)

        return {'status': 'ok'}


    if 'channel_post' in data:
        return process_dump_post(data['channel_post'])

    if 'message' in data:
        chat_id = data['message']['chat']['id']
        if 'document' in data['message']:
            id = data['message']['from']['id']
            if id in ADMIN_ID:
                file_id = data['message']['document']['file_id']
                file_size = data['message']['document'].get('file_size', 0)
                caption = data['message'].get('caption', '')
                if file_size < 20 * 1024 * 1024:
                    save_path = download_pdf(file_id)
                    try:
                        if caption!='/auto':
                            send_message(chat_id, 'Сканирую обложку...\n\n')
                        pages_path = extract_cover_images(save_path)

                        categories = get_all_categories()
                        cats_str = (', ').join([c[1] for c in categories] if categories else 'Категорий нет.')
                        book_data = analyze_covers_with_ai(pages_path, cats_str)
                        title = book_data['title']
                        author = book_data['author']
                        category = book_data.get('category', 'Неразобранное')
                        if caption == '/auto':
                            book_id, new_book_stat = add_book(author, title, file_id)
                            if new_book_stat:
                                cat_id, new_cat_stat = add_category(category)
                                update_book_category(cat_id, book_id)
                                print(f'\nАвтопарсер сохранил книгу {title}, книг в базе: {count_books()}\n')
                                send_message(chat_id, f'Загружена {title}\n')
                            else:
                                send_message(chat_id, f"Дубликат {title}")
                        else:
                            user_states[chat_id] = {'action': 'waiting_for_ai_confirmation',
                                                    'file_id': file_id,
                                                    'title': title,
                                                    'author': author}
                            inline_keyboard = [[{'text': '✅ Верно, выбрать раздел',
                                                 'callback_data': 'ai_confirm'}], [{'text': '❌ Ошибка, введу сам',
                                                                                    'callback_data': 'ai_reject'}]]
                            reply_markup = {'inline_keyboard': inline_keyboard}
                            send_message(chat_id,
                                         f'Мы распознали обложку: Автор: {author}, Название: {title}; Все верно? \n\n',
                                         reply_markup)
                        os.remove(save_path)
                        return {'status': 'ok'}

                    except Exception as e:
                        send_message(chat_id, 'ИИ не справился с распознанием обложки, введи автора вручную.\n\n')
                        if save_path in locals() and os.path.exists(save_path):
                            os.remove(save_path)
                        if caption == '/auto':
                            send_message(chat_id, 'Файл пропущен (ошибка)\n')
                            return {'status': 'ok'}
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
                    send_message(chat_id,
                                 'Размер файла слишком большой для анализа обложки, введи название и автора вручную. \n\n')
                    user_states[chat_id] = {
                        'action': 'waiting_for_author',
                        'file_id': file_id,
                        'author': None
                    }
                    send_message(chat_id,
                                 '\nФайл загружен, напиши автора в форме: Иванов А. А.; и напиши название (двумя разными сообщениями), если его нет то оставь "-"\n\n')
                    return {'status': 'ok'}
            else:
                send_message(chat_id, 'У вас нет прав добавлять книги!\n')
        text = data['message'].get('text', '')
        if not text:
            send_message(chat_id, 'Пожалуйста воспользуйтесь меню ниже, или напишите /start')
            return {'status': 'ok'}

        if chat_id in user_states:
            if user_states[chat_id].get('action') == 'waiting_for_new_category':
                new_category_name = text.strip()
                book_id = user_states[chat_id]['book_id']
                tup_add_category = add_category(new_category_name)
                new_cat_id = tup_add_category[0]
                if tup_add_category[1]:
                    update_book_category(new_cat_id, book_id)
                    send_message(chat_id, f'Создан новый раздел: {new_category_name} и книга добавлена в него.')
                else:
                    update_book_category(new_cat_id, book_id)
                    send_message(chat_id, f'Раздел {new_category_name} уже существует, книга добавлена в него.')
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
                author = user_states[chat_id]['author']
                file_id = user_states[chat_id]['file_id']
                tup_add_book = add_book(author, title_name, file_id)
                if tup_add_book[1]:
                    book_id = tup_add_book[0]
                    categories = get_all_categories()
                    inline_keyboard = []
                    for cat in categories:
                        button = [{'text': cat[1], 'callback_data': f"setcat_{book_id}_{cat[0]}"}]
                        inline_keyboard.append(button)
                    inline_keyboard.append([{"text": "➕ Создать свой раздел", "callback_data": f"addcat_{book_id}"}])
                    reply_markup = {"inline_keyboard": inline_keyboard}
                    send_message(chat_id, f"Книга {title_name} успешно сохранена, выбери раздел: ",
                                 reply_markup)
                else:
                    send_message(chat_id, f"Книга {title_name} уже есть в библиотеке")
                del user_states[chat_id]
                return {'status': 'ok'}

            if user_states[chat_id]['action'] == 'waiting_for_search_query':
                url = f'{telegram_api_url}/editMessageText'
                search_text = data['message']['text'].strip()
                pattern = f'%{search_text}%'
                books = search_book(pattern)
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

        elif text == 'ℹ️ О библиотеке':
            send_message(chat_id, 'Тут хранятся различные книги, ассортимент постоянно пополняется, вы можете'
                                  'загрузить любую книгу на выбор себе в формате pdf. Напишите /start, приятного пользования:)\n')
            return {'status': 'ok'}

        elif text.startswith('/get_'):
            book_id_str = text[5:]
            if book_id_str.isdigit():
                book_id = int(book_id_str)
                book_data = get_book_for_download(book_id)
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

@app.post('/webhook')
async def receive_update(request: Request, background_tasks: BackgroundTasks):
    # Мгновенно вытаскиваем данные из запроса Телеграма
    data = await request.json()

    # Передаем данные нашей функции-"работяге" в фоновый режим
    background_tasks.add_task(process_telegram_update, data)

    # Моментально отдаем Телеграму код 200 OK
    return {"ok": True}


