App({
    onLaunch() {
        // Initialize Douyin MP SDK
        const DouyinMP = require('./sdks/douyin/api.js').DouyinMP;
        const dp = Object.create(DouyinMP);
        dp.baseURL = '{{ base_url }}';

        // Try to restore previous session
        if (dp.restoreToken()) {
            console.log('[VeroRun] Token restored');
        }

        // Store globally
        this.globalData = {
            douyin: dp,
            baseURL: '{{ base_url }}',
            apiPrefix: '{{ api_prefix }}',
            appName: '{{ app_name }}',
            primaryColor: '{{ primary_color }}',
        };
    },

    globalData: {
        douyin: null,
        baseURL: '{{ base_url }}',
        apiPrefix: '{{ api_prefix }}',
        appName: '{{ app_name }}',
        primaryColor: '{{ primary_color }}',
    }
});