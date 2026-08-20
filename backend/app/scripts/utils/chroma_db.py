import chromadb

client = chromadb.HttpClient(host='localhost', port=8000)

try:
    client.heartbeat()
    print("✅ Соединение с ChromaDB установлено")
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")