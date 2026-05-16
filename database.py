import sqlite3
from config import DB_NAME

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

def get_all_categories():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, name FROM categories''')
    categories = cursor.fetchall()
    conn.close()
    return categories

def update_book_category(category_id, book_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''UPDATE books SET category_id = ? WHERE id = ?''', (category_id, book_id))
    conn.commit()
    conn.close()

def get_books_in_category_and_name(category_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, title, author, telegram_file_id FROM books WHERE category_id = ?''', (category_id,))
    books = cursor.fetchall()
    cursor.execute('''SELECT name FROM categories WHERE id = ?''', (category_id,))
    category_name = cursor.fetchone()[0]
    conn.close()
    return category_name, books

def add_book(author, title, file_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT INTO books (author, title, telegram_file_id) VALUES (?, ?, ?)''',
                       (author, title, file_id,))
        book_id = cursor.lastrowid
        conn.commit()
        return book_id, True
    except sqlite3.IntegrityError:
        return None, False
    finally:
        conn.close()

def add_category(new_category_name):
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    new_category_name_low = new_category_name.strip().capitalize()
    if new_category_name_low == 'It':
        new_category_name_low = 'IT'
    cursor.execute('''SELECT id FROM categories WHERE name = ?''', (new_category_name_low,))
    result_id = cursor.fetchone()
    if result_id:
        category_id = result_id[0]
        conn.close()
        return category_id, False
    else:
        cursor.execute('''INSERT INTO categories (name) VALUES (?)''', (new_category_name_low,))
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return category_id, True

def search_book(pattern):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, title, author, telegram_file_id FROM books
                    WHERE title LIKE ? OR author LIKE ?''', (pattern, pattern,))
    books = cursor.fetchall()
    conn.close()
    return books

def get_book_for_download(book_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''SELECT telegram_file_id, title FROM books WHERE id = ?''', (book_id,))
    book_data = cursor.fetchone()
    conn.close()
    return book_data

def count_books():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT COUNT(*) FROM books''')
    total = cursor.fetchone()[0]
    conn.close()
    return total

def count_books_in_category(category_id):
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT COUNT(*) FROM books WHERE category_id = ?''', (category_id,))
    count = int(cursor.fetchone()[0])
    conn.close()
    return count

def get_books_in_category_and_name_limit(category_id, limit, offset):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, title, author, telegram_file_id FROM books WHERE category_id = ?
    LIMIT ? OFFSET ?''', (category_id, limit, offset))
    books = cursor.fetchall()
    cursor.execute('''SELECT name FROM categories WHERE id = ?''', (category_id,))
    category_name = cursor.fetchone()[0]
    conn.close()
    return category_name, books




