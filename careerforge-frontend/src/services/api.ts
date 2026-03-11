/**
 * CareerForge API Service — handles all backend communication.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ChatResponse {
  session_id: string;
  response: string;
  user_id: string;
}

export interface ResumeUploadResponse {
  session_id: string;
  message: string;
  resume_data: Record<string, unknown> | null;
}

export interface UserProfile {
  current_role: string;
  industry: string;
  years_experience: number;
  education_level: string;
  satisfaction_level: number;
  burnout_level: number;
  confidence_level: number;
  pain_points: string[];
  dream_roles: string[];
  motivation: string[];
  leadership_vs_ic: string;
  timeline: string;
  technical_skills: string[];
  soft_skills: string[];
  has_portfolio: boolean;
  work_style: string;
  company_size_preference: string;
  deal_breakers: string[];
  location: string;
  willing_to_relocate: boolean;
  current_salary: number | null;
  target_salary: number | null;
  savings_months: number | null;
  obligations: string[];
  risk_tolerance: number;
  learning_hours_per_week: number;
}

export interface ProfileResponse {
  session_id: string;
  message: string;
  profile_summary: string;
}

/** Submit user profile from onboarding questionnaire */
export async function submitProfile(
  profile: Partial<UserProfile>,
  sessionId?: string
): Promise<ProfileResponse> {
  const res = await fetch(`${API_BASE}/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...profile,
      session_id: sessionId || null,
    }),
  });
  if (!res.ok) throw new Error(`Profile submission failed: ${res.statusText}`);
  return res.json();
}

/** Send a text message to Forge */
export async function sendMessage(
  message: string,
  sessionId?: string,
  userId = 'user_01'
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId || null,
      user_id: userId,
    }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);
  return res.json();
}

/** Upload a resume file for vision analysis */
export async function uploadResume(
  file: File,
  sessionId?: string
): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (sessionId) formData.append('session_id', sessionId);

  const res = await fetch(`${API_BASE}/upload-resume`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

/** Download the generated PDF */
export function getPdfDownloadUrl(sessionId: string): string {
  return `${API_BASE}/download-pdf/${sessionId}`;
}

/** Fetch the career plan data for dashboard display */
export async function getSessionPlan(sessionId: string) {
  const res = await fetch(`${API_BASE}/session/${sessionId}/plan`);
  if (!res.ok) throw new Error(`Failed to fetch plan: ${res.statusText}`);
  return res.json();
}

/** Check API health */
export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

/**
 * Create a WebSocket connection for real-time streaming chat.
 */
export function createChatWebSocket(
  sessionId: string,
  onMessage: (data: { type: string; content: string; is_final: boolean }) => void,
  onError?: (error: Event) => void,
  onClose?: () => void
): WebSocket {
  const wsBase = API_BASE.replace(/^http/, 'ws');
  const ws = new WebSocket(`${wsBase}/ws/chat/${sessionId}`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onerror = (event) => {
    onError?.(event);
  };

  ws.onclose = () => {
    onClose?.();
  };

  return ws;
}
