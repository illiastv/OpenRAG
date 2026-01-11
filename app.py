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

# Читаем API ключ из .env
openai_key = os.getenv("OPENAI_API_KEY")

if not openai_key:
    st.error("❌ OPENAI_API_KEY не найден в .env файле!")
    st.stop()

# Инициализация движка (пересоздаем каждый раз для обновления кода)
try:
    engine = ContextEngine(openai_key)
    if "engine" not in st.session_state:
        st.session_state.engine = engine
except Exception as e:
    st.error(f"Ошибка инициализации: {e}")
    st.stop()
engine = st.session_state.engine

# === LAYOUT: 3 колонки ===
left_col, center_col, right_col = st.columns([1.5, 3, 1.5])

# === ЛЕВАЯ ПАНЕЛЬ: БИБЛИОТЕКА ===
with left_col:
    st.header("📚 Библиотека")
    
    if st.session_state.uploaded_files_list:
        st.caption(f"Загружено файлов: {len(st.session_state.uploaded_files_list)}")
        
        for idx, file_info in enumerate(st.session_state.uploaded_files_list):
            filename = file_info["name"]
            
            with st.container(border=True):
                col1, col2, col3 = st.columns([0.1, 0.6, 0.3])
                
                # Чекбокс для включения/выключения
                with col1:
                    is_active = st.checkbox(
                        "✓", 
                        value=filename in st.session_state.active_files,
                        key=f"active_{idx}_{filename}",
                        label_visibility="collapsed"
                    )
                    
                    if is_active and filename not in st.session_state.active_files:
                        st.session_state.active_files.add(filename)
                    elif not is_active and filename in st.session_state.active_files:
                        st.session_state.active_files.discard(filename)
                
                # Название файла
                with col2:
                    icon = "📕" if filename.endswith('.pdf') else "📄"
                    st.write(f"{icon} {filename[:20]}..." if len(filename) > 20 else f"{icon} {filename}")
                
                # Кнопка удаления
                with col3:
                    if st.button("🗑️", key=f"del_{idx}_{filename}"):
                        st.session_state.uploaded_files_list.pop(idx)
                        st.session_state.active_files.discard(filename)
                        st.rerun()
    else:
        st.info("👈 Загрузите файлы справа")

# === ЦЕНТРАЛЬНАЯ ПАНЕЛЬ: ПОИСК И РЕЗУЛЬТАТЫ ===
with center_col:
    st.header("🔍 Поиск по книгам")
    
    # Поле поиска
    query = st.text_input(
        "Что вы ищете?", 
        placeholder="Например: 'Что автор пишет о свободе?'",
        label_visibility="collapsed"
    )
    
    # Кнопка поиска
    if st.button("🔎 Найти", type="primary", use_container_width=True):
        if not st.session_state.uploaded_files_list:
            st.warning("⚠️ Сначала загрузите файлы!")
        elif not st.session_state.active_files:
            st.warning("⚠️ Выберите хотя бы один файл для поиска!")
        elif not query:
            st.warning("⚠️ Введите поисковый запрос!")
        else:
            with st.spinner("Ищу..."):
                try:
                    results = engine.search(
                        query, 
                        st.session_state.session_id, 
                        limit=15,
                        filter_files=list(st.session_state.active_files)
                    )
                    st.session_state.search_results = results
                    if not results:
                        st.warning("Ничего не найдено. Попробуйте другие слова.")
                except Exception as e:
                    st.error(f"Ошибка поиска: {e}")
    
    st.divider()
    
    # Показываем результаты
    if st.session_state.search_results:
        st.subheader(f"Найдено: {len(st.session_state.search_results)} цитат")
        
        for idx, result in enumerate(st.session_state.search_results):
            with st.container(border=True):
                # Заголовок
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.markdown(f"**📄 {result['filename']}** | Страница {result.get('page', '?')}")
                with col2:
                    st.caption(f"Релевантность: {result['score']:.2f}")
                
                # Превью текста
                preview = result['text'][:400] + "..." if len(result['text']) > 400 else result['text']
                st.write(preview)
                
                # Кнопки действий
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📖 Открыть полностью", key=f"open_{idx}"):
                        st.session_state.selected_result = result
                with col2:
                    if st.button("📋 Копировать цитату", key=f"copy_{idx}"):
                        citation = f'"{result["text"]}"\n\n— {result["filename"]}, стр. {result.get("page", "?")}'
                        st.code(citation, language="text")
                        st.success("✅ Скопируйте текст выше")
                with col3:
                    # Placeholder для будущего "Открыть в PDF"
                    st.button("📕 В PDF", key=f"pdf_{idx}", disabled=True)
    
    # Модальное окно с полным текстом
    if st.session_state.selected_result:
        st.divider()
        st.subheader("📖 Полный фрагмент")
        
        result = st.session_state.selected_result
        st.markdown(f"**Источник:** {result['filename']}, страница {result.get('page', '?')}")
        st.text_area(
            "Текст", 
            value=result['text'], 
            height=300,
            label_visibility="collapsed"
        )
        
        if st.button("❌ Закрыть"):
            st.session_state.selected_result = None
            st.rerun()

# === ПРАВАЯ ПАНЕЛЬ: УПРАВЛЕНИЕ ===
with right_col:
    st.header("⚙️ Управление")
    
    # Загрузка файлов
    with st.expander("➕ Добавить файлы", expanded=True):
        uploaded_files = st.file_uploader(
            "PDF, TXT, MD, PY, JS...",
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        if uploaded_files and st.button("📥 Загрузить", use_container_width=True):
            # Добавляем в список
            for file in uploaded_files:
                if file.name not in [f["name"] for f in st.session_state.uploaded_files_list]:
                    st.session_state.uploaded_files_list.append({
                        "name": file.name,
                        "file": file
                    })
                    st.session_state.active_files.add(file.name)
            st.success(f"✅ Добавлено файлов: {len(uploaded_files)}")
            st.rerun()
    
    # Индексация
    with st.expander("🔄 Индексировать базу"):
        st.caption("Создает поисковый индекс из всех загруженных файлов")
        
        if st.button("🚀 Индексировать сейчас", type="primary", use_container_width=True):
            if not st.session_state.uploaded_files_list:
                st.warning("⚠️ Нет файлов для индексации!")
            else:
                with st.spinner("Обрабатываю файлы..."):
                    try:
                        files_to_index = [f["file"] for f in st.session_state.uploaded_files_list]
                        count = engine.process_and_index(files_to_index, st.session_state.session_id)
                        st.success(f"✅ Проиндексировано {count} фрагментов из {len(files_to_index)} файлов!")
                    except Exception as e:
                        st.error(f"Ошибка индексации: {e}")
    
    # Статистика
    st.divider()
    st.subheader("📊 Статистика")
    st.metric("Файлов загружено", len(st.session_state.uploaded_files_list))
    st.metric("Активных файлов", len(st.session_state.active_files))
    st.metric("Результатов поиска", len(st.session_state.search_results))
    
    # Сброс
    if st.button("🗑️ Очистить всё", use_container_width=True):
        st.session_state.uploaded_files_list = []
        st.session_state.active_files = set()
        st.session_state.search_results = []
        st.session_state.selected_result = None
        st.rerun()

# Футер
st.divider()
st.caption("💡 Совет: Включите только нужные книги для более точного поиска")