'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Upload, FileText, Loader2 } from 'lucide-react';
import api, { QueryResponse, Document } from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  timestamp: Date;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadDocuments = async () => {
    try {
      const docs = await api.listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      await api.uploadDocument(file);
      await loadDocuments();
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: `File "${file.name}" uploaded successfully. It's now being processed.`,
        timestamp: new Date(),
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Upload failed: ${err.message}`,
        timestamp: new Date(),
      }]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await api.query(input);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${err.message}`,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 p-4 flex flex-col">
        <h1 className="text-xl font-bold text-white mb-6">OmniRAG</h1>
        
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-lg transition-colors mb-4"
        >
          {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {isUploading ? 'Uploading...' : 'Upload Document'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.doc,.docx,.txt,.md"
          onChange={handleUpload}
          className="hidden"
        />

        <div className="flex-1 overflow-auto">
          <h2 className="text-sm font-semibold text-slate-400 mb-2">Documents</h2>
          {documents.length === 0 ? (
            <p className="text-sm text-slate-500">No documents yet</p>
          ) : (
            <ul className="space-y-2">
              {documents.map(doc => (
                <li key={doc.id} className="flex items-center gap-2 text-sm text-slate-300">
                  <FileText className="w-4 h-4" />
                  <span className="truncate">{doc.filename}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-slate-400">
              <div className="text-center">
                <h2 className="text-2xl font-semibold mb-2">Welcome to OmniRAG</h2>
                <p>Ask questions about your documents or upload new ones</p>
              </div>
            </div>
          ) : (
            messages.map(msg => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[70%] rounded-lg px-4 py-2 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-800 text-slate-100'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-600">
                      <p className="text-xs text-slate-400 mb-1">Sources:</p>
                      {msg.sources.map((src: any, i: number) => (
                        <p key={i} className="text-xs text-slate-400 truncate">
                          [{i + 1}] {src.content?.substring(0, 100)}...
                        </p>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-slate-500 mt-1">
                    {msg.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 rounded-lg px-4 py-2">
                <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-4 border-t border-slate-800">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="flex-1 px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}