/**
 * Profile page — User profile for Douyin Mini-Program
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
        this.dp = app.globalData.douyin;
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
            const res = await this.dp.request('/api/v1/mini-program/user/profile');
            this.setData({
                user: res.data || null,
                loading: false,
            });
        } catch (e) {
            console.error('[Profile] Failed to load:', e);
            this.setData({ loading: false });
            tt.showToast({ title: 'Failed to load', icon: 'error' });
        }
    },

    onLogout() {
        tt.showModal({
            title: 'Logout',
            content: 'Are you sure you want to logout?',
            success: (res) => {
                if (res.confirm) {
                    this.dp.token = null;
                    tt.removeStorageSync('vero_token');
                    tt.reLaunch({ url: '/pages/chat/chat' });
                }
            },
        });
    },

    onNavigateToChat() {
        tt.navigateTo({ url: '/pages/chat/chat' });
    },
});