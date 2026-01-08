# code_rag.py

# ========== IMPORTS ==========

# os - for file system operations (reading folders, files)
import os

# typing - for type hints to make code clearer
from typing import List, Dict, Optional

# uuid - for generating unique IDs
import uuid

# OpenAI - client for OpenAI API (embeddings, GPT)
from openai import OpenAI

# Qdrant - client for the vector database
from qdrant_client import QdrantClient

# Qdrant models for database configuration
from qdrant_client.models import Distance, VectorParams, PointStruct

# dotenv - for loading API keys from a .env file
from dotenv import load_dotenv


# ========== RAG SYSTEM CLASS ==========

class CodeRAG:
    """
    RAG system specifically for codebases.
    Can read code folders, index files, and answer questions.
    """

    def __init__(self, openai_api_key: str, qdrant_path: str = "./qdrant_storage"):
        """
        Constructor - runs when creating a CodeRAG object.

        Args:
            openai_api_key: Your OpenAI API key
            qdrant_path: path to store the vector DB locally
        """

        # Create OpenAI client and save it to self.openai_client
        # self - reference to the current class object
        # All variables with self. are available in all class methods
        self.openai_client = OpenAI(api_key=openai_api_key)

        # Create Qdrant client
        # path: indicates local storage (not cloud)
        self.qdrant_client = QdrantClient(path=qdrant_path)

        # Collection name (like a table in a regular DB)
        self.collection_name = "code_base"

        # Model for creating embeddings (vectors)
        # text-embedding-3-small - fast and cheap
        self.embedding_model = "text-embedding-3-small"

        # Model for generating answers
        # gpt-4o-mini - cheaper version of GPT-4
        self.llm_model = "gpt-4o-mini"

        # File extensions to read
        # You can add your own: ".java", ".go", ".rs", etc.
        self.code_extensions = {
            '.py',  # Python
            '.js',  # JavaScript
            '.ts',  # TypeScript
            '.jsx',  # React
            '.tsx',  # React TypeScript
            '.java',  # Java
            '.cpp',  # C++
            '.c',  # C
            '.h',  # C headers
            '.go',  # Go
            '.rs',  # Rust
            '.rb',  # Ruby
            '.php',  # PHP
            '.swift',  # Swift
            '.kt',  # Kotlin
            '.scala',  # Scala
            '.css',  # CSS
            '.html',  # HTML
            '.md',  # Markdown (documentation)
            '.json',  # JSON configs
            '.yaml',  # YAML configs
            '.yml',  # YAML configs
        }

        # Directories to ignore
        self.ignore_dirs = {
            'node_modules',  # npm packages
            '.git',  # git folder
            '__pycache__',  # Python cache
            'venv',  # Python virtual environment
            'env',  # also venv
            '.venv',  # also venv
            'dist',  # compiled code
            'build',  # build artifacts
            '.next',  # Next.js build
            'target',  # Java/Rust build
            'bin',  # binaries
            'obj',  # object files
        }

        # Create collection in Qdrant upon initialization
        self._setup_collection()

    def _setup_collection(self):
        """
        Create a collection in Qdrant.
        Method starting with _ = private (used only inside the class).
        """

        try:
            # Try to get existing collection
            self.qdrant_client.get_collection(self.collection_name)

            # If reached here - collection exists
            print(f"✅ Collection '{self.collection_name}' already exists")

        except Exception:
            # If error received - collection doesn't exist, create a new one

            # create_collection - creates a new collection
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,  # name

                # vectors_config - vector settings
                vectors_config=VectorParams(
                    # size - vector size (text-embedding-3-small produces 1536)
                    size=1536,

                    # distance - distance metric between vectors
                    # COSINE = cosine similarity (from -1 to 1)
                    # Closer to 1 = more similar
                    distance=Distance.COSINE
                )
            )

            print(f"✅ Created new collection '{self.collection_name}'")

    # ========== STEP 1: READING THE CODEBASE ==========

    def read_file(self, file_path: str) -> Optional[str]:
        """
        Read content of a single file.

        Args:
            file_path: path to the file

        Returns:
            file content or None if error
        """

        try:
            # open() - opens the file
            # 'r' - read mode
            # encoding='utf-8' - encoding (for special characters and emoji)
            # errors='ignore' - ignore broken characters
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:

                # f.read() - reads the entire file into a string
                content = f.read()

            return content

        except Exception as e:
            # If error - print and return None
            print(f"⚠️  Error reading {file_path}: {e}")
            return None

    def scan_directory(self, directory_path: str) -> List[Dict]:
        """
        Recursive scan of the folder and all subfolders.

        Args:
            directory_path: path to the folder to scan

        Returns:
            list of files with their content and metadata
        """

        print(f"\n{'=' * 60}")
        print(f"📁 SCANNING DIRECTORY: {directory_path}")
        print(f"{'=' * 60}\n")

        # List to store found files
        files = []

        # os.walk() - recursively walks through all folders
        # root - current folder
        # dirs - list of subfolders in current folder
        # filenames - list of files in current folder
        for root, dirs, filenames in os.walk(directory_path):

            # Remove ignored folders from dirs
            # dirs[:] - modifies the list in place
            # This is needed so os.walk doesn't enter these folders
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

            # Iterate over all files in current folder
            for filename in filenames:

                # os.path.splitext() - splits filename into name and extension
                # e.g.: "main.py" -> ("main", ".py")
                # [1] takes the second element (extension)
                file_extension = os.path.splitext(filename)[1]

                # Check if extension is in our list
                if file_extension in self.code_extensions:

                    # os.path.join() - joins paths correctly for any OS
                    file_path = os.path.join(root, filename)

                    # Read file content
                    content = self.read_file(file_path)

                    # If read successful
                    if content:
                        # os.path.relpath() - makes relative path
                        # E.g.: /home/user/project/src/main.py -> src/main.py
                        relative_path = os.path.relpath(file_path, directory_path)

                        # Add file info to list
                        files.append({
                            "filename": filename,  # filename
                            "path": file_path,  # full path
                            "relative_path": relative_path,  # relative path
                            "extension": file_extension,  # extension
                            "content": content,  # content
                            "size": len(content),  # size in characters
                        })

                        # Print progress
                        print(f"  ✅ {relative_path} ({len(content)} chars)")

        print(f"\n✅ Found {len(files)} code files")
        print(f"{'=' * 60}\n")

        return files

    # ========== STEP 2: CODE CHUNKING ==========

    def chunk_code_file(self, file_info: Dict, chunk_size: int = 1000) -> List[Dict]:
        """
        Split code file into chunks.
        For code, it's better to split by functions/classes, but for simplicity
        we use line splitting with smart boundary selection.

        Args:
            file_info: file information (from scan_directory)
            chunk_size: chunk size in characters

        Returns:
            list of chunks with metadata
        """

        # Get file content
        content = file_info["content"]

        # split('\n') - splits text into lines by newline character
        lines = content.split('\n')

        chunks = []
        current_chunk_lines = []  # lines of current chunk
        current_chunk_size = 0  # size of current chunk
        chunk_id = 0

        # Iterate over all lines
        for line_num, line in enumerate(lines):

            # Line size + 1 (for newline character)
            line_size = len(line) + 1

            # If adding this line exceeds chunk_size
            if current_chunk_size + line_size > chunk_size and current_chunk_lines:

                # Save current chunk
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

                # Start new chunk
                chunk_id += 1
                current_chunk_lines = [line]
                current_chunk_size = line_size
            else:
                # Add line to current chunk
                current_chunk_lines.append(line)
                current_chunk_size += line_size

        # Don't forget the last chunk
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

    # ========== STEP 3: EMBEDDINGS ==========

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get vector representations (embeddings) for texts.

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
            input=texts  # list of texts
        )

        # response.data - list of embedding objects
        # item.embedding - the vector itself (list of 1536 numbers)
        # List comprehension iterates over all elements and takes embedding
        embeddings = [item.embedding for item in response.data]

        print(f"✅ Got {len(embeddings)} embeddings")

        return embeddings

    # ========== STEP 4: INDEXING ==========

    def index_codebase(self, directory_path: str) -> Dict:
        """
        Full codebase indexing pipeline.

        Args:
            directory_path: path to code folder

        Returns:
            indexing statistics
        """

        print(f"\n{'=' * 60}")
        print(f"🚀 STARTING CODEBASE INDEXING")
        print(f"{'=' * 60}\n")

        # 1. Scan directory
        files = self.scan_directory(directory_path)

        # If no files - exit
        if not files:
            print("⚠️  No code files found!")
            return {"total_files": 0, "total_chunks": 0}

        # 2. Chunk all files
        print(f"✂️  Chunking {len(files)} files...")
        all_chunks = []

        # Iterate over each file
        for file_info in files:
            # Split file into chunks
            file_chunks = self.chunk_code_file(file_info, chunk_size=1000)

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

        # zip() - combines two lists element-wise
        # enumerate() - adds element counter
        for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):

            # Create point for Qdrant
            point = PointStruct(
                # str(uuid.uuid4()) - generates unique ID
                id=str(uuid.uuid4()),

                # Vector (embedding)
                vector=embedding,

                # payload - metadata (like JSON)
                # Data stored together with the vector
                payload={
                    "text": chunk["text"],  # code itself
                    "filename": chunk["filename"],  # filename
                    "relative_path": chunk["relative_path"],  # path
                    "extension": chunk["extension"],  # extension
                    "chunk_id": chunk["chunk_id"],  # chunk ID in file
                    "start_line": chunk["start_line"],  # start line
                    "end_line": chunk["end_line"],  # end line
                }
            )

            points.append(point)

            # Show progress every 100 points
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(all_chunks)} chunks...")

        # upsert - adds or updates points in Qdrant
        # If point with ID exists - updates, if not - creates
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"\n✅ INDEXING COMPLETE!")
        print(f"{'=' * 60}\n")

        # Return stats
        return {
            "total_files": len(files),
            "total_chunks": len(all_chunks),
            "indexed_at": directory_path
        }

    # ========== STEP 5: SEARCH ==========

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for relevant code chunks by query.

        Args:
            query: user question or description of what to find
            top_k: number of results to return

        Returns:
            list of found chunks with metadata
        """

        print(f"\n{'=' * 60}")
        print(f"🔍 SEARCHING: '{query}'")
        print(f"{'=' * 60}\n")

        # 1. Convert query to vector
        print(f"🧠 Converting query to embedding...")

        # Get embedding for query (one text = one [0])
        query_embedding = self.get_embeddings([query])[0]

        # 2. Search similar vectors in Qdrant
        print(f"🔎 Searching in vector database...")

        # search() - looks for nearest vectors
        search_results = self.qdrant_client.search(
            collection_name=self.collection_name,  # where to search
            query_vector=query_embedding,  # query vector
            limit=top_k  # how many results
        )

        # 3. Format results
        results = []

        # enumerate() adds counter (i)
        for i, hit in enumerate(search_results):
            # hit.score - how similar this chunk is (from 0 to 1)
            # hit.payload - metadata we saved
            results.append({
                "rank": i + 1,  # rank
                "score": hit.score,  # similarity score
                "text": hit.payload["text"],  # code
                "filename": hit.payload["filename"],  # file
                "path": hit.payload["relative_path"],  # path
                "lines": f"{hit.payload['start_line']}-{hit.payload['end_line']}",  # lines
                "extension": hit.payload["extension"]  # extension
            })

            # Print results
            print(f"  [{i + 1}] Score: {hit.score:.4f} | {hit.payload['relative_path']}")
            print(f"      Lines {hit.payload['start_line']}-{hit.payload['end_line']}")
            print(f"      Preview: {hit.payload['text'][:100]}...")
            print()

        print(f"✅ Found {len(results)} relevant code chunks")
        print(f"{'=' * 60}\n")

        return results

    # ========== STEP 6: ANSWER GENERATION ==========

    def generate_answer(self, query: str, search_results: List[Dict]) -> Dict:
        """
        Generate answer based on found code chunks.

        Args:
            query: user question
            search_results: found code chunks

        Returns:
            answer and full prompt
        """

        print(f"💬 Generating answer with LLM...")

        # 1. Form context from found files
        context_parts = []

        for i, result in enumerate(search_results):
            # Format each chunk nicely
            context_part = f"""
[Code Snippet {i + 1}] (Relevance: {result['score']:.3f})
File: {result['path']}
Lines: {result['lines']}
```{result['extension'][1:]}  
{result['text']}