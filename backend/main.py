import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from rag_core import ContextEngine

# Завантажуємо змінні оточення
load_dotenv()

app = FastAPI(title="BookMind API")

# --- CORS (Дозволяємо фронтенду стукати сюди) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для розробки дозволяємо всім (потім зміниш на localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Ініціалізація движка ---
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    print("WARNING: OPENAI_API_KEY not found!")

# Зберігаємо engine глобально (для MVP це ок, в проді краще dependency injection)
# Але оскільки Qdrant в пам'яті, нам треба тримати об'єкт живим.
# УВАГА: При перезапуску сервера пам'ять очиститься.
engine = ContextEngine(openai_key=OPENAI_KEY)

# --- Pydantic моделі для валідації вхідних даних ---
class SearchRequest(BaseModel):
    query: str
    session_id: str
    active_files: List[str] = []

class SearchResponse(BaseModel):
    results: List[dict]

# --- Ендпоінти ---

@app.get("/")
def read_root():
    return {"status": "BookMind API is running 🚀"}

@app.post("/upload")
async def upload_files(
    session_id: str = Form(...), 
    files: List[UploadFile] = File(...)
):
    """Приймає файли, зберігає тимчасово, індексує і видаляє."""
    try:
        temp_files = []
        
        # 1. Зберігаємо файли на диск тимчасово, щоб rag_core міг їх прочитати
        # (rag_core чекає об'єкти з .name, тут треба адаптувати трохи логіку або передавати байт-стрім)
        # Але щоб не ламати твій rag_core, зробимо фінт:
        
        # Ми можемо передати файли прямо в engine, але треба переконатися, 
        # що rag_core вміє читати SpooledTemporaryFile від FastAPI.
        # Твій код використовує uploaded_file.name і uploaded_file.getvalue() (для streamlit).
        # FastAPI файли мають .filename і .file.read(). Треба трохи адаптувати rag_core або тут.
        
        # АДАПТАЦІЯ ТУТ:
        class FileAdapter:
            def __init__(self, file: UploadFile):
                self.name = file.filename
                self._file = file.file
            def getvalue(self):
                self._file.seek(0)
                return self._file.read()
            # Для pypdf
            def seek(self, offset):
                self._file.seek(offset)
            def read(self, size=-1):
                return self._file.read(size)
            def tell(self):
                return self._file.tell()

        adapted_files = [FileAdapter(f) for f in files]
        
        count = engine.process_and_index(adapted_files, session_id)
        
        return {
            "status": "success", 
            "indexed_chunks": count, 
            "files": [f.filename for f in files]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search(req: SearchRequest):
    """Пошук по базі."""
    try:
        results = engine.search(
            query=req.query,
            session_id=req.session_id,
            limit=15,
            filter_files=req.active_files if req.active_files else None
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export")
async def export_index(session_id: str):
    """Завантажити .lib файл."""
    try:
        data = engine.export_index(session_id)
        if not data:
            raise HTTPException(status_code=404, detail="Index is empty")
        
        # Повертаємо як файл
        from fastapi.responses import Response
        return Response(
            content=data, 
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=library_{session_id}.lib"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/import")
async def import_index(session_id: str = Form(...), file: UploadFile = File(...)):
    """Завантажити .lib файл назад."""
    try:
        content = await file.read()
        count, filenames = engine.import_index(session_id, content)
        return {
            "status": "success",
            "chunks_loaded": count,
            "filenames": filenames
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Запуск: uvicorn main:app --reload