import chromadb
import json
from sentence_transformers import SentenceTransformer
client = chromadb.HttpClient(host='localhost', port=8000)
collection = client.get_collection("spanish_grammar")

# 1. Проверяем общее количество
count = collection.count()
print(f"Количество записей в базе: {count}")

# 2. Извлекаем первые 2 записи для проверки метаданных и текста
results = collection.get(limit=2)
print("\nПример данных из базы:")
for i in range(len(results['ids'])):
    print(f"ID: {results['ids'][i]}")
    print(f"Metadata: {results['metadatas'][i]}")
    print(f"Text snippet: {results['documents'][i][:100]}...")
    print("-" * 30)




model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
query_text = "How to use ser and estar?"

# Кодируем запрос
query_embedding = model.encode(query_text).tolist()

# Ищем 3 наиболее похожих чанка
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3
)

print(f"\nРезультаты поиска по запросу '{query_text}':")
for i, doc in enumerate(results['documents'][0]):
    print(f"{i+1}. [ID: {results['ids'][0][i]}]")
    print(f"   Текст: {doc[:150]}...")

# Получаем все данные из коллекции
# include=['metadatas', 'documents'] — без векторов, чтобы не забивать экран
all_data = collection.get(include=['metadatas', 'documents'])

# Превращаем в список объектов (строк)
rows = []
for i in range(len(all_data['ids'])):
    rows.append({
        "id": all_data['ids'][i],
        "metadata": all_data['metadatas'][i],
        "content": all_data['documents'][i][:100] + "..." # обрезаем для читаемости
    })

print(json.dumps(rows, indent=2, ensure_ascii=False))