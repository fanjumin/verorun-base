/**
 * VeroAuth — Unified Authentication SDK for Social Media Mini-Programs
 * 
 * Handles platform-specific login and exchanges platform credentials
 * for a system JWT token via the /api/v1/mini-program/auth/login endpoint.
 * 
 * @module sdks/common/auth
 */

class VeroAuth {

    /**
     * @param {Object} config
     * @param {string} config.baseURL  - System base URL (e.g., 'https://easykai.cn')
     * @param {string} config.platform - 'douyin' | 'wechat' | 'telegram' | 'line'
     */
    constructor(config) {
        this.baseURL = config.baseURL;
        this.platform = config.platform;
    }

    /**
     * Login with platform-specific credentials.
     * 
     * The credentials object shape varies by platform:
     * 
     *   Douyin/WeChat:  { code: "..." }
     *   Telegram:       { initData: "..." }
     *   LINE:           { accessToken: "...", userId: "..." }
     * 
     * @param {Object} credentials - Platform-specific credentials
     * @returns {Promise<Object>} { success, data: { token, user: { id, username, display_name, platform, platform_user_id, is_new_user } } }
     */
    async login(credentials) {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...credentials, platform: this.platform })
        });
        return res.json();
    }

    /**
     * Validate a stored JWT token.
     * 
     * @param {string} token - JWT token to validate
     * @returns {Promise<Object>} { success, data: { valid, user } }
     */
    async validateToken(token) {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/auth/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        return res.json();
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VeroAuth };
}