import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Link as LinkIcon, User, Bot, Loader, X, Edit2, Youtube } from 'lucide-react';
import { Button, Input } from './ui';
import { chatService } from '../services/api';
import { cn } from '../utils';

export const ChatInterface = () => {
    const [url, setUrl] = useState('');
    const [isStarted, setIsStarted] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [chatId, setChatId] = useState(null);
    const [videoTitle, setVideoTitle] = useState('');
    const [videoAuthor, setVideoAuthor] = useState('');
    const [videoThumbnail, setVideoThumbnail] = useState('');
    const [isEditingTitle, setIsEditingTitle] = useState(false);
    const [editedTitle, setEditedTitle] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
  
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);
  
    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
  
    useEffect(() => {
      scrollToBottom();
    }, [messages]);

    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
      }
    }, [input]);
  
    const handleStartChat = async (e) => {
      e.preventDefault();
      if (!url) return;
      
      setLoading(true);
      try {
        const chat = await chatService.createChat(url);
        setChatId(chat.id);
        setVideoTitle(chat.title || '');
        setVideoAuthor(chat.author || '');
        setVideoThumbnail(chat.thumbnail_url || '');
        setIsStarted(true);
      } catch (error) {
        console.error("Failed to start chat", error);
      } finally {
        setLoading(false);
      }
    };

    const handleStop = () => {
      setIsGenerating(false);
      setLoading(false);
    };

    const handleEdit = (messageIndex) => {
      const message = messages[messageIndex];
      if (message.role === 'user') {
        setInput(message.content);
        // Remove messages from this point
        setMessages(prev => prev.slice(0, messageIndex));
      }
    };

    const handleFollowUpClick = (question) => {
      setInput(question);
      textareaRef.current?.focus();
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault();
        setInput(prev => prev + '\n');
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage(e);
      }
    };
  
    const handleSendMessage = async (e) => {
      e.preventDefault();
      if (!input.trim() || !chatId || loading) return;
  
      const userMessage = { role: 'user', content: input };
      setMessages(prev => [...prev, userMessage]);
      setInput('');
      setLoading(true);
      setIsGenerating(true);
      
      try {
        const response = await chatService.sendMessage(chatId, userMessage.content);
        
        // Extract data from response
        const parsedResponse = typeof response === 'string' ? JSON.parse(response) : response;
        
        // Update video title if present
        if (parsedResponse.title && !videoTitle) {
          setVideoTitle(parsedResponse.title);
        }

        const assistantMessage = { 
            role: 'assistant', 
            content: parsedResponse.answer || parsedResponse,
            follow_up: parsedResponse.follow_up || []
        };
        setMessages(prev => [...prev, assistantMessage]);
      } catch (error) {
        console.error("Failed to send message", error);
        setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error. Please try again." }]);
      } finally {
        setLoading(false);
        setIsGenerating(false);
      }
    };

    const handleSaveTitle = () => {
      if (editedTitle.trim()) {
        setVideoTitle(editedTitle);
        setIsEditingTitle(false);
      }
    };
  
    if (!isStarted) {
      return (
        <div className="h-full flex flex-col items-center justify-center p-6 bg-gradient-to-b from-zinc-50 to-zinc-100 dark:from-zinc-950 dark:to-zinc-900">
          <div className="max-w-md w-full space-y-8 animate-fade-in">
            <div className="text-center space-y-4">
              <div className="w-20 h-20 bg-red-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-red-600/30">
                <svg className="w-12 h-12" viewBox="0 0 159 110" fill="none">
                  <path d="M64 69.5L103 47L64 24.5V69.5Z" fill="white"/>
                </svg>
              </div>
              <h1 className="text-4xl font-bold text-zinc-900 dark:text-white">
                TubeChat AI
              </h1>
              <p className="text-zinc-600 dark:text-zinc-400 text-lg">
                Chat with any YouTube video using AI. Paste a video URL to begin.
              </p>
            </div>
  
            <form onSubmit={handleStartChat} className="mt-8 space-y-4">
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <LinkIcon className="h-5 w-5 text-zinc-500 group-focus-within:text-red-500 transition-colors" />
                </div>
                <Input
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  className="pl-10 h-14 bg-white dark:bg-zinc-900 border-zinc-300 dark:border-zinc-800 text-lg text-zinc-900 dark:text-white"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                />
              </div>
              <Button 
                type="submit" 
                className="w-full h-12 text-lg font-semibold bg-red-600 hover:bg-red-700"
                isLoading={loading}
              >
                Start Chatting
              </Button>
            </form>
          </div>
        </div>
      );
    }
  
    return (
      <div className="flex flex-col h-full bg-zinc-50 dark:bg-zinc-950">
        {/* Video Info Card */}
        {videoTitle && (
          <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
            <div className="max-w-4xl mx-auto flex gap-4 items-start">
              {videoThumbnail && (
                <img src={videoThumbnail} alt={videoTitle} className="w-32 h-20 object-cover rounded-lg shadow-lg" />
              )}
              <div className="flex-1 min-w-0">
                {isEditingTitle ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      className="flex-1 px-3 py-2 bg-zinc-100 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-white"
                      autoFocus
                      onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()}
                    />
                    <Button size="sm" onClick={handleSaveTitle} className="bg-red-600 hover:bg-red-700">Save</Button>
                    <Button size="sm" variant="ghost" onClick={() => setIsEditingTitle(false)}>Cancel</Button>
                  </div>
                ) : (
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <h2 className="text-lg font-semibold text-zinc-900 dark:text-white truncate">{videoTitle}</h2>
                      {videoAuthor && <p className="text-sm text-zinc-600 dark:text-zinc-400">{videoAuthor}</p>}
                    </div>
                    <button onClick={() => { setEditedTitle(videoTitle); setIsEditingTitle(true); }} className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors">
                      <Edit2 className="w-4 h-4 text-zinc-400" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Old Title Header - Remove this */}
        {false && videoTitle && (
          <div className="p-4 border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-xl">
            {isEditingTitle ? (
              <div className="flex items-center gap-2 max-w-4xl mx-auto">
                <input
                  type="text"
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()}
                />
                <Button size="sm" onClick={handleSaveTitle}>Save</Button>
                <Button size="sm" variant="ghost" onClick={() => setIsEditingTitle(false)}>Cancel</Button>
              </div>
            ) : (
              <div className="flex items-center gap-3 max-w-4xl mx-auto">
                <Youtube className="w-5 h-5 text-red-500" />
                <h2 className="flex-1 text-lg font-semibold text-white truncate animate-slide-in-left">{videoTitle}</h2>
                <button onClick={() => { setEditedTitle(videoTitle); setIsEditingTitle(true); }} className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
                  <Edit2 className="w-4 h-4 text-zinc-400" />
                </button>
              </div>
            )}
          </div>
        )}

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 bg-zinc-50 dark:bg-zinc-950">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={cn(
                "flex gap-4 max-w-4xl mx-auto animate-slide-up",
                msg.role === 'user' ? "flex-row-reverse" : "flex-row"
              )}
            >
              <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1",
                msg.role === 'user' ? "bg-red-600" : "bg-zinc-300 dark:bg-zinc-700"
              )}>
                {msg.role === 'user' ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-zinc-700 dark:text-white" />}
              </div>
              
              <div className="flex-1 space-y-2">
                <div className={cn(
                  "rounded-2xl p-4 md:p-6 shadow-lg relative group",
                  msg.role === 'user' 
                    ? "bg-red-600 text-white rounded-tr-sm" 
                    : "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 rounded-tl-sm border border-zinc-200 dark:border-zinc-800"
                )}>
                  {msg.role === 'user' && (
                    <button
                      onClick={() => handleEdit(idx)}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-700 rounded-lg transition-all"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  )}
                   <div className={cn(
                     "prose max-w-none text-sm md:text-base leading-relaxed",
                     msg.role === 'user' ? "prose-invert" : "prose-zinc dark:prose-invert"
                   )}>
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                </div>
                
                {msg.follow_up && msg.follow_up.length > 0 && (
                    <div className="space-y-2 pl-2">
                        <p className="text-xs font-semibold text-zinc-500 dark:text-zinc-500 uppercase tracking-wider">Follow-up Questions</p>
                        <div className="flex flex-wrap gap-2">
                            {msg.follow_up.map((q, i) => (
                                <button
                                    key={i} 
                                    onClick={() => handleFollowUpClick(q)}
                                    className="text-sm bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 px-3 py-2 rounded-lg transition-colors text-left border border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
             <div className="flex gap-4 max-w-4xl mx-auto animate-pulse">
                <div className="w-8 h-8 rounded-full bg-zinc-300 dark:bg-zinc-700 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-zinc-700 dark:text-white" />
                </div>
                <div className="bg-white dark:bg-zinc-900 rounded-2xl p-4 rounded-tl-sm border border-zinc-200 dark:border-zinc-800 flex items-center gap-2 text-zinc-600 dark:text-zinc-400">
                    <Loader className="w-4 h-4 animate-spin" /> Thinking...
                </div>
             </div>
          )}
          <div ref={messagesEndRef} />
        </div>
  
        {/* Input Area */}
        <div className="p-4 bg-white dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800">
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
            <div className="relative flex gap-2 items-end">
              <div className="flex-1 relative">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask something about the video... (Ctrl+Enter for new line)"
                  className="w-full min-h-[52px] max-h-40 px-4 py-3 pr-24 bg-zinc-100 dark:bg-zinc-900 border-2 border-zinc-300 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 placeholder-zinc-500 dark:placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-red-500/50 focus:border-red-500 transition-all duration-300 resize-none"
                  disabled={loading}
                  rows={1}
                />
                <div className="absolute right-2 bottom-2 flex gap-1">
                  {isGenerating && (
                    <button
                      type="button"
                      onClick={handleStop}
                      className="p-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                      title="Stop generating"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="p-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                    title="Send message (Enter)"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
            <p className="text-xs text-zinc-600 mt-2 text-center">Press Enter to send, Ctrl+Enter for new line</p>
          </form>
        </div>
      </div>
    );
  };
