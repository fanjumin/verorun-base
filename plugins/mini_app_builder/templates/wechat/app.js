App({
    onLaunch() {
        const WechatMP = require('./sdks/wechat/api.js').WechatMP;
        const wp = Object.create(WechatMP);
        wp.baseURL = '{{ base_url }}';

        if (wp.restoreToken()) {
            console.log('[mini-app] Token restored');
        }

        this.globalData = {
            wechat: wp,
            baseURL: '{{ base_url }}',
            apiPrefix: '{{ api_prefix }}',
            appName: '{{ app_name }}',
            primaryColor: '{{ primary_color }}',
        };
    },

    globalData: {
        wechat: null,
        baseURL: '{{ base_url }}',
        apiPrefix: '{{ api_prefix }}',
        appName: '{{ app_name }}',
        primaryColor: '{{ primary_color }}',
    }
});