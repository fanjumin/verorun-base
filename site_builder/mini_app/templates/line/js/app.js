/**
 * LINE MINI App — Application Logic
 * 
 * Rendered with brand and API context substitution from Site_builder generator.
 */

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

const LineMiniApp = {
    baseURL: '{{ base_url }}',
    token: null,
    profile: null,
    liffId: null,

    async init(liffId) {
        this.liffId = liffId;
        await liff.init({ liffId, withLoginOnExternalBrowser: true });
        if (!liff.isLoggedIn()) { liff.login(); }
        this.profile = await liff.getProfile();
        return this;
    },

    async authenticate() {
        const accessToken = liff.getAccessToken();
        const res = await fetch(this.baseURL + '/api/v1/mini-program/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: 'line',
                accessToken: accessToken,
                userId: this.profile.userId,
                displayName: this.profile.displayName,
                pictureUrl: this.profile.pictureUrl
            })
        });
        const data = await res.json();
        if (data.success) {
            this.token = data.data.token;
            localStorage.setItem('vero_token', this.token);
        }
        return data;
    },

    restoreToken() {
        this.token = localStorage.getItem('vero_token') || null;
        return !!this.token;
    }
};