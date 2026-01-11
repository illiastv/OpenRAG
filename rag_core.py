import uuid
from typing import List, Dict, Any
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


class ContextEngine:
    def __init__(self, openai_key: str, qdrant_url: str = None, qdrant_key: str = None):
        # Всегда используем локальную память
        self.qdrant = QdrantClient(location=":memory:")
        self.openai = OpenAI(api_key=openai_key)
        self.embedding_model = "text-embedding-3-small"
        
        # Настройщик нарезки текста
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts: 
            return []
        try:
            clean_texts = [t.replace("\n", " ") for t in texts]
            resp = self.openai.embeddings.create(input=clean_texts, model=self.embedding_model)
            return [d.embedding for d in resp.data]
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return []

    def process_and_index(self, files, session_id: str):
        collection_name = f"sess_{session_id}"
        
        # Пересоздаем коллекцию
        try:
            self.qdrant.delete_collection(collection_name=collection_name)
        except:
            pass
        
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )

        all_points = []
        total_chunks = 0
        
        for uploaded_file in files:
            text_content = ""
            file_name = uploaded_file.name
            
            try:
                if file_name.endswith('.pdf'):
                    pdf_reader = PdfReader(uploaded_file)
                    for page in pdf_reader.pages:
                        text_content += (page.extract_text() or "") + "\n"
                else:
                    text_content = uploaded_file.getvalue().decode("utf-8", errors='ignore')
            except Exception as e:
                print(f"Error reading {file_name}: {e}")
                continue

            if not text_content.strip():
                continue

            # Нарезаем на куски
            chunks = self.splitter.split_text(text_content)
            print(f"File: {file_name}, Chunks: {len(chunks)}")
            
            # Готовим векторы
            vectors = self._get_embeddings(chunks)
            
            if len(vectors) != len(chunks):
                print(f"Warning: Vector count mismatch for {file_name}")
                continue
            
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                all_points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "text": chunk,
                        "filename": file_name,
                        "chunk_id": i
                    }
                ))
                total_chunks += 1

        # Загружаем в Qdrant батчами
        if all_points:
            batch_size = 100
            for i in range(0, len(all_points), batch_size):
                self.qdrant.upsert(
                    collection_name=collection_name,
                    points=all_points[i : i + batch_size]
                )
            print(f"Total indexed: {total_chunks} chunks")
            
        return total_chunks

    def search(self, query: str, session_id: str, limit: int = 5):
        collection_name = f"sess_{session_id}"
        
        try:
            # Проверяем, существует ли коллекция
            collections = self.qdrant.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                print(f"Collection {collection_name} не найдена")
                return []
            
            query_vector = self._get_embeddings([query])
            if not query_vector:
                print("Не удалось получить embedding для запроса")
                return []
            
            # ПРАВИЛЬНЫЙ МЕТОД - query(), а не search()!
            hits = self.qdrant.query_points(
                collection_name=collection_name,
                query=query_vector[0],
                limit=limit
            ).points
            
            print(f"Found {len(hits)} results")
            
            return [
                {
                    "score": hit.score,
                    "text": hit.payload["text"],
                    "filename": hit.payload["filename"],
                    "chunk_id": hit.payload["chunk_id"]
                } 
                for hit in hits
            ]
        except Exception as e:
            print(f"Search error details: {e}")
            import traceback
            traceback.print_exc()
            return []