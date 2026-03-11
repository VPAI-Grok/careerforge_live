import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ArrowRight,
    ArrowLeft,
    Briefcase,
    Target,
    Heart,
    DollarSign,
    Sparkles,
    Check,
    Mic,
} from 'lucide-react';
import { submitProfile, type UserProfile } from '../services/api';
import './OnboardingPage.css';

const PAIN_POINTS = [
    'Bad manager', 'No growth', 'Underpaid', 'Burnout',
    'Bored', 'Toxic culture', 'Job insecurity', 'No work-life balance',
    'Imposter syndrome', 'Overqualified',
];

const MOTIVATIONS = [
    'Money', 'Impact', 'Work-Life Balance', 'Growth', 'Passion', 'Status', 'Security', 'Creativity',
];

const OBLIGATIONS = [
    'Mortgage', 'Kids', 'Student loans', 'Car payment', 'Caregiving', 'None',
];

const DEAL_BREAKERS = [
    'Travel >25%', 'On-call', 'Relocation required', 'No remote option',
    'Long commute', 'Weekend work', 'Open office', 'None',
];

const STEPS = [
    { icon: <Briefcase size={20} />, label: 'Career Info' },
    { icon: <Target size={20} />, label: 'Goals & Skills' },
    { icon: <Heart size={20} />, label: 'How You Feel' },
    { icon: <DollarSign size={20} />, label: 'Life Context' },
];

// ── Helpers (outside component to avoid re-creation) ──
const SOFT_KEYWORDS = [
    'leadership', 'communication', 'teamwork', 'collaboration',
    'problem solving', 'critical thinking', 'time management',
    'public speaking', 'negotiation', 'mentoring', 'empathy',
    'adaptability', 'creativity', 'decision making', 'conflict resolution',
    'interpersonal', 'presentation', 'strategic thinking', 'management',
];

function mapEducation(edu?: string): string {
    if (!edu) return "Bachelor's";
    const lower = edu.toLowerCase();
    if (lower.includes('phd') || lower.includes('doctor')) return 'PhD';
    if (lower.includes('master') || lower.includes('mba') || lower.includes('m.s') || lower.includes('m.a'))
        return "Master's";
    if (lower.includes('bachelor') || lower.includes('b.s') || lower.includes('b.a') || lower.includes('b.e'))
        return "Bachelor's";
    return 'High School';
}

function classifySkills(skills?: string[]): { tech: string[]; soft: string[] } {
    if (!skills || !Array.isArray(skills)) return { tech: [], soft: [] };
    const tech: string[] = [];
    const soft: string[] = [];
    for (const skill of skills) {
        const lower = skill.toLowerCase();
        if (SOFT_KEYWORDS.some((kw) => lower.includes(kw))) {
            soft.push(skill);
        } else {
            tech.push(skill);
        }
    }
    return { tech, soft };
}

type ProfileDraft = Partial<UserProfile>;

export default function OnboardingPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const resumeState = location.state as {
        resumeSessionId?: string;
        resumeData?: Record<string, any>;
    } | null;

    const resumeData = resumeState?.resumeData || null;

    // Track which fields came from resume
    const [fromResume, setFromResume] = useState<Set<string>>(new Set());

    const [step, setStep] = useState(0);
    const [submitting, setSubmitting] = useState(false);
    const [profile, setProfile] = useState<ProfileDraft>({
        current_role: '',
        industry: '',
        years_experience: 3,
        education_level: "Bachelor's",
        dream_roles: [],
        technical_skills: [],
        soft_skills: [],
        motivation: [],
        leadership_vs_ic: 'Both',
        timeline: '1 year',
        work_style: 'Hybrid',
        company_size_preference: 'No preference',
        has_portfolio: false,
        satisfaction_level: 5,
        burnout_level: 3,
        confidence_level: 5,
        risk_tolerance: 5,
        pain_points: [],
        deal_breakers: [],
        location: '',
        willing_to_relocate: false,
        current_salary: null,
        target_salary: null,
        savings_months: null,
        obligations: [],
        learning_hours_per_week: 5,
    });

    // ── Apply resume data AFTER mount ──
    useEffect(() => {
        if (!resumeData) return;
        console.log('📄 Resume data received for pre-population:', resumeData);

        const skills = classifySkills(resumeData.skills);
        const fields: Set<string> = new Set();
        const updates: Partial<ProfileDraft> = {};

        if (resumeData.current_role) {
            updates.current_role = resumeData.current_role;
            fields.add('current_role');
        }
        if (resumeData.industries && Array.isArray(resumeData.industries) && resumeData.industries.length > 0) {
            updates.industry = resumeData.industries.join(', ');
            fields.add('industry');
        }
        if (resumeData.experience_years != null) {
            updates.years_experience = resumeData.experience_years;
            fields.add('years_experience');
        }
        if (resumeData.education) {
            updates.education_level = mapEducation(resumeData.education);
            fields.add('education_level');
        }
        if (skills.tech.length > 0) {
            updates.technical_skills = skills.tech;
            fields.add('technical_skills');
        }
        if (skills.soft.length > 0) {
            updates.soft_skills = skills.soft;
            fields.add('soft_skills');
        }

        console.log('✅ Pre-populating fields:', updates);
        setProfile((prev) => ({ ...prev, ...updates }));
        setFromResume(fields);
    }, [resumeData]);

    const [dreamRoleInput, setDreamRoleInput] = useState('');
    const [techSkillInput, setTechSkillInput] = useState('');
    const [softSkillInput, setSoftSkillInput] = useState('');

    const update = (fields: Partial<ProfileDraft>) =>
        setProfile((prev) => ({ ...prev, ...fields }));

    const toggleChip = (field: keyof ProfileDraft, value: string) => {
        setProfile((prev) => {
            const arr = (prev[field] as string[]) || [];
            return {
                ...prev,
                [field]: arr.includes(value)
                    ? arr.filter((v) => v !== value)
                    : [...arr, value],
            };
        });
    };

    const addTag = (
        field: keyof ProfileDraft,
        value: string,
        setter: (v: string) => void
    ) => {
        if (!value.trim()) return;
        const arr = (profile[field] as string[]) || [];
        if (!arr.includes(value.trim())) {
            update({ [field]: [...arr, value.trim()] });
        }
        setter('');
    };

    const removeTag = (field: keyof ProfileDraft, value: string) => {
        const arr = (profile[field] as string[]) || [];
        update({ [field]: arr.filter((v) => v !== value) });
    };

    const handleSubmit = async (type: 'live' | 'text') => {
        setSubmitting(true);
        try {
            const res = await submitProfile(profile, resumeState?.resumeSessionId);
            const route = type === 'live' ? `/live/${res.session_id}` : `/session/${res.session_id}`;
            navigate(route, {
                state: { profileSubmitted: true },
            });
        } catch {
            // Fallback
            const route = type === 'live' ? '/live/new' : '/session/new';
            navigate(route, { state: { profileSubmitted: true } });
        } finally {
            setSubmitting(false);
        }
    };

    const canProceed = () => {
        if (step === 0) return profile.current_role !== '';
        return true;
    };

    return (
        <div className="onboarding">
            <div className="onboarding-bg">
                <div className="bg-orb bg-orb-1" />
                <div className="bg-orb bg-orb-2" />
            </div>

            {/* Header */}
            <header className="onboarding-header">
                <button className="btn btn-secondary btn-icon" onClick={() => navigate('/')} id="onboard-back-btn">
                    <ArrowLeft size={18} />
                </button>
                <div className="onboarding-title">
                    <Sparkles size={18} className="gradient-text" />
                    <span>{resumeData ? 'Confirm & Fill in the Gaps' : 'Help Forge Understand You'}</span>
                </div>
                <div className="step-count">{step + 1} / {STEPS.length}</div>
            </header>

            {/* Progress Bar */}
            <div className="progress-bar">
                <motion.div
                    className="progress-fill"
                    animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
                    transition={{ duration: 0.4, ease: 'easeInOut' }}
                />
            </div>

            {/* Step Indicators */}
            <div className="step-indicators">
                {STEPS.map((s, i) => (
                    <button
                        key={s.label}
                        className={`step-pill ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
                        onClick={() => i <= step && setStep(i)}
                    >
                        {i < step ? <Check size={14} /> : s.icon}
                        <span className="step-pill-label">{s.label}</span>
                    </button>
                ))}
            </div>

            {/* Step Content */}
            <div className="step-content">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={step}
                        initial={{ opacity: 0, x: 40 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -40 }}
                        transition={{ duration: 0.3 }}
                        className="step-inner"
                    >
                        {/* ── Step 0: Career Info ── */}
                        {step === 0 && (
                            <>
                                <h2>Where are you now?</h2>
                                <p className="step-desc">
                                    {resumeData
                                        ? 'We extracted these from your resume — confirm or edit.'
                                        : 'Tell Forge about your current career situation.'}
                                </p>

                                <div className="field-group">
                                    <label>Current Role / Title {fromResume.has('current_role') && <span className="from-resume">✓ From resume</span>}</label>
                                    <input
                                        type="text"
                                        className="field-input"
                                        value={profile.current_role}
                                        onChange={(e) => update({ current_role: e.target.value })}
                                        placeholder="e.g. Marketing Coordinator"
                                        id="field-current-role"
                                    />
                                </div>

                                <div className="field-row">
                                    <div className="field-group">
                                        <label>Industry {fromResume.has('industry') && <span className="from-resume">✓ From resume</span>}</label>
                                        <input
                                            type="text"
                                            className="field-input"
                                            value={profile.industry}
                                            onChange={(e) => update({ industry: e.target.value })}
                                            placeholder="e.g. Tech, Healthcare"
                                        />
                                    </div>
                                    <div className="field-group">
                                        <label>Years of Experience {fromResume.has('years_experience') && <span className="from-resume">✓ From resume</span>}</label>
                                        <input
                                            type="number"
                                            className="field-input"
                                            value={profile.years_experience ?? 0}
                                            onChange={(e) => update({ years_experience: parseInt(e.target.value) || 0 })}
                                            min={0}
                                            max={40}
                                        />
                                    </div>
                                </div>

                                <div className="field-row">
                                    <div className="field-group">
                                        <label>Education Level {fromResume.has('education_level') && <span className="from-resume">✓ From resume</span>}</label>
                                        <div className="card-select">
                                            {["High School", "Bachelor's", "Master's", "PhD"].map((ed) => (
                                                <button
                                                    key={ed}
                                                    className={`card-option ${profile.education_level === ed ? 'selected' : ''}`}
                                                    onClick={() => update({ education_level: ed })}
                                                >
                                                    {ed}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="field-group">
                                        <label>Location</label>
                                        <input
                                            type="text"
                                            className="field-input"
                                            value={profile.location}
                                            onChange={(e) => update({ location: e.target.value })}
                                            placeholder="e.g. Toronto, Canada"
                                        />
                                    </div>
                                </div>
                            </>
                        )}

                        {/* ── Step 1: Goals & Skills ── */}
                        {step === 1 && (
                            <>
                                <h2>Where do you want to go?</h2>
                                <p className="step-desc">
                                    {resumeData
                                        ? 'Skills from your resume are pre-filled. Add your dream roles and preferences.'
                                        : 'Your dream roles, skills, and career preferences.'}
                                </p>

                                <div className="field-group">
                                    <label>Dream Roles (type and press Enter)</label>
                                    <input
                                        type="text"
                                        className="field-input"
                                        value={dreamRoleInput}
                                        onChange={(e) => setDreamRoleInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('dream_roles', dreamRoleInput, setDreamRoleInput))}
                                        placeholder="e.g. Product Manager, Data Analyst"
                                    />
                                    <div className="tag-list">
                                        {(profile.dream_roles || []).map((r) => (
                                            <span key={r} className="tag">
                                                {r}
                                                <button onClick={() => removeTag('dream_roles', r)}>×</button>
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <div className="field-group">
                                    <label>Technical Skills {fromResume.has('technical_skills') && <span className="from-resume">✓ From resume</span>}</label>
                                    <input
                                        type="text"
                                        className="field-input"
                                        value={techSkillInput}
                                        onChange={(e) => setTechSkillInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('technical_skills', techSkillInput, setTechSkillInput))}
                                        placeholder="e.g. Python, SQL, Figma"
                                    />
                                    <div className="tag-list">
                                        {(profile.technical_skills || []).map((s) => (
                                            <span key={s} className="tag tag-tech">
                                                {s}
                                                <button onClick={() => removeTag('technical_skills', s)}>×</button>
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <div className="field-group">
                                    <label>Soft Skills {fromResume.has('soft_skills') && <span className="from-resume">✓ From resume</span>}</label>
                                    <input
                                        type="text"
                                        className="field-input"
                                        value={softSkillInput}
                                        onChange={(e) => setSoftSkillInput(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('soft_skills', softSkillInput, setSoftSkillInput))}
                                        placeholder="e.g. Leadership, Public Speaking"
                                    />
                                    <div className="tag-list">
                                        {(profile.soft_skills || []).map((s) => (
                                            <span key={s} className="tag tag-soft">
                                                {s}
                                                <button onClick={() => removeTag('soft_skills', s)}>×</button>
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <div className="field-row">
                                    <div className="field-group">
                                        <label>Career Track</label>
                                        <div className="card-select">
                                            {['Lead people', 'Go deep technically', 'Both'].map((t) => (
                                                <button
                                                    key={t}
                                                    className={`card-option ${profile.leadership_vs_ic === t ? 'selected' : ''}`}
                                                    onClick={() => update({ leadership_vs_ic: t })}
                                                >
                                                    {t}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="field-group">
                                        <label>Timeline</label>
                                        <div className="card-select">
                                            {['3 months', '6 months', '1 year', '2+ years'].map((t) => (
                                                <button
                                                    key={t}
                                                    className={`card-option ${profile.timeline === t ? 'selected' : ''}`}
                                                    onClick={() => update({ timeline: t })}
                                                >
                                                    {t}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                <div className="field-group">
                                    <label>What drives you? (select all that apply)</label>
                                    <div className="chip-grid">
                                        {MOTIVATIONS.map((m) => (
                                            <button
                                                key={m}
                                                className={`chip ${(profile.motivation || []).includes(m) ? 'chip-active' : ''}`}
                                                onClick={() => toggleChip('motivation', m)}
                                            >
                                                {m}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </>
                        )}

                        {/* ── Step 2: How You Feel ── */}
                        {step === 2 && (
                            <>
                                <h2>How are you feeling?</h2>
                                <p className="step-desc">Be honest — this helps Forge coach you the right way.</p>

                                <div className="slider-group">
                                    <label>Job Satisfaction <span className="slider-value">{profile.satisfaction_level}/10</span></label>
                                    <input
                                        type="range"
                                        min={1}
                                        max={10}
                                        value={profile.satisfaction_level}
                                        onChange={(e) => update({ satisfaction_level: parseInt(e.target.value) })}
                                        className="slider"
                                    />
                                    <div className="slider-labels"><span>Miserable</span><span>Love it</span></div>
                                </div>

                                <div className="slider-group">
                                    <label>Burnout Level <span className="slider-value">{profile.burnout_level}/10</span></label>
                                    <input
                                        type="range"
                                        min={1}
                                        max={10}
                                        value={profile.burnout_level}
                                        onChange={(e) => update({ burnout_level: parseInt(e.target.value) })}
                                        className="slider slider-danger"
                                    />
                                    <div className="slider-labels"><span>Energized</span><span>Burned out</span></div>
                                </div>

                                <div className="slider-group">
                                    <label>Confidence Level <span className="slider-value">{profile.confidence_level}/10</span></label>
                                    <input
                                        type="range"
                                        min={1}
                                        max={10}
                                        value={profile.confidence_level}
                                        onChange={(e) => update({ confidence_level: parseInt(e.target.value) })}
                                        className="slider"
                                    />
                                    <div className="slider-labels"><span>Uncertain</span><span>Very confident</span></div>
                                </div>

                                <div className="slider-group">
                                    <label>Risk Tolerance <span className="slider-value">{profile.risk_tolerance}/10</span></label>
                                    <input
                                        type="range"
                                        min={1}
                                        max={10}
                                        value={profile.risk_tolerance}
                                        onChange={(e) => update({ risk_tolerance: parseInt(e.target.value) })}
                                        className="slider"
                                    />
                                    <div className="slider-labels"><span>Play it safe</span><span>Go bold</span></div>
                                </div>

                                <div className="field-group">
                                    <label>Career Pain Points</label>
                                    <div className="chip-grid">
                                        {PAIN_POINTS.map((p) => (
                                            <button
                                                key={p}
                                                className={`chip ${(profile.pain_points || []).includes(p) ? 'chip-active chip-warn' : ''}`}
                                                onClick={() => toggleChip('pain_points', p)}
                                            >
                                                {p}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="field-row">
                                    <div className="field-group">
                                        <label>Work Style</label>
                                        <div className="card-select">
                                            {['Remote', 'Hybrid', 'On-site'].map((w) => (
                                                <button
                                                    key={w}
                                                    className={`card-option ${profile.work_style === w ? 'selected' : ''}`}
                                                    onClick={() => update({ work_style: w })}
                                                >
                                                    {w}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="field-group">
                                        <label>Company Size</label>
                                        <div className="card-select">
                                            {['Startup', 'SMB', 'Enterprise', 'No preference'].map((c) => (
                                                <button
                                                    key={c}
                                                    className={`card-option ${profile.company_size_preference === c ? 'selected' : ''}`}
                                                    onClick={() => update({ company_size_preference: c })}
                                                >
                                                    {c}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}

                        {/* ── Step 3: Life Context ── */}
                        {step === 3 && (
                            <>
                                <h2>Life context</h2>
                                <p className="step-desc">Optional but helps Forge give realistic, safe advice.</p>

                                <div className="field-row">
                                    <div className="field-group">
                                        <label>Current Salary (annual)</label>
                                        <div className="input-prefix">
                                            <span>$</span>
                                            <input
                                                type="number"
                                                className="field-input"
                                                value={profile.current_salary ?? ''}
                                                onChange={(e) => update({ current_salary: e.target.value ? parseInt(e.target.value) : null })}
                                                placeholder="65,000"
                                            />
                                        </div>
                                    </div>
                                    <div className="field-group">
                                        <label>Target Salary</label>
                                        <div className="input-prefix">
                                            <span>$</span>
                                            <input
                                                type="number"
                                                className="field-input"
                                                value={profile.target_salary ?? ''}
                                                onChange={(e) => update({ target_salary: e.target.value ? parseInt(e.target.value) : null })}
                                                placeholder="95,000"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="field-row">
                                    <div className="field-group">
                                        <label>Savings (months of runway)</label>
                                        <input
                                            type="number"
                                            className="field-input"
                                            value={profile.savings_months ?? ''}
                                            onChange={(e) => update({ savings_months: e.target.value ? parseInt(e.target.value) : null })}
                                            placeholder="e.g. 6"
                                            min={0}
                                        />
                                    </div>
                                    <div className="field-group">
                                        <label>Hours/week for learning</label>
                                        <input
                                            type="number"
                                            className="field-input"
                                            value={profile.learning_hours_per_week ?? 5}
                                            onChange={(e) => update({ learning_hours_per_week: parseInt(e.target.value) || 5 })}
                                            min={1}
                                            max={40}
                                        />
                                    </div>
                                </div>

                                <div className="field-group">
                                    <label>Financial Obligations</label>
                                    <div className="chip-grid">
                                        {OBLIGATIONS.map((o) => (
                                            <button
                                                key={o}
                                                className={`chip ${(profile.obligations || []).includes(o) ? 'chip-active' : ''}`}
                                                onClick={() => toggleChip('obligations', o)}
                                            >
                                                {o}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="field-group">
                                    <label>Deal Breakers</label>
                                    <div className="chip-grid">
                                        {DEAL_BREAKERS.map((d) => (
                                            <button
                                                key={d}
                                                className={`chip ${(profile.deal_breakers || []).includes(d) ? 'chip-active chip-warn' : ''}`}
                                                onClick={() => toggleChip('deal_breakers', d)}
                                            >
                                                {d}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="field-row">
                                    <div className="field-group">
                                        <label className="checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={profile.willing_to_relocate}
                                                onChange={(e) => update({ willing_to_relocate: e.target.checked })}
                                            />
                                            Open to relocation
                                        </label>
                                    </div>
                                    <div className="field-group">
                                        <label className="checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={profile.has_portfolio}
                                                onChange={(e) => update({ has_portfolio: e.target.checked })}
                                            />
                                            I have a portfolio / side projects
                                        </label>
                                    </div>
                                </div>
                            </>
                        )}
                    </motion.div>
                </AnimatePresence>
            </div>

            {/* Footer with navigation */}
            <footer className="onboarding-footer">
                <button
                    className="btn btn-secondary"
                    onClick={() => setStep((s) => s - 1)}
                    disabled={step === 0}
                    id="onboard-prev-btn"
                >
                    <ArrowLeft size={16} /> Back
                </button>

                {step < STEPS.length - 1 ? (
                    <button
                        className="btn btn-primary"
                        onClick={() => setStep((s) => s + 1)}
                        disabled={!canProceed()}
                        id="onboard-next-btn"
                    >
                        Next <ArrowRight size={16} />
                    </button>
                ) : (
                    <div className="onboarding-final-actions" style={{ display: 'flex', gap: '12px', width: '100%', maxWidth: '600px' }}>
                        <button
                            className="btn btn-success btn-lg"
                            onClick={() => handleSubmit('live')}
                            disabled={submitting}
                            id="onboard-submit-live-btn"
                            style={{ flex: 1, background: 'linear-gradient(135deg, #22c55e, #16a34a)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                        >
                            {submitting ? (
                                <><div className="spinner" /> Loading...</>
                            ) : (
                                <><Mic size={18} /> Start Live Voice Session</>
                            )}
                        </button>
                        <button
                            className="btn btn-primary btn-lg"
                            onClick={() => handleSubmit('text')}
                            disabled={submitting}
                            id="onboard-submit-text-btn"
                            style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                        >
                            {submitting ? (
                                <><div className="spinner" /> Loading...</>
                            ) : (
                                <><Sparkles size={18} /> Start Text Chat</>
                            )}
                        </button>
                    </div>
                )}
            </footer>
        </div>
    );
}
