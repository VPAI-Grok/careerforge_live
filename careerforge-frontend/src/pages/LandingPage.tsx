import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import {
    Upload,
    Mic,
    Sparkles,
    FileText,
    Target,
    Brain,
    Download,
    ArrowRight,
    Zap,
} from 'lucide-react';
import './LandingPage.css';

export default function LandingPage() {
    const navigate = useNavigate();
    const [uploading, setUploading] = useState(false);

    const onDrop = useCallback(
        async (acceptedFiles: File[]) => {
            if (acceptedFiles.length === 0) return;
            const file = acceptedFiles[0];
            setUploading(true);

            try {
                const formData = new FormData();
                formData.append('file', file);

                const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                const res = await fetch(`${baseUrl}/upload-resume`, {
                    method: 'POST',
                    body: formData,
                });
                const data = await res.json();
                // Navigate to onboarding with resume data for pre-population
                navigate('/onboarding', {
                    state: {
                        resumeSessionId: data.session_id,
                        resumeData: data.resume_data,
                    },
                });
            } catch {
                // Fallback: go to chat without resume
                navigate('/onboarding');
            } finally {
                setUploading(false);
            }
        },
        [navigate]
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
    });

    return (
        <div className="landing">
            {/* Background Effects */}
            <div className="landing-bg">
                <div className="bg-orb bg-orb-1" />
                <div className="bg-orb bg-orb-2" />
                <div className="bg-orb bg-orb-3" />
                <div className="bg-grid" />
            </div>

            {/* Hero Section */}
            <motion.header
                className="landing-hero"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7 }}
            >
                <div className="hero-badge">
                    <Sparkles size={14} />
                    <span>Powered by Gemini AI</span>
                </div>

                <h1 className="hero-title">
                    Meet <span className="gradient-text">Forge</span>, Your AI
                    <br />
                    Career Coach
                </h1>

                <p className="hero-subtitle">
                    Talk to a world-class career counselor in real time. Upload your resume,
                    have a natural conversation, and walk away with a personalised career
                    roadmap — in under 15 minutes.
                </p>

                {/* CTA Section */}
                <div className="hero-ctas">
                    {/* Resume Upload */}
                    <div
                        {...getRootProps()}
                        className={`upload-zone ${isDragActive ? 'upload-zone-active' : ''} ${uploading ? 'upload-zone-loading' : ''}`}
                        id="resume-upload-zone"
                    >
                        <input {...getInputProps()} id="resume-file-input" />
                        {uploading ? (
                            <div className="upload-loading">
                                <div className="spinner" />
                                <p>Analyzing your resume...</p>
                            </div>
                        ) : isDragActive ? (
                            <div className="upload-active">
                                <Upload size={32} />
                                <p>Drop your resume here</p>
                            </div>
                        ) : (
                            <div className="upload-content">
                                <div className="upload-icon-wrap">
                                    <FileText size={28} />
                                </div>
                                <p className="upload-title">Drop your resume here</p>
                                <p className="upload-hint">PDF, PNG, or JPEG — we'll scan it with AI vision</p>
                            </div>
                        )}
                    </div>

                    <div className="cta-divider">
                        <span>or</span>
                    </div>

                    <div className="cta-buttons">
                        {/* Start Live Voice Session */}
                        <motion.button
                            className="btn btn-primary btn-lg start-live-btn"
                            onClick={() => navigate('/live/new')}
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.97 }}
                            id="start-live-btn"
                            style={{
                                background: 'linear-gradient(135deg, #22c55e, #16a34a)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                            }}
                        >
                            <Mic size={20} />
                            🎙️ Start Live Session
                            <ArrowRight size={18} />
                        </motion.button>

                        {/* Start Text Chat Button */}
                        <motion.button
                            className="btn btn-primary btn-lg start-talking-btn"
                            onClick={() => navigate('/onboarding')}
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.97 }}
                            id="start-talking-btn"
                        >
                            <Sparkles size={20} />
                            Text Coaching
                            <ArrowRight size={18} />
                        </motion.button>
                    </div>
                </div>
            </motion.header>

            {/* Features Grid */}
            <motion.section
                className="features-section"
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.3 }}
            >
                <div className="features-grid">
                    {[
                        {
                            icon: <Brain size={24} />,
                            title: 'AI Resume Vision',
                            desc: 'Reads any resume layout — even scanned photos — and references your specific experience in conversation.',
                        },
                        {
                            icon: <Mic size={24} />,
                            title: 'Natural Conversation',
                            desc: 'Real-time chat with Forge who asks smart follow-up questions, interrupts thoughtfully, and remembers everything.',
                        },
                        {
                            icon: <Target size={24} />,
                            title: 'Live Market Data',
                            desc: 'Real-time salary ranges, in-demand skills, and trending roles pulled from current job postings.',
                        },
                        {
                            icon: <Zap size={24} />,
                            title: 'Short + Long-Term Plans',
                            desc: 'Month-by-month action plan plus a 5-year vision with salary progression and promotion paths.',
                        },
                        {
                            icon: <Download size={24} />,
                            title: 'PDF Report',
                            desc: 'Professional downloadable career roadmap with timelines, skill checklists, and course links.',
                        },
                        {
                            icon: <Sparkles size={24} />,
                            title: 'Empathetic Mentor',
                            desc: 'Warm, honest, and encouraging. Handles tough topics like burnout and career changes with care.',
                        },
                    ].map((feat, i) => (
                        <motion.div
                            key={feat.title}
                            className="feature-card glass-card"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.4 + i * 0.1 }}
                        >
                            <div className="feature-icon">{feat.icon}</div>
                            <h3>{feat.title}</h3>
                            <p>{feat.desc}</p>
                        </motion.div>
                    ))}
                </div>
            </motion.section>

            {/* Footer */}
            <footer className="landing-footer">
                <p>
                    CareerForge Live — Built for the Gemini AI Agent Challenge
                </p>
            </footer>
        </div>
    );
}
