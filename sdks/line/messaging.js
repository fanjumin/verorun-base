/**
 * LineMessaging — LINE Messaging API Helper
 *
 * Provides methods for common LINE Messaging API operations.
 * These are typically called from the backend server.
 *
 * @module sdks/line/messaging
 */

const LineMessaging = {
    /**
     * Reply to a user message.
     * POST https://api.line.me/v2/bot/message/reply
     *
     * @param {string} channelAccessToken - LINE channel access token
     * @param {string} replyToken - Reply token from webhook event
     * @param {Object[]} messages - LINE message objects
     * @returns {Promise<Object>}
     */
    async reply(channelAccessToken, replyToken, messages) {
        const res = await fetch('https://api.line.me/v2/bot/message/reply', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${channelAccessToken}`
            },
            body: JSON.stringify({ replyToken, messages })
        });
        return res.json();
    },

    /**
     * Push a message to a user.
     * POST https://api.line.me/v2/bot/message/push
     *
     * @param {string} channelAccessToken
     * @param {string} userId - LINE user ID
     * @param {Object[]} messages - LINE message objects
     * @returns {Promise<Object>}
     */
    async push(channelAccessToken, userId, messages) {
        const res = await fetch('https://api.line.me/v2/bot/message/push', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${channelAccessToken}`
            },
            body: JSON.stringify({ to: userId, messages })
        });
        return res.json();
    },

    /**
     * Get user profile.
     * GET https://api.line.me/v2/bot/profile/{userId}
     *
     * @param {string} channelAccessToken
     * @param {string} userId
     * @returns {Promise<Object>}
     */
    async getProfile(channelAccessToken, userId) {
        const res = await fetch(
            `https://api.line.me/v2/bot/profile/${userId}`,
            { headers: { 'Authorization': `Bearer ${channelAccessToken}` } }
        );
        return res.json();
    },

    /**
     * Create a text message object.
     * @param {string} text
     * @returns {Object} { type: 'text', text }
     */
    createTextMessage(text) {
        return { type: 'text', text };
    },

    /**
     * Create a flex message (bubble) object.
     * @param {Object} contents - Flex Message contents
     * @param {string} [altText='Flex Message']
     * @returns {Object}
     */
    createFlexMessage(contents, altText = 'Flex Message') {
        return { type: 'flex', altText, contents };
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { LineMessaging };
}