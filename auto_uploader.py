import os.path

from config import CHANNEL_DUMP_ID
from send_func import *
from cover_book import *
import requests
import json
from google.api_core import exceptions as google_exceptions
from database import *
import time

def process_dump_post(post_data):
    print("🔍 [АВТОПАРСЕР] Зашли в функцию обработки канала!")
    chat_id = post_data['chat']['id']
    print(f"ℹ️ Сравниваем ID: Пришел {chat_id} | В конфиге {CHANNEL_DUMP_ID}")

    if 'document' not in post_data:
        return {'status': 'ok'}

    else:
        file_id = post_data['document']['file_id']
        file_size = post_data['document']['file_size']
        save_path = None
        saved_files = None
        print(f"✅ Документ найден! Размер: {file_size / 1024 / 1024:.2f} МБ")
        if file_size < 20 * 1024 * 1024:
            print("🚀 Начинаем скачивание...")
            try:
                save_path = download_pdf(file_id)
                saved_files = extract_cover_images(save_path)
                categories = get_all_categories()
                cats_str = (', ').join([c[1] for c in categories] if categories else 'Категорий нет.')
                book_data = analyze_covers_with_ai(saved_files, cats_str)
                title = book_data['title']
                author = book_data['author']
                category = book_data.get('category', 'Неразобранное')
                book_id, new_book_stat = add_book(author, title, file_id)
                if new_book_stat:
                    cat_id, new_cat_stat = add_category(category)
                    update_book_category(cat_id, book_id)
                    print(f'\nАвтопарсер сохранил книгу {title}, книг в базе: {count_books()}\n')
                    send_message(chat_id, f'Загружена {title}\n')
                else:
                    send_message(chat_id, f"Дубликат {title}")
                time.sleep(4.5)
                return {'status': 'ok'}

            except json.JSONDecodeError as e:
                print('ИИ прислал кривой JSON')
            except google_exceptions.GoogleAPIError as e:
                print('Ошибка google api')
            except Exception as e:
                print(f'Неизвестная ошибка: {e}')
            finally:
                if save_path and os.path.exists(save_path):
                    os.remove(save_path)
        return {'status': 'ok'}




