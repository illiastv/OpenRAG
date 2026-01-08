# app.py
import streamlit as st
import os
from code_rag import CodeRAG # Import your class from the neighboring file
from dotenv import load_dotenv

# Page configuration
st.set_page_config(page_title="Code RAG Visualizer", layout="wide")
load_dotenv()

# --- INITIALIZATION ---
if "rag" not in st.session_state:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("No API Key found! Create a .env file or enter the key in the sidebar.")
    else:
        # Initialize your class
        st.session_state.rag = CodeRAG(openai_api_key=api_key)

# --- SIDEBAR (Settings) ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # If the key is not in .env, it can be entered here
    if "rag" not in st.session_state:
        key_input = st.text_input("OpenAI API Key", type="password")
        if key_input:
            st.session_state.rag = CodeRAG(openai_api_key=key_input)
            st.rerun()

    st.divider()
    
    # Indexing
    path_input = st.text_input("Path to project (local):", value="./my_project")
    if st.button("🚀 Index Database"):
        if "rag" in st.session_state:
            with st.spinner("Reading files and vectorizing..."):
                stats = st.session_state.rag.index_codebase(path_input)
            st.success(f"Done! Files: {stats['total_files']}, Chunks: {stats['total_chunks']}")
        else:
            st.error("Initialize RAG first (Key required)")

# --- MAIN SCREEN ---
st.title("🧠 Code RAG Dashboard")

# Tabs: Chat and Database Viewer
tab1, tab2 = st.tabs(["💬 Chat with Code", "💾 Database Viewer (Storage)"])

# === TAB 1: CHAT ===
with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = []

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

            # Get answer from your script
            with st.spinner("Thinking..."):
                result = st.session_state.rag.ask(prompt)
            
            answer = result["answer"]
            
            # Add bot answer
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)
                
                # Show which code chunks were found (Debug)
                with st.expander("🔍 What was found in DB (Context):"):
                    for chunk in result["retrieved_chunks"]:
                        st.markdown(f"**File:** `{chunk['path']}` (lines {chunk['lines']})")
                        st.markdown(f"**Relevance:** {chunk['score']:.4f}")
                        st.code(chunk['text'], language=chunk['extension'][1:])
        else:
            st.error("RAG is not initialized")

# === TAB 2: DATABASE VISUALIZATION ===
with tab2:
    st.header("Vector Database Content (Qdrant)")
    
    if "rag" in st.session_state:
        try:
            client = st.session_state.rag.qdrant_client
            collection_name = st.session_state.rag.collection_name
            
            # Get collection info
            col_info = client.get_collection(collection_name)
            st.metric("Total chunks in DB", col_info.points_count)
            
            # Refresh button
            if st.button("Refresh Table"):
                pass
            
            # Fetch data (scroll the database)
            # Taking the first 50 records for example
            records, _ = client.scroll(
                collection_name=collection_name,
                limit=50,
                with_payload=True,
                with_vectors=False
            )
            
            # Format table for display
            data_list = []
            for record in records:
                payload = record.payload
                data_list.append({
                    "ID": record.id,
                    "File": payload.get('filename'),
                    "Path": payload.get('relative_path'),
                    "Preview": payload.get('text')[:50] + "...", # Truncate text
                    "Full Text": payload.get('text') # For detailed view
                })
            
            if data_list:
                # Show table
                st.dataframe(data_list, column_config={
                    "Full Text": st.column_config.TextColumn(help="Full chunk text")
                }, use_container_width=True)
                
                # Detailed view of selected item
                st.subheader("Detailed Chunk View")
                selected_id = st.selectbox("Select Chunk ID", [d["ID"] for d in data_list])
                
                selected_item = next(item for item in data_list if item["ID"] == selected_id)
                st.text(f"File: {selected_item['Path']}")
                st.code(selected_item['Full Text'])
                
            else:
                st.info("Database is empty. Go to settings and click 'Index Database'.")
                
        except Exception as e:
            st.error(f"Error reading database: {e}")
            st.caption("Database might not be created yet. Index the files.")
    else:
        st.warning("Enter API Key to access the database")