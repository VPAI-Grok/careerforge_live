import { useState, useRef, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import {
    ArrowLeft,
    Mic,
    MicOff,
    PhoneOff,
    Send,
    Sparkles,
    User,
    Loader2,
    Upload,
    FileText,
    CheckCircle2,
    Briefcase,
    GraduationCap,
    Code2,
} from 'lucide-react';
import { useLiveAgent } from '../hooks/useLiveAgent';
import './LiveSession.css';

interface ResumeData {
    name?: string;
    email?: string;
    skills?: string[];
    experience?: Array<{ title?: string; company?: string; duration?: string }>;
    education?: Array<{ degree?: string; institution?: string }>;
    career_level?: string;
    [key: string]: unknown;
}

export default function LiveSession() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const live = useLiveAgent();
    const [textInput, setTextInput] = useState('');
    const [showTextInput, setShowTextInput] = useState(false);
    const transcriptEndRef = useRef<HTMLDivElement>(null);
    const sessionIdRef = useRef(id && id !== 'new' ? id : crypto.randomUUID());

    // ── Resume Gate State ────────────────────────────────────────────────
    const [resumeData, setResumeData] = useState<ResumeData | null>(null);
    const [uploadingResume, setUploadingResume] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [resumeFileName, setResumeFileName] = useState<string | null>(null);

    // Resume is required to start the session
    const hasResume = resumeData !== null;

    // ── Resume Upload Handler ────────────────────────────────────────────
    const onDrop = useCallback(
        async (acceptedFiles: File[]) => {
            if (acceptedFiles.length === 0) return;
            const file = acceptedFiles[0];
            setUploadingResume(true);
            setUploadError(null);
            setResumeFileName(file.name);

            try {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('session_id', sessionIdRef.current);

                const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                const res = await fetch(`${baseUrl}/upload-resume`, {
                    method: 'POST',
                    body: formData,
                });
                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.detail || 'Upload failed');
                }
                const data = await res.json();
                setResumeData(data.resume_data || {});
            } catch (error: any) {
                console.error('Resume upload failed:', error);
                setUploadError(error.message || 'Upload failed. Please try again.');
                setResumeFileName(null);
            } finally {
                setUploadingResume(false);
            }
        },
        []
    );

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf'],
            'image/png': ['.png'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/webp': ['.webp'],
        },
        maxFiles: 1,
        multiple: false,
        disabled: uploadingResume,
    });

    // ── Session Handlers ─────────────────────────────────────────────────
    const handleStartSession = async () => {
        await live.connect('user_01', sessionIdRef.current);
    };

    const handleEndSession = () => {
        live.disconnect();
        // Redirect to the post-session report page to generate the career plan
        navigate(`/report/${sessionIdRef.current}`);
    };

    const handleSendText = () => {
        if (!textInput.trim()) return;
        live.sendText(textInput.trim());
        setTextInput('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendText();
        }
    };

    const handleNewResume = () => {
        setResumeData(null);
        setResumeFileName(null);
        setUploadError(null);
    };

    // Auto-scroll transcripts
    useEffect(() => {
        transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [live.transcripts, live.inputTranscript, live.outputTranscript]);

    // ── Status Helpers ───────────────────────────────────────────────────
    const getStatusText = () => {
        switch (live.status) {
            case 'connecting':
                return 'Connecting to Forge...';
            case 'connected':
                if (live.isForgeSpeaking) return 'Forge is speaking...';
                if (live.isMicActive) return 'Listening to you...';
                return 'Connected — tap mic to speak';
            case 'disconnected':
                return 'Session ended';
            case 'error':
                return live.error || 'Connection error';
            default:
                return 'Ready';
        }
    };

    const getStatusColor = () => {
        switch (live.status) {
            case 'connected':
                return 'status-connected';
            case 'connecting':
                return 'status-connecting';
            case 'error':
                return 'status-error';
            default:
                return '';
        }
    };

    // ── Extract display data from resume ─────────────────────────────────
    const getSkillsPreview = () => {
        if (!resumeData?.skills) return [];
        return (resumeData.skills as string[]).slice(0, 6);
    };

    const getLatestRole = () => {
        if (!resumeData?.experience || !Array.isArray(resumeData.experience)) return null;
        return resumeData.experience[0] || null;
    };

    const getEducation = () => {
        if (!resumeData?.education || !Array.isArray(resumeData.education)) return null;
        return resumeData.education[0] || null;
    };

    // ── Render ───────────────────────────────────────────────────────────
    return (
        <div className="live-page">
            {/* Top bar */}
            <header className="live-header">
                <button
                    className="live-back-btn"
                    onClick={() => navigate('/')}
                    id="live-back-btn"
                >
                    <ArrowLeft size={20} />
                </button>

                <div className="live-header-center">
                    <div className={`live-connection-dot ${getStatusColor()}`} />
                    <span className="live-header-title">CareerForge Live</span>
                </div>

                <button
                    className="live-end-btn"
                    onClick={handleEndSession}
                    id="live-end-btn"
                >
                    <PhoneOff size={18} />
                    <span className="hide-mobile">End</span>
                </button>
            </header>

            {/* Main content area */}
            <div className="live-main">
                {/* ── GATE: Resume Upload (before session) ──────────────── */}
                {live.status === 'idle' && (
                    <div className="resume-gate">
                        <AnimatePresence mode="wait">
                            {!hasResume ? (
                                /* Step 1: Upload Resume */
                                <motion.div
                                    key="upload"
                                    className="resume-gate-content"
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                    transition={{ duration: 0.3 }}
                                >
                                    <div className="resume-gate-icon">
                                        <Sparkles size={32} />
                                    </div>
                                    <h2 className="resume-gate-title">Upload Your Resume</h2>
                                    <p className="resume-gate-subtitle">
                                        Forge needs your resume to provide personalized career coaching.
                                        Upload it and we'll start your session with full context.
                                    </p>

                                    <div
                                        {...getRootProps()}
                                        className={`resume-dropzone ${isDragActive ? 'dropzone-active' : ''} ${uploadingResume ? 'dropzone-uploading' : ''}`}
                                        id="resume-dropzone"
                                    >
                                        <input {...getInputProps()} id="resume-file-input" />
                                        {uploadingResume ? (
                                            <div className="dropzone-content">
                                                <Loader2 size={36} className="spin" />
                                                <span className="dropzone-text">Analyzing your resume...</span>
                                                <span className="dropzone-hint">{resumeFileName}</span>
                                            </div>
                                        ) : (
                                            <div className="dropzone-content">
                                                <Upload size={36} />
                                                <span className="dropzone-text">
                                                    {isDragActive ? 'Drop your resume here' : 'Drag & drop your resume'}
                                                </span>
                                                <span className="dropzone-hint">or click to browse • PDF, PNG, JPEG</span>
                                            </div>
                                        )}
                                    </div>

                                    {uploadError && (
                                        <motion.p
                                            className="resume-error"
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                        >
                                            {uploadError}
                                        </motion.p>
                                    )}
                                </motion.div>
                            ) : (
                                /* Step 2: Resume Summary + Begin Session */
                                <motion.div
                                    key="summary"
                                    className="resume-gate-content"
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                    transition={{ duration: 0.3 }}
                                >
                                    <div className="resume-gate-icon resume-gate-success">
                                        <CheckCircle2 size={32} />
                                    </div>
                                    <h2 className="resume-gate-title">Resume Analyzed</h2>
                                    <p className="resume-gate-subtitle">
                                        Here's what Forge found. Ready to start your coaching session?
                                    </p>

                                    {/* Resume Summary Card */}
                                    <div className="resume-summary-card">
                                        {resumeData?.name && (
                                            <div className="resume-summary-name">
                                                <User size={16} />
                                                <span>{resumeData.name as string}</span>
                                            </div>
                                        )}

                                        {getLatestRole() && (
                                            <div className="resume-summary-row">
                                                <Briefcase size={14} />
                                                <span>
                                                    {getLatestRole()?.title}
                                                    {getLatestRole()?.company && ` at ${getLatestRole()?.company}`}
                                                </span>
                                            </div>
                                        )}

                                        {getEducation() && (
                                            <div className="resume-summary-row">
                                                <GraduationCap size={14} />
                                                <span>
                                                    {getEducation()?.degree}
                                                    {getEducation()?.institution && ` — ${getEducation()?.institution}`}
                                                </span>
                                            </div>
                                        )}

                                        {getSkillsPreview().length > 0 && (
                                            <div className="resume-summary-skills">
                                                <div className="resume-skills-label">
                                                    <Code2 size={14} />
                                                    <span>Skills</span>
                                                </div>
                                                <div className="resume-skill-tags">
                                                    {getSkillsPreview().map((skill, i) => (
                                                        <span key={i} className="resume-skill-tag">{skill}</span>
                                                    ))}
                                                    {(resumeData?.skills as string[])?.length > 6 && (
                                                        <span className="resume-skill-tag resume-skill-more">
                                                            +{(resumeData?.skills as string[]).length - 6}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        <div className="resume-file-info">
                                            <FileText size={12} />
                                            <span>{resumeFileName}</span>
                                        </div>
                                    </div>

                                    {/* Action Buttons */}
                                    <div className="resume-gate-actions">
                                        <motion.button
                                            className="live-start-btn"
                                            onClick={handleStartSession}
                                            whileHover={{ scale: 1.03 }}
                                            whileTap={{ scale: 0.97 }}
                                            id="start-session-btn"
                                        >
                                            <Mic size={24} />
                                            <span>Begin Session</span>
                                        </motion.button>

                                        <button
                                            className="resume-change-btn"
                                            onClick={handleNewResume}
                                            id="change-resume-btn"
                                        >
                                            Upload different resume
                                        </button>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                )}

                {/* ── ACTIVE SESSION (after connecting) ────────────────── */}
                {live.status !== 'idle' && (
                    <>
                        {/* Avatar / Visualizer */}
                        <div className="live-avatar-area">
                            {live.status === 'connecting' ? (
                                <div className="live-orb-container">
                                    <div className="live-avatar">
                                        <Loader2 size={40} className="spin" />
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <div className="live-orb-container">
                                        {/* Advanced Pulsing rings when speaking or listening */}
                                        <AnimatePresence>
                                            {(live.isForgeSpeaking || live.isMicActive) && (
                                                <>
                                                    {[0, 1, 2, 3].map((i) => (
                                                        <motion.div
                                                            key={i}
                                                            className={`pulse-ring ${live.isForgeSpeaking ? 'ring-speaking' : 'ring-listening'}`}
                                                            initial={{ scale: 1, opacity: live.isForgeSpeaking ? 0.8 : 0.4 }}
                                                            animate={{ scale: live.isForgeSpeaking ? 2.0 + i * 0.4 : 1.5 + i * 0.2, opacity: 0 }}
                                                            transition={{
                                                                duration: live.isForgeSpeaking ? 1.5 : 3,
                                                                repeat: Infinity,
                                                                delay: i * (live.isForgeSpeaking ? 0.2 : 0.6),
                                                                ease: 'easeOut',
                                                            }}
                                                        />
                                                    ))}
                                                </>
                                            )}
                                        </AnimatePresence>

                                        <motion.div
                                            className={`live-avatar ${live.isForgeSpeaking
                                                ? 'avatar-speaking'
                                                : live.isMicActive
                                                    ? 'avatar-listening'
                                                    : 'avatar-idle'
                                                }`}
                                            animate={{
                                                scale: live.isForgeSpeaking
                                                    ? [1, 1.15, 1]
                                                    : live.isMicActive
                                                        ? [1, 1.05, 1]
                                                        : [1, 1.02, 1],
                                                borderRadius: live.isForgeSpeaking 
                                                    ? [
                                                        "40% 60% 70% 30% / 40% 50% 60% 50%",
                                                        "60% 40% 30% 70% / 60% 30% 70% 40%",
                                                        "30% 70% 70% 30% / 30% 30% 70% 70%",
                                                        "40% 60% 70% 30% / 40% 50% 60% 50%"
                                                    ] 
                                                    : [
                                                        "50% 50% 50% 50% / 50% 50% 50% 50%",
                                                        "52% 48% 51% 49% / 51% 49% 52% 48%",
                                                        "50% 50% 50% 50% / 50% 50% 50% 50%"
                                                    ],
                                                rotate: live.isForgeSpeaking ? [0, 90, 180, 270, 360] : [0, 10, -10, 0],
                                            }}
                                            transition={{
                                                scale: {
                                                    duration: live.isForgeSpeaking ? 0.8 : 3,
                                                    repeat: Infinity,
                                                    ease: 'easeInOut',
                                                },
                                                borderRadius: {
                                                    duration: live.isForgeSpeaking ? 4 : 8,
                                                    repeat: Infinity,
                                                    ease: 'easeInOut',
                                                },
                                                rotate: {
                                                    duration: live.isForgeSpeaking ? 8 : 15,
                                                    repeat: Infinity,
                                                    ease: 'linear',
                                                }
                                            }}
                                        />
                                    </div>
                                </>
                            )}
                            
                            {/* Status text */}
                            <p className={`live-status-text ${getStatusColor()}`}>
                                {live.status === 'connecting' && <Loader2 size={14} className="spin" />}
                                {getStatusText()}
                            </p>
                        </div>

                        {/* Transcription area */}
                        <div className="live-transcripts" id="live-transcripts">
                            {live.transcripts.map((t, i) => (
                                <motion.div
                                    key={i}
                                    className={`transcript-line ${t.type === 'input' ? 'transcript-user' : 'transcript-forge'}`}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.2 }}
                                >
                                    <div className="transcript-icon">
                                        {t.type === 'input' ? <User size={12} /> : <Sparkles size={12} />}
                                    </div>
                                    <span>{t.text}</span>
                                </motion.div>
                            ))}

                            {/* Live partial transcripts */}
                            {live.inputTranscript && live.isMicActive && (
                                <div className="transcript-line transcript-user transcript-partial">
                                    <div className="transcript-icon">
                                        <Mic size={12} />
                                    </div>
                                    <span>{live.inputTranscript}</span>
                                </div>
                            )}
                            {live.outputTranscript && live.isForgeSpeaking && (
                                <div className="transcript-line transcript-forge transcript-partial">
                                    <div className="transcript-icon">
                                        <Sparkles size={12} />
                                    </div>
                                    <span>{live.outputTranscript}</span>
                                </div>
                            )}

                            <div ref={transcriptEndRef} />
                        </div>
                    </>
                )}
            </div>

            {/* Bottom controls (only when connected) */}
            {live.status !== 'idle' && (
                <div className="live-controls">
                    {/* Text input toggle */}
                    {showTextInput && (
                        <motion.div
                            className="live-text-input-area"
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                        >
                            <input
                                type="text"
                                className="live-text-input"
                                value={textInput}
                                onChange={(e) => setTextInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Type a message..."
                                id="live-text-input"
                            />
                            <button
                                className="live-send-btn"
                                onClick={handleSendText}
                                disabled={!textInput.trim()}
                                id="live-send-btn"
                            >
                                <Send size={16} />
                            </button>
                        </motion.div>
                    )}

                    <div className="live-btn-row">
                        {/* Text toggle button */}
                        <button
                            className={`live-control-btn secondary ${showTextInput ? 'active' : ''}`}
                            onClick={() => setShowTextInput(!showTextInput)}
                            title="Type instead"
                            id="toggle-text-btn"
                        >
                            <Send size={20} />
                        </button>

                        {/* Main mic button */}
                        <button
                            className={`live-mic-btn ${live.isMicActive ? 'mic-active' : ''} ${live.status !== 'connected' ? 'mic-disabled' : ''
                                }`}
                            onClick={live.toggleMic}
                            disabled={live.status !== 'connected'}
                            title={live.isMicActive ? 'Mute microphone' : 'Unmute microphone'}
                            id="live-mic-btn"
                        >
                            {live.isMicActive ? <Mic size={28} /> : <MicOff size={28} />}
                        </button>

                        {/* End call */}
                        <button
                            className="live-control-btn danger"
                            onClick={handleEndSession}
                            title="End session"
                            id="end-call-btn"
                        >
                            <PhoneOff size={20} />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
