/**
 * Profile page — User profile for WeChat Mini-Program
 */
const app = getApp();

Page({
    data: {
        appName: '{{ app_name }}',
        primaryColor: '{{ primary_color }}',
        user: null,
        loading: true,
    },

    onLoad() {
        this.wp = app.globalData.wechat;
        this._loadProfile();
    },

    onShow() {
        if (!this.data.user) {
            this._loadProfile();
        }
    },

    async _loadProfile() {
        this.setData({ loading: true });
        try {
            const res = await this.wp.request('/api/v1/mini-program/user/profile');
            this.setData({
                user: res.data || null,
                loading: false,
            });
        } catch (e) {
            console.error('[Profile] Failed to load:', e);
            this.setData({ loading: false });
            wx.showToast({ title: 'Failed to load', icon: 'error' });
        }
    },

    onLogout() {
        wx.showModal({
            title: 'Logout',
            content: 'Are you sure you want to logout?',
            success: (res) => {
                if (res.confirm) {
                    this.wp.token = null;
                    wx.removeStorageSync('vero_token');
                    wx.reLaunch({ url: '/pages/chat/chat' });
                }
            },
        });
    },

    onNavigateToChat() {
        wx.navigateTo({ url: '/pages/chat/chat' });
    },
});