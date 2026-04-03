import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Plus, Send, ArrowRight, FileText, Check, AlertCircle, Loader2, Sparkles, MessageSquare, Database } from 'lucide-react';
import { api } from './services/api';
import './index.css';

function App() {
  const [activeTab, setActiveTab] = useState('query');
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef(null);

  // Ingest state
  const [ingestMode, setIngestMode] = useState('file'); // 'file' or 'text'
  const [textInput, setTextInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [history, isTyping]);

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMsg = { role: 'user', content: query };
    setHistory(prev => [...prev, userMsg]);
    setQuery('');
    setIsTyping(true);

    try {
      const res = await api.query(userMsg.content);
      const aiMsg = {
        role: 'ai',
        content: res.answer,
        citations: res.citations || [],
        timing: res.timing
      };
      setHistory(prev => [...prev, aiMsg]);
    } catch (err) {
      console.error(err);
      const errorMessage = err.response?.data?.detail || "Failed to get an answer. Please check if the backend is running.";
      setHistory(prev => [...prev, { role: 'error', content: errorMessage }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadStatus(null);
    try {
      const res = await api.ingestFile(file);
      setUploadStatus({ type: 'success', msg: `Added ${file.name}` });
    } catch (err) {
      setUploadStatus({ type: 'error', msg: "Upload failed" });
    } finally {
      setIsUploading(false);
    }
  };

  const handleTextIngest = async () => {
    if (!textInput.trim()) return;

    setIsUploading(true);
    setUploadStatus(null);
    try {
      // Ingest text using first few words as title
      const title = textInput.split(' ').slice(0, 5).join(' ') + '...';
      const res = await api.ingestText(textInput, title);
      setUploadStatus({ type: 'success', msg: `Added text snippet` });
      setTextInput('');
    } catch (err) {
      console.error(err);
      setUploadStatus({ type: 'error', msg: "Ingest failed" });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="app-layout">
      {/* Background Ambience */}
      <div className="ambient-glow glow-1"></div>
      <div className="ambient-glow glow-2"></div>

      <div className="main-container">
        {/* Header */}
        <header className="app-header animate-enter">
          <div className="logo-section">
            <div className="logo-icon">
              <Sparkles size={18} fill="currentColor" />
            </div>
            <span className="logo-text">Aura RAG</span>
          </div>

          <nav className="nav-toggle">
            <button
              onClick={() => setActiveTab('query')}
              className={`nav-btn ${activeTab === 'query' ? 'active' : ''}`}
            >
              <MessageSquare size={16} />
              <span>Chat</span>
            </button>
            <button
              onClick={() => setActiveTab('ingest')}
              className={`nav-btn ${activeTab === 'ingest' ? 'active' : ''}`}
            >
              <Database size={16} />
              <span>Sources</span>
            </button>
          </nav>
        </header>

        {/* content */}
        <main className="content-area">
          <AnimatePresence mode="wait">
            {activeTab === 'query' ? (
              <motion.div
                key="query"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="view-container chat-view"
              >
                <div className="messages-scroll">
                  {history.length === 0 && (
                    <div className="empty-state">
                      <div className="empty-icon-wrapper">
                        <Sparkles size={32} />
                      </div>
                      <h3>How can I help you today?</h3>
                      <p>Ask questions about your uploaded documents.</p>
                      <div className="suggestions">
                        {['Summarize the latest report', 'What are the key risks?', 'Explain the methodology'].map(s => (
                          <button key={s} onClick={() => setQuery(s)} className="suggestion-chip">
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {history.map((msg, idx) => (
                    <div key={idx} className={`message-row ${msg.role}`}>
                      <div className="message-content">
                        {msg.role === 'error' ? (
                          <div className="error-text">
                            <AlertCircle size={16} />
                            {msg.content}
                          </div>
                        ) : (
                          <>
                            <div className="text-body">{msg.content}</div>

                            {msg.citations && msg.citations.length > 0 && (
                              <div className="citations-grid">
                                {msg.citations.map((cite, cIdx) => (
                                  <div key={cIdx} className="citation-card">
                                    <div className="citation-badge">{cIdx + 1}</div>
                                    <p>{cite.text}</p>
                                  </div>
                                ))}
                              </div>
                            )}

                            {msg.timing && (
                              <div className="message-meta">
                                Generated in {msg.timing.toFixed(2)}s
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  ))}

                  {isTyping && (
                    <div className="message-row ai">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  )}
                  <div ref={bottomRef} />
                </div>

                <div className="input-area">
                  <form onSubmit={handleQuery} className="search-bar-wrapper">
                    <input
                      className="search-input"
                      placeholder="Ask a question..."
                      value={query}
                      onChange={e => setQuery(e.target.value)}
                      autoFocus
                    />
                    <button
                      type="submit"
                      disabled={!query.trim() || isTyping}
                      className="send-btn"
                    >
                      {isTyping ? <Loader2 size={20} className="animate-spin" /> : <ArrowRight size={20} />}
                    </button>
                  </form>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="ingest"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                className="view-container ingest-view"
              >
                <div className="upload-card">
                  <div className="card-header">
                    <h2>Knowledge Base</h2>
                    <p>Add content to power the AI.</p>
                  </div>

                  {/* Mode Toggle */}
                  <div className="mode-toggle">
                    <button
                      className={`mode-btn ${ingestMode === 'file' ? 'active' : ''}`}
                      onClick={() => setIngestMode('file')}
                    >
                      <FileText size={16} /> File Upload
                    </button>
                    <button
                      className={`mode-btn ${ingestMode === 'text' ? 'active' : ''}`}
                      onClick={() => setIngestMode('text')}
                    >
                      <FileText size={16} /> Paste Text
                    </button>
                  </div>

                  {ingestMode === 'file' ? (
                    <label className="drop-zone">
                      <input type="file" className="hidden-input" accept=".pdf,.txt,.md" onChange={handleFileUpload} />

                      <div className="drop-content">
                        {isUploading ? (
                          <div className="uploading-state">
                            <Loader2 size={40} className="spinner" />
                            <span>Processing...</span>
                          </div>
                        ) : (
                          <>
                            <div className="icon-circle">
                              <Plus size={24} />
                            </div>
                            <span className="drop-text">Click or Drop file here</span>
                            <span className="drop-subtext">Supports PDF, TXT, MD</span>
                          </>
                        )}
                      </div>
                    </label>
                  ) : (
                    <div className="text-ingest-area">
                      <textarea
                        className="text-input-area"
                        placeholder="Paste your text content here..."
                        value={textInput}
                        onChange={(e) => setTextInput(e.target.value)}
                      />
                      <button
                        className="ingest-btn"
                        onClick={handleTextIngest}
                        disabled={!textInput.trim() || isUploading}
                      >
                        {isUploading ? <Loader2 size={16} className="animate-spin" /> : "Ingest Text"}
                      </button>
                    </div>
                  )}

                  {uploadStatus && (
                    <div className={`status-message ${uploadStatus.type}`}>
                      {uploadStatus.type === 'success' ? <Check size={18} /> : <AlertCircle size={18} />}
                      <span>{uploadStatus.msg}</span>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

export default App;
