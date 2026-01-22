import uuid
import pickle
from typing import List, Optional
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchAny
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class ContextEngine:
    def __init__(self, openai_key: str):
        self.qdrant = QdrantClient(location=":memory:")
        self.openai = OpenAI(api_key=openai_key)
        self.embedding_model = "text-embedding-3-small"
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts: return []
        try:
            clean_texts = [t.replace("\n", " ") for t in texts]
            resp = self.openai.embeddings.create(input=clean_texts, model=self.embedding_model)
            return [d.embedding for d in resp.data]
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return []

    def _extract_page_number(self, pdf_reader, page_index: int) -> int:
        return page_index + 1

    def process_and_index(self, files, session_id: str):
        collection_name = f"sess_{session_id}"
        
        # Перевіряємо чи колекція існує, якщо ні - створюємо
        collections = self.qdrant.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)
        
        if not collection_exists:
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )

        all_points = []
        total_chunks = 0
        
        for uploaded_file in files:
            text_content = ""
            file_name = uploaded_file.name
            page_mapping = {}
            
            try:
                if file_name.endswith('.pdf'):
                    pdf_reader = PdfReader(uploaded_file)
                    current_char_count = 0
                    for page_idx, page in enumerate(pdf_reader.pages):
                        page_text = (page.extract_text() or "") + "\n"
                        page_num = self._extract_page_number(pdf_reader, page_idx)
                        start_char = current_char_count
                        end_char = current_char_count + len(page_text)
                        for char_pos in range(start_char, end_char, 100):
                            page_mapping[char_pos] = page_num
                        text_content += page_text
                        current_char_count = end_char
                else:
                    text_content = uploaded_file.getvalue().decode("utf-8", errors='ignore')
            except Exception as e:
                print(f"Error reading {file_name}: {e}")
                continue

            if not text_content.strip(): continue

            chunks = self.splitter.split_text(text_content)
            vectors = self._get_embeddings(chunks)
            
            current_position = 0
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                page_num = None
                if file_name.endswith('.pdf'):
                    closest_pos = min(page_mapping.keys(), key=lambda x: abs(x - current_position), default=None)
                    if closest_pos: page_num = page_mapping[closest_pos]
                
                all_points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={"text": chunk, "filename": file_name, "chunk_id": i, "page": page_num}
                ))
                total_chunks += 1
                current_position += len(chunk)

        if all_points:
            batch_size = 100
            for i in range(0, len(all_points), batch_size):
                self.qdrant.upsert(collection_name=collection_name, points=all_points[i : i + batch_size])
            
        return total_chunks

    def search(self, query: str, session_id: str, limit: int = 5, filter_files: Optional[List[str]] = None):
        collection_name = f"sess_{session_id}"
        try:
            collections = self.qdrant.get_collections().collections
            if not any(c.name == collection_name for c in collections): return []
            
            query_vector = self._get_embeddings([query])
            if not query_vector: return []
            
            query_filter = None
            if filter_files:
                query_filter = Filter(must=[FieldCondition(key="filename", match=MatchAny(any=filter_files))])
            
            hits = self.qdrant.query_points(collection_name=collection_name, query=query_vector[0], limit=limit, query_filter=query_filter).points
            
            return [{"score": hit.score, "text": hit.payload["text"], "filename": hit.payload["filename"], "page": hit.payload.get("page", "?"), "id": hit.id} for hit in hits]
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def export_index(self, session_id: str) -> bytes:
        collection_name = f"sess_{session_id}"
        try:
            all_points = []
            offset = None
            while True:
                points_batch, offset = self.qdrant.scroll(collection_name=collection_name, limit=1000, offset=offset, with_payload=True, with_vectors=True)
                all_points.extend(points_batch)
                if offset is None: break
            return pickle.dumps(all_points)
        except: return b""

    def import_index(self, session_id: str, file_bytes: bytes) -> tuple[int, List[str]]:
        collection_name = f"sess_{session_id}"
        try:
            points = pickle.loads(file_bytes)
            try: self.qdrant.delete_collection(collection_name)
            except: pass
            self.qdrant.create_collection(collection_name=collection_name, vectors_config=VectorParams(size=1536, distance=Distance.COSINE))
            if points:
                batch_size = 100
                for i in range(0, len(points), batch_size):
                    self.qdrant.upsert(collection_name=collection_name, points=points[i : i + batch_size])
            filenames = set(p.payload["filename"] for p in points if p.payload)
            return len(points), list(filenames)
        except Exception as e: raise e