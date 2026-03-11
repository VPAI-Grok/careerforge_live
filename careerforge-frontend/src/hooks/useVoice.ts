import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * Browser-native voice input/output using the Web Speech API.
 * - Speech-to-text (recognition) for user voice input
 * - Text-to-speech (synthesis) for Forge's spoken responses
 */

interface UseVoiceOptions {
    /** Callback fired when a final transcript is available */
    onTranscript?: (text: string) => void;
    /** Language for recognition (default: en-US) */
    lang?: string;
    /** Auto-speak Forge's responses? */
    autoSpeak?: boolean;
}

interface UseVoiceReturn {
    /** Whether the mic is currently listening */
    isListening: boolean;
    /** Interim (partial) transcript while speaking */
    interim: string;
    /** Start listening for voice input */
    startListening: () => void;
    /** Stop listening */
    stopListening: () => void;
    /** Toggle listening on/off */
    toggleListening: () => void;
    /** Speak text aloud using TTS */
    speak: (text: string) => void;
    /** Stop any current speech */
    stopSpeaking: () => void;
    /** Whether TTS is currently speaking */
    isSpeaking: boolean;
    /** Whether the browser supports speech recognition */
    isSupported: boolean;
}

export function useVoice(options: UseVoiceOptions = {}): UseVoiceReturn {
    const { onTranscript, lang = 'en-US', autoSpeak = true } = options;
    const [isListening, setIsListening] = useState(false);
    const [interim, setInterim] = useState('');
    const [isSpeaking, setIsSpeaking] = useState(false);

    const recognitionRef = useRef<any>(null);
    const onTranscriptRef = useRef(onTranscript);
    onTranscriptRef.current = onTranscript;

    // Check browser support
    const SpeechRecognitionAPI =
        typeof window !== 'undefined'
            ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
            : null;

    const isSupported = !!SpeechRecognitionAPI;

    // Initialize recognition
    useEffect(() => {
        if (!SpeechRecognitionAPI) return;

        const recognition = new SpeechRecognitionAPI();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = lang;

        recognition.onresult = (event: any) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript;
                } else {
                    interimTranscript += result[0].transcript;
                }
            }

            setInterim(interimTranscript);

            if (finalTranscript) {
                onTranscriptRef.current?.(finalTranscript.trim());
                setInterim('');
            }
        };

        recognition.onerror = (event: any) => {
            console.warn('Speech recognition error:', event.error);
            if (event.error !== 'no-speech') {
                setIsListening(false);
            }
        };

        recognition.onend = () => {
            // Restart if we're still supposed to be listening
            if (recognitionRef.current && isListening) {
                try {
                    recognition.start();
                } catch {
                    setIsListening(false);
                }
            } else {
                setIsListening(false);
            }
        };

        recognitionRef.current = recognition;

        return () => {
            recognition.abort();
            recognitionRef.current = null;
        };
    }, [SpeechRecognitionAPI, lang]);

    const startListening = useCallback(() => {
        if (!recognitionRef.current) return;
        try {
            recognitionRef.current.start();
            setIsListening(true);
            setInterim('');
        } catch {
            // Already started
        }
    }, []);

    const stopListening = useCallback(() => {
        if (!recognitionRef.current) return;
        recognitionRef.current.stop();
        setIsListening(false);
        setInterim('');
    }, []);

    const toggleListening = useCallback(() => {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    }, [isListening, startListening, stopListening]);

    // ── Text-to-Speech ──
    const speak = useCallback(
        (text: string) => {
            if (!autoSpeak) return;
            if (typeof window === 'undefined' || !window.speechSynthesis) return;

            // Cancel any ongoing speech
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.lang = lang;

            // Try to pick a natural-sounding voice
            const voices = window.speechSynthesis.getVoices();
            const preferred = voices.find(
                (v) => v.lang.startsWith('en') && v.name.toLowerCase().includes('natural')
            ) || voices.find(
                (v) => v.lang.startsWith('en') && !v.name.toLowerCase().includes('compact')
            );
            if (preferred) utterance.voice = preferred;

            utterance.onstart = () => setIsSpeaking(true);
            utterance.onend = () => setIsSpeaking(false);
            utterance.onerror = () => setIsSpeaking(false);

            window.speechSynthesis.speak(utterance);
        },
        [autoSpeak, lang]
    );

    const stopSpeaking = useCallback(() => {
        if (typeof window !== 'undefined' && window.speechSynthesis) {
            window.speechSynthesis.cancel();
            setIsSpeaking(false);
        }
    }, []);

    return {
        isListening,
        interim,
        startListening,
        stopListening,
        toggleListening,
        speak,
        stopSpeaking,
        isSpeaking,
        isSupported,
    };
}
