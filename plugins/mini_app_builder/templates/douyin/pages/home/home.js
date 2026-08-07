/**
 * Home page — Site content display for Douyin Mini-Program
 */
const app = getApp();

Page({
    data: {
        appName: '{{ app_name }}',
        primaryColor: '{{ primary_color }}',
        siteInfo: null,
        pages: [],
        loading: true,
    },

    onLoad() {
        this.dp = app.globalData.douyin;
        this._loadSiteData();
    },

    onPullDownRefresh() {
        this._loadSiteData().then(() => tt.stopPullDownRefresh());
    },

    async _loadSiteData() {
        this.setData({ loading: true });
        try {
            const [infoRes, pagesRes] = await Promise.all([
                this.dp.request('/api/v1/mini-program/site/info'),
                this.dp.request('/api/v1/mini-program/site/pages'),
            ]);
            this.setData({
                siteInfo: infoRes.data || {},
                pages: pagesRes.data || [],
                loading: false,
            });
        } catch (e) {
            console.error('[Home] Failed to load site data:', e);
            this.setData({ loading: false });
            tt.showToast({ title: 'Failed to load', icon: 'error' });
        }
    },

    onNavigateToPage(e) {
        const slug = e.currentTarget.dataset.slug;
        if (!slug) return;
        tt.navigateTo({ url: `/pages/page/page?slug=${slug}` });
    },

    onNavigateToChat() {
        tt.navigateTo({ url: '/pages/chat/chat' });
    },
});