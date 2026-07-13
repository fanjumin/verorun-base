/**
 * Telegram Mini App — Application Logic
 * 
 * This file is rendered with {{ variable }} substitution
 * from the Site_builder generator.
 */

// VeroChat class (embedded for standalone deployment)
class VeroChat {
    constructor(config) {
        this.baseURL = config.baseURL;
        this.token = config.token;
        this.platform = config.platform;
    }

    async streamChat(message, history, onToken, onDone) {
        const res = await fetch(this.baseURL + '/api/v1/mini-program/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + this.token
            },
            body: JSON.stringify({ message, history, platform: this.platform })
        });
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '', fullReply = '';
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
                            onToken && onToken(data.content);
                        } else if (data.type === 'done') {
                            onDone && onDone({ reply: fullReply, retrievedKnowledge: data.retrievedKnowledge });
                        }
                    } catch (e) {}
                }
            }
        }
    }
}

// TelegramMiniApp SDK
const TelegramMiniApp = {
    tg: null,
    baseURL: '{{ base_url }}',
    token: null,
    user: null,

    init() {
        this.tg = window.Telegram.WebApp;
        this.tg.ready();
        this.tg.expand();
        this.user = this.tg.initDataUnsafe?.user;

        if (this.tg.backgroundColor) {
            document.documentElement.style.setProperty('--tg-bg-color', this.tg.backgroundColor);
        }
        if (this.tg.textColor) {
            document.documentElement.style.setProperty('--tg-text-color', this.tg.textColor);
        }
        return this;
    },

    async authenticate() {
        const res = await fetch(this.baseURL + '/api/v1/mini-program/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: 'telegram', initData: this.tg.initData })
        });
        const data = await res.json();
        if (data.success) {
            this.token = data.data.token;
            this.user = data.data.user;
            localStorage.setItem('vero_token', this.token);
        }
        return data;
    },

    restoreToken() {
        this.token = localStorage.getItem('vero_token') || null;
        return !!this.token;
    }
};