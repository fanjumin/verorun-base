/**
 * VeroChat — Unified Chat SDK for Social Media Mini-Programs
 * 
 * Provides chat.send(), chat.streamChat(), and chat.searchKnowledge() methods
 * that communicate with the VeroRun system backend API.
 * 
 * @module sdks/common/chat
 */

class VeroChat {

    /**
     * @param {Object} config
     * @param {string} config.baseURL  - System base URL (e.g., 'https://your-domain.com')
     * @param {string} config.token    - JWT token from VeroAuth.login()
     * @param {string} config.platform - 'douyin' | 'wechat' | 'telegram' | 'line'
     */
    constructor(config) {
        this.baseURL = config.baseURL;
        this.token = config.token;
        this.platform = config.platform;
    }

    /**
     * Send a message and get a non-streaming AI reply.
     * 
     * @param {string} message - User message text
     * @param {Array<{role: string, content: string}>} [history=[]] - Previous messages
     * @returns {Promise<Object>} { success, data: { reply, retrievedKnowledge } }
     */
    async send(message, history = []) {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/chat/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({ message, history, platform: this.platform })
        });
        return res.json();
    }

    /**
     * Send a message and receive streaming AI reply via SSE.
     * 
     * @param {string} message - User message text
     * @param {Array<{role: string, content: string}>} [history=[]] - Previous messages
     * @param {Function} [onToken] - Callback for each token: (token: string) => void
     * @param {Function} [onDone] - Callback when stream completes: ({ reply, retrievedKnowledge }) => void
     * @returns {Promise<void>}
     */
    async streamChat(message, history = [], onToken, onDone) {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({ message, history, platform: this.platform })
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullReply = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.type === 'token') {
                            fullReply += data.content;
                            if (onToken) onToken(data.content);
                        } else if (data.type === 'done') {
                            if (onDone) onDone({
                                reply: fullReply,
                                retrievedKnowledge: data.retrievedKnowledge || []
                            });
                        } else if (data.type === 'error') {
                            if (onDone) onDone({
                                reply: fullReply,
                                error: data.error,
                                retrievedKnowledge: []
                            });
                        }
                    } catch (e) {
                        // Skip unparseable SSE lines
                    }
                }
            }
        }
    }

    /**
     * Search the RAG knowledge base.
     * 
     * @param {string} query - Search query
     * @returns {Promise<Object>} { success, data: [...] }
     */
    async searchKnowledge(query) {
        const res = await fetch(
            `${this.baseURL}/api/v1/mini-program/knowledge/search?q=${encodeURIComponent(query)}`,
            { headers: { 'Authorization': `Bearer ${this.token}` } }
        );
        return res.json();
    }

    /**
     * Get conversation history.
     * 
     * @returns {Promise<Object>} { success, data: { messages: [...] } }
     */
    async getHistory() {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/chat/history`, {
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
        return res.json();
    }
}

// Export for module usage; also available as global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VeroChat };
}