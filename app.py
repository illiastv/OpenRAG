import streamlit as st
import uuid
import os
from dotenv import load_dotenv
from rag_core import ContextEngine

# Загружаем .env
load_dotenv()

st.set_page_config(page_title="BookMind", page_icon="📚", layout="wide")

# Инициализация сессии
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "uploaded_files_list" not in st.session_state:
    st.session_state.uploaded_files_list = []
if "active_files" not in st.session_state:
    st.session_state.active_files = set()
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "selected_result" not in st.session_state:
    st.session_state.selected_result = None
if "is_indexed" not in st.session_state:
    st.session_state.is_indexed = False

# Читаем API ключ из .env
openai_key = os.getenv("OPENAI_API_KEY")

if not openai_key:
    st.error("❌ OPENAI_API_KEY не найден в .env файле!")
    st.stop()

# Инициализация движка
try:
    if "engine" not in st.session_state:
        st.session_state.engine = ContextEngine(openai_key)
    engine = st.session_state.engine
except Exception as e:
    st.error(f"Ошибка инициализации: {e}")
    st.stop()

# === LAYOUT: 3 колонки ===
left_col, center_col, right_col = st.columns([1.5, 3, 1.5])

# === ЛЕВАЯ ПАНЕЛЬ: БИБЛИОТЕКА ===
with left_col:
    st.header("📚 Библиотека")
    
    if st.session_state.uploaded_files_list:
        st.caption(f"Файлов в базе: {len(st.session_state.uploaded_files_list)}")
        
        # Кнопка "Выбрать все"
        if st.button("Выбрать все", key="select_all", use_container_width=True):
             st.session_state.active_files = set(f["name"] for f in st.session_state.uploaded_files_list)
             st.rerun()

        for idx, file_info in enumerate(st.session_state.uploaded_files_list):
            filename = file_info["name"]
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([0.15, 0.65, 0.2])
                
                # Чекбокс
                with col1:
                    is_active = filename in st.session_state.active_files
                    if st.checkbox("✓", value=is_active, key=f"chk_{idx}"):
                        st.session_state.active_files.add(filename)
                    else:
                        st.session_state.active_files.discard(filename)
                
                # Имя файла
                with col2:
                    icon = "📕" if filename.endswith('.pdf') else "📄"
                    st.write(f"{icon} {filename}")
                
                # Удаление (только визуально из списка, из базы удалять сложно без переиндексации)
                with col3:
                    if st.button("🗑️", key=f"del_{idx}"):
                        st.session_state.uploaded_files_list.pop(idx)
                        st.session_state.active_files.discard(filename)
                        st.rerun()
    else:
        st.info("👈 Загрузите файлы или библиотеку справа")

# === ЦЕНТРАЛЬНАЯ ПАНЕЛЬ: ПОИСК ===
with center_col:
    st.header("🔍 Поиск по смыслу")
    
    query = st.text_input(
        "Что ищем?", 
        placeholder="Например: 'Что автор пишет о свободе?'",
        label_visibility="collapsed"
    )
    
    if st.button("🔎 Найти", type="primary", use_container_width=True):
        if not st.session_state.is_indexed and not st.session_state.uploaded_files_list:
            st.warning("⚠️ База пуста. Загрузите файлы и нажмите 'Индексировать'.")
        elif not st.session_state.active_files:
            st.warning("⚠️ Выберите галочками книги для поиска (слева).")
        elif not query:
            st.warning("⚠️ Введите запрос.")
        else:
            with st.spinner("Анализирую тексты..."):
                results = engine.search(
                    query, 
                    st.session_state.session_id, 
                    limit=15,
                    filter_files=list(st.session_state.active_files)
                )
                st.session_state.search_results = results
                if not results:
                    st.warning("Ничего не найдено.")

    st.divider()
    
    if st.session_state.search_results:
        st.subheader(f"Результаты ({len(st.session_state.search_results)})")
        
        for idx, result in enumerate(st.session_state.search_results):
            with st.container(border=True):
                c1, c2 = st.columns([0.8, 0.2])
                with c1:
                    st.markdown(f"**{result['filename']}** (стр. {result.get('page', '?')})")
                with c2:
                    st.caption(f"Score: {result['score']:.2f}")
                
                preview = result['text'][:300] + "..."
                st.write(preview)
                
                bc1, bc2 = st.columns(2)
                if bc1.button("📖 Читать", key=f"read_{idx}"):
                    st.session_state.selected_result = result
                
                if bc2.button("📋 Цитата", key=f"copy_{idx}"):
                    citation = f'"{result["text"]}"\n— {result["filename"]}, стр. {result.get("page", "?")}'
                    st.code(citation, language="text")

    # Модалка с полным текстом
    if st.session_state.selected_result:
        st.divider()
        res = st.session_state.selected_result
        st.info(f"📄 {res['filename']} | Страница {res.get('page', '?')}")
        st.text_area("Полный текст", value=res['text'], height=300)
        if st.button("Закрыть"):
            st.session_state.selected_result = None
            st.rerun()

# === ПРАВАЯ ПАНЕЛЬ: УПРАВЛЕНИЕ ===
with right_col:
    st.header("⚙️ Управление")
    
    # 1. Загрузка новых файлов
    with st.expander("📤 1. Добавить файлы", expanded=True):
        uploaded_files = st.file_uploader("PDF, TXT, MD...", accept_multiple_files=True)
        
        if uploaded_files and st.button("🚀 Индексировать", type="primary", use_container_width=True):
            with st.spinner("Обработка и индексация (это стоит $)..."):
                # Сохраняем ссылки на файлы
                for f in uploaded_files:
                    # Проверяем дубликаты
                    if f.name not in [x["name"] for x in st.session_state.uploaded_files_list]:
                        st.session_state.uploaded_files_list.append({"name": f.name, "file": f})
                        st.session_state.active_files.add(f.name)
                
                # Индексируем
                count = engine.process_and_index(uploaded_files, st.session_state.session_id)
                st.session_state.is_indexed = True
                st.success(f"Готово! Добавлено {count} фрагментов.")
                st.rerun()

    # 2. Сохранение/Загрузка (ЭКОНОМИЯ ДЕНЕГ)
    with st.expander("💾 2. Сохранить/Загрузить Библиотеку", expanded=True):
        st.caption("Сохраните файл .lib, чтобы не платить за индексацию завтра.")
        
        # Кнопка СКАЧАТЬ (появляется только если есть что качать)
        if st.session_state.is_indexed:
            lib_data = engine.export_index(st.session_state.session_id)
            if lib_data:
                st.download_button(
                    label="💾 Скачать мою библиотеку (.lib)",
                    data=lib_data,
                    file_name="my_library.lib",
                    mime="application/octet-stream",
                    use_container_width=True
                )
        
        # Кнопка ЗАГРУЗИТЬ
        uploaded_lib = st.file_uploader("📂 Открыть .lib файл", type="lib")
        if uploaded_lib:
            if st.button("Восстановить библиотеку", use_container_width=True):
                with st.spinner("Восстановление памяти..."):
                    try:
                        count, filenames = engine.import_index(st.session_state.session_id, uploaded_lib.getvalue())
                        
                        # Восстанавливаем список файлов в UI
                        st.session_state.uploaded_files_list = [{"name": name} for name in filenames]
                        st.session_state.active_files = set(filenames)
                        st.session_state.is_indexed = True
                        
                        st.success(f"Успешно! Загружено {len(filenames)} книг ({count} фрагментов).")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка файла: {e}")

    # Статистика
    st.divider()
    st.metric("Активных книг", len(st.session_state.active_files))
    if st.button("🧹 Полный сброс", use_container_width=True):
        st.session_state.clear()
        st.rerun()
# Футер
st.divider()
st.caption("💡 Совет: Включите только нужные книги для более точного поиска")