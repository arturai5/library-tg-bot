from google import genai

# Вставь сюда свой ключ в кавычках
API_KEY = "AIzaSyBI3Flb0c6i0LwWT8Lf4AajGVUdV08HZj8"

# Создаем клиента (теперь это делается так)
client = genai.Client(api_key=API_KEY)

print("Отправляю запрос...")

# Вызываем генерацию текста через новую структуру
response = client.models.generate_content(
    model='gemma-3-27b-it',
    contents='Привет! Напиши короткий факт о физике.'
)

print("Ответ ИИ:")
print(response.text)