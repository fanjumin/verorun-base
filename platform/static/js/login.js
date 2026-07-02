var cd = 0, cdTimer = null, tab = 'sms', capToken = '', capSolved = false;

var ICON_CHECK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>';
var ICON_CROSS = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18M6 6l12 12"/></svg>';
var ICON_EYE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
var ICON_EYE_OFF = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

document.addEventListener('captcha-success', function(e) {
  capToken = e.detail.token;
  capSolved = true;
});

document.addEventListener('DOMContentLoaded', function() {
  var savedPhone = localStorage.getItem('tm_phone');
  if (savedPhone) {
    document.getElementById('phone').value = savedPhone;
  }

  document.getElementById('tabSms').addEventListener('click', function() { switchTab('sms'); });
  document.getElementById('tabPwd').addEventListener('click', function() { switchTab('pwd'); });
  document.getElementById('toPwdTab').addEventListener('click', function() { switchTab('pwd'); });
  document.getElementById('sendBtn').addEventListener('click', sendCode);
  document.getElementById('loginSmsBtn').addEventListener('click', smsLogin);
  document.getElementById('loginPwdBtn').addEventListener('click', pwdLogin);
  document.getElementById('pwdEye').addEventListener('click', togglePwd);
  document.getElementById('douyinLogin').addEventListener('click', function() {
    window.location.href = '/auth/oauth/douyin/login?redirect=' + encodeURIComponent(window.location.origin + '/');
  });
  var alipayBtn = document.getElementById('alipayLogin');
  if (alipayBtn) {
    alipayBtn.addEventListener('click', function() {
      window.location.href = '/auth/oauth/alipay/login?redirect=' + encodeURIComponent(window.location.origin + '/');
    });
  }

  document.getElementById('phone').addEventListener('keydown', function(e) { if (e.key === 'Enter') sendCode(); });
  document.getElementById('code').addEventListener('keydown', function(e) { if (e.key === 'Enter') smsLogin(); });
  document.getElementById('pwdPhone').addEventListener('keydown', function(e) { if (e.key === 'Enter') pwdLogin(); });
  document.getElementById('password').addEventListener('keydown', function(e) { if (e.key === 'Enter') pwdLogin(); });

  document.getElementById('phone').addEventListener('input', function() {
    var v = this.value.replace(/\D/g, '').slice(0, 11);
    if (v.length > 7) v = v.slice(0, 3) + ' ' + v.slice(3, 7) + ' ' + v.slice(7);
    else if (v.length > 3) v = v.slice(0, 3) + ' ' + v.slice(3);
    this.value = v;
  });

  document.getElementById('code').addEventListener('input', function() {
    this.value = this.value.replace(/\D/g, '');
    if (this.value.length === 6 && rawPhone().length === 11) {
      smsLogin();
    }
  });
});

function switchTab(t) {
  tab = t;
  document.getElementById('smsTab').style.display = t === 'sms' ? '' : 'none';
  document.getElementById('pwdTab').style.display = t === 'pwd' ? '' : 'none';
  document.getElementById('tabSms').classList.toggle('active', t === 'sms');
  document.getElementById('tabPwd').classList.toggle('active', t === 'pwd');
  setTimeout(function() {
    document.getElementById(t === 'sms' ? 'phone' : 'pwdPhone').focus();
  }, 100);
}

function rawPhone() {
  return document.getElementById('phone').value.replace(/\D/g, '');
}

function showCaptcha() {
  var wrap = document.getElementById('captchaWrap');
  if (wrap && wrap.style.display === 'none') {
    wrap.style.display = '';
    if (window.PuzzleCaptchaBuild) {
      try {
        window.PuzzleCaptchaBuild();
      } catch (e) {}
    }
  }
}

function hideCaptcha() {
  var wrap = document.getElementById('captchaWrap');
  if (wrap) {
    wrap.style.display = 'none';
  }
}

async function sendCode() {
  var p = rawPhone();
  if (p.length < 11) { showMsg('phoneMsg', '请输入11位手机号', 'error'); return; }
  hideMsg('phoneMsg');
  var btn = document.getElementById('sendBtn');
  btn.disabled = true;
  btn.classList.add('countdown');
  try {
    var r = await fetch('/auth/sms/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: p, purpose: 'login', captcha_id: capToken })
    });
    var d = await r.json();
    if (d.success) {
      localStorage.setItem('tm_phone', p);
      toast('验证码已发送', 'success');
      startCd(60);
      capSolved = false;
      capToken = '';
      hideCaptcha();
      setTimeout(function() { document.getElementById('code').focus(); }, 100);
    } else {
      if (d.error && d.error.includes('验证码')) {
        showCaptcha();
        capSolved = false;
        capToken = '';
      }
      showMsg('phoneMsg', d.error || '发送失败', 'error');
      btn.disabled = false;
      btn.classList.remove('countdown');
    }
  } catch (e) {
    showMsg('phoneMsg', '网络错误，请重试', 'error');
    btn.disabled = false;
    btn.classList.remove('countdown');
  }
}

function startCd(s) {
  cd = s;
  var btn = document.getElementById('sendBtn');
  function tick() {
    cd--;
    btn.textContent = cd + 's';
    if (cd <= 0) {
      clearInterval(cdTimer);
      btn.textContent = '重新获取';
      btn.disabled = false;
      btn.classList.remove('countdown');
    }
  }
  tick();
  clearInterval(cdTimer);
  cdTimer = setInterval(tick, 1000);
}

async function smsLogin() {
  var p = rawPhone();
  var c = document.getElementById('code').value.replace(/\D/g, '');
  if (!p || p.length < 11) { showMsg('codeMsg', '请填写手机号', 'error'); return; }
  if (!c || c.length < 6) { showMsg('codeMsg', '请输入6位验证码', 'error'); return; }
  hideMsg('codeMsg');
  var btn = document.getElementById('loginSmsBtn');
  btn.disabled = true;
  btn.classList.add('loading');
  try {
    var r = await fetch('/auth/sms/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: p, code: c, captcha_id: capToken })
    });
    var d = await r.json();
    if (d.success) {
      localStorage.setItem('tm_token', d.data.token);
      localStorage.setItem('sso_token', d.data.token);
      localStorage.setItem('token', d.data.token);
      localStorage.setItem('tm_user', JSON.stringify(d.data.user));
      toast('登录成功，正在跳转...', 'success');
      setTimeout(function() {
        var rd = new URLSearchParams(location.search).get('redirect') || window.location.origin;
        window.location.href = rd + (rd.indexOf('?') !== -1 ? '&' : '?') + 'token=' + d.data.token;
      }, 600);
    } else {
      if (d.error && d.error.includes('验证码')) {
        showCaptcha();
        capSolved = false;
        capToken = '';
      }
      showMsg('codeMsg', d.error || '登录失败', 'error');
      btn.disabled = false;
      btn.classList.remove('loading');
    }
  } catch (e) {
    showMsg('codeMsg', '网络错误', 'error');
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

async function pwdLogin() {
  var p = document.getElementById('pwdPhone').value.trim();
  var pw = document.getElementById('password').value;
  if (!p || !pw) { showMsg('pwdMsg', '请填写账号和密码', 'error'); return; }
  hideMsg('pwdMsg');
  var btn = document.getElementById('loginPwdBtn');
  btn.disabled = true;
  btn.classList.add('loading');
  try {
    var r = await fetch('/user/password/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: p, password: pw, captcha_id: capToken })
    });
    var d = await r.json();
    if (d.success) {
      localStorage.setItem('tm_token', d.data.token);
      localStorage.setItem('sso_token', d.data.token);
      localStorage.setItem('token', d.data.token);
      localStorage.setItem('tm_user', JSON.stringify(d.data.user));
      toast('登录成功，正在跳转...', 'success');
      setTimeout(function() {
        var rd = new URLSearchParams(location.search).get('redirect') || window.location.origin;
        window.location.href = rd + (rd.indexOf('?') !== -1 ? '&' : '?') + 'token=' + d.data.token;
      }, 600);
    } else {
      if (d.error && d.error.includes('验证码')) {
        showCaptcha();
        capSolved = false;
        capToken = '';
      }
      showMsg('pwdMsg', d.error || '登录失败', 'error');
      btn.disabled = false;
      btn.classList.remove('loading');
    }
  } catch (e) {
    showMsg('pwdMsg', '网络错误', 'error');
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

function showMsg(id, msg, type) {
  var el = document.getElementById(id);
  el.className = 'lf-msg ' + type;
  el.innerHTML = (type === 'error' ? ICON_CROSS : ICON_CHECK);
  el.appendChild(document.createTextNode(' ' + msg));
}
function hideMsg(id) {
  document.getElementById(id).className = 'lf-msg';
}

function toast(msg, type) {
  var wrap = document.getElementById('toastWrap');
  if (!wrap) return;
  var el = document.createElement('div');
  el.className = 'toast-el ' + type;
  el.innerHTML = (type === 'success' ? ICON_CHECK : ICON_CROSS);
  var textSpan = document.createElement('span');
  textSpan.textContent = msg;
  el.appendChild(textSpan);
  wrap.appendChild(el);
  setTimeout(function() {
    el.classList.add('leave');
    setTimeout(function() { el.remove(); }, 250);
  }, 3000);
}

function togglePwd() {
  var el = document.getElementById('password');
  var eye = document.getElementById('pwdEye');
  if (el.type === 'password') {
    el.type = 'text';
    eye.innerHTML = ICON_EYE_OFF;
  } else {
    el.type = 'password';
    eye.innerHTML = ICON_EYE;
  }
}
