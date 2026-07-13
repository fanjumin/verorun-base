/**
 * LineMiniApp — LINE MINI App (LIFF) SDK
 *
 * Integrates with the LINE Front-end Framework (LIFF v2)
 * (https://developers.line.biz/en/docs/liff/) and the VeroRun system backend.
 *
 * Requires the LIFF SDK to be loaded:
 *   <script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
 *
 * Usage:
 *   const line = Object.create(LineMiniApp);
 *   await line.init('1234567890-AbCdEfGh');
 *   await line.authenticate();
 *   const chat = new VeroChat({ baseURL: line.baseURL, token: line.token, platform: 'line' });
 *
 * @module sdks/line/liff
 */

const LineMiniApp = {
    baseURL: 'https://easykai.cn',
    token: null,
    profile: null,
    liffId: null,

    /**
     * Initialize LIFF.
     * Must be called before any other methods.
     *
     * @param {string} liffId - LIFF ID from LINE Developers Console
     * @returns {Promise<this>}
     */
    async init(liffId) {
        this.liffId = liffId;
        await liff.init({ liffId, withLoginOnExternalBrowser: true });

        if (!liff.isLoggedIn()) {
            liff.login();
        }

        this.profile = await liff.getProfile();
        return this;
    },

    /**
     * Authenticate with the system backend.
     *
     * @returns {Promise<Object>} { success, data: { token, user } }
     */
    async authenticate() {
        const accessToken = liff.getAccessToken();

        const res = await fetch(`${this.baseURL}/api/v1/mini-program/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: 'line',
                accessToken: accessToken,
                userId: this.profile.userId,
                displayName: this.profile.displayName,
                pictureUrl: this.profile.pictureUrl,
            })
        });
        const data = await res.json();
        if (data.success) {
            this.token = data.data.token; // Replace LIFF access token with system JWT
            localStorage.setItem('vero_token', this.token);
            localStorage.setItem('vero_user', JSON.stringify(data.data.user));
        }
        return data;
    },

    /**
     * Restore token from localStorage.
     * @returns {boolean} true if token was restored
     */
    restoreToken() {
        this.token = localStorage.getItem('vero_token') || null;
        if (this.token) {
            try {
                this.profile = JSON.parse(localStorage.getItem('vero_user') || 'null');
            } catch (e) {
                this.profile = null;
            }
        }
        return !!this.token;
    },

    /**
     * Logout — clear stored token and close LIFF.
     */
    logout() {
        this.token = null;
        this.profile = null;
        localStorage.removeItem('vero_token');
        localStorage.removeItem('vero_user');
        if (liff.isLoggedIn()) {
            liff.logout();
        }
    },

    /**
     * Close the LIFF app window.
     */
    close() {
        liff.closeWindow();
    },

    /**
     * Open an external URL in the LINE in-app browser.
     * @param {string} url
     */
    openWindow(url) {
        liff.openWindow({ url, external: true });
    },

    /**
     * Send a message to the chat screen (only works if opened from a chat).
     * @param {Object[]} messages - LINE message objects
     * @returns {Promise<void>}
     */
    async sendMessages(messages) {
        await liff.sendMessages(messages);
    },

    /**
     * Get the LIFF context (type, viewType, etc.).
     * @returns {Object}
     */
    getContext() {
        return liff.getContext();
    },

    /**
     * Check if the app is running in a LINE client.
     * @returns {boolean}
     */
    isInClient() {
        return liff.isInClient();
    },

    /**
     * Get the current language.
     * @returns {string} e.g., 'ja', 'en', 'zh-TW'
     */
    getLanguage() {
        return liff.getLanguage();
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { LineMiniApp };
}