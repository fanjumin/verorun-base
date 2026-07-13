/**
 * TelegramMiniApp — Telegram Mini App (WebView) SDK
 *
 * Integrates with the Telegram WebApp JavaScript API
 * (https://core.telegram.org/bots/webapps) and the VeroRun system backend.
 *
 * Usage:
 *   const tg = Object.create(TelegramMiniApp);
 *   tg.init();
 *   await tg.authenticate();
 *   const chat = new VeroChat({ baseURL: tg.baseURL, token: tg.token, platform: 'telegram' });
 *
 * @module sdks/telegram/webapp
 */

const TelegramMiniApp = {
    tg: null,
    baseURL: 'https://easykai.cn',
    token: null,
    user: null,

    /**
     * Initialize the Telegram WebApp.
     * Must be called before any other methods.
     *
     * @returns {this}
     */
    init() {
        if (!window.Telegram || !window.Telegram.WebApp) {
            console.error('[TelegramMiniApp] Telegram WebApp SDK not loaded. Include telegram-web-app.js');
            return this;
        }
        this.tg = window.Telegram.WebApp;
        this.tg.ready();
        this.tg.expand(); // Use full available height

        this.user = this.tg.initDataUnsafe?.user || null;

        // Apply Telegram theme colors
        if (this.tg.backgroundColor) {
            document.documentElement.style.setProperty('--tg-bg-color', this.tg.backgroundColor);
        }
        if (this.tg.textColor) {
            document.documentElement.style.setProperty('--tg-text-color', this.tg.textColor);
        }
        if (this.tg.buttonColor) {
            document.documentElement.style.setProperty('--tg-button-color', this.tg.buttonColor);
        }
        if (this.tg.buttonTextColor) {
            document.documentElement.style.setProperty('--tg-button-text-color', this.tg.buttonTextColor);
        }

        return this;
    },

    /**
     * Authenticate with the system backend using Telegram initData.
     *
     * @returns {Promise<Object>} { success, data: { token, user } }
     */
    async authenticate() {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: 'telegram',
                initData: this.tg.initData
            })
        });
        const data = await res.json();
        if (data.success) {
            this.token = data.data.token;
            this.user = data.data.user;
            localStorage.setItem('vero_token', this.token);
            localStorage.setItem('vero_user', JSON.stringify(this.user));
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
                this.user = JSON.parse(localStorage.getItem('vero_user') || 'null');
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
        localStorage.removeItem('vero_token');
        localStorage.removeItem('vero_user');
    },

    /**
     * Show a Telegram native popup dialog.
     *
     * @param {string} message - Message to display
     * @param {Function} [callback] - Called with button_id when user clicks
     */
    showPopup(message, callback) {
        this.tg.showPopup(
            { title: 'VeroRun AI', message, buttons: [{ type: 'ok' }] },
            callback
        );
    },

    /**
     * Show a confirmation dialog.
     *
     * @param {string} message
     * @param {Function} callback - Called with true if confirmed, false otherwise
     */
    showConfirm(message, callback) {
        this.tg.showPopup(
            {
                title: 'VeroRun AI',
                message,
                buttons: [
                    { type: 'cancel', text: 'Cancel' },
                    { type: 'ok', text: 'OK' }
                ]
            },
            (buttonId) => callback(buttonId === 'ok')
        );
    },

    /**
     * Show the Telegram back button.
     * @param {Function} callback - Called when back button is pressed
     */
    showBackButton(callback) {
        this.tg.BackButton.show();
        this.tg.BackButton.onClick(callback);
    },

    /**
     * Hide the Telegram back button.
     */
    hideBackButton() {
        this.tg.BackButton.hide();
    },

    /**
     * Send data to the bot (will be received via sendData event).
     * @param {Object|string} data
     */
    sendData(data) {
        const payload = typeof data === 'string' ? data : JSON.stringify(data);
        this.tg.sendData(payload);
    },

    /**
     * Close the WebApp.
     */
    close() {
        this.tg.close();
    },

    /**
     * Get the current color scheme ('light' or 'dark').
     * @returns {string}
     */
    getColorScheme() {
        return this.tg.colorScheme || 'light';
    },

    /**
     * Enable or disable the main button.
     * @param {string} text - Button text
     * @param {Function} [onClick] - Click handler
     * @param {Object} [options] - { color, textColor, isActive, isVisible }
     */
    setMainButton(text, onClick, options = {}) {
        const btn = this.tg.MainButton;
        btn.setText(text);
        if (onClick) btn.onClick(onClick);
        if (options.color) btn.color = options.color;
        if (options.textColor) btn.textColor = options.textColor;
        if (options.isVisible !== false) btn.show();
        if (options.isActive !== false) btn.enable();
    },

    /**
     * Hide the main button.
     */
    hideMainButton() {
        this.tg.MainButton.hide();
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TelegramMiniApp };
}