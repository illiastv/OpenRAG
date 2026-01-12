import React, { useState, useEffect, type ChangeEvent, type KeyboardEvent } from 'react';
import { Search, Upload, Download, BookOpen, Trash2, CheckSquare, Square, X, FileText, Copy, Loader2, ChevronDown, ExternalLink } from 'lucide-react';
import axios from 'axios';

// --- КОНФИГУРАЦИЯ ---
const API_URL = 'http://localhost:8001';

// --- ТИПЫ ---
interface FileItem {
  id: string;
  name: string;
  type: string;
  pages: number | string;
}

interface SearchResult {
  id: string;
  filename: string;
  page: number | string;
  score: number;
  text: string;
  chunk_id?: number;
}

interface SearchResponse {
  results: SearchResult[];
}

interface ImportResponse {
  status: string;
  chunks_loaded: number;
  filenames: string[];
}

const BookMindApp: React.FC = () => {
  // Сессия
  const [sessionId] = useState<string>(() => {
    const saved = localStorage.getItem('session_id');
    const newId = Math.random().toString(36).substring(7);
    return saved || newId;
  });

  useEffect(() => {
    localStorage.setItem('session_id', sessionId);
  }, [sessionId]);

  // Состояния
  const [files, setFiles] = useState<FileItem[]>([]);
  const [activeFiles, setActiveFiles] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [isIndexing, setIsIndexing] = useState<boolean>(false);
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  // --- API ЗАПРОСЫ ---

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    const uploadedFiles = Array.from(e.target.files);
    setIsIndexing(true);
    
    const formData = new FormData();
    formData.append('session_id', sessionId);
    uploadedFiles.forEach(file => {
      formData.append('files', file);
    });

    try {
      await axios.post(`${API_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const newFiles: FileItem[] = uploadedFiles.map(f => ({
        id: f.name,
        name: f.name,
        type: f.type,
        pages: '?'
      }));

      setFiles(prev => {
        const unique = [...prev];
        newFiles.forEach(nf => {
          if (!unique.find(f => f.name === nf.name)) unique.push(nf);
        });
        return unique;
      });

      setActiveFiles(prev => {
        const newActive = new Set(prev);
        newFiles.forEach(f => newActive.add(f.name));
        return newActive;
      });

    } catch (error) {
      console.error("Upload failed:", error);
      alert("Ошибка загрузки! Убедись, что Backend запущен на порту 8001.");
    } finally {
      setIsIndexing(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() || activeFiles.size === 0) return;
    
    setIsSearching(true);
    try {
      const response = await axios.post<SearchResponse>(`${API_URL}/search`, {
        query: searchQuery,
        session_id: sessionId,
        active_files: Array.from(activeFiles)
      });
      
      const mappedResults = response.data.results.map((r, idx) => ({
        ...r,
        id: r.id || `res_${idx}`,
      }));

      setSearchResults(mappedResults);
    } catch (error) {
      console.error("Search failed:", error);
      alert("Ошибка поиска. Сервер доступен?");
    } finally {
      setIsSearching(false);
    }
  };

  const handleExport = async () => {
    try {
      const response = await axios.get(`${API_URL}/export?session_id=${sessionId}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `library_${sessionId}.lib`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert("Не удалось скачать базу. Возможно она пустая?");
    }
  };

  const handleImport = async (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('file', file);

    setIsIndexing(true);
    try {
      const response = await axios.post<ImportResponse>(`${API_URL}/import`, formData);
      const filenames = response.data.filenames;
      
      const restoredFiles: FileItem[] = filenames.map(name => ({
        id: name,
        name: name,
        type: 'application/pdf',
        pages: '?'
      }));

      setFiles(restoredFiles);
      setActiveFiles(new Set(filenames));
      alert(`Успешно восстановлено книг: ${filenames.length}`);
    } catch (error) {
      console.error(error);
      alert("Ошибка импорта файла .lib");
    } finally {
      setIsIndexing(false);
    }
  };

  // --- UI ЛОГИКА ---

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') handleSearch();
  };

  const toggleFile = (id: string): void => {
    setActiveFiles(prev => {
      const newActive = new Set(prev);
      if (newActive.has(id)) newActive.delete(id);
      else newActive.add(id);
      return newActive;
    });
  };

  const selectAll = (): void => setActiveFiles(new Set(files.map(f => f.id)));
  const deselectAll = (): void => setActiveFiles(new Set());

  const deleteFile = (id: string): void => {
    setFiles(prev => prev.filter(f => f.id !== id));
    setActiveFiles(prev => {
      const newActive = new Set(prev);
      newActive.delete(id);
      return newActive;
    });
  };

  const toggleExpanded = (id: string): void => {
    setExpandedResults(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(id)) newExpanded.delete(id);
      else newExpanded.add(id);
      return newExpanded;
    });
  };

  const copyToClipboard = (text: string): void => {
    navigator.clipboard.writeText(text);
  };

  const resetAll = (): void => {
    setFiles([]);
    setActiveFiles(new Set());
    setSearchResults([]);
    setSearchQuery('');
    setSelectedResult(null);
    setExpandedResults(new Set());
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
                BookMind
              </h1>
              <p className="text-[#7890ab] text-sm mt-1">AI Search Engine for your Books</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="px-4 py-2 bg-white/5 rounded-xl border border-white/10">
                <span className="text-[#7890ab] text-sm">Index: </span>
                <span className="text-white font-bold">{activeFiles.size}</span>
                <span className="text-[#7890ab] text-sm"> / {files.length}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar */}
          <div className="w-80 border-r border-white/10 bg-white/5 backdrop-blur-xl flex flex-col">
            <div className="p-6 border-b border-white/10">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-[#667eea]" /> Library
              </h2>
              {files.length > 0 && (
                <div className="flex gap-2">
                  <button onClick={selectAll} className="flex-1 px-3 py-2 bg-[#667eea]/20 text-[#667eea] text-sm font-bold rounded-lg hover:bg-[#667eea]/30 transition">All</button>
                  <button onClick={deselectAll} className="flex-1 px-3 py-2 bg-white/5 text-[#7890ab] text-sm font-bold rounded-lg hover:bg-white/10 transition">None</button>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
              {files.length === 0 ? (
                <div className="text-center py-20 text-[#7890ab]">
                  <Upload className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p className="text-sm">Empty Library</p>
                  {/* ИСПРАВЛЕНА ОШИБКА ЗДЕСЬ: */}
                  <p className="text-xs mt-2 opacity-70">Upload PDF files --&gt;</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {files.map((file) => {
                    const isActive = activeFiles.has(file.id);
                    return (
                      <div key={file.id} onClick={() => toggleFile(file.id)} className={`group relative rounded-xl p-4 border cursor-pointer transition ${isActive ? 'bg-[#667eea]/10 border-[#667eea]/50' : 'bg-white/5 border-white/10 hover:border-white/20'}`}>
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5">{isActive ? <CheckSquare className="w-5 h-5 text-[#667eea]" /> : <Square className="w-5 h-5 text-[#7890ab]" />}</div>
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-medium truncate ${isActive ? 'text-white' : 'text-[#b4c2d9]'}`}>{file.name}</p>
                            <p className="text-xs text-[#7890ab]">{file.pages} p.</p>
                          </div>
                          <button onClick={(e) => { e.stopPropagation(); deleteFile(file.id); }} className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Search Area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="p-6 border-b border-white/10 bg-white/5 backdrop-blur-xl">
              <div className="max-w-4xl mx-auto relative">
                <input 
                  type="text" 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Ask a question (e.g. 'What is the concept of freedom?')" 
                  className="w-full px-6 py-4 pr-32 bg-white/10 border border-white/20 rounded-2xl text-white placeholder-[#7890ab] focus:outline-none focus:border-[#667eea] focus:ring-2 focus:ring-[#667eea]/50 transition-all"
                  disabled={activeFiles.size === 0}
                />
                <button 
                  onClick={handleSearch}
                  disabled={isSearching || !searchQuery.trim() || activeFiles.size === 0}
                  className="absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2.5 bg-gradient-to-r from-[#667eea] to-[#764ba2] rounded-xl text-white font-semibold transition hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 flex items-center gap-2">
                  {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  <span className="hidden sm:inline">Search</span>
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
              {searchResults.length === 0 ? (
                <div className="flex items-center justify-center h-full text-[#7890ab] text-center">
                  <div>
                    <Search className="w-20 h-20 mx-auto mb-6 opacity-20" />
                    <p className="text-lg">Results will appear here</p>
                  </div>
                </div>
              ) : (
                <div className="max-w-4xl mx-auto space-y-4">
                  {searchResults.map((result) => {
                    const isExpanded = expandedResults.has(result.id);
                    return (
                      <div key={result.id} className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 hover:border-[#667eea]/30 transition overflow-hidden">
                        <div className="p-5 border-b border-white/10 flex justify-between items-start">
                          <div>
                            <div className="flex items-center gap-3 mb-2">
                              <FileText className="w-5 h-5 text-[#f093fb]" />
                              <h4 className="text-white font-semibold">{result.filename}</h4>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-[#7890ab]">
                              <span>Page {result.page}</span>
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-[#11998e]"></div>
                                <span className="text-[#11998e]">{(result.score * 100).toFixed(0)}% Match</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        <div className="p-5">
                          <p className="text-[#b4c2d9] leading-relaxed mb-4">{result.text}</p>
                          <div className="flex gap-3">
                            <button onClick={() => {
                               const citation = `"${result.text}"\n\n— ${result.filename}, p. ${result.page}`;
                               copyToClipboard(citation);
                            }} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl text-white text-sm font-medium transition flex items-center gap-2">
                              <Copy className="w-4 h-4" /> Copy Citation
                            </button>
                            <button onClick={() => setSelectedResult(result)} className="px-4 py-2 bg-gradient-to-r from-[#4facfe] to-[#00f2fe] rounded-xl text-white text-sm font-semibold transition hover:scale-105 flex items-center gap-2">
                              <ExternalLink className="w-4 h-4" /> Read
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right Controls */}
          <div className="w-96 border-l border-white/10 bg-white/5 backdrop-blur-xl flex flex-col p-6 gap-6">
            <div>
              <h2 className="text-xl font-bold text-white mb-2 flex items-center gap-2"><Upload className="w-5 h-5 text-[#f093fb]" /> Upload</h2>
              <label className="block cursor-pointer group">
                <input type="file" multiple accept=".pdf,.txt,.md" onChange={handleFileUpload} className="hidden" />
                <div className={`border-2 border-dashed border-white/10 rounded-2xl p-8 text-center transition ${isIndexing ? 'bg-[#667eea]/10 border-[#667eea]' : 'group-hover:border-[#667eea]/50 group-hover:bg-white/5'}`}>
                  {isIndexing ? (
                    <div><Loader2 className="w-8 h-8 mx-auto animate-spin text-[#667eea] mb-2" /><p className="text-[#667eea] font-bold">Indexing...</p></div>
                  ) : (
                    <div><Upload className="w-8 h-8 mx-auto text-[#7890ab] mb-2" /><p className="text-white font-bold">Click to Upload</p><p className="text-sm text-[#7890ab]">PDF, TXT</p></div>
                  )}
                </div>
              </label>
            </div>

            <div className="bg-white/5 rounded-2xl p-5 border border-white/10">
              <h3 className="text-white font-semibold mb-3 flex items-center gap-2"><Download className="w-4 h-4" /> Memory</h3>
              <div className="space-y-3">
                <button onClick={handleExport} className="w-full px-4 py-3 bg-[#11998e]/20 hover:bg-[#11998e]/30 text-[#11998e] border border-[#11998e]/50 rounded-xl font-bold transition flex justify-center gap-2">Save .lib</button>
                <label className="block">
                  <input type="file" accept=".lib" onChange={handleImport} className="hidden" />
                  <div className="w-full px-4 py-3 bg-white/10 hover:bg-white/15 border border-white/20 rounded-xl text-white font-bold text-center cursor-pointer transition">Load .lib</div>
                </label>
              </div>
            </div>
            
            <button onClick={resetAll} className="mt-auto w-full px-4 py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-xl font-bold transition">Clear All</button>
          </div>
        </div>
      </div>

      {/* Modal */}
      {selectedResult && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#0f1729] border border-white/20 rounded-3xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
            <div className="p-6 border-b border-white/10 flex justify-between items-center">
              <div><h3 className="text-xl font-bold text-white">{selectedResult.filename}</h3><p className="text-[#7890ab]">Page {selectedResult.page}</p></div>
              <button onClick={() => setSelectedResult(null)}><X className="w-6 h-6 text-white" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-8"><p className="text-[#b4c2d9] text-lg leading-relaxed whitespace-pre-wrap">{selectedResult.text}</p></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BookMindApp;