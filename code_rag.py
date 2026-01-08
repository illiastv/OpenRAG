# code_rag.py

# ========== IMPORTS ==========

# os - for working with file system (reading folders, files)
import os

# typing - for type hints, makes code clearer
from typing import List, Dict, Optional

# uuid - for generating unique IDs
import uuid

# OpenAI - client for working with OpenAI API (embeddings, GPT)
from openai import OpenAI

# Qdrant - client for vector database
from qdrant_client import QdrantClient

# Qdrant models for database configuration
from qdrant_client.models import Distance, VectorParams, PointStruct

# dotenv - for loading API keys from .env file
from dotenv import load_dotenv


# ========== GLOBAL QDRANT CLIENT CACHE ==========

# Global dictionary to store Qdrant clients by path
# This prevents "already accessed" errors when multiple instances try to use the same path
_qdrant_clients = {}


def _get_qdrant_client(qdrant_path: str) -> QdrantClient:
    """
    Get or create Qdrant client for a given path.
    Reuses existing client if one already exists for this path.
    
    Args:
        qdrant_path: path to Qdrant storage
        
    Returns:
        QdrantClient instance
    """
    if qdrant_path not in _qdrant_clients:
        _qdrant_clients[qdrant_path] = QdrantClient(path=qdrant_path)
    return _qdrant_clients[qdrant_path]


# ========== RAG SYSTEM CLASS ==========

class CodeRAG:
    """
    RAG system specifically for codebases.
    Can read code folders, index files and answer questions.
    """
    
    def __init__(self, openai_api_key: str, qdrant_path: str = "./qdrant_storage"):
        """
        Constructor - runs when you create a CodeRAG() object
        
        Args:
            openai_api_key: your OpenAI API key
            qdrant_path: path where to store the vector database locally
        """
        
        # Create OpenAI client and save it to self.openai_client
        # self - reference to the current class object
        # All variables with self. are accessible in all class methods
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Create or reuse Qdrant client
        # Uses global cache to prevent "already accessed" errors
        # path: means local storage (not in cloud)
        self.qdrant_client = _get_qdrant_client(qdrant_path)
        
        # Collection name (like a table in a regular database)
        self.collection_name = "code_base"
        
        # Model for creating embeddings (vectors)
        # text-embedding-3-small - fast and cheap
        self.embedding_model = "text-embedding-3-small"
        
        # Model for generating answers
        # gpt-4o-mini - cheap version of GPT-4
        self.llm_model = "gpt-4o-mini"
        
        # Default prompt templates (can be customized)
        self.system_prompt = "You are a helpful code assistant that explains code clearly."
        self.context_template = """[Code Snippet {i}] (Relevance: {score:.3f})
File: {path}
Lines: {lines}
```{extension}
{text}
```"""
        self.user_prompt_template = """You are an expert code assistant. Help the user understand their codebase.

Based on the following code snippets from the codebase, answer the user's question.

Code Context:
{context}

User Question: {query}

Please provide a clear, helpful answer. Reference specific files and line numbers when relevant.

Answer:"""
        
        # Analytics tracking
        self.analytics = {
            "total_queries": 0,
            "total_tokens_used": 0,
            "total_cost": 0.0,
            "total_embedding_cost": 0.0,
            "total_generation_cost": 0.0,
            "query_history": []
        }
        
        # Chunking strategy settings
        self.chunking_strategy = "lines"  # "lines", "functions", "files"
        self.chunk_size = 1000
        
        # File extensions we will read
        # You can add your own: ".java", ".go", ".rs", etc.
        self.code_extensions = {
            '.py',   # Python
            '.js',   # JavaScript
            '.ts',   # TypeScript
            '.jsx',  # React
            '.tsx',  # React TypeScript
            '.java', # Java
            '.cpp',  # C++
            '.c',    # C
            '.h',    # C headers
            '.go',   # Go
            '.rs',   # Rust
            '.rb',   # Ruby
            '.php',  # PHP
            '.swift',# Swift
            '.kt',   # Kotlin
            '.scala',# Scala
            '.css',  # CSS
            '.html', # HTML
            '.md',   # Markdown (documentation)
            '.json', # JSON configs
            '.yaml', # YAML configs
            '.yml',  # YAML configs
        }
        
        # Folders to ignore
        self.ignore_dirs = {
            'node_modules',  # npm packages
            '.git',          # git folder
            '__pycache__',   # Python cache
            'venv',          # Python virtual environment
            'env',           # also venv
            '.venv',         # also venv
            'dist',          # compiled code
            'build',         # build artifacts
            '.next',         # Next.js build
            'target',        # Java/Rust build
            'bin',           # binaries
            'obj',           # object files
        }
        
        # Create collection in Qdrant on initialization
        self._setup_collection()
    
    
    def _setup_collection(self):
        """
        Create collection in Qdrant.
        Method with _ at the beginning = private (used only inside the class)
        """
        
        try:
            # Try to get existing collection
            self.qdrant_client.get_collection(self.collection_name)
            
            # If we got here - collection exists
            print(f"✅ Collection '{self.collection_name}' already exists")
            
        except Exception:
            # If we got an error - collection doesn't exist, create new one
            
            # create_collection - creates a new collection
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,  # name
                
                # vectors_config - vector settings
                vectors_config=VectorParams(
                    # size - vector size (text-embedding-3-small makes 1536)
                    size=1536,
                    
                    # distance - distance metric between vectors
                    # COSINE = cosine similarity (from -1 to 1)
                    # Closer to 1 = more similar
                    distance=Distance.COSINE
                )
            )
            
            print(f"✅ Created new collection '{self.collection_name}'")
    
    
    # ========== STEP 1: READING CODEBASE ==========
    
    def read_file(self, file_path: str) -> Optional[str]:
        """
        Read contents of a single file
        
        Args:
            file_path: path to file
            
        Returns:
            file contents or None if error
        """
        
        try:
            # open() - opens file
            # 'r' - read mode
            # encoding='utf-8' - encoding (for Russian letters and emoji)
            # errors='ignore' - ignore broken characters
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                
                # f.read() - reads entire file into string
                content = f.read()
                
            return content
            
        except Exception as e:
            # If error - print and return None
            print(f"⚠️  Error reading {file_path}: {e}")
            return None
    
    
    def scan_directory(self, directory_path: str) -> List[Dict]:
        """
        Recursive scanning of folder and all subfolders
        
        Args:
            directory_path: path to folder for scanning
            
        Returns:
            list of files with their contents and metadata
        """
        
        print(f"\n{'='*60}")
        print(f"📁 SCANNING DIRECTORY: {directory_path}")
        print(f"{'='*60}\n")
        
        # List to store found files
        files = []
        
        # os.walk() - recursively traverses all folders
        # root - current folder
        # dirs - list of subfolders in current folder
        # filenames - list of files in current folder
        for root, dirs, filenames in os.walk(directory_path):
            
            # Remove ignored folders from dirs
            # dirs[:] - modifies list in place
            # This is needed so os.walk doesn't enter these folders
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            
            # Iterate through all files in current folder
            for filename in filenames:
                
                # os.path.splitext() - splits filename into name and extension
                # example: "main.py" -> ("main", ".py")
                # [1] takes second element (extension)
                file_extension = os.path.splitext(filename)[1]
                
                # Check that extension is in our list
                if file_extension in self.code_extensions:
                    
                    # os.path.join() - joins paths correctly for any OS
                    file_path = os.path.join(root, filename)
                    
                    # Read file contents
                    content = self.read_file(file_path)
                    
                    # If reading successful
                    if content:
                        
                        # os.path.relpath() - makes relative path
                        # Example: /home/user/project/src/main.py -> src/main.py
                        relative_path = os.path.relpath(file_path, directory_path)
                        
                        # Add file information to list
                        files.append({
                            "filename": filename,           # file name
                            "path": file_path,             # full path
                            "relative_path": relative_path, # relative path
                            "extension": file_extension,    # extension
                            "content": content,            # contents
                            "size": len(content),          # size in characters
                        })
                        
                        # Print progress
                        print(f"  ✅ {relative_path} ({len(content)} chars)")
        
        print(f"\n✅ Found {len(files)} code files")
        print(f"{'='*60}\n")
        
        return files
    
    
    # ========== STEP 2: CODE CHUNKING ==========
    
    def chunk_code_file(self, file_info: Dict, chunk_size: int = None, strategy: str = None) -> List[Dict]:
        """
        Split code file into chunks using different strategies.
        
        Args:
            file_info: file information (from scan_directory)
            chunk_size: chunk size in characters (uses self.chunk_size if None)
            strategy: chunking strategy - "lines", "functions", "files" (uses self.chunking_strategy if None)
            
        Returns:
            list of chunks with metadata
        """
        
        if chunk_size is None:
            chunk_size = self.chunk_size
        if strategy is None:
            strategy = self.chunking_strategy
        
        content = file_info["content"]
        
        # Strategy: whole file as one chunk
        if strategy == "files":
            return [{
                "chunk_id": 0,
                "text": content,
                "filename": file_info["filename"],
                "relative_path": file_info["relative_path"],
                "extension": file_info["extension"],
                "start_line": 0,
                "end_line": len(content.split('\n')),
                "size": len(content)
            }]
        
        # Strategy: by functions/classes (basic implementation)
        if strategy == "functions":
            return self._chunk_by_functions(file_info, chunk_size)
        
        # Strategy: by lines (default)
        return self._chunk_by_lines(file_info, chunk_size)
    
    def _chunk_by_lines(self, file_info: Dict, chunk_size: int) -> List[Dict]:
        """Chunk file by lines with size limit."""
        content = file_info["content"]
        lines = content.split('\n')
        
        chunks = []
        current_chunk_lines = []
        current_chunk_size = 0
        chunk_id = 0
        
        for line_num, line in enumerate(lines):
            line_size = len(line) + 1
            
            if current_chunk_size + line_size > chunk_size and current_chunk_lines:
                chunk_text = '\n'.join(current_chunk_lines)
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "filename": file_info["filename"],
                    "relative_path": file_info["relative_path"],
                    "extension": file_info["extension"],
                    "start_line": line_num - len(current_chunk_lines),
                    "end_line": line_num,
                    "size": len(chunk_text)
                })
                chunk_id += 1
                current_chunk_lines = [line]
                current_chunk_size = line_size
            else:
                current_chunk_lines.append(line)
                current_chunk_size += line_size
        
        if current_chunk_lines:
            chunk_text = '\n'.join(current_chunk_lines)
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "filename": file_info["filename"],
                "relative_path": file_info["relative_path"],
                "extension": file_info["extension"],
                "start_line": len(lines) - len(current_chunk_lines),
                "end_line": len(lines),
                "size": len(chunk_text)
            })
        
        return chunks
    
    def _chunk_by_functions(self, file_info: Dict, chunk_size: int) -> List[Dict]:
        """Chunk file by functions/classes (basic regex-based implementation)."""
        import re
        content = file_info["content"]
        extension = file_info["extension"]
        
        chunks = []
        chunk_id = 0
        
        # Patterns for different languages
        patterns = {
            '.py': r'(def\s+\w+|class\s+\w+)',
            '.js': r'(function\s+\w+|const\s+\w+\s*=\s*\(|class\s+\w+)',
            '.ts': r'(function\s+\w+|const\s+\w+\s*=\s*\(|class\s+\w+)',
            '.java': r'(public|private|protected)?\s*(static)?\s*(class|interface|enum)\s+\w+|(public|private|protected)\s+.*\s+\w+\s*\(',
        }
        
        pattern = patterns.get(extension, r'(def\s+\w+|class\s+\w+|function\s+\w+)')
        matches = list(re.finditer(pattern, content))
        
        if not matches:
            # Fallback to line-based if no functions found
            return self._chunk_by_lines(file_info, chunk_size)
        
        # Split by function boundaries
        for i, match in enumerate(matches):
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            chunk_text = content[start_pos:end_pos].strip()
            if len(chunk_text) > chunk_size:
                # If function is too large, split it further
                sub_chunks = self._chunk_by_lines({
                    "content": chunk_text,
                    "filename": file_info["filename"],
                    "relative_path": file_info["relative_path"],
                    "extension": file_info["extension"]
                }, chunk_size)
                for sub_chunk in sub_chunks:
                    sub_chunk["chunk_id"] = chunk_id
                    sub_chunk["start_line"] += content[:start_pos].count('\n')
                    chunks.append(sub_chunk)
                    chunk_id += 1
            else:
                start_line = content[:start_pos].count('\n')
                end_line = content[:end_pos].count('\n')
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "filename": file_info["filename"],
                    "relative_path": file_info["relative_path"],
                    "extension": file_info["extension"],
                    "start_line": start_line,
                    "end_line": end_line,
                    "size": len(chunk_text)
                })
                chunk_id += 1
        
        return chunks if chunks else self._chunk_by_lines(file_info, chunk_size)
    
    
    # ========== STEP 3: EMBEDDINGS ==========
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get vector representations (embeddings) for texts
        
        Args:
            texts: list of texts (code chunks)
            
        Returns:
            list of vectors (each vector = list of 1536 numbers)
        """
        
        print(f"🧠 Getting embeddings for {len(texts)} chunks...")
        
        # Call OpenAI API
        # embeddings.create() - creates embeddings
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,  # which model to use
            input=texts                  # list of texts
        )
        
        # response.data - list of objects with embeddings
        # item.embedding - the vector itself (list of 1536 numbers)
        # List comprehension iterates through all elements and gets embedding
        embeddings = [item.embedding for item in response.data]
        
        # Track embedding costs (text-embedding-3-small: $0.02 per 1M tokens)
        tokens_used = response.usage.total_tokens
        embedding_cost = (tokens_used / 1_000_000) * 0.02
        self.analytics["total_embedding_cost"] += embedding_cost
        self.analytics["total_cost"] += embedding_cost
        
        print(f"✅ Got {len(embeddings)} embeddings ({tokens_used} tokens, ${embedding_cost:.4f})")
        
        return embeddings
    
    
    # ========== STEP 4: INDEXING ==========
    
    def index_codebase(self, directory_path: str, chunk_size: int = 1000) -> Dict:
        """
        Full codebase indexing pipeline
        
        Args:
            directory_path: path to code folder
            chunk_size: size of chunks in characters (default: 1000)
            
        Returns:
            indexing statistics
        """
        
        print(f"\n{'='*60}")
        print(f"🚀 STARTING CODEBASE INDEXING")
        print(f"{'='*60}\n")
        print(f"📏 Using chunk size: {chunk_size} characters")
        
        # 1. Scan directory
        files = self.scan_directory(directory_path)
        
        # If no files - exit
        if not files:
            print("⚠️  No code files found!")
            return {"total_files": 0, "total_chunks": 0}
        
        # 2. Chunk all files
        print(f"✂️  Chunking {len(files)} files...")
        all_chunks = []
        
        # Iterate through each file
        for file_info in files:
            # Split file into chunks using current strategy
            file_chunks = self.chunk_code_file(file_info, chunk_size=chunk_size, strategy=self.chunking_strategy)
            
            # Add chunks to general list
            all_chunks.extend(file_chunks)
        
        print(f"✅ Created {len(all_chunks)} chunks total")
        
        # 3. Get embeddings
        # Take only text from each chunk for embeddings
        chunk_texts = [chunk["text"] for chunk in all_chunks]
        
        # Get vectors for all chunks
        embeddings = self.get_embeddings(chunk_texts)
        
        # 4. Save to Qdrant
        print(f"💾 Storing in Qdrant...")
        
        points = []  # list of points for Qdrant
        
        # zip() - joins two lists element by element
        # enumerate() - adds element number
        for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
            
            # Create point for Qdrant
            point = PointStruct(
                # str(uuid.uuid4()) - generates unique ID
                id=str(uuid.uuid4()),
                
                # Vector (embedding)
                vector=embedding,
                
                # payload - metadata (like JSON)
                # This is data stored together with the vector
                payload={
                    "text": chunk["text"],              # the code itself
                    "filename": chunk["filename"],      # file name
                    "relative_path": chunk["relative_path"],  # path
                    "extension": chunk["extension"],    # extension
                    "chunk_id": chunk["chunk_id"],      # chunk ID in file
                    "start_line": chunk["start_line"],  # start line
                    "end_line": chunk["end_line"],      # end line
                }
            )
            
            points.append(point)
            
            # Every 100 points show progress
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(all_chunks)} chunks...")
        
        # upsert - adds or updates points in Qdrant
        # If point with such ID exists - updates, if not - creates
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        print(f"\n✅ INDEXING COMPLETE!")
        print(f"{'='*60}\n")
        
        # Return statistics
        return {
            "total_files": len(files),
            "total_chunks": len(all_chunks),
            "indexed_at": directory_path
        }
    
    
    # ========== STEP 5: SEARCH ==========
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for relevant code chunks by query
        
        Args:
            query: question or description of what we're looking for
            top_k: how many results to return
            
        Returns:
            list of found chunks with metadata
        """
        
        print(f"\n{'='*60}")
        print(f"🔍 SEARCHING: '{query}'")
        print(f"{'='*60}\n")
        
        # 1. Convert query to vector
        print(f"🧠 Converting query to embedding...")
        
        # Get embedding for query (one text = one [0])
        query_embedding = self.get_embeddings([query])[0]
        
        # 2. Search for similar vectors in Qdrant
        print(f"🔎 Searching in vector database...")
        
        try:
            # Try the newest API first (qdrant-client 1.8+)
            search_results = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,  # Changed from query_vector to query
                limit=top_k
            ).points
        except (TypeError, AttributeError) as e:
            try:
                # Fallback to older search method
                search_results = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    limit=top_k
                )
            except Exception as e2:
                print(f"❌ Search error: {e2}")
                raise
        
        # 3. Format results
        results = []
        
        # enumerate() adds counter (i)
        for i, hit in enumerate(search_results):
            
            # hit.score - how similar this chunk is (from 0 to 1)
            # hit.payload - metadata we saved
            results.append({
                "rank": i + 1,                          # position in top
                "score": hit.score,                     # similarity score
                "text": hit.payload["text"],           # code
                "filename": hit.payload["filename"],   # file
                "path": hit.payload["relative_path"], # path
                "lines": f"{hit.payload['start_line']}-{hit.payload['end_line']}",  # lines
                "extension": hit.payload["extension"]  # extension
            })
            
            # Print results
            print(f"  [{i+1}] Score: {hit.score:.4f} | {hit.payload['relative_path']}")
            print(f"      Lines {hit.payload['start_line']}-{hit.payload['end_line']}")
            print(f"      Preview: {hit.payload['text'][:100]}...")
            print()
        
        print(f"✅ Found {len(results)} relevant code chunks")
        print(f"{'='*60}\n")
        
        return results
    
    
    # ========== STEP 6: ANSWER GENERATION ==========
    
    def generate_answer(self, query: str, search_results: List[Dict], 
                       system_prompt: str = None, 
                       context_template: str = None,
                       user_prompt_template: str = None) -> Dict:
        """
        Generate answer based on found code chunks with customizable prompts
        
        Args:
            query: user question
            search_results: found code chunks
            system_prompt: custom system prompt (uses self.system_prompt if None)
            context_template: custom context template (uses self.context_template if None)
            user_prompt_template: custom user prompt template (uses self.user_prompt_template if None)
            
        Returns:
            answer and full prompt
        """
        
        import time
        start_time = time.time()
        
        print(f"💬 Generating answer with LLM...")
        
        # Use custom prompts or defaults
        system_prompt = system_prompt or self.system_prompt
        context_template = context_template or self.context_template
        user_prompt_template = user_prompt_template or self.user_prompt_template
        
        # 1. Form context from found files using template
        context_parts = []
        
        for i, result in enumerate(search_results):
            # Format each chunk using template
            context_part = context_template.format(
                i=i+1,
                score=result['score'],
                path=result['path'],
                lines=result['lines'],
                extension=result['extension'][1:],
                text=result['text']
            )
            context_parts.append(context_part)
        
        context = '\n'.join(context_parts)
        
        # 2. Form full prompt using template
        full_prompt = user_prompt_template.format(
            context=context,
            query=query
        )
        
        # 3. Call GPT to generate answer
        response = self.openai_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            temperature=0.3
        )
        
        # Extract answer
        answer = response.choices[0].message.content
        
        # Calculate costs and track analytics
        generation_time = time.time() - start_time
        tokens_used = response.usage.total_tokens
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        
        # Cost calculation (approximate for gpt-4o-mini)
        cost_per_1k_prompt = 0.15 / 1000  # $0.15 per 1M tokens
        cost_per_1k_completion = 0.60 / 1000  # $0.60 per 1M tokens
        generation_cost = (prompt_tokens * cost_per_1k_prompt) + (completion_tokens * cost_per_1k_completion)
        
        # Update analytics
        self.analytics["total_queries"] += 1
        self.analytics["total_tokens_used"] += tokens_used
        self.analytics["total_generation_cost"] += generation_cost
        self.analytics["total_cost"] += generation_cost
        self.analytics["query_history"].append({
            "query": query,
            "tokens": tokens_used,
            "cost": generation_cost,
            "time": generation_time,
            "timestamp": time.time()
        })
        
        print(f"✅ Answer generated ({len(answer)} chars, {tokens_used} tokens, ${generation_cost:.4f}, {generation_time:.2f}s)")
        
        return {
            "answer": answer,
            "full_prompt": full_prompt,
            "system_prompt": system_prompt,
            "tokens_used": tokens_used,
            "cost": generation_cost,
            "generation_time": generation_time
        }
    
    
    # ========== FULL RAG PIPELINE ==========
    
    def ask(self, question: str, top_k: int = 5, 
            system_prompt: str = None,
            context_template: str = None,
            user_prompt_template: str = None) -> Dict:
        """
        Full RAG: search + answer generation with customizable prompts
        
        Args:
            question: question about codebase
            top_k: how many chunks to use for context
            system_prompt: custom system prompt
            context_template: custom context template
            user_prompt_template: custom user prompt template
            
        Returns:
            full result with answer and all details
        """
        import time
        total_start = time.time()
        
        # 1. Search for relevant code
        search_results = self.search(question, top_k=top_k)
        
        # 2. Generate answer with custom prompts
        generation_result = self.generate_answer(
            question, 
            search_results,
            system_prompt=system_prompt,
            context_template=context_template,
            user_prompt_template=user_prompt_template
        )
        
        total_time = time.time() - total_start
        
        # 3. Return everything together
        return {
            "question": question,
            "answer": generation_result["answer"],
            "retrieved_chunks": search_results,
            "full_prompt": generation_result["full_prompt"],
            "system_prompt": generation_result.get("system_prompt", self.system_prompt),
            "tokens_used": generation_result.get("tokens_used", 0),
            "cost": generation_result.get("cost", 0),
            "generation_time": generation_result.get("generation_time", 0),
            "total_time": total_time
        }
    
    def set_prompts(self, system_prompt: str = None, 
                    context_template: str = None,
                    user_prompt_template: str = None):
        """Update prompt templates."""
        if system_prompt:
            self.system_prompt = system_prompt
        if context_template:
            self.context_template = context_template
        if user_prompt_template:
            self.user_prompt_template = user_prompt_template
    
    def set_chunking_strategy(self, strategy: str, chunk_size: int = None):
        """Set chunking strategy and size."""
        if strategy in ["lines", "functions", "files"]:
            self.chunking_strategy = strategy
        if chunk_size:
            self.chunk_size = chunk_size
    
    def get_analytics(self) -> Dict:
        """Get analytics summary."""
        return {
            "total_queries": self.analytics["total_queries"],
            "total_tokens": self.analytics["total_tokens_used"],
            "total_cost": self.analytics["total_cost"],
            "embedding_cost": self.analytics["total_embedding_cost"],
            "generation_cost": self.analytics["total_generation_cost"],
            "avg_cost_per_query": self.analytics["total_cost"] / max(self.analytics["total_queries"], 1),
            "recent_queries": self.analytics["query_history"][-10:]  # Last 10 queries
        }


# ========== USAGE EXAMPLE ==========

if __name__ == "__main__":
    """
    This code will run only if file is run directly
    (not on import)
    """
    
    # Load variables from .env file
    load_dotenv()
    
    # os.getenv() - gets environment variable
    # Create .env file with content:
    # OPENAI_API_KEY=sk-your-key-here
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Check that key exists
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Create a .env file with: OPENAI_API_KEY=sk-your-key-here")
        exit(1)  # exit(1) - terminates program with error
    
    # Create RAG system object
    rag = CodeRAG(
        openai_api_key=api_key,
        qdrant_path="./qdrant_storage"  # local folder for database
    )
    
    # Index codebase
    # Replace with path to your code folder!
    codebase_path = "./my_project"
    
    print(f"Starting indexing of: {codebase_path}")
    
    # index_codebase - reads folder, chunks, makes embeddings, saves
    stats = rag.index_codebase(codebase_path)
    
    print(f"\n📊 Indexing Stats:")
    print(f"   Files: {stats['total_files']}")
    print(f"   Chunks: {stats['total_chunks']}")
    
    # Now we can ask questions!
    print("\n" + "="*60)
    print("Ready to answer questions about your codebase!")
    print("="*60 + "\n")
    
    # Example questions:
    questions = [
        "Where is the function for processing requests?",
        "Show how authentication is implemented",
        "What API endpoints are in the project?"
    ]
    
    # Or you can make interactive mode:
    while True:
        # input() - reads user input
        question = input("\n🤔 Your question (or 'quit' to exit): ")
        
        # Check for exit
        if question.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        # If empty query - skip
        if not question.strip():
            continue
        
        # Ask question to RAG system
        result = rag.ask(question, top_k=3)
        
        # Print result
        print("\n" + "="*60)
        print("📝 ANSWER")
        print("="*60)
        print(result["answer"])
        
        # Show where information came from
        print("\n📚 Sources:")
        for chunk in result["retrieved_chunks"]:
            print(f"  • {chunk['path']} (lines {chunk['lines']})")
        
        # Optionally: show full prompt
        show_prompt = input("\n🔍 Show full prompt? (y/n): ")
        if show_prompt.lower() == 'y':
            print("\n" + "="*60)
            print("FULL PROMPT")
            print("="*60)
            print(result["full_prompt"])