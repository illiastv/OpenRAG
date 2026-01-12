// Додали 'type' до імпортів, щоб TypeScript не сварився
import React, { useState, type ChangeEvent, type KeyboardEvent } from 'react';
import { Search, Upload, Download, BookOpen, Trash2, CheckSquare, Square, X, FileText, Copy, Loader2, ChevronDown, ExternalLink } from 'lucide-react';

// Types
interface FileItem {
  id: string;
  name: string;
  type: string;
  pages: number;
}

interface SearchResult {
  id: number;
  filename: string;
  page: number;
  score: number;
  text: string;
  fullText: string;
}

const BookMindApp: React.FC = () => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [activeFiles, setActiveFiles] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [isIndexing, setIsIndexing] = useState<boolean>(false);
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set());

  const handleFileUpload = (e: ChangeEvent<HTMLInputElement>): void => {
    const uploadedFiles = e.target.files;
    if (!uploadedFiles) return;
    
    const fileArray = Array.from(uploadedFiles);
    setIsIndexing(true);
    
    setTimeout(() => {
      const newFiles: FileItem[] = fileArray.map(f => ({
        id: Math.random().toString(36).substr(2, 9),
        name: f.name,
        type: f.type,
        pages: Math.floor(Math.random() * 300) + 50
      }));
      
      setFiles(prevFiles => [...prevFiles, ...newFiles]);
      
      setActiveFiles(prevActive => {
        const newActive = new Set(prevActive);
        newFiles.forEach(f => newActive.add(f.id));
        return newActive;
      });
      
      setIsIndexing(false);
    }, 1500);
  };

  const toggleFile = (id: string): void => {
    setActiveFiles(prevActive => {
      const newActive = new Set(prevActive);
      if (newActive.has(id)) {
        newActive.delete(id);
      } else {
        newActive.add(id);
      }
      return newActive;
    });
  };

  const selectAll = (): void => {
    setActiveFiles(new Set(files.map(f => f.id)));
  };

  const deselectAll = (): void => {
    setActiveFiles(new Set());
  };

  const deleteFile = (id: string): void => {
    setFiles(prevFiles => prevFiles.filter(f => f.id !== id));
    setActiveFiles(prevActive => {
      const newActive = new Set(prevActive);
      newActive.delete(id);
      return newActive;
    });
  };

  const handleSearch = (): void => {
    if (!searchQuery.trim() || activeFiles.size === 0) return;
    
    setIsSearching(true);
    
    setTimeout(() => {
      const mockResults: SearchResult[] = [
        {
          id: 1,
          filename: 'Філософія свободи.pdf',
          page: 42,
          score: 0.94,
          text: 'Свобода є не лише правом, а й відповідальністю кожної людини. Вона вимагає від нас усвідомленого вибору та готовності нести наслідки своїх рішень. Автор наголошує, що справжня свобода можлива лише через самопізнання та розуміння власних обмежень.',
          fullText: 'Свобода є не лише правом, а й відповідальністю кожної людини. Вона вимагає від нас усвідомленого вибору та готовності нести наслідки своїх рішень. Автор наголошує, що справжня свобода можлива лише через самопізнання та розуміння власних обмежень.\n\nУ цьому контексті важливо розрізняти свободу "від" і свободу "для". Перша означає відсутність зовнішніх обмежень, друга - наявність внутрішньої мети та напрямку. Справжня свобода поєднує обидва аспекти.'
        },
        {
          id: 2,
          filename: 'Історія думки.txt',
          page: 156,
          score: 0.87,
          text: 'У контексті свободи волі, філософи епохи Просвітництва стверджували, що людина народжується вільною, але скрізь у кайданах суспільних норм. Це протиріччя залишається центральним у дискусії про природу людської свободи.',
          fullText: 'У контексті свободи волі, філософи епохи Просвітництва стверджували, що людина народжується вільною, але скрізь у кайданах суспільних норм. Це протиріччя залишається центральним у дискусії про природу людської свободи.\n\nРуссо писав про суспільний договір як спосіб примирити природну свободу з необхідністю соціального порядку. Кант же бачив свободу як автономію розуму.'
        },
        {
          id: 3,
          filename: 'Етика та мораль.pdf',
          page: 89,
          score: 0.82,
          text: 'Моральна свобода передбачає здатність діяти відповідно до власних етичних принципів, навіть коли це суперечить зовнішнім обставинам чи тиску.',
          fullText: 'Моральна свобода передбачає здатність діяти відповідно до власних етичних принципів, навіть коли це суперечить зовнішнім обставинам чи тиску. Це вища форма свободи, яка вимагає мужності та цілісності характеру.'
        }
      ];
      
      setSearchResults(mockResults);
      setIsSearching(false);
    }, 1000);
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const toggleExpanded = (id: number): void => {
    setExpandedResults(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(id)) {
        newExpanded.delete(id);
      } else {
        newExpanded.add(id);
      }
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
      {/* Animated Mesh Gradient Background */}
      <div className="fixed inset-0 opacity-20 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-600 rounded-full mix-blend-multiply filter blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-600 rounded-full mix-blend-multiply filter blur-3xl animate-pulse" style={{animationDelay: '2s'}}></div>
        <div className="absolute top-1/2 left-1/2 w-96 h-96 bg-pink-600 rounded-full mix-blend-multiply filter blur-3xl animate-pulse" style={{animationDelay: '4s'}}></div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 h-screen flex flex-col">
        {/* Header */}
        <div className="px-8 py-6 border-b border-white/10 bg-white/5 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-[#667eea] via-[#764ba2] to-[#f093fb] bg-clip-text text-transparent">
                BookMind
              </h1>
              <p className="text-[#7890ab] text-sm mt-1">Семантичний пошук по вашій базі знань</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="px-4 py-2 bg-white/5 rounded-xl border border-white/10">
                <span className="text-[#7890ab] text-sm">Активно: </span>
                <span className="text-white font-bold">{activeFiles.size}</span>
                <span className="text-[#7890ab] text-sm"> / {files.length}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Layout */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left Sidebar - File Library */}
          <div className="w-80 border-r border-white/10 bg-white/5 backdrop-blur-xl flex flex-col">
            <div className="p-6 border-b border-white/10">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-[#667eea]" />
                Завантажена база
              </h2>
              
              {files.length > 0 && (
                <div className="flex gap-2">
                  <button
                    onClick={selectAll}
                    className="flex-1 px-3 py-2 bg-[#667eea]/20 hover:bg-[#667eea]/30 border border-[#667eea]/50 rounded-lg text-[#667eea] text-sm font-medium transition-all duration-300"
                  >
                    Всі
                  </button>
                  <button
                    onClick={deselectAll}
                    className="flex-1 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-[#b4c2d9] text-sm font-medium transition-all duration-300"
                  >
                    Скинути
                  </button>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
              {files.length === 0 ? (
                <div className="text-center py-20 text-[#7890ab]">
                  <Upload className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p className="text-sm">База порожня</p>
                  <p className="text-xs mt-2 opacity-70">Завантажте файли справа →</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {files.map((file) => {
                    const isActive = activeFiles.has(file.id);
                    return (
                      <div
                        key={file.id}
                        className={`group relative rounded-xl p-4 border transition-all duration-300 cursor-pointer ${
                          isActive 
                            ? 'bg-[#667eea]/10 border-[#667eea]/50 shadow-lg shadow-[#667eea]/20' 
                            : 'bg-white/5 border-white/10 hover:border-white/20'
                        }`}
                        onClick={() => toggleFile(file.id)}
                      >
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5">
                            {isActive ? (
                              <CheckSquare className="w-5 h-5 text-[#667eea]" />
                            ) : (
                              <Square className="w-5 h-5 text-[#7890ab]" />
                            )}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <FileText className="w-4 h-4 text-[#f093fb] flex-shrink-0" />
                              <p className={`text-sm font-medium truncate ${isActive ? 'text-white' : 'text-[#b4c2d9]'}`}>
                                {file.name}
                              </p>
                            </div>
                            <p className="text-xs text-[#7890ab]">{file.pages} сторінок</p>
                          </div>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteFile(file.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-red-400 hover:text-red-300"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Center - Search Results */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Search Bar */}
            <div className="p-6 border-b border-white/10 bg-white/5 backdrop-blur-xl">
              <div className="max-w-4xl mx-auto">
                <div className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Введіть питання або тему для пошуку..."
                    className="w-full px-6 py-4 pr-32 bg-white/10 border border-white/20 rounded-2xl text-white placeholder-[#7890ab] focus:outline-none focus:border-[#667eea] focus:ring-2 focus:ring-[#667eea]/50 transition-all duration-300"
                    disabled={activeFiles.size === 0}
                  />
                  <button
                    onClick={handleSearch}
                    disabled={isSearching || !searchQuery.trim() || activeFiles.size === 0}
                    className="absolute right-2 top-1/2 -translate-y-1/2 px-6 py-2.5 bg-gradient-to-r from-[#667eea] to-[#764ba2] hover:from-[#764ba2] hover:to-[#667eea] rounded-xl text-white font-semibold transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-2"
                  >
                    {isSearching ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="hidden sm:inline">Шукаю...</span>
                      </>
                    ) : (
                      <>
                        <Search className="w-4 h-4" />
                        <span className="hidden sm:inline">Знайти</span>
                      </>
                    )}
                  </button>
                </div>
                
                {activeFiles.size === 0 && (
                  <p className="text-[#7890ab] text-sm mt-3 text-center">
                    ← Виберіть файли зліва для пошуку
                  </p>
                )}
              </div>
            </div>

            {/* Results Area */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
              {searchResults.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-[#7890ab]">
                    <Search className="w-20 h-20 mx-auto mb-6 opacity-20" />
                    <p className="text-lg mb-2">Результати з'являться тут</p>
                    <p className="text-sm opacity-70">Введіть запит та натисніть "Знайти"</p>
                  </div>
                </div>
              ) : (
                <div className="max-w-4xl mx-auto space-y-4">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-xl font-bold text-white">
                      Знайдено {searchResults.length} контекстів
                    </h3>
                    <p className="text-sm text-[#7890ab]">
                      Запит: "{searchQuery}"
                    </p>
                  </div>

                  {searchResults.map((result) => {
                    const isExpanded = expandedResults.has(result.id);
                    return (
                      <div
                        key={result.id}
                        className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 hover:border-[#667eea]/30 transition-all duration-300 overflow-hidden"
                      >
                        {/* Result Header */}
                        <div className="p-5 border-b border-white/10">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <FileText className="w-5 h-5 text-[#f093fb]" />
                                <h4 className="text-white font-semibold">{result.filename}</h4>
                              </div>
                              <div className="flex items-center gap-4 text-sm">
                                <span className="text-[#7890ab]">Сторінка {result.page}</span>
                                <div className="h-4 w-px bg-white/10"></div>
                                <div className="flex items-center gap-2">
                                  <div className="w-2 h-2 rounded-full bg-gradient-to-r from-[#11998e] to-[#38ef7d]"></div>
                                  <span className="text-[#11998e] font-medium">
                                    {(result.score * 100).toFixed(0)}% релевантність
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Result Content */}
                        <div className="p-5">
                          <p className="text-[#b4c2d9] leading-relaxed mb-4">
                            {isExpanded ? result.fullText : result.text}
                          </p>

                          <div className="flex items-center gap-3 flex-wrap">
                            <button
                              onClick={() => toggleExpanded(result.id)}
                              className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl text-white text-sm font-medium transition-all duration-300 hover:scale-105 flex items-center gap-2"
                            >
                              {isExpanded ? 'Згорнути' : 'Показати повністю'}
                              <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                            </button>

                            <button
                              onClick={() => {
                                const citation = `"${result.text}"\n\n— ${result.filename}, стр. ${result.page}`;
                                copyToClipboard(citation);
                              }}
                              className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl text-white text-sm font-medium transition-all duration-300 hover:scale-105 flex items-center gap-2"
                            >
                              <Copy className="w-4 h-4" />
                              Копіювати цитату
                            </button>

                            <button
                              onClick={() => setSelectedResult(result)}
                              className="px-4 py-2 bg-gradient-to-r from-[#4facfe] to-[#00f2fe] hover:from-[#00f2fe] hover:to-[#4facfe] rounded-xl text-white text-sm font-semibold transition-all duration-300 hover:scale-105 flex items-center gap-2"
                            >
                              <ExternalLink className="w-4 h-4" />
                              Відкрити PDF
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

          {/* Right Sidebar - Upload & Controls */}
          <div className="w-96 border-l border-white/10 bg-white/5 backdrop-blur-xl flex flex-col">
            <div className="p-6 border-b border-white/10">
              <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
                <Upload className="w-5 h-5 text-[#f093fb]" />
                Завантаження
              </h2>
              <p className="text-[#7890ab] text-sm">Додайте файли в базу</p>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
              {/* Upload Files */}
              <div>
                <label className="block">
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.txt,.md"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <div className="relative group cursor-pointer">
                    <div className="absolute inset-0 bg-gradient-to-r from-[#f093fb] to-[#f5576c] rounded-2xl blur-xl opacity-50 group-hover:opacity-75 transition-opacity"></div>
                    <div className="relative px-6 py-8 bg-gradient-to-r from-[#f093fb] to-[#f5576c] hover:from-[#f5576c] hover:to-[#f093fb] rounded-2xl text-white text-center transition-all duration-300 group-hover:scale-105">
                      {isIndexing ? (
                        <div className="space-y-3">
                          <Loader2 className="w-8 h-8 mx-auto animate-spin" />
                          <p className="font-semibold">Індексація...</p>
                          <p className="text-sm opacity-90">Обробка файлів</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <Upload className="w-8 h-8 mx-auto" />
                          <p className="font-semibold text-lg">Завантажити файли</p>
                          <p className="text-sm opacity-90">PDF, TXT, MD</p>
                        </div>
                      )}
                    </div>
                  </div>
                </label>
              </div>

              {/* Save/Load Library */}
              <div className="bg-white/5 rounded-2xl p-5 border border-white/10">
                <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  Збереження бази
                </h3>
                <p className="text-[#7890ab] text-sm mb-4">
                  Зберігайте .lib файл, щоб не платити за повторну індексацію
                </p>
                <div className="space-y-3">
                  <button className="w-full px-4 py-3 bg-gradient-to-r from-[#11998e] to-[#38ef7d] hover:from-[#38ef7d] hover:to-[#11998e] rounded-xl text-white font-semibold transition-all duration-300 hover:scale-105 flex items-center justify-center gap-2 shadow-lg">
                    <Download className="w-4 h-4" />
                    Експорт .lib
                  </button>
                  <label>
                    <input type="file" accept=".lib" className="hidden" />
                    <div className="w-full px-4 py-3 bg-white/10 hover:bg-white/15 border border-white/20 rounded-xl text-white font-medium transition-all duration-300 hover:scale-105 flex items-center justify-center gap-2 cursor-pointer">
                      <Upload className="w-4 h-4" />
                      Імпорт .lib
                    </div>
                  </label>
                </div>
              </div>

              {/* Stats */}
              <div className="bg-gradient-to-br from-[#667eea]/20 to-[#764ba2]/20 rounded-2xl p-5 border border-[#667eea]/30">
                <h3 className="text-white font-semibold mb-4">Статистика</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-[#b4c2d9] text-sm">Всього файлів:</span>
                    <span className="text-white font-bold text-lg">{files.length}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#b4c2d9] text-sm">Активних:</span>
                    <span className="text-[#667eea] font-bold text-lg">{activeFiles.size}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[#b4c2d9] text-sm">Результатів:</span>
                    <span className="text-[#11998e] font-bold text-lg">{searchResults.length}</span>
                  </div>
                </div>
              </div>

              {/* Reset */}
              <button 
                onClick={resetAll}
                className="w-full px-4 py-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 hover:border-red-500/50 rounded-xl text-red-400 font-medium transition-all duration-300 hover:scale-105"
              >
                🧹 Очистити все
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* PDF Viewer Modal */}
      {selectedResult && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#0f1729] border border-white/20 rounded-3xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl">
            <div className="p-6 border-b border-white/10 flex items-center justify-between">
              <div>
                <h3 className="text-2xl font-bold text-white mb-1">
                  {selectedResult.filename}
                </h3>
                <p className="text-[#7890ab]">Сторінка {selectedResult.page}</p>
              </div>
              <button
                onClick={() => setSelectedResult(null)}
                className="text-white/50 hover:text-white transition-colors hover:bg-white/10 p-2 rounded-xl"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
              <div className="bg-white/5 rounded-2xl p-8 border border-white/10">
                <p className="text-[#b4c2d9] leading-relaxed text-lg whitespace-pre-wrap">
                  {selectedResult.fullText}
                </p>
              </div>
            </div>

            <div className="p-6 border-t border-white/10 flex gap-3">
              <button
                onClick={() => {
                  const citation = `"${selectedResult.fullText}"\n\n— ${selectedResult.filename}, стр. ${selectedResult.page}`;
                  copyToClipboard(citation);
                }}
                className="flex-1 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-xl text-white font-semibold transition-all duration-300 hover:scale-105 flex items-center justify-center gap-2"
              >
                <Copy className="w-5 h-5" />
                Копіювати повний текст
              </button>
              <button
                onClick={() => setSelectedResult(null)}
                className="flex-1 px-6 py-3 bg-gradient-to-r from-[#667eea] to-[#764ba2] rounded-xl text-white font-semibold transition-all duration-300 hover:scale-105"
              >
                Закрити
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BookMindApp;