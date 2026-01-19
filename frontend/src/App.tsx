import React, { useState, useEffect } from 'react';
import { 
  Search, Upload, FolderOpen, FileText, Code, ChevronRight, ChevronDown,
  Loader2, X, Eye, Send, FileCode, Layers, GitBranch, CheckSquare, Square
} from 'lucide-react';
import axios from 'axios';

const API_URL = '/api';

// Список системних папок та файлів, які не обираються по дефолту
const SYSTEM_PATTERNS = [
  'node_modules',
  '.git',
  '.vscode',
  '.idea',
  '__pycache__',
  '.pytest_cache',
  '.mypy_cache',
  'venv',
  'env',
  '.env',
  'dist',
  'build',
  '.next',
  '.nuxt',
  '.cache',
  'coverage',
  '.nyc_output',
  '.sass-cache',
  '.parcel-cache',
  '.turbo',
  '.DS_Store',
  'Thumbs.db',
  '.gitignore',
  '.gitattributes',
  '.editorconfig',
  '.prettierignore',
  '.eslintignore',
  'package-lock.json',
  'yarn.lock',
  'pnpm-lock.yaml',
  '.npm',
  '.yarn',
];

const isSystemPath = (path: string): boolean => {
  const parts = path.split(/[/\\]/);
  return parts.some(part => {
    // Перевіряємо точну відповідність або початок з крапки
    return SYSTEM_PATTERNS.some(pattern => 
      part === pattern || 
      part.toLowerCase() === pattern.toLowerCase() ||
      (pattern.startsWith('.') && part.startsWith('.'))
    );
  });
};

interface FileItem {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: FileItem[];
  chunksCount?: number;
  isIndexed?: boolean;
  file?: File; // Зберігаємо File об'єкт для локально завантажених файлів
}

interface Chunk {
  id: string;
  chunk_id: number;
  text: string;
  filename: string;
  page?: number | string;
}

interface SearchResult {
  id: string;
  filename: string;
  page: number | string;
  score: number;
  text: string;
  chunk_id?: number;
}

const OpenRAGApp: React.FC = () => {
  const [sessionId] = useState<string>(() => {
    const saved = localStorage.getItem('session_id');
    const newId = Math.random().toString(36).substring(7);
    return saved || newId;
  });

  useEffect(() => {
    localStorage.setItem('session_id', sessionId);
    loadFiles();
  }, [sessionId]);

  const [localFileTree, setLocalFileTree] = useState<FileItem[]>([]); // Локально завантажені файли
  const [indexedFileTree, setIndexedFileTree] = useState<FileItem[]>([]); // Індексовані файли з сервера
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [isIndexing, setIsIndexing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [viewingFile, setViewingFile] = useState<string | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [selectedChunk, setSelectedChunk] = useState<Chunk | null>(null);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);

  const loadFiles = async () => {
    try {
      const response = await axios.get(`${API_URL}/files?session_id=${sessionId}`);
      const files = response.data.files || [];
      
      if (files.length === 0) {
        setIndexedFileTree([]);
        return;
      }
      
      // Створюємо дерево з файлів
      const tree: { [key: string]: FileItem } = {};
      
      files.forEach((file: any) => {
        const parts = file.filename.split(/[/\\]/).filter((p: string) => p);
        let currentPath = '';
        
        parts.forEach((part: string, index: number) => {
          const isLast = index === parts.length - 1;
          const path = currentPath ? `${currentPath}/${part}` : part;
          
          if (!tree[path]) {
            tree[path] = {
              name: part,
              path: path,
              type: isLast ? 'file' : 'folder',
              children: [],
              chunksCount: isLast ? file.chunks_count : undefined,
              isIndexed: isLast ? true : undefined
            };
          } else if (isLast) {
            // Оновлюємо інформацію про файл
            tree[path].chunksCount = file.chunks_count;
            tree[path].isIndexed = true;
          }
          
          // Додаємо до батьківської папки
          if (currentPath && tree[currentPath]) {
            if (!tree[currentPath].children) {
              tree[currentPath].children = [];
            }
            if (!tree[currentPath].children!.find(c => c.path === path)) {
              tree[currentPath].children!.push(tree[path]);
            }
          }
          
          currentPath = path;
        });
      });
      
      // Сортуємо дітей в кожній папці
      Object.values(tree).forEach(item => {
        if (item.children) {
          item.children.sort((a, b) => {
            if (a.type !== b.type) {
              return a.type === 'folder' ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
          });
        }
      });
      
      // Знаходимо кореневі елементи
      const rootItems: FileItem[] = [];
      const childPaths = new Set<string>();
      
      Object.values(tree).forEach(item => {
        if (item.children) {
          item.children.forEach(child => {
            childPaths.add(child.path);
          });
        }
      });
      
      Object.values(tree).forEach(item => {
        if (!childPaths.has(item.path)) {
          rootItems.push(item);
        }
      });
      
      // Сортуємо кореневі елементи
      rootItems.sort((a, b) => {
        if (a.type !== b.type) {
          return a.type === 'folder' ? -1 : 1;
        }
        return a.name.localeCompare(b.name);
      });
      
      setIndexedFileTree(rootItems);
    } catch (error) {
      console.error('Error loading files:', error);
      setIndexedFileTree([]);
    }
  };

  const handleFolderUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    const files = Array.from(e.target.files);
    
    // Створюємо дерево з локально завантажених файлів
    const tree: { [key: string]: FileItem } = {};
    
    files.forEach((file) => {
      // Використовуємо webkitRelativePath якщо доступний, інакше name
      const filePath = (file as any).webkitRelativePath || file.name;
      const parts = filePath.split(/[/\\]/).filter((p: string) => p);
      let currentPath = '';
      
      parts.forEach((part: string, index: number) => {
        const isLast = index === parts.length - 1;
        const path = currentPath ? `${currentPath}/${part}` : part;
        
        if (!tree[path]) {
          tree[path] = {
            name: part,
            path: path,
            type: isLast ? 'file' : 'folder',
            children: [],
            file: isLast ? file : undefined
          };
        }
        
        // Додаємо до батьківської папки
        if (currentPath && tree[currentPath]) {
          if (!tree[currentPath].children) {
            tree[currentPath].children = [];
          }
          if (!tree[currentPath].children!.find(c => c.path === path)) {
            tree[currentPath].children!.push(tree[path]);
          }
        }
        
        currentPath = path;
      });
    });
    
    // Знаходимо кореневі елементи
    const rootItems: FileItem[] = [];
    const childPaths = new Set<string>();
    
    Object.values(tree).forEach(item => {
      if (item.children) {
        item.children.forEach(child => {
          childPaths.add(child.path);
        });
      }
    });
    
    Object.values(tree).forEach(item => {
      if (!childPaths.has(item.path)) {
        rootItems.push(item);
      }
    });
    
    // Сортуємо
    rootItems.sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === 'folder' ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    });
    
    // Сортуємо дітей
    const sortChildren = (items: FileItem[]) => {
      items.forEach(item => {
        if (item.children) {
          item.children.sort((a, b) => {
            if (a.type !== b.type) {
              return a.type === 'folder' ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
          });
          sortChildren(item.children);
        }
      });
    };
    sortChildren(rootItems);
    
    setLocalFileTree(rootItems);
    
    // Автоматично обираємо всі файли, крім системних
    const getAllNonSystemFilePaths = (items: FileItem[]): string[] => {
      const paths: string[] = [];
      items.forEach(item => {
        if (item.type === 'file' && !item.isIndexed && item.file) {
          // Пропускаємо системні файли
          if (!isSystemPath(item.path)) {
            paths.push(item.path);
          }
        }
        if (item.children) {
          paths.push(...getAllNonSystemFilePaths(item.children));
        }
      });
      return paths;
    };
    
    const nonSystemPaths = getAllNonSystemFilePaths(rootItems);
    setSelectedFiles(new Set(nonSystemPaths));
    
    // Очищаємо input
    e.target.value = '';
  };

  const handleSendToRAG = async () => {
    if (selectedFiles.size === 0) {
      alert('Оберіть файли для відправки в RAG');
      return;
    }
    
    // Збираємо всі File об'єкти для обраних файлів
    const filesToSend: File[] = [];
    
    const collectFiles = (items: FileItem[]) => {
      items.forEach(item => {
        if (item.type === 'file' && item.file && selectedFiles.has(item.path)) {
          filesToSend.push(item.file);
        }
        if (item.children) {
          collectFiles(item.children);
        }
      });
    };
    
    collectFiles(localFileTree);
    
    if (filesToSend.length === 0) {
      alert('Не знайдено файлів для відправки');
      return;
    }
    
    setIsIndexing(true);
    
    const formData = new FormData();
    formData.append('session_id', sessionId);
    filesToSend.forEach(file => {
      formData.append('files', file);
    });

    try {
      await axios.post(`${API_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Очищаємо локальні файли після успішної відправки
      setLocalFileTree([]);
      setSelectedFiles(new Set());
      
      // Завантажуємо індексовані файли
      await loadFiles();
      
      alert(`Успішно відправлено ${filesToSend.length} файлів в RAG!`);
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Помилка відправки в RAG! Перевірте логи сервера.");
    } finally {
      setIsIndexing(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      alert('Введіть запит для пошуку');
      return;
    }
    
    if (indexedFileTree.length === 0) {
      alert('Немає індексованих файлів. Спочатку завантажте та відправте файли в RAG.');
      return;
    }
    
    setIsSearching(true);
    try {
      // Збираємо всі шляхи індексованих файлів
      const getAllIndexedFilePaths = (items: FileItem[]): string[] => {
        const paths: string[] = [];
        items.forEach(item => {
          if (item.type === 'file' && item.isIndexed) {
            paths.push(item.path);
          }
          if (item.children) {
            paths.push(...getAllIndexedFilePaths(item.children));
          }
        });
        return paths;
      };
      
      const allIndexedPaths = getAllIndexedFilePaths(indexedFileTree);
      // Використовуємо обрані файли якщо є, інакше всі індексовані
      const filesToSearch = selectedFiles.size > 0 
        ? Array.from(selectedFiles).filter(path => allIndexedPaths.includes(path))
        : allIndexedPaths;
      
      const response = await axios.post(`${API_URL}/search`, {
        query: searchQuery,
        session_id: sessionId,
        active_files: filesToSearch.length > 0 ? filesToSearch : undefined
      });
      
      setSearchResults(response.data.results || []);
    } catch (error) {
      console.error("Search failed:", error);
      alert("Помилка пошуку. Сервер доступний?");
    } finally {
      setIsSearching(false);
    }
  };

  const handleViewChunks = async (filePath: string) => {
    setViewingFile(filePath);
    setIsLoadingChunks(true);
    try {
      const encodedPath = encodeURIComponent(filePath);
      const response = await axios.get(`${API_URL}/files/${encodedPath}/chunks?session_id=${sessionId}`);
      setChunks(response.data.chunks || []);
    } catch (error) {
      console.error("Error loading chunks:", error);
      alert("Помилка завантаження chunks");
    } finally {
      setIsLoadingChunks(false);
    }
  };

  const toggleExpand = (path: string) => {
    setExpandedPaths(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const toggleFileSelection = (path: string) => {
    setSelectedFiles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const selectAllLocalFiles = () => {
    const getAllLocalFilePaths = (items: FileItem[]): string[] => {
      const paths: string[] = [];
      items.forEach(item => {
        if (item.type === 'file' && !item.isIndexed && item.file) {
          // Пропускаємо системні файли
          if (!isSystemPath(item.path)) {
            paths.push(item.path);
          }
        }
        if (item.children) {
          paths.push(...getAllLocalFilePaths(item.children));
        }
      });
      return paths;
    };
    
    const allPaths = getAllLocalFilePaths(localFileTree);
    setSelectedFiles(new Set(allPaths));
  };

  const deselectAllFiles = () => {
    setSelectedFiles(new Set());
  };

  const renderFileTree = (items: FileItem[], isIndexed: boolean, level: number = 0): React.ReactNode => {
    return items.map(item => {
      const isExpanded = expandedPaths.has(item.path);
      const isSelected = selectedFiles.has(item.path);
      const hasChildren = item.children && item.children.length > 0;
      
      return (
        <div key={item.path}>
          <div
            className={`flex items-center gap-2 px-2 py-1.5 rounded hover:bg-white/5 ${
              isSelected ? 'bg-[#667eea]/20' : ''
            }`}
            style={{ paddingLeft: `${level * 16 + 8}px` }}
          >
            {hasChildren ? (
              <button
                onClick={() => toggleExpand(item.path)}
                className="text-[#7890ab] hover:text-white"
              >
                {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </button>
            ) : (
              <div className="w-4" />
            )}
            
            {/* Кнопка вибору для файлів */}
            {item.type === 'file' && !isIndexed && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleFileSelection(item.path);
                }}
                className="text-[#667eea] hover:text-[#764ba2] transition"
                title={isSelected ? 'Зняти вибір' : 'Обрати для відправки в RAG'}
              >
                {isSelected ? (
                  <CheckSquare className="w-4 h-4" />
                ) : (
                  <Square className="w-4 h-4" />
                )}
              </button>
            )}
            
            {item.type === 'folder' ? (
              <FolderOpen className="w-4 h-4 text-[#667eea]" />
            ) : (
              <FileCode className="w-4 h-4 text-[#f093fb]" />
            )}
            
            <span className="flex-1 text-sm text-[#b4c2d9] truncate">
              {item.name}
            </span>
            
            {item.type === 'file' && (
              <>
                {item.isIndexed && (
                  <span className="text-xs text-[#11998e] px-2 py-0.5 bg-[#11998e]/20 rounded">
                    {item.chunksCount} chunks
                  </span>
                )}
                {item.isIndexed && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleViewChunks(item.path);
                    }}
                    className="text-[#667eea] hover:text-[#764ba2] transition"
                    title="Переглянути chunks"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                )}
              </>
            )}
          </div>
          
          {hasChildren && isExpanded && item.children && (
            <div>
              {renderFileTree(item.children, isIndexed, level + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0f1e] via-[#0f1729] to-[#1a2332] relative overflow-hidden font-sans text-slate-200">
      <div className="fixed inset-0 opacity-20 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
      </div>

      <div className="relative z-10 h-screen flex flex-col">
        {/* Header */}
        <div className="px-8 py-6 border-b border-white/10 bg-white/5 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-[#667eea] via-[#764ba2] to-[#f093fb] bg-clip-text text-transparent">
                OpenRAG
              </h1>
              <p className="text-[#7890ab] text-sm mt-1">RAG система для програмістів</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="px-4 py-2 bg-white/5 rounded-xl border border-white/10">
                <span className="text-[#7890ab] text-sm">Обрано: </span>
                <span className="text-white font-bold">{selectedFiles.size}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar - File Tree */}
          <div className="w-96 border-r border-white/10 bg-white/5 backdrop-blur-xl flex flex-col">
            <div className="p-6 border-b border-white/10">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <GitBranch className="w-5 h-5 text-[#667eea]" /> Структура проекту
              </h2>
              <label className="block cursor-pointer group">
                <input
                  type="file"
                  multiple
                  {...({ webkitdirectory: '', directory: '' } as any)}
                  onChange={handleFolderUpload}
                  className="hidden"
                />
                <div className={`border-2 border-dashed border-white/10 rounded-2xl p-6 text-center transition ${
                  isIndexing ? 'bg-[#667eea]/10 border-[#667eea]' : 'group-hover:border-[#667eea]/50 group-hover:bg-white/5'
                }`}>
                  {isIndexing ? (
                    <div>
                      <Loader2 className="w-8 h-8 mx-auto animate-spin text-[#667eea] mb-2" />
                      <p className="text-[#667eea] font-bold">Індексація...</p>
                    </div>
                  ) : (
                    <div>
                      <Upload className="w-8 h-8 mx-auto text-[#7890ab] mb-2" />
                      <p className="text-white font-bold">Завантажити папку</p>
                      <p className="text-sm text-[#7890ab]">Виберіть папку з кодом</p>
                    </div>
                  )}
                </div>
              </label>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
              {localFileTree.length === 0 && indexedFileTree.length === 0 ? (
                <div className="text-center py-20 text-[#7890ab]">
                  <FolderOpen className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p className="text-sm">Порожня структура</p>
                  <p className="text-xs mt-2 opacity-70">Завантажте папку з кодом</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {localFileTree.length > 0 && (
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-2 px-2">
                        <div className="text-xs text-[#667eea] font-semibold">Локальні файли (не індексовані)</div>
                        <div className="flex gap-2">
                          <button
                            onClick={selectAllLocalFiles}
                            className="text-xs text-[#667eea] hover:text-[#764ba2] px-2 py-1 rounded hover:bg-white/5 transition"
                            title="Обрати всі"
                          >
                            Всі
                          </button>
                          <button
                            onClick={deselectAllFiles}
                            className="text-xs text-[#7890ab] hover:text-white px-2 py-1 rounded hover:bg-white/5 transition"
                            title="Зняти вибір"
                          >
                            Нічого
                          </button>
                        </div>
                      </div>
                      {renderFileTree(localFileTree, false)}
                    </div>
                  )}
                  {indexedFileTree.length > 0 && (
                    <div>
                      <div className="text-xs text-[#11998e] font-semibold mb-2 px-2">Індексовані файли</div>
                      {renderFileTree(indexedFileTree, true)}
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {localFileTree.length > 0 && selectedFiles.size > 0 && (
              <div className="p-4 border-t border-white/10">
                <button
                  onClick={handleSendToRAG}
                  disabled={isIndexing}
                  className="w-full px-4 py-3 bg-gradient-to-r from-[#667eea] to-[#764ba2] rounded-xl text-white font-semibold transition hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 flex items-center justify-center gap-2"
                >
                  {isIndexing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Відправка в RAG...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      <span>Відправити в RAG ({selectedFiles.size})</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Main Content */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Search Bar */}
            <div className="p-6 border-b border-white/10 bg-white/5 backdrop-blur-xl">
              <div className="max-w-4xl mx-auto relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Запитайте щось про ваш код (наприклад: 'Як працює автентифікація?')"
                  className="w-full px-6 py-4 pr-32 bg-white/10 border border-white/20 rounded-2xl text-white placeholder-[#7890ab] focus:outline-none focus:border-[#667eea] focus:ring-2 focus:ring-[#667eea]/50 transition-all"
                  disabled={indexedFileTree.length === 0}
                />
                <button
                  onClick={handleSearch}
                  disabled={isSearching || !searchQuery.trim() || indexedFileTree.length === 0}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2.5 bg-gradient-to-r from-[#667eea] to-[#764ba2] rounded-xl text-white font-semibold transition hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 flex items-center gap-2"
                >
                  {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  <span className="hidden sm:inline">Пошук</span>
                </button>
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-hidden flex">
              {/* Search Results or Chunks View */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                {viewingFile ? (
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        <Layers className="w-5 h-5 text-[#667eea]" />
                        Chunks: {viewingFile}
                      </h3>
                      <button
                        onClick={() => {
                          setViewingFile(null);
                          setChunks([]);
                          setSelectedChunk(null);
                        }}
                        className="text-[#7890ab] hover:text-white"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                    
                    {isLoadingChunks ? (
                      <div className="flex items-center justify-center py-20">
                        <Loader2 className="w-8 h-8 animate-spin text-[#667eea]" />
                      </div>
                    ) : chunks.length === 0 ? (
                      <div className="text-center py-20 text-[#7890ab]">
                        <p>Chunks не знайдено</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {chunks.map((chunk) => (
                          <div
                            key={chunk.id}
                            className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 hover:border-[#667eea]/30 transition overflow-hidden cursor-pointer"
                            onClick={() => setSelectedChunk(chunk)}
                          >
                            <div className="p-4 border-b border-white/10 flex justify-between items-center">
                              <div className="flex items-center gap-3">
                                <Code className="w-5 h-5 text-[#f093fb]" />
                                <span className="text-white font-semibold">Chunk #{chunk.chunk_id}</span>
                              </div>
                              <span className="text-xs text-[#7890ab]">ID: {chunk.id.substring(0, 8)}...</span>
                            </div>
                            <div className="p-4">
                              <pre className="text-[#b4c2d9] text-sm whitespace-pre-wrap font-mono">
                                {chunk.text.substring(0, 300)}{chunk.text.length > 300 ? '...' : ''}
                              </pre>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : searchResults.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-[#7890ab] text-center">
                    <div>
                      <Search className="w-20 h-20 mx-auto mb-6 opacity-20" />
                      <p className="text-lg">Результати пошуку з'являться тут</p>
                      <p className="text-sm mt-2 opacity-70">Або оберіть файл і натисніть на іконку ока для перегляду chunks</p>
                    </div>
                  </div>
                ) : (
                  <div className="max-w-4xl mx-auto space-y-4">
                    {searchResults.map((result) => (
                      <div
                        key={result.id}
                        className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 hover:border-[#667eea]/30 transition overflow-hidden"
                      >
                        <div className="p-5 border-b border-white/10 flex justify-between items-start">
                          <div>
                            <div className="flex items-center gap-3 mb-2">
                              <FileText className="w-5 h-5 text-[#f093fb]" />
                              <h4 className="text-white font-semibold">{result.filename}</h4>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-[#7890ab]">
                              {result.chunk_id !== undefined && (
                                <span>Chunk #{result.chunk_id}</span>
                              )}
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-[#11998e]"></div>
                                <span className="text-[#11998e]">{(result.score * 100).toFixed(0)}% Match</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        <div className="p-5">
                          <pre className="text-[#b4c2d9] leading-relaxed mb-4 whitespace-pre-wrap font-mono text-sm">
                            {result.text}
                          </pre>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Chunk Detail Modal */}
      {selectedChunk && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#0f1729] border border-white/20 rounded-3xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
            <div className="p-6 border-b border-white/10 flex justify-between items-center">
              <div>
                <h3 className="text-xl font-bold text-white">{selectedChunk.filename}</h3>
                <p className="text-[#7890ab]">Chunk #{selectedChunk.chunk_id}</p>
              </div>
              <button onClick={() => setSelectedChunk(null)}>
                <X className="w-6 h-6 text-white" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-8">
              <pre className="text-[#b4c2d9] text-sm leading-relaxed whitespace-pre-wrap font-mono">
                {selectedChunk.text}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OpenRAGApp;
