import { useState, useRef, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Send,
    ArrowLeft,
    Download,
    Sparkles,
    User,
    Loader2,
    RotateCcw,
    Mic,
    MicOff,
    Volume2,
    VolumeX,
} from 'lucide-react';
import { useChat, type Message } from '../hooks/useChat';
import { useVoice } from '../hooks/useVoice';
import { getPdfDownloadUrl } from '../services/api';
import './ChatSession.css';

export default function ChatSession() {
    const { id } = useParams<{ id: string }>();
    const location = useLocation();
    const navigate = useNavigate();
    const { messages, isLoading, sessionId, send, reset, addMessage, setSessionId } = useChat();
    const [input, setInput] = useState('');
    const [autoSpeak, setAutoSpeak] = useState(true);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const hasInitialized = useRef(false);
    const lastSpokenRef = useRef<string>('');

    // Voice hook — sends transcript to the chat
    const voice = useVoice({
        autoSpeak,
        onTranscript: (text) => {
            if (text.trim()) {
                send(text.trim());
            }
        },
    });

    // Auto-scroll to latest message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-speak Forge's responses
    useEffect(() => {
        if (!autoSpeak || messages.length === 0) return;
        const last = messages[messages.length - 1];
        if (last.role === 'forge' && last.content !== lastSpokenRef.current) {
            lastSpokenRef.current = last.content;
            voice.speak(last.content);
        }
    }, [messages, autoSpeak, voice]);

    // Handle initial state from profile submission or new session
    useEffect(() => {
        if (hasInitialized.current) return;
        hasInitialized.current = true;

        const state = location.state as {
            resumeUploaded?: boolean;
            initialMessage?: string;
            profileSubmitted?: boolean;
        } | null;

        if (state?.resumeUploaded && state?.initialMessage) {
            if (id && id !== 'new') setSessionId(id);
            addMessage('forge', state.initialMessage);
        } else if (state?.profileSubmitted && id && id !== 'new') {
            // Profile was submitted — session already created, send greeting
            setSessionId(id);
            send("Hi! I've just completed my profile. Let's start my career coaching session.");
        } else {
            send("Hi! I'd like to get career coaching. Let's start.");
        }
    }, []);

    const handleSend = () => {
        if (!input.trim() || isLoading) return;
        send(input.trim());
        setInput('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleNewSession = () => {
        reset();
        voice.stopSpeaking();
        hasInitialized.current = false;
        navigate('/session/new', { replace: true });
        setTimeout(() => {
            send("Hi! I'd like to get career coaching. Let's start.");
        }, 100);
    };

    return (
        <div className="chat-page">
            {/* Header */}
            <header className="chat-header">
                <button
                    className="btn btn-secondary btn-icon"
                    onClick={() => navigate('/')}
                    title="Back to home"
                    id="back-btn"
                >
                    <ArrowLeft size={18} />
                </button>

                <div className="chat-header-center">
                    <div className={`forge-avatar ${voice.isSpeaking ? 'speaking' : ''}`}>
                        <Sparkles size={18} />
                    </div>
                    <div>
                        <h2>Forge</h2>
                        <span className="forge-status">
                            {isLoading
                                ? 'Thinking...'
                                : voice.isSpeaking
                                    ? 'Speaking...'
                                    : voice.isListening
                                        ? '🎙️ Listening...'
                                        : 'Your AI Career Coach'}
                        </span>
                    </div>
                </div>

                <div className="chat-header-actions">
                    {/* TTS Toggle */}
                    <button
                        className={`btn btn-secondary btn-icon ${autoSpeak ? 'active-toggle' : ''}`}
                        onClick={() => {
                            setAutoSpeak(!autoSpeak);
                            if (autoSpeak) voice.stopSpeaking();
                        }}
                        title={autoSpeak ? 'Mute Forge' : 'Unmute Forge'}
                        id="tts-toggle-btn"
                    >
                        {autoSpeak ? <Volume2 size={16} /> : <VolumeX size={16} />}
                    </button>

                    {sessionId && (
                        <a
                            href={getPdfDownloadUrl(sessionId)}
                            className="btn btn-success"
                            target="_blank"
                            rel="noopener noreferrer"
                            id="download-pdf-btn"
                        >
                            <Download size={16} />
                            <span className="hide-mobile">PDF</span>
                        </a>
                    )}
                    <button
                        className="btn btn-secondary btn-icon"
                        onClick={handleNewSession}
                        title="New session"
                        id="new-session-btn"
                    >
                        <RotateCcw size={16} />
                    </button>
                </div>
            </header>

            {/* Messages */}
            <div className="chat-messages" id="chat-messages">
                <AnimatePresence>
                    {messages.map((msg: Message) => (
                        <motion.div
                            key={msg.id}
                            className={`chat-bubble ${msg.role === 'user' ? 'chat-user' : 'chat-forge'}`}
                            initial={{ opacity: 0, y: 12, scale: 0.97 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{ duration: 0.3 }}
                        >
                            <div className="bubble-avatar">
                                {msg.role === 'user' ? <User size={16} /> : <Sparkles size={16} />}
                            </div>
                            <div className="bubble-content">
                                <div className="bubble-name">
                                    {msg.role === 'user' ? 'You' : 'Forge'}
                                </div>
                                <div className="bubble-text">{msg.content}</div>
                                <div className="bubble-time">
                                    {msg.timestamp.toLocaleTimeString([], {
                                        hour: '2-digit',
                                        minute: '2-digit',
                                    })}
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {/* Typing Indicator */}
                {isLoading && (
                    <motion.div
                        className="chat-bubble chat-forge typing-indicator"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        <div className="bubble-avatar">
                            <Sparkles size={16} />
                        </div>
                        <div className="bubble-content">
                            <div className="typing-dots">
                                <span />
                                <span />
                                <span />
                            </div>
                        </div>
                    </motion.div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Voice Interim Display */}
            {voice.isListening && voice.interim && (
                <div className="voice-interim">
                    <Mic size={14} />
                    <span>{voice.interim}</span>
                </div>
            )}

            {/* Input Area */}
            <div className="chat-input-area">
                <div className="chat-input-wrap glass-card">
                    {/* Voice Button */}
                    {voice.isSupported && (
                        <button
                            className={`btn btn-icon voice-btn ${voice.isListening ? 'voice-active' : ''}`}
                            onClick={voice.toggleListening}
                            title={voice.isListening ? 'Stop listening' : 'Voice input'}
                            id="voice-btn"
                        >
                            {voice.isListening ? <MicOff size={18} /> : <Mic size={18} />}
                        </button>
                    )}

                    <textarea
                        ref={inputRef}
                        className="chat-input"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={voice.isListening ? 'Listening... speak now' : 'Tell Forge about your career goals...'}
                        rows={1}
                        disabled={isLoading}
                        id="chat-input"
                    />
                    <button
                        className={`btn btn-primary btn-icon send-btn ${!input.trim() || isLoading ? 'disabled' : ''}`}
                        onClick={handleSend}
                        disabled={!input.trim() || isLoading}
                        id="send-btn"
                    >
                        {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
                    </button>
                </div>
                <p className="chat-disclaimer">
                    Forge uses Gemini AI with live market data. 🎙️ Click the mic to talk.
                </p>
            </div>
        </div>
    );
}
