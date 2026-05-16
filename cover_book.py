import fitz
import os
from google import genai
from PIL import Image
import json
from config import API_KEY

# pdf_path = 'pdf_files/Термодинамика_И.П._Базаров (4).pdf'
def extract_cover_images(pdf_path):
    os.makedirs('covers', exist_ok=True)
    saved_files = []
    doc = fitz.open(pdf_path)
    for i in range(min(len(doc), 3)):
        page = doc.load_page(i)
        zoom_matrix = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix = zoom_matrix)
        name = f'covers/page{i + 1}.jpg'
        pix.save(name)
        saved_files.append(name)
    doc.close()
    return saved_files

def analyze_covers_with_ai(image_paths, existing_categories = ""):
    prompt_contents = []
    for path in image_paths:
        prompt_contents.append(Image.open(path))
    prompt = f"""
        Проанализируй эти страницы книги (обложку и первые страницы). 
        Вытащи название книги и автора.

        Также определи категорию книги. Вот список уже существующих категорий в нашей библиотеке:
        {existing_categories}

        Если книга подходит под одну из них, напиши её название ТОЧНО как в списке. 
        Если ни одна не подходит, придумай новую короткую и понятную категорию (1-2 слова, например: "Программирование", "Фантастика", "Медицина").

        Верни ответ СТРОГО в формате JSON:
        {{
            "title": "Название книги",
            "author": "Имя Автора",
            "category": "Название Категории"
        }}
        Если автора нет, напиши "-".
        """
    prompt_contents.append(prompt)
    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model = 'gemma-4-31b-it',
        contents = prompt_contents
    )
    print(response.text)
    json_dict_prev = response.text.replace('```json', '')
    json_dict = json_dict_prev.replace('```', '')
    book_data = json.loads(json_dict)
    for path in image_paths:
        os.remove(path)
    return book_data
