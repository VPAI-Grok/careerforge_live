import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * useLiveAgent — React hook for bidirectional audio streaming with
 * the Gemini Live API via the CareerForge backend.
 *
 * Audio flow:
 *   Mic → AudioWorklet (PCM 16kHz 16-bit) → WebSocket binary → Backend → Gemini Live API
 *   Gemini Live API → Backend → WebSocket JSON events → AudioBufferSourceNode playback (24kHz)
 *
 * PLAYBACK: Uses AudioBufferSourceNode queue (no AudioWorklet needed for playback,
 * avoids Blob URL worklet issues in some browsers).
 */

// Derive WebSocket URL from API URL (http→ws, https→wss)
const _apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = _apiUrl.replace(/^http/, 'ws');
const SAMPLE_RATE = 16000;
const PLAYBACK_RATE = 24000;

interface Transcription {
    text: string;
    type: 'input' | 'output';
}

interface UseLiveAgentReturn {
    status: 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';
    isMicActive: boolean;
    isForgeSpeaking: boolean;
    inputTranscript: string;
    outputTranscript: string;
    transcripts: Transcription[];
    textResponse: string;
    error: string | null;
    connect: (userId: string, sessionId: string) => Promise<void>;
    disconnect: () => void;
    toggleMic: () => void;
    sendText: (text: string) => void;
}

// ── Inline AudioWorklet: PCM Mic Capture (16kHz 16-bit mono) ─────────────────
const RECORDER_WORKLET_CODE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
    process(inputs) {
        const input = inputs[0];
        if (input.length > 0) {
            const channelData = input[0];
            const pcm16 = new Int16Array(channelData.length);
            for (let i = 0; i < channelData.length; i++) {
                const s = Math.max(-1, Math.min(1, channelData[i]));
                pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
        }
        return true;
    }
}
registerProcessor('pcm-capture-processor', PcmCaptureProcessor);
`;

function base64ToArrayBuffer(base64: string): ArrayBuffer {
    // Handle base64url formatting and padding, which Gemini might use
    const b64Str = base64.replace(/-/g, '+').replace(/_/g, '/');
    const padded = b64Str.padEnd(b64Str.length + (4 - (b64Str.length % 4)) % 4, '=');

    const binary = atob(padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

// ── Helper: Int16 PCM → Float32 audio samples ───────────────────────────────
function int16ToFloat32(int16Buffer: ArrayBuffer): Float32Array {
    const int16 = new Int16Array(int16Buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768;
    }
    return float32;
}

export function useLiveAgent(): UseLiveAgentReturn {
    const [status, setStatus] = useState<UseLiveAgentReturn['status']>('idle');
    const [isMicActive, setIsMicActive] = useState(false);
    const [isForgeSpeaking, setIsForgeSpeaking] = useState(false);
    const [inputTranscript, setInputTranscript] = useState('');
    const [outputTranscript, setOutputTranscript] = useState('');
    const [transcripts, setTranscripts] = useState<Transcription[]>([]);
    const [textResponse, setTextResponse] = useState('');
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);

    // Mic capture refs
    const recorderContextRef = useRef<AudioContext | null>(null);
    const recorderNodeRef = useRef<AudioWorkletNode | null>(null);
    const mediaStreamRef = useRef<MediaStream | null>(null);

    // Audio playback refs (simple queue approach — no worklet needed)
    const playerContextRef = useRef<AudioContext | null>(null);
    const nextPlayTimeRef = useRef(0);
    const isPlayingRef = useRef(false);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            stopMicInternal();
            if (playerContextRef.current) {
                playerContextRef.current.close();
                playerContextRef.current = null;
            }
            if (wsRef.current) wsRef.current.close();
        };
    }, []);

    // ── Mic capture ──────────────────────────────────────────────────────────
    const startMicInternal = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: SAMPLE_RATE,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            mediaStreamRef.current = stream;

            const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
            recorderContextRef.current = ctx;

            const blob = new Blob([RECORDER_WORKLET_CODE], { type: 'application/javascript' });
            const url = URL.createObjectURL(blob);
            await ctx.audioWorklet.addModule(url);
            URL.revokeObjectURL(url);

            const source = ctx.createMediaStreamSource(stream);
            const worklet = new AudioWorkletNode(ctx, 'pcm-capture-processor');
            recorderNodeRef.current = worklet;

            worklet.port.onmessage = (e: MessageEvent) => {
                if (wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(e.data);
                }
            };

            source.connect(worklet);
            // Don't connect to destination (no local feedback)
            setIsMicActive(true);
            console.log('[LiveAgent] Mic capture started');
        } catch (err) {
            console.error('[LiveAgent] Microphone error:', err);
            setError('Failed to access microphone. Please allow microphone permissions.');
        }
    }, []);

    const stopMicInternal = useCallback(() => {
        recorderNodeRef.current?.disconnect();
        recorderNodeRef.current = null;
        mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
        recorderContextRef.current?.close();
        recorderContextRef.current = null;
        setIsMicActive(false);
    }, []);

    // ── Audio playback (simple queue — schedule AudioBufferSourceNodes) ──────
    const initPlayer = useCallback(async () => {
        console.log('[LiveAgent] Initializing audio player...');
        const ctx = new AudioContext({ sampleRate: PLAYBACK_RATE });
        playerContextRef.current = ctx;

        if (ctx.state === 'suspended') {
            console.log('[LiveAgent] AudioContext suspended, calling resume()...');
            await ctx.resume();
        }
        console.log('[LiveAgent] AudioContext state:', ctx.state, 'sampleRate:', ctx.sampleRate);
        nextPlayTimeRef.current = 0;
        isPlayingRef.current = false;
    }, []);

    const playPcmChunk = useCallback((pcmArrayBuffer: ArrayBuffer) => {
        try {
            const ctx = playerContextRef.current;
            if (!ctx) {
                console.error('[LiveAgent] No AudioContext, cannot play audio');
                return;
            }

            // Resume if suspended (e.g. Chrome autoplay)
            if (ctx.state === 'suspended') {
                ctx.resume();
            }

            // Convert Int16 PCM → Float32
            const float32 = int16ToFloat32(pcmArrayBuffer);

            // Create an AudioBuffer with the samples
            const audioBuffer = ctx.createBuffer(1, float32.length, PLAYBACK_RATE);
            audioBuffer.getChannelData(0).set(float32);

            // Diagnostic log: check max amplitude to ensure it's not silent or NaN
            let maxVal = 0;
            for (let i = 0; i < float32.length; i++) {
                if (Math.abs(float32[i]) > maxVal) maxVal = Math.abs(float32[i]);
            }
            console.error(`[AudioPlayer] float32 len: ${float32.length}, maxAmp: ${maxVal.toFixed(4)}, duration: ${audioBuffer.duration.toFixed(3)}s`);

            // Schedule playback
            const source = ctx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(ctx.destination);

            const now = ctx.currentTime;
            const startTime = Math.max(now, nextPlayTimeRef.current);
            source.start(startTime);

            // Track when this chunk will finish so the next one starts right after
            nextPlayTimeRef.current = startTime + audioBuffer.duration;
            isPlayingRef.current = true;

            source.onended = () => {
                // If no more chunks are upcoming (i.e. currentTime caught up), mark not playing
                if (ctx.currentTime >= nextPlayTimeRef.current - 0.01) {
                    isPlayingRef.current = false;
                }
            };
        } catch (err) {
            console.error('[LiveAgent] ERROR in playPcmChunk:', err);
        }
    }, []);

    const clearPlayback = useCallback(() => {
        // Reset playback timing so any queued chunks are effectively skipped
        nextPlayTimeRef.current = 0;
        isPlayingRef.current = false;
    }, []);

    // ── Handle incoming ADK events ──────────────────────────────────────────
    const handleEvent = useCallback((adkEvent: any) => {
        // Handle turn complete
        if (adkEvent.turnComplete === true) {
            console.log('[LiveAgent] Turn complete');
            setIsForgeSpeaking(false);
            return;
        }

        // Handle interrupted (barge-in)
        if (adkEvent.interrupted === true) {
            console.log('[LiveAgent] Interrupted (barge-in)');
            clearPlayback();
            setIsForgeSpeaking(false);
            return;
        }

        // Handle input transcription (user's spoken words)
        if (adkEvent.inputTranscription?.text) {
            const text = adkEvent.inputTranscription.text;
            const isFinished = adkEvent.inputTranscription.finished === true;
            setInputTranscript(text);
            if (isFinished) {
                setTranscripts((prev) => [...prev, { text, type: 'input' }]);
                setInputTranscript('');
            }
        }

        // Handle output transcription (Forge's spoken words)
        if (adkEvent.outputTranscription?.text) {
            const text = adkEvent.outputTranscription.text;
            const isFinished = adkEvent.outputTranscription.finished === true;
            setOutputTranscript(text);
            if (isFinished) {
                setTranscripts((prev) => [...prev, { text, type: 'output' }]);
                setOutputTranscript('');
            }
        }

        // Handle content events (audio + text)
        if (adkEvent.content?.parts) {
            for (const part of adkEvent.content.parts) {
                // Audio data from Gemini
                if (part.inlineData) {
                    const mime = part.inlineData.mimeType || '';
                    const dataLen = part.inlineData.data?.length || 0;
                    console.log(`[LiveAgent] Audio chunk: mime=${mime}, base64_len=${dataLen}`);

                    if (mime.startsWith('audio/pcm') && part.inlineData.data) {
                        const pcmBuffer = base64ToArrayBuffer(part.inlineData.data);
                        playPcmChunk(pcmBuffer);
                        setIsForgeSpeaking(true);
                    } else {
                        console.warn(`[LiveAgent] Unexpected inlineData mimeType: ${mime}`);
                    }
                }

                // Text fallback (for non-audio responses)
                if (part.text && !part.thought) {
                    setTextResponse((prev) => prev + part.text);
                }
            }
        }
    }, [playPcmChunk, clearPlayback]);

    // ── Connect ─────────────────────────────────────────────────────────────
    const connect = useCallback(
        async (userId: string, sessionId: string) => {
            if (wsRef.current) wsRef.current.close();

            setStatus('connecting');
            setError(null);
            setTranscripts([]);
            setInputTranscript('');
            setOutputTranscript('');
            setTextResponse('');

            // Initialize audio player FIRST (must be in user gesture context)
            await initPlayer();

            const wsUrl = new URL(
                `${WS_BASE}/ws/live/${encodeURIComponent(userId)}/${encodeURIComponent(sessionId)}`
            );
            const apiKey = localStorage.getItem('gemini_api_key');
            if (apiKey) {
                wsUrl.searchParams.append('api_key', apiKey);
            }
            const ws = new WebSocket(wsUrl.toString());
            ws.binaryType = 'arraybuffer';

            ws.onopen = async () => {
                console.log('[LiveAgent] WebSocket connected');
                setStatus('connected');
                await startMicInternal();
            };

            ws.onmessage = (event: MessageEvent) => {
                try {
                    const data = JSON.parse(event.data);
                    handleEvent(data);
                } catch (err) {
                    // Log the error instead of swallowing it silently 
                    console.error('[LiveAgent] Error processing message:', err);
                }
            };

            ws.onerror = () => {
                setStatus('error');
                setError('WebSocket connection error');
            };

            ws.onclose = () => {
                setStatus('disconnected');
                stopMicInternal();
            };

            wsRef.current = ws;
        },
        [startMicInternal, initPlayer, stopMicInternal, handleEvent]
    );

    // ── Disconnect ──────────────────────────────────────────────────────────
    const disconnect = useCallback(() => {
        try {
            wsRef.current?.send(JSON.stringify({ type: 'close' }));
        } catch { /* ignore */ }
        wsRef.current?.close();
        wsRef.current = null;
        stopMicInternal();
        if (playerContextRef.current) {
            playerContextRef.current.close();
            playerContextRef.current = null;
        }
        setStatus('idle');
    }, [stopMicInternal]);

    // ── Toggle mic ──────────────────────────────────────────────────────────
    const toggleMic = useCallback(() => {
        if (isMicActive) {
            stopMicInternal();
        } else {
            startMicInternal();
        }
    }, [isMicActive, startMicInternal, stopMicInternal]);

    // ── Send text ───────────────────────────────────────────────────────────
    const sendText = useCallback((text: string) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'text', text }));
        }
    }, []);

    return {
        status,
        isMicActive,
        isForgeSpeaking,
        inputTranscript,
        outputTranscript,
        transcripts,
        textResponse,
        error,
        connect,
        disconnect,
        toggleMic,
        sendText,
    };
}
