/**
 * DouyinMP — Douyin/Toutiao Mini-Program SDK
 *
 * Wraps tt.* API for seamless integration with the VeroRun system backend.
 * Also compatible with Toutiao (shares the same ByteDance mini-program ecosystem).
 *
 * @module sdks/douyin/api
 */

const DouyinMP = {
    baseURL: 'https://your-domain.com',
    token: null,
    user: null,

    /**
     * Initialize and login.
     * Calls tt.login() → exchanges code for system JWT → stores in tt.setStorageSync().
     *
     * @returns {Promise<Object>} { success, data: { token, user } }
     */
    async init() {
        const loginResult = await this._promisify(tt.login)();
        const code = loginResult.code;

        const res = await this.request('/api/v1/mini-program/auth/login', {
            method: 'POST',
            data: { code, platform: 'douyin' }
        });

        if (res.success) {
            this.token = res.data.token;
            this.user = res.data.user;
            tt.setStorageSync('vero_token', this.token);
            tt.setStorageSync('vero_user', JSON.stringify(this.user));
        }
        return res;
    },

    /**
     * Restore token from tt storage.
     * @returns {boolean} true if token was restored
     */
    restoreToken() {
        this.token = tt.getStorageSync('vero_token') || null;
        if (this.token) {
            try {
                this.user = JSON.parse(tt.getStorageSync('vero_user') || 'null');
            } catch (e) {
                this.user = null;
            }
        }
        return !!this.token;
    },

    /**
     * Logout — clear stored token.
     */
    logout() {
        this.token = null;
        this.user = null;
        tt.removeStorageSync('vero_token');
        tt.removeStorageSync('vero_user');
    },

    /**
     * Wrapper for tt.request() with automatic Authorization header.
     *
     * @param {string} url - API endpoint path (e.g., '/api/v1/mini-program/chat/send')
     * @param {Object} [options={}]
     * @param {string} [options.method='GET']
     * @param {Object} [options.data]
     * @param {Object} [options.header]
     * @returns {Promise<Object>} Response data
     */
    request(url, options = {}) {
        return new Promise((resolve, reject) => {
            tt.request({
                url: `${this.baseURL}${url}`,
                method: options.method || 'GET',
                data: options.data,
                header: {
                    'Content-Type': 'application/json',
                    'Authorization': this.token ? `Bearer ${this.token}` : '',
                    ...options.header
                },
                success: (res) => {
                    if (res.statusCode >= 200 && res.statusCode < 300) {
                        resolve(res.data);
                    } else {
                        reject(new Error(`HTTP ${res.statusCode}: ${JSON.stringify(res.data)}`));
                    }
                },
                fail: (err) => reject(new Error(err.errMsg || 'Network error'))
            });
        });
    },

    /**
     * Get current user profile.
     * @returns {Promise<Object>}
     */
    async getUserProfile() {
        const res = await this.request('/api/v1/mini-program/user/profile');
        return res.data;
    },

    /**
     * Get site brand info.
     * @returns {Promise<Object>}
     */
    async getSiteInfo() {
        const res = await this.request('/api/v1/mini-program/site/info');
        return res.data;
    },

    /**
     * Navigate to another page in the mini-program.
     * @param {string} pagePath - e.g., '/pages/chat/chat'
     * @param {Object} [query]
     */
    navigateTo(pagePath, query = {}) {
        const qs = Object.keys(query).length
            ? '?' + Object.entries(query).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&')
            : '';
        tt.navigateTo({ url: `${pagePath}${qs}` });
    },

    /**
     * Show a toast message.
     * @param {string} title
     * @param {string} [icon='none']
     */
    showToast(title, icon = 'none') {
        tt.showToast({ title, icon, duration: 2000 });
    },

    /**
     * Convert tt.* callback-style API to Promise.
     * @param {Function} fn - tt API function
     * @returns {Function} Promise-returning wrapper
     * @private
     */
    _promisify(fn) {
        return (options = {}) => new Promise((resolve, reject) => {
            fn({ ...options, success: resolve, fail: reject });
        });
    }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DouyinMP };
}