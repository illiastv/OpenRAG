import streamlit as st
import uuid
from rag_core import ContextEngine

st.set_page_config(page_title="Universal Context Builder", page_icon="📚", layout="wide")

# Инициализация сессии
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "selected_snippets" not in st.session_state:
    st.session_state.selected_snippets = []
if "indexed" not in st.session_state:
    st.session_state.indexed = False
if "last_search" not in st.session_state:
    st.session_state.last_search = []

# --- SIDEBAR: НАСТРОЙКИ ---
with st.sidebar:
    st.header("🔑 Settings")
    openai_key = st.text_input("OpenAI API Key", type="password", help="Needed for embeddings")
    st.caption("⚠️ Using In-Memory Storage (Data lost on refresh)")

# --- MAIN ---
st.title("📚 Context Builder: Code & Docs")
st.markdown("Upload **PDFs** or **Code**, search intelligently, and get context.")

if not openai_key:
    st.warning("👈 Please enter your OpenAI API Key in the sidebar to start.")
    st.stop()

# Инициализация движка (всегда локально)
try:
    if "engine" not in st.session_state:
        st.session_state.engine = ContextEngine(openai_key)
    engine = st.session_state.engine
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# 1. ЗАГРУЗКА ФАЙЛОВ
st.subheader("📤 1. Upload Documents or Code")
uploaded_files = st.file_uploader(
    "Supported: .pdf, .py, .js, .txt, .md, etc.", 
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("🚀 Index Files", type="primary"):
        with st.spinner("Processing PDF/Code & Embedding..."):
            try:
                count = engine.process_and_index(uploaded_files, st.session_state.session_id)
                st.session_state.indexed = True
                st.success(f"✅ Indexed {len(uploaded_files)} files ({count} chunks) into knowledge base!")
            except Exception as e:
                st.error(f"Indexing error: {e}")

st.divider()

# 2. ПОИСК
st.subheader("🔍 2. Search Your Documents")
query = st.text_input("What do you need context for?", placeholder="e.g. 'How does authentication work?' or 'Summary of Chapter 4'")

if query and st.button("🔎 Find Context", type="primary"):
    if not st.session_state.indexed:
        st.warning("⚠️ Please index files first!")
    else:
        with st.spinner("Searching..."):
            try:
                results = engine.search(query, st.session_state.session_id, limit=10)
                st.session_state.last_search = results
                if not results:
                    st.warning("No results found. Try different keywords.")
            except Exception as e:
                st.error(f"Search error: {e}")

st.divider()

# 3. ПОКАЗ РЕЗУЛЬТАТОВ И ВЫБОР
if st.session_state.last_search:
    st.subheader("✅ 3. Select Snippets")
    
    for idx, res in enumerate(st.session_state.last_search):
        snippet_id = f"{res['filename']}_{res['chunk_id']}"
        is_checked = snippet_id in [s['id'] for s in st.session_state.selected_snippets]
        
        with st.container(border=True):
            col1, col2 = st.columns([0.08, 0.92])
            
            with col1:
                toggle = st.checkbox("", key=f"chk_{idx}_{snippet_id}", value=is_checked)
            
            with col2:
                st.markdown(f"**📄 {res['filename']}** | Relevance: `{res['score']:.3f}`")
                preview = res['text'][:300] + "..." if len(res['text']) > 300 else res['text']
                st.text(preview)
                
                with st.expander("Show full text"):
                    st.code(res['text'], language="text")

            # Логика добавления в корзину
            if toggle and not is_checked:
                st.session_state.selected_snippets.append({
                    "id": snippet_id, 
                    "text": res['text'], 
                    "file": res['filename']
                })
            elif not toggle and is_checked:
                st.session_state.selected_snippets = [
                    s for s in st.session_state.selected_snippets if s['id'] != snippet_id
                ]

# 4. ФИНАЛЬНЫЙ КОНТЕКСТ
st.divider()
st.subheader("📋 4. Your Context (Copy & Paste)")

if st.session_state.selected_snippets:
    total_chars = sum([len(s['text']) for s in st.session_state.selected_snippets])
    st.info(f"📊 Selected {len(st.session_state.selected_snippets)} snippets. Approx **{total_chars // 4} tokens**.")
    
    # Формируем итоговый промпт
    final_prompt = "I have the following context documents:\n\n"
    for item in st.session_state.selected_snippets:
        final_prompt += f"--- Source: {item['file']} ---\n{item['text']}\n\n"
    
    if query:
        final_prompt += f"My Request: {query}\n"
    
    st.text_area("📝 Final Context", value=final_prompt, height=400)
    
    if st.button("🗑️ Clear Selection"):
        st.session_state.selected_snippets = []
        st.rerun()
else:
    st.write("👆 Select snippets above to generate the final prompt.")