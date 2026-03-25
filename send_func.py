from fastapi import FastAPI
import requests
import sqlite3
import os
from config import telegram_api_url, TELEGRAM_TOKEN


def send_message(chat_id: int, text: str, reply_markup: dict = None):
    url = f'{telegram_api_url}/sendMessage'
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    response = requests.post(url, json = payload)
    print(f"ОТВЕТ ОТ ТЕЛЕГРАМА: {response.json()}")

def send_document(chat_id: int, file_id: str):
    url = f'{telegram_api_url}/sendDocument'
    payload = {'chat_id': chat_id, 'document': file_id}
    requests.post(url, json = payload)

def download_pdf(file_id):
    os.makedirs('temp_pdf', exist_ok = True)
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}'
    response = requests.get(url).json()
    file_path = response['result']['file_path']
    download_url = f'https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}'
    file = requests.get(download_url)
    save_path = os.path.join('temp_pdf', f'{file_id}.pdf')

    with open(save_path, 'wb') as f:
        f.write(file.content)

    return save_path

