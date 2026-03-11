import { useState, useCallback, useRef } from 'react';
import { sendMessage, type ChatResponse } from '../services/api';

export interface Message {
    id: string;
    role: 'user' | 'forge';
    content: string;
    timestamp: Date;
}

export function useChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const msgIdCounter = useRef(0);

    const addMessage = useCallback((role: 'user' | 'forge', content: string) => {
        const msg: Message = {
            id: `msg-${++msgIdCounter.current}`,
            role,
            content,
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, msg]);
        return msg;
    }, []);

    const send = useCallback(
        async (text: string) => {
            if (!text.trim() || isLoading) return;

            setError(null);
            addMessage('user', text);
            setIsLoading(true);

            try {
                const res: ChatResponse = await sendMessage(text, sessionId || undefined);
                setSessionId(res.session_id);
                addMessage('forge', res.response);
            } catch (err) {
                const errMsg = err instanceof Error ? err.message : 'Something went wrong';
                setError(errMsg);
                addMessage('forge', `Sorry, I hit a snag: ${errMsg}. Can you try again?`);
            } finally {
                setIsLoading(false);
            }
        },
        [isLoading, sessionId, addMessage]
    );

    const reset = useCallback(() => {
        setMessages([]);
        setSessionId(null);
        setError(null);
        setIsLoading(false);
    }, []);

    return { messages, isLoading, sessionId, error, send, reset, addMessage, setSessionId };
}
