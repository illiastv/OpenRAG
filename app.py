# app.py
import streamlit as st
import os
from code_rag import CodeRAG
from dotenv import load_dotenv

# Page configuration
st.set_page_config(page_title="Code RAG Visualizer", layout="wide", page_icon="🧠")
load_dotenv()

# --- INITIALIZATION ---
if "rag" not in st.session_state:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("No API Key found! Create a .env file or enter the key in the sidebar.")
    else:
        st.session_state.rag = CodeRAG(openai_api_key=api_key)

# Initialize settings in session state
if "chunk_size" not in st.session_state:
    st.session_state.chunk_size = 1000
if "top_k" not in st.session_state:
    st.session_state.top_k = 5
if "chunking_strategy" not in st.session_state:
    st.session_state.chunking_strategy = "lines"

# --- SIDEBAR (Settings) ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key input
    if "rag" not in st.session_state:
        key_input = st.text_input("OpenAI API Key", type="password")
        if key_input:
            st.session_state.rag = CodeRAG(openai_api_key=key_input)
            st.rerun()
    else:
        st.success("✅ RAG Initialized")

    st.divider()
    
    # === CHUNKING SETTINGS ===
    st.subheader("📄 Chunking Settings")
    
    st.session_state.chunking_strategy = st.selectbox(
        "Chunking Strategy:",
        options=["lines", "functions", "files"],
        help="lines = by line count, functions = by code blocks (future), files = whole files"
    )
    
    st.session_state.chunk_size = st.slider(
        "Chunk Size (characters):",
        min_value=500,
        max_value=3000,
        value=st.session_state.chunk_size,
        step=100,
        help="Larger chunks = more context but fewer chunks retrieved"
    )
    
    st.caption(f"📊 Current: {st.session_state.chunk_size} chars per chunk")
    
    st.divider()
    
    # === RETRIEVAL SETTINGS ===
    st.subheader("🔍 Retrieval Settings")
    
    st.session_state.top_k = st.slider(
        "Number of chunks to retrieve:",
        min_value=1,
        max_value=15,
        value=st.session_state.top_k,
        help="How many relevant code chunks to use for answering"
    )
    
    st.caption(f"🎯 Will retrieve top {st.session_state.top_k} most relevant chunks")
    
    # Show estimated token usage
    estimated_tokens = st.session_state.top_k * (st.session_state.chunk_size // 4)  # rough estimate
    st.info(f"💰 Est. context size: ~{estimated_tokens:,} tokens")
    
    st.divider()
    
    # === INDEXING ===
    st.subheader("🚀 Index Project")
    
    path_input = st.text_input("Path to project:", value="./my_project")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Re-Index", use_container_width=True):
            if "rag" in st.session_state:
                with st.spinner("Indexing with new settings..."):
                    stats = st.session_state.rag.index_codebase(
                        path_input,
                        chunk_size=st.session_state.chunk_size
                    )
                st.success(f"✅ Indexed!\n\n📁 Files: {stats['total_files']}\n📦 Chunks: {stats['total_chunks']}")
            else:
                st.error("Initialize RAG first")
    
    with col2:
        if st.button("🗑️ Clear DB", use_container_width=True):
            if "rag" in st.session_state:
                try:
                    st.session_state.rag.qdrant_client.delete_collection(
                        st.session_state.rag.collection_name
                    )
                    st.session_state.rag._setup_collection()
                    st.success("Database cleared!")
                except Exception as e:
                    st.error(f"Error: {e}")

# --- MAIN SCREEN ---
st.title("🧠 Code RAG Dashboard")
st.caption(f"🎛️ Settings: {st.session_state.chunk_size} char chunks | Top-{st.session_state.top_k} retrieval")

# Tabs
tab1, tab2, tab3 = st.tabs(["💬 Chat with Code", "💾 Database Viewer", "🔍 Prompt Inspector"])

# === TAB 1: CHAT ===
with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input question
    if prompt := st.chat_input("Ask a question about the code..."):
        if "rag" in st.session_state:
            # Add user question
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get answer with custom top_k
            with st.spinner("Searching and generating answer..."):
                result = st.session_state.rag.ask(prompt, top_k=st.session_state.top_k)
            
            st.session_state.last_result = result
            answer = result["answer"]
            
            # Add bot answer
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)
                
                # Show retrieved chunks
                with st.expander(f"🔍 Retrieved {len(result['retrieved_chunks'])} code chunks (Context)"):
                    for i, chunk in enumerate(result["retrieved_chunks"]):
                        st.markdown(f"### 🥇 Rank #{i+1} - Score: {chunk['score']:.4f}")
                        st.markdown(f"**File:** `{chunk['path']}` (lines {chunk['lines']})")
                        st.code(chunk['text'], language=chunk['extension'][1:])
                        st.divider()
        else:
            st.error("RAG is not initialized")

# === TAB 2: DATABASE VISUALIZATION ===
with tab2:
    st.header("💾 Vector Database Content")
    
    if "rag" in st.session_state:
        try:
            client = st.session_state.rag.qdrant_client
            collection_name = st.session_state.rag.collection_name
            
            # Get collection info
            col_info = client.get_collection(collection_name)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Chunks", col_info.points_count)
            with col2:
                st.metric("Vector Dimensions", col_info.config.params.vectors.size)
            with col3:
                st.metric("Distance Metric", col_info.config.params.vectors.distance.name)
            
            st.divider()
            
            # Control panel
            col_a, col_b = st.columns([3, 1])
            with col_a:
                limit = st.slider("Show records:", 10, 200, 50)
            with col_b:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
            
            # Fetch data
            records, _ = client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Format table
            data_list = []
            for record in records:
                payload = record.payload
                data_list.append({
                    "ID": str(record.id)[:8] + "...",
                    "File": payload.get('filename', 'N/A'),
                    "Path": payload.get('relative_path', 'N/A'),
                    "Lines": f"{payload.get('start_line', 0)}-{payload.get('end_line', 0)}",
                    "Size": len(payload.get('text', '')),
                    "Preview": payload.get('text', '')[:100] + "...",
                    "Full Text": payload.get('text', ''),
                    "Extension": payload.get('extension', '')
                })
            
            if data_list:
                st.dataframe(
                    data_list,
                    column_config={
                        "Full Text": None,  # Hide full text column
                        "Extension": None,
                        "Size": st.column_config.NumberColumn("Size (chars)", format="%d"),
                    },
                    use_container_width=True,
                    height=400
                )
                
                # Detailed view
                st.subheader("📄 Detailed Chunk View")
                selected_index = st.selectbox(
                    "Select chunk to view:",
                    range(len(data_list)),
                    format_func=lambda i: f"{data_list[i]['File']} - {data_list[i]['Path']}"
                )
                
                selected = data_list[selected_index]
                st.text(f"📁 File: {selected['Path']}")
                st.text(f"📏 Lines: {selected['Lines']}")
                st.text(f"📊 Size: {selected['Size']} characters")
                
                ext = selected['Extension'].replace('.', '') if selected['Extension'] else 'text'
                st.code(selected['Full Text'], language=ext)
                
            else:
                st.info("🗂️ Database is empty. Index some code first!")
                
        except Exception as e:
            st.error(f"❌ Error reading database: {e}")
            st.caption("Database might not be created yet. Index files first.")
    else:
        st.warning("⚠️ Enter API Key to access the database")

# === TAB 3: PROMPT INSPECTOR ===
with tab3:
    st.header("🔍 Prompt Inspector")
    st.caption("See exactly what was sent to the LLM")
    
    if st.session_state.get("last_result"):
        result = st.session_state.last_result
        
        st.subheader("📝 User Question")
        st.info(result["question"])
        
        st.subheader("🤖 Full Prompt Sent to GPT")
        st.code(result["full_prompt"], language="markdown")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Copy Prompt", use_container_width=True):
                st.write("Prompt copied! (use Ctrl+C)")
        with col2:
            # Download prompt as file
            st.download_button(
                label="💾 Download Prompt",
                data=result["full_prompt"],
                file_name="prompt.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        st.divider()
        
        st.subheader("🎯 Retrieved Context Breakdown")
        for i, chunk in enumerate(result["retrieved_chunks"]):
            with st.expander(f"Chunk {i+1}: {chunk['path']} (Score: {chunk['score']:.3f})"):
                st.text(f"Lines: {chunk['lines']}")
                st.code(chunk['text'], language=chunk['extension'][1:])
        
        st.divider()
        
        st.subheader("💡 Generated Answer")
        st.success(result["answer"])
        
    else:
        st.info("👆 Ask a question in the Chat tab first to see the prompt details here!")
        st.caption("This tab will show the full prompt that was sent to GPT-4")