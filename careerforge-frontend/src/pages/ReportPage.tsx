import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './ReportPage.css';

interface ReportResponse {
    status: string;
    message: string;
    has_pdf: boolean;
}

export default function ReportPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [report, setReport] = useState<ReportResponse | null>(null);

    useEffect(() => {
        if (!id) return;

        let isMounted = true;

        const generateReport = async () => {
            try {
                const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                const response = await axios.post<ReportResponse>(`${baseUrl}/generate-report`, {
                    session_id: id
                });
                if (isMounted) {
                    setReport(response.data);
                    setLoading(false);
                }
            } catch (err: any) {
                console.error('Failed to generate report:', err);
                if (isMounted) {
                    setError('Failed to generate your career plan. Please check the server logs or try again.');
                    setLoading(false);
                }
            }
        };

        generateReport();

        return () => {
            isMounted = false;
        };
    }, [id]);

    const handleDownloadPdf = () => {
        if (!id) return;
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        window.open(`${baseUrl}/download-pdf/${id}`, '_blank');
    };

    return (
        <div className="report-page">
            <header className="report-header">
                <h2>⚡ CareerForge</h2>
                <div className="report-session-id">Session ID: {id}</div>
            </header>

            <main className="report-container">
                {loading && (
                    <div className="report-loading">
                        <div className="report-spinner"></div>
                        <h3>Generating your personalised career roadmap...</h3>
                        <p>Our AI is analysing your profile, searching the live job market, identifying skill gaps, and building a month-by-month plan. This usually takes about 30-45 seconds.</p>
                    </div>
                )}

                {error && (
                    <div className="report-error">
                        <h3>Error</h3>
                        <p>{error}</p>
                        <button className="btn-secondary" onClick={() => navigate('/')}>
                            Return to Home
                        </button>
                    </div>
                )}

                {!loading && !error && report && (
                    <div className="report-content">
                        <h3>Your Career Plan is Ready!</h3>

                        <div className="report-markdown">
                            <ReactMarkdown>{report.message}</ReactMarkdown>
                        </div>

                        <div className="report-actions">
                            {report.has_pdf && (
                                <button className="btn-primary btn-download" onClick={handleDownloadPdf}>
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon-pdf">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                        <polyline points="7 10 12 15 17 10"></polyline>
                                        <line x1="12" y1="15" x2="12" y2="3"></line>
                                    </svg>
                                    Download PDF Report
                                </button>
                            )}

                            <button className="btn-secondary" onClick={() => navigate('/')}>
                                Start New Session
                            </button>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
