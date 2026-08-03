/**
 * TelegramBot — Telegram Bot API Helper
 *
 * Provides methods for common Bot API operations. These are typically
 * called from the backend, but can also be used from frontend for
 * simple operations (with caution — never expose bot_token in frontend).
 *
 * @module sdks/telegram/bot
 */

const TelegramBot = {
    /**
     * Set the bot's webhook URL.
     * POST https://api.telegram.org/bot{token}/setWebhook
     *
     * @param {string} botToken - Bot token from @BotFather
     * @param {string} webhookUrl - Public HTTPS URL for webhook
     * @returns {Promise<Object>}
     */
    async setWebhook(botToken, webhookUrl) {
        const res = await fetch(
            `https://api.telegram.org/bot${botToken}/setWebhook`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: webhookUrl })
            }
        );
        return res.json();
    },

    /**
     * Set the bot's menu button to open a Mini App.
     * POST https://api.telegram.org/bot{token}/setChatMenuButton
     *
     * @param {string} botToken
     * @param {string} webappUrl - URL of the Mini App
     * @param {string} [buttonText='Open App']
     * @returns {Promise<Object>}
     */
    async setMiniAppMenuButton(botToken, webappUrl, buttonText = 'Open App') {
        const res = await fetch(
            `https://api.telegram.org/bot${botToken}/setChatMenuButton`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    menu_button: {
                        type: 'web_app',
                        text: buttonText,
                        web_app: { url: webappUrl }
                    }
                })
            }
        );
        return res.json();
    },

    /**
     * Send a text message to a chat.
     * POST https://api.telegram.org/bot{token}/sendMessage
     *
     * @param {string} botToken
     * @param {number|string} chatId
     * @param {string} text
     * @param {Object} [options] - { parseMode, replyMarkup, ... }
     * @returns {Promise<Object>}
     */
    async sendMessage(botToken, chatId, text, options = {}) {
        const res = await fetch(
            `https://api.telegram.org/bot${botToken}/sendMessage`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: chatId,
                    text: text,
                    parse_mode: options.parseMode || 'HTML',
                    reply_markup: options.replyMarkup || undefined,
                    disable_web_page_preview: options.disablePreview || false,
                })
            }
        );
        return res.json();
    },

    /**
     * Get bot info.
     * GET https://api.telegram.org/bot{token}/getMe
     *
     * @param {string} botToken
     * @returns {Promise<Object>}
     */
    async getMe(botToken) {
        const res = await fetch(
            `https://api.telegram.org/bot${botToken}/getMe`
        );
        return res.json();
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TelegramBot };
}