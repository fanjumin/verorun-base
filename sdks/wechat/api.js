/**
 * WechatMP — WeChat Mini-Program SDK
 *
 * Wraps wx.* API for seamless integration with the VeroRun system backend.
 *
 * @module sdks/wechat/api
 */

const WechatMP = {
    baseURL: 'https://your-domain.com',
    token: null,
    user: null,

    /**
     * Initialize and login.
     * Calls wx.login() → exchanges code for system JWT → stores in wx.setStorageSync().
     *
     * @returns {Promise<Object>} { success, data: { token, user } }
     */
    async init() {
        const loginResult = await this._promisify(wx.login)();
        const code = loginResult.code;

        const res = await this.request('/api/v1/mini-program/auth/login', {
            method: 'POST',
            data: { code, platform: 'wechat' }
        });

        if (res.success) {
            this.token = res.data.token;
            this.user = res.data.user;
            wx.setStorageSync('vero_token', this.token);
            wx.setStorageSync('vero_user', JSON.stringify(this.user));
        }
        return res;
    },

    /**
     * Restore token from storage.
     * @returns {boolean} true if token was restored
     */
    restoreToken() {
        this.token = wx.getStorageSync('vero_token') || null;
        if (this.token) {
            try {
                this.user = JSON.parse(wx.getStorageSync('vero_user') || 'null');
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
        wx.removeStorageSync('vero_token');
        wx.removeStorageSync('vero_user');
    },

    /**
     * Wrapper for wx.request() with automatic Authorization header.
     *
     * @param {string} url - API endpoint path
     * @param {Object} [options={}]
     * @param {string} [options.method='GET']
     * @param {Object} [options.data]
     * @param {Object} [options.header]
     * @returns {Promise<Object>} Response data
     */
    request(url, options = {}) {
        return new Promise((resolve, reject) => {
            wx.request({
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
     * Navigate to another page.
     * @param {string} pagePath - e.g., '/pages/chat/chat'
     * @param {Object} [query]
     */
    navigateTo(pagePath, query = {}) {
        const qs = Object.keys(query).length
            ? '?' + Object.entries(query).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&')
            : '';
        wx.navigateTo({ url: `${pagePath}${qs}` });
    },

    /**
     * Show a toast message.
     * @param {string} title
     * @param {string} [icon='none']
     */
    showToast(title, icon = 'none') {
        wx.showToast({ title, icon, duration: 2000 });
    },

    /**
     * Convert wx.* callback-style API to Promise.
     * @param {Function} fn
     * @returns {Function}
     * @private
     */
    _promisify(fn) {
        return (options = {}) => new Promise((resolve, reject) => {
            fn({ ...options, success: resolve, fail: reject });
        });
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { WechatMP };
}