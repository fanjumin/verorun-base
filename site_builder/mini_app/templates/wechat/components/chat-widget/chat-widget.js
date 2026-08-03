/**
 * Chat Widget — Reusable chat component for WeChat Mini-Program
 */
Component({
    properties: {
        platform: {
            type: String,
            value: 'wechat',
        },
        primaryColor: {
            type: String,
            value: '#333',
        },
        placeholder: {
            type: String,
            value: 'Type your message...',
        },
    },

    data: {
        messages: [],
        inputValue: '',
        isStreaming: false,
        showWidget: false,
    },

    lifetimes: {
        attached() {
            const app = getApp();
            this.wp = app.globalData.wechat;
            this.chat = null;
            this._initChat();
        },
    },

    methods: {
        async _initChat() {
            if (!this.wp || !this.wp.token) {
                try {
                    await this.wp.init();
                } catch (e) {
                    console.error('[ChatWidget] Init failed:', e);
                }
            }

            const { VeroChat } = require('../../sdks/common/chat.js');
            this.chat = new VeroChat({
                baseURL: this.wp.baseURL,
                token: this.wp.token,
                platform: this.properties.platform,
            });
        },

        onToggle() {
            this.setData({ showWidget: !this.data.showWidget });
        },

        onClose() {
            this.setData({ showWidget: false });
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
                }
            );
        },
    },
});