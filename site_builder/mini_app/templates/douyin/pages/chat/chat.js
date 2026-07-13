/**
 * Chat page — AI Advisor chat interface for Douyin Mini-Program
 */
const app = getApp();

Page({
    data: {
        messages: [],
        inputValue: '',
        isStreaming: false,
        appName: '{{ app_name }}',
    },

    onLoad() {
        this.dp = app.globalData.douyin;
        this.chat = null;
        this._initChat();
    },

    async _initChat() {
        // Ensure logged in
        if (!this.dp.token) {
            const res = await this.dp.init();
            if (!res.success) {
                tt.showToast({ title: 'Login failed', icon: 'error' });
                return;
            }
        }

        // Load VeroChat module
        const { VeroChat } = require('./sdks/common/chat.js');
        this.chat = new VeroChat({
            baseURL: this.dp.baseURL,
            token: this.dp.token,
            platform: 'douyin'
        });
    },

    onInput(e) {
        this.setData({ inputValue: e.detail.value });
    },

    async onSend() {
        const text = this.data.inputValue.trim();
        if (!text || this.data.isStreaming) return;

        const messages = [...this.data.messages, { role: 'user', content: text }];
        this.setData({ messages, inputValue: '', isStreaming: true });

        // Add assistant placeholder
        const assistantIndex = messages.length;
        messages.push({ role: 'assistant', content: '' });
        this.setData({ messages });

        const history = messages.slice(0, -1).filter(m => m.role !== 'assistant' || m.content);

        await this.chat.streamChat(
            text,
            history,
            // onToken
            (token) => {
                messages[assistantIndex].content += token;
                this.setData({ messages });
            },
            // onDone
            (result) => {
                this.setData({ isStreaming: false });
                console.log('[Chat] Done:', result.retrievedKnowledge?.length, 'knowledge items');
            }
        );
    },

    onBack() {
        tt.navigateBack();
    },
});