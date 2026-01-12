import os
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from rag_core import ContextEngine

load_dotenv()

app = FastAPI(title="BookMind API")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENGINE SETUP ---
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    print("WARNING: OPENAI_API_KEY not found!")

engine = ContextEngine(openai_key=OPENAI_KEY)

# --- MODELS ---
class SearchRequest(BaseModel):
    query: str
    session_id: str
    active_files: List[str] = []

# --- ENDPOINTS ---

@app.post("/upload")
async def upload_files(session_id: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        class FileAdapter:
            def __init__(self, file: UploadFile):
                self.name = file.filename
                self._file = file.file
            
            def getvalue(self):
                self._file.seek(0)
                return self._file.read()
            
            # ВАЖНО: Добавили whence=0, чтобы PDF-читалка не крашилась
            def seek(self, offset, whence=0):
                self._file.seek(offset, whence)
            
            def read(self, size=-1):
                return self._file.read(size)
            
            def tell(self):
                return self._file.tell()

        adapted_files = [FileAdapter(f) for f in files]
        count = engine.process_and_index(adapted_files, session_id)
        
        return {"status": "success", "indexed_chunks": count, "files": [f.filename for f in files]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search(req: SearchRequest):
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
    try:
        data = engine.export_index(session_id)
        if not data:
            raise HTTPException(status_code=404, detail="Index is empty")
        
        from fastapi.responses import Response
        return Response(content=data, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename=library_{session_id}.lib"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/import")
async def import_index(session_id: str = Form(...), file: UploadFile = File(...)):
    try:
        content = await file.read()
        count, filenames = engine.import_index(session_id, content)
        return {"status": "success", "chunks_loaded": count, "filenames": filenames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))