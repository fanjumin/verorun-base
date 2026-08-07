/**
 * Chat page — AI Advisor chat interface for WeChat Mini-Program
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
        this.wp = app.globalData.wechat;
        this.chat = null;
        this._initChat();
    },

    async _initChat() {
        if (!this.wp.token) {
            const res = await this.wp.init();
            if (!res.success) {
                wx.showToast({ title: 'Login failed', icon: 'error' });
                return;
            }
        }

        const { VeroChat } = require('../../sdks/common/chat.js');
        this.chat = new VeroChat({
            baseURL: this.wp.baseURL,
            token: this.wp.token,
            platform: 'wechat'
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

        const assistantIndex = messages.length;
        messages.push({ role: 'assistant', content: '' });
        this.setData({ messages });

        const history = messages.slice(0, -1).filter(m => m.role !== 'assistant' || m.content);

        await this.chat.streamChat(
            text,
            history,
            (token) => {
                messages[assistantIndex].content += token;
                this.setData({ messages });
            },
            (result) => {
                this.setData({ isStreaming: false });
                console.log('[Chat] Done:', result.retrievedKnowledge?.length, 'knowledge items');
            }
        );
    },

    onBack() {
        wx.navigateBack();
    },
});