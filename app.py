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
if "custom_system_prompt" not in st.session_state:
    st.session_state.custom_system_prompt = None
if "custom_context_template" not in st.session_state:
    st.session_state.custom_context_template = None
if "custom_user_template" not in st.session_state:
    st.session_state.custom_user_template = None

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
    
    # === CHUNKING STRATEGY EDITOR ===
    st.subheader("📄 Chunking Strategy Editor")
    
    strategy_info = {
        "lines": "Split by line count (smart boundaries)",
        "functions": "Split by functions/classes (language-aware)",
        "files": "Whole file as one chunk"
    }
    
    st.session_state.chunking_strategy = st.selectbox(
        "Chunking Strategy:",
        options=["lines", "functions", "files"],
        format_func=lambda x: f"{x.upper()} - {strategy_info[x]}",
        help="Choose how to split your code into chunks"
    )
    
    if st.session_state.chunking_strategy != "files":
        st.session_state.chunk_size = st.slider(
            "Chunk Size (characters):",
            min_value=500,
            max_value=3000,
            value=st.session_state.chunk_size,
            step=100,
            help="Larger chunks = more context but fewer chunks retrieved"
        )
        st.caption(f"📊 Current: {st.session_state.chunk_size} chars per chunk")
    else:
        st.info("ℹ️ Files strategy uses entire file as one chunk (no size limit)")
    
    if st.button("💾 Apply Strategy", use_container_width=True):
        if "rag" in st.session_state:
            st.session_state.rag.set_chunking_strategy(
                st.session_state.chunking_strategy,
                st.session_state.chunk_size if st.session_state.chunking_strategy != "files" else None
            )
            st.success("✅ Strategy applied! Re-index to use new strategy.")
        else:
            st.error("Initialize RAG first")
    
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
    
    # === PROMPT EDITOR ===
    st.subheader("✏️ Prompt Editor")
    
    prompt_tab1, prompt_tab2, prompt_tab3 = st.tabs(["System", "Context", "User"])
    
    with prompt_tab1:
        default_system = "You are a helpful code assistant that explains code clearly."
        st.session_state.custom_system_prompt = st.text_area(
            "System Prompt:",
            value=st.session_state.custom_system_prompt or default_system,
            height=100,
            help="Defines the AI's role and behavior"
        )
        if st.button("🔄 Reset to Default", key="reset_system"):
            st.session_state.custom_system_prompt = default_system
            st.rerun()
    
    with prompt_tab2:
        default_context = """[Code Snippet {i}] (Relevance: {score:.3f})
File: {path}
Lines: {lines}
```{extension}
{text}
```"""
        st.session_state.custom_context_template = st.text_area(
            "Context Template:",
            value=st.session_state.custom_context_template or default_context,
            height=150,
            help="Template for formatting code chunks. Use {i+1}, {score}, {path}, {lines}, {extension}, {text}"
        )
        if st.button("🔄 Reset to Default", key="reset_context"):
            st.session_state.custom_context_template = default_context
            st.rerun()
    
    with prompt_tab3:
        default_user = """You are an expert code assistant. Help the user understand their codebase.

Based on the following code snippets from the codebase, answer the user's question.

Code Context:
{context}

User Question: {query}

Please provide a clear, helpful answer. Reference specific files and line numbers when relevant.

Answer:"""
        st.session_state.custom_user_template = st.text_area(
            "User Prompt Template:",
            value=st.session_state.custom_user_template or default_user,
            height=200,
            help="Main prompt template. Use {context} and {query} placeholders"
        )
        if st.button("🔄 Reset to Default", key="reset_user"):
            st.session_state.custom_user_template = default_user
            st.rerun()
    
    if st.button("💾 Save Prompts", use_container_width=True):
        if "rag" in st.session_state:
            st.session_state.rag.set_prompts(
                system_prompt=st.session_state.custom_system_prompt,
                context_template=st.session_state.custom_context_template,
                user_prompt_template=st.session_state.custom_user_template
            )
            st.success("✅ Prompts saved!")
        else:
            st.error("Initialize RAG first")
    
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
tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat with Code", "💾 Database Viewer", "🔍 Prompt Inspector", "📊 Analytics"])

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

            # Get answer with custom top_k and prompts
            with st.spinner("Searching and generating answer..."):
                result = st.session_state.rag.ask(
                    prompt, 
                    top_k=st.session_state.top_k,
                    system_prompt=st.session_state.custom_system_prompt,
                    context_template=st.session_state.custom_context_template,
                    user_prompt_template=st.session_state.custom_user_template
                )
            
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

# === TAB 4: ANALYTICS ===
with tab4:
    st.header("📊 Analytics Dashboard")
    st.caption("Track usage, costs, and performance metrics")
    
    if "rag" in st.session_state:
        analytics = st.session_state.rag.get_analytics()
        
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Queries", analytics["total_queries"])
        with col2:
            st.metric("Total Tokens", f"{analytics['total_tokens']:,}")
        with col3:
            st.metric("Total Cost", f"${analytics['total_cost']:.4f}")
        with col4:
            st.metric("Avg Cost/Query", f"${analytics['avg_cost_per_query']:.4f}")
        
        st.divider()
        
        # Cost Breakdown
        st.subheader("💰 Cost Breakdown")
        cost_col1, cost_col2 = st.columns(2)
        with cost_col1:
            st.metric("Embedding Cost", f"${analytics['embedding_cost']:.4f}")
        with cost_col2:
            st.metric("Generation Cost", f"${analytics['generation_cost']:.4f}")
        
        st.divider()
        
        # Recent Queries
        st.subheader("📝 Recent Query History")
        if analytics["recent_queries"]:
            query_data = []
            for q in analytics["recent_queries"]:
                import datetime
                timestamp = datetime.datetime.fromtimestamp(q["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                query_data.append({
                    "Time": timestamp,
                    "Query": q["query"][:50] + "..." if len(q["query"]) > 50 else q["query"],
                    "Tokens": q["tokens"],
                    "Cost": f"${q['cost']:.4f}",
                    "Time (s)": f"{q['time']:.2f}"
                })
            
            st.dataframe(
                query_data,
                use_container_width=True,
                height=300
            )
        else:
            st.info("No queries yet. Start asking questions in the Chat tab!")
        
        st.divider()
        
        # Reset Analytics
        if st.button("🗑️ Reset Analytics", type="secondary"):
            st.session_state.rag.analytics = {
                "total_queries": 0,
                "total_tokens_used": 0,
                "total_cost": 0.0,
                "total_embedding_cost": 0.0,
                "total_generation_cost": 0.0,
                "query_history": []
            }
            st.success("Analytics reset!")
            st.rerun()
        
    else:
        st.warning("⚠️ Initialize RAG to see analytics")