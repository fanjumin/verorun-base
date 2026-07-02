
// ── Admin JS runs FIRST, Quill loads async below ──
var T = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIwLXpxTXh2OW5wdzdGWlByNGZnWmlRIiwidXNlcl9pZCI6MSwicGhvbmUiOiIxMzkxMDYwNDI5OSIsImFwcF9uYW1lIjoidHJhZGVtaW5kIiwiaXNfYWRtaW4iOnRydWUsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJpYXQiOjE3ODI5ODM3MTQsImV4cCI6MTc4MzU4ODUxNH0.92FAlq8siJ2jo_fZdeg8R7QdK56bZm-XHLi8AQy39AM";
if(!T||T.length<10)T=localStorage.getItem("sso_token")||localStorage.getItem("tm_token")||localStorage.getItem("token");
var P=new URLSearchParams(location.search);
if(P.get("token")){T=P.get("token");localStorage.setItem("sso_token",T);localStorage.setItem("tm_token",T);localStorage.setItem("token",T);window.history.replaceState({},"",window.location.pathname)}
function S(p){return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+p+'</svg>'}
var I={
  dashboard:S('<rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>'),
  users:S('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
  customers:S('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/><path d="M19 7v6"/><path d="M16 10h6"/>'),
  i18n_translations:S('<circle cx="12" cy="12" r="2"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M2 12h20"/>'),
  enterprise_verify:S('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>'),
  agents:S('<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16.01"/><line x1="16" y1="16" x2="16" y2="16.01"/>'),
  keys:S('<circle cx="8" cy="21" r="2"/><path d="M8 17V3l3 2 3-2 3 2 3-2v8"/><path d="M16 21c0-2.5-2-4-4-4"/>'),
  cms:S('<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>'),
  contentfactory:S('<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 13h5l-5-5"/><path d="M7 13H2l5-5"/>'),
  posts:S('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'),
  community:S('<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'),
  comments:S('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><line x1="8" y1="9" x2="16" y2="9"/><line x1="12" y1="13" x2="12" y2="13"/>'),
  matrix:S('<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="2" x2="9" y2="4"/><line x1="15" y1="2" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="22"/><line x1="15" y1="20" x2="15" y2="22"/>'),
  automation:S('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'),
  health:S('<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'),
  analytics:S('<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>'),
  plans:S('<path d="M16.5 9.4 7.55 4.24"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" y1="22" x2="12" y2="12"/>'),
  subscriptions:S('<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>'),
  sub_orders:S('<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>'),
  sub_stats:S('<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>'),
  coupons:S('<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><circle cx="12" cy="12" r="2"/>'),
  sub_events:S('<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="14" y2="14"/>'),
  config:S('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>'),
   logs:S('<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/>'),
   admins:S('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>'),
   email:S('<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>'),
   sms:S('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><line x1="8" y1="9" x2="16" y2="9"/><line x1="12" y1="13" x2="12" y2="13"/>'),
   tickets:S('<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/>'),
   feedback:S('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>'),
   channels:S('<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'),
   contacts:S('<path d="M3 8l7.89 5.26a2 2 0 0 0 2.22 0L21 8M5 19h14a2 2 0 0 0 2-2V7a2 2 0 0 0 2-2H5a2 2 0 0 0-2-2v10a2 2 0 0 0-2 2z"/>'),
   ai_chat:S('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><circle cx="12" cy="10" r="2"/><path d="M9 15a3 3 0 0 1 6 0"/><circle cx="9" cy="8" r="1" fill="currentColor"/><circle cx="15" cy="8" r="1" fill="currentColor"/>'),
  social_media:S('<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2v20"/><circle cx="12" cy="12" r="3"/>'),
  cluster_services:S('<rect x="2" y="2" width="8" height="8" rx="1"/><rect x="14" y="2" width="8" height="8" rx="1"/><rect x="2" y="14" width="8" height="8" rx="1"/><rect x="14" y="14" width="8" height="8" rx="1"/><line x1="6" y1="6" x2="18" y2="6"/><line x1="6" y1="18" x2="18" y2="18"/>'),
  themes:S('<circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><circle cx="12" cy="12" r="3"/>'),
  headernav:S('<path d="M3 12h18M3 6h18M3 18h18"/><circle cx="8" cy="6" r="1"/><circle cx="16" cy="12" r="1"/><circle cx="10" cy="18" r="1"/>'),
  brand:S('<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/><circle cx="12" cy="12" r="3" fill="none"/>'),
  token_monitoring:S('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="18" y1="6" x2="15" y2="9"/>'),
  notifications:S('<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>'),
  reward_rules:S('<circle cx="12" cy="8" r="6"/><path d="M15.33 12.5l1.17 9.5-4.5-3-4.5 3 1.17-9.5"/>'),
  ads:S('<rect x="3" y="3" width="18" height="18" rx="3"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M15 15l6 6"/><circle cx="18" cy="18" r="1.5"/>'),
  nav_settings:S('<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><circle cx="9" cy="6" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/>'),
  downloads:S('<circle cx="12" cy="12" r="10"/><path d="M12 6v8"/><path d="M8 10l4 4 4-4"/><rect x="4" y="16" width="16" height="4" rx="1"/>'),
  model_providers:S('<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>'),
  media_video:S('<rect x="2" y="4" width="20" height="16" rx="2"/><polygon points="10,8 16,12 10,16"/><rect x="4" y="20" width="16" height="3" rx="1"/><line x1="8" y1="23" x2="16" y2="23"/>'),
  ppt_gen:S('<rect x="3" y="5" width="18" height="14" rx="2"/><rect x="7" y="2" width="10" height="3" rx="1"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="13" x2="14" y2="13"/><line x1="8" y1="16" x2="12" y2="16"/><circle cx="19" cy="16" r="2" fill="var(--accent)"/>'),
  media_library:S('<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>'),
  shop:S('<path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/>'),
  shop_cat:S('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'),
  cleaner:S('<path d="M12 2l2.4 7.2L21 12l-6.6 2.8L12 22l-2.4-7.2L3 12l6.6-2.8z"/>'),
  deploy:S('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>')
};
var GROUPS=[
  ["Dashboard",false,[["dashboard",I.dashboard,"Dashboard"]]],
  ["AI Chat",false,[["ai_chat",I.ai_chat,"Command Console"]]],
  ["System",true,[["config",I.config,"Basic Settings"],["oauth",I.social_media,"OAuth Login"],["nav_settings",I.nav_settings,"Navigation Settings"],["model_providers",I.model_providers,"Model Management"],["admins",I.admins,"Admins"],["brand",I.brand,"Brand Settings"],["cluster_services",I.cluster_services,"Site Group Management"],["themes",I.themes,"Template Management"]]],
  ["Content",true,[["contentfactory",I.contentfactory,"Capture"],["cms",I.cms,"Omni-Media Creation"],["downloads",I.downloads,"Download Management"],["media_library",I.media_library,"Media Library"]]],
  ["AI Create",true,[["ppt",I.ppt_gen,"PPT Generation"],["image",I.media_video,"Image Gen"],["media_tools",I.media_video,"Multimedia"]]],
  ["Strategy",true,[["matrix",I.matrix,"Matrix"],["cleaner",I.cleaner,"Cleaner"],["automation",I.automation,"Auto Schedule"],["channels",I.channels,"IM Gateway"]]],
  ["Operations",true,[["plans",I.plans,"Subscription"],["subscriptions",I.subscriptions,"Subscription List"],["sub_orders",I.sub_orders,"Order Management"],["deploy",I.deploy,"Deploy Code Management"],["sub_stats",I.sub_stats,"Revenue Dashboard"],["coupons",I.coupons,"Coupon"],["sub_events",I.sub_events,"Billing Log"],["reward_rules",I.reward_rules,"Rewards"],["ads",I.ads,"Ad Management"],["shop_categories",I.shop_cat,"Category"],["shop_products",I.shop,"Product Management"],["shop_orders",I.sub_orders,"Order Management"],["shop_coupons",I.coupons,"Coupon Management"],["shop_purchases",I.subscriptions,"Purchases"]]],
  ["Messages &amp; Support",true,[["email",I.email,"Email Service"],["notifications",I.notifications,"Notifications"],["tickets",I.tickets,"User Tickets"]]],
  ["Customer Management",true,[["customers",I.customers,"All Customers"],["enterprise_verify",I.enterprise_verify,"Enterprise Verification"],["customer_agents",I.agents,"Customer Agents"],["api_keys",I.keys,"API Tokens"]]],
  ["Risk &amp; Audit",true,[["posts",I.posts,"Post Audit"],["comments",I.comments,"Comment Moderation"]]],
  ["International",true,[["i18n_translations",I.i18n_translations,"Translations"]]],
  ["Ops Data",true,[["analytics",I.analytics,"Analytics"],["health",I.health,"Health Check"],["token_monitoring",I.token_monitoring,"Token Usage"],["logs",I.logs,"Operation Log"]]],
];
function renderNav(){var e=document.getElementById("nav"),h='';GROUPS.forEach(function(g,i){var n=g[0],c=g[1],t=g[2];if(!c&&t.length===1){var k=t[0][0],x=t[0][1],l=t[0][2];h+='<div class="ni" onclick="go(\''+k+'\')\" id="n-'+k+'">'+x+'<span>'+l+'</span></div>'}else{h+='<div class="ng" id="ng-'+i+'"><div class="ns" onclick="toggleGroup('+i+')"><span class="ns-arrow">'+(c?'▶':'▼')+'</span><span class="ns-label">'+n+'</span></div><div class="ng-body'+(c?' collapsed':'')+'" id="ngb-'+i+'">';t.forEach(function(m){var k=m[0],x=m[1],l=m[2];h+='<div class="ni" onclick="go(\''+k+'\')\" id="n-'+k+'">'+x+'<span>'+l+'</span></div>'});h+='</div></div>'}});e.innerHTML=h}
function toggleGroup(i){var b=document.getElementById("ngb-"+i),a=document.querySelector("#ng-"+i+" .ns-arrow");b.classList.contains("collapsed")?(b.classList.remove("collapsed"),a.textContent="▼"):(b.classList.add("collapsed"),a.textContent="▶")}
renderNav();

function esc(s){if(!s)return'';return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;').replace(/'/g,'&#39;')}

if(!T){document.getElementById("mc").innerHTML='<div class="em">Please <a href="/admin/login">Log In</a></div>'}else{init()}

function init(){
  var c=document.getElementById("mc");
  var to=setTimeout(function(){c.innerHTML='<div class="em"><div style="color:var(--dim);font-size:12px;margin-bottom:8px">Connection Timeout，Check Network or <a href="/admin/login">Re-login</a></div></div>'},8000);
  fetch("/admin/dashboard",{headers:{"Authorization":"Bearer "+T}}).then(function(r){
    clearTimeout(to);
    if(r.status===403){c.innerHTML='<div class="em">Admin Only</div>';return Promise.reject()}
    if(r.status===401){c.innerHTML='<div class="em">Please <a href="/admin/login">Log In</a></div>';return Promise.reject()}
    return r.json()
  }).then(function(d){if(d.success){document.getElementById("an").textContent="Admin";go("dashboard")}else{c.innerHTML='<div class="em"><div style="color:var(--dim);font-size:12px">'+esc(d.error||"Load failed")+' <a href="/admin/login">Please Re-login</a></div></div>'}}).catch(function(){clearTimeout(to);c.innerHTML='<div class="em"><div style="color:var(--dim);font-size:12px">Connection Failed：<a href="/admin/login">Please Re-login</a></div></div>'})
}

function logout(){
  fetch("/admin/logout",{method:"POST",headers:{"Authorization":"Bearer "+T}}).catch(function(){});
  localStorage.removeItem("sso_token");
  localStorage.removeItem("tm_token");
  localStorage.removeItem("token");
  document.cookie="sso_token=; path=/; max-age=0";
  showToast("Logged out","success");
  setTimeout(function(){window.location.href="/admin/login"},800);
}

function go(s){
  document.querySelectorAll(".ni").forEach(function(n){n.classList.remove("sel")});
  var el=document.getElementById("n-"+s);if(el)el.classList.add("sel");
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  if(typeof window["l_"+s]=="function")window["l_"+s]();
}


window.l_dashboard=function(){
  document.getElementById("pt").textContent="Overview";
  fetch("/admin/dashboard",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var ds=d.data, h="";
    h+='<div class="cd"><div class="st">Core Metrics</div></div>';
    h+='<div class="gr">';
    h+=hk("Total Users",ds.total_users+' <span style="font-size:11px;color:var(--dim)">+'+ds.today_new_users+' Today</span>',"b");
    h+=hk("Active Subscriptions",ds.active_subscriptions,"g");
    h+=hk("Today API Call",ds.today_calls,"b");
    h+=hk("Active Agent",ds.active_agents+"/"+ds.total_agents,"g");
    h+=hk("Monthly Revenue","\u00a5"+ds.monthly_revenue,"g");
    h+='</div>';
    // Token Usage Card (2026-05-16)
    var tt=ds.today_tokens||0, ta=ds.top_token_agents||[];
    var tf=function(n){if(n>=1e6)return (n/1e6).toFixed(1)+'M';if(n>=1e3)return (n/1e3).toFixed(1)+'K';return n.toString()};
    var th='<div class="cd" onclick="go(\'token_monitoring\')" style="cursor:pointer" onmouseover="this.style.borderColor=\'var(--accent)\'" onmouseout="this.style.borderColor=\'var(--border)\'"><div class="st">Today Token Spend <span style="font-size:10px;color:var(--dim)">→ Details</span></div>';
    th+='<div class="v b" style="font-size:22px">'+tf(tt)+'</div>';
    if(ta.length){th+='<div style="font-size:11px;color:var(--dim);margin-top:6px;display:flex;gap:12px;flex-wrap:wrap">';ta.forEach(function(a,i){th+='<span>'+(i+1)+'. '+esc(a.agent_name||'Agent#'+a.agent_id)+' <span style="color:var(--accent)">'+tf(a.total)+'</span></span>'});th+='</div>'}
    th+='</div>';
    h+=th;
    h+=svcCard(ds.services);
    var pn=ds.pending_posts+ds.pending_reviews+ds.pending_contacts+ds.today_failed_tasks;
    h+='<div class="cd" style="margin-top:4px"><div class="st">Pending'+(pn>0?' <span style="color:var(--rose)">('+pn+')</span>':'')+'</div></div>';
    h+='<div class="gr">';
    h+=hk("Pending Review Post",ds.pending_posts,ds.pending_posts>0?"r":"");
    h+=hk("Pending Review Content",ds.pending_reviews,ds.pending_reviews>0?"r":"");
    h+=hk("Pending Ticket",ds.pending_contacts,ds.pending_contacts>0?"r":"");
    h+=hk("Today Failed Tasks",ds.today_failed_tasks,ds.today_failed_tasks>0?"r":"");
    h+='</div>';
    h+='<div class="cd" style="margin-top:4px"><div class="st">Today Traffic</div></div>';
    h+='<div class="gr">';
    h+=hk("PV",ds.today_pv,"b");
    h+=hk("UV",ds.today_uv,"g");
    h+=hk("Online Now",ds.online_now,"g");
    h+='</div>';
    if(ds.top_pages&&ds.top_pages.length){
      h+='<div class="cd" style="margin-top:4px"><div class="st">Popular Pages</div><table style="font-size:12px;margin-top:8px">';
      h+='<tr><th>Page</th><th style="text-align:right">PV</th></tr>';
      ds.top_pages.forEach(function(p){h+='<tr><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+p.path+'</td><td style="text-align:right">'+p.pv+'</td></tr>'});
      h+='</table></div>';
    }
    h+='<div class="g2" style="margin-top:4px">';
    h+='<div class="cd"><div class="st">Recent Registrations</div><table style="font-size:12px;margin-top:8px">';
    h+='<tr><th>ID</th><th>Nickname</th><th>Phone</th><th>Time</th></tr>';
    if(ds.recent_users&&ds.recent_users.length){
      ds.recent_users.forEach(function(u){h+='<tr><td>'+u.id+'</td><td>'+(u.nickname||'-')+'</td><td>'+(u.phone||'-')+'</td><td>'+u.created_at+'</td></tr>'});
    }
    h+='</table></div>';
    h+='<div class="cd"><div class="st">Recent Orders</div><table style="font-size:12px;margin-top:8px">';
    h+='<tr><th>ID</th><th>Plan</th><th>Amount</th><th>Status</th></tr>';
    if(ds.recent_orders&&ds.recent_orders.length){
      ds.recent_orders.forEach(function(o){
        var st=o.status==='paid'?'<span class="bdg on">Paid</span>':(o.status==='pending'?'<span class="bdg off">Unpaid</span>':o.status);
        h+='<tr><td>'+o.id+'</td><td>'+(o.item_desc||'-')+'</td><td>\u00a5'+(o.amount||0)+'</td><td>'+st+'</td></tr>';
      });
    }
    h+='</table></div>';
    h+='</div>';
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){document.getElementById("mc").innerHTML='<div class="em">Load failed</div>'})
}
function svcCard(svcs){
  var h='<div class="gr"><div class="cd"><div class="l">Service Status</div><div class="v" style="display:flex;gap:6px;flex-wrap:wrap">';
  svcs.forEach(function(s){
    var c=s.alive?'var(--green)':'var(--rose)';
    h+='<span style="display:flex;align-items:center;gap:3px;font-size:11px"><span style="width:6px;height:6px;border-radius:50%;background:'+c+'"></span>'+s.name+'</span>';
  });
  h+='</div></div></div>';
  return h;
}
function hk(l,v,c){return '<div class="cd"><div class="l">'+l+'</div><div class="v '+(c||"")+'">'+v+'</div></div>'}


window.l_users=function(){
  document.getElementById("pt").textContent="User Management";
  var ind=document.getElementById("uIndustry")?document.getElementById("uIndustry").value:'';
  var occ=document.getElementById("uOccupation")?document.getElementById("uOccupation").value:'';
  var reg=document.getElementById("uRegion")?document.getElementById("uRegion").value:'';
  var url="/admin/users?limit=100";
  if(ind)url+="&industry="+encodeURIComponent(ind);
  if(occ)url+="&occupation="+encodeURIComponent(occ);
  if(reg)url+="&region="+encodeURIComponent(reg);
  fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var ds=d.data;
    var h='<div class="cd">';
    // Filter Bar
    h+='<div class="st" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px">';
    h+='<span style="font-size:12px">User List ('+ds.total+')</span>';
    h+='<select id="uIndustry" onchange="l_users()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:11px"><option value="">All Industries</option><option value="Fintech">Fintech</option><option value="AI">AI</option><option value="Quantitative Trading">Quantitative Trading</option><option value="Blockchain">Blockchain</option><option value="Traditional Finance">Traditional Finance</option><option value="Internet">Internet</option><option value="Education">Education</option><option value="Healthcare">Healthcare</option><option value="E-Commerce">E-Commerce</option><option value="Other">Other</option></select>';
    h+='<select id="uOccupation" onchange="l_users()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:11px"><option value="">All Occupations</option><option value="Developer">Developer</option><option value="Quantitative Engineer">Quantitative Engineer</option><option value="Trader">Trader</option><option value="Researcher">Researcher</option><option value="Product Manager">Product Manager</option><option value="Designer">Designer</option><option value="Student">Student</option><option value="Freelancer">Freelancer</option><option value="Other">Other</option></select>';
    h+='<input type="text" id="uRegion" placeholder="Region Filter..." onchange="l_users()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:11px;width:120px">';
    h+='<span class="btn bo bs" style="padding:2px 8px;font-size:11px" onclick="document.getElementById(\'uIndustry\').value=\'\';document.getElementById(\'uOccupation\').value=\'\';document.getElementById(\'uRegion\').value=\'\';l_users()">Reset</span>';
    h+='<span class="btn bo bs" style="padding:2px 8px;font-size:11px" onclick="exportUsers()">ExportCSV</span>';
    h+='<span style="font-weight:400;font-size:11px;color:var(--dim)">Click Row for Details · Click🤖ExpandAgent</span>';
    h+='</div>';
    h+='<table><tr><th>ID</th><th>Avatar</th><th>Nickname</th><th>Phone</th><th>Agent</th><th>Industry</th><th>Career</th><th>Certification</th><th>Level</th><th>Status</th><th>Registered</th></tr>';
    ds.users.forEach(function(u){
      var st=u.active?'<span class="bdg on">Active</span>':'<span class="bdg off">Disabled</span>';
      var verified=u.verified_by?'<span class="bdg on">'+u.verified_by+'</span>':'<span class="bdg dim">Unverified</span>';
      var ava=u.avatar_url?'<img src="'+escAttr(u.avatar_url)+'" style="width:28px;height:28px;border-radius:50%;object-fit:cover;border:1px solid var(--border)">':dicebearImgTag(u.nickname||u.phone||u.id,'initials',28);
      h+='<tr style="cursor:pointer" onclick="showUserDetail('+u.id+')"><td>'+u.id+'</td><td>'+ava+'</td><td>'+(u.nickname||'')+'</td><td>'+(u.phone||'-')+'</td>';
      h+='<td><span class="btn bo bs" style="padding:2px 8px;font-size:11px;cursor:pointer" onclick="event.stopPropagation();toggleUserAgents('+u.id+',this)">🤖 Expand</span></td>';
      h+='<td style="font-size:11px">'+(u.industry||'-')+'</td><td style="font-size:11px">'+(u.occupation||'-')+'</td>';
      h+='<td style="font-size:11px">'+verified+'</td>';
      h+='<td>'+(u.tier||'free')+'</td><td>'+st+'</td><td>'+(u.created_at||'')+'</td></tr>';
      h+='<tr id="ua-row-'+u.id+'" style="display:none"><td colspan="11"><div id="ua-content-'+u.id+'" style="padding:8px 16px;background:var(--bg2);border-radius:6px;font-size:12px">Loading......</div></td></tr>';
    });
    h+="</table></div>";
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){
    document.getElementById("mc").innerHTML='<div class="em">Load failed</div>';
  });
}

function exportUsers(){
  var ind=document.getElementById("uIndustry")?document.getElementById("uIndustry").value:'';
  var occ=document.getElementById("uOccupation")?document.getElementById("uOccupation").value:'';
  var reg=document.getElementById("uRegion")?document.getElementById("uRegion").value:'';
  var url="/admin/users/export?";
  var params=[];
  if(ind)params.push("industry="+encodeURIComponent(ind));
  if(occ)params.push("occupation="+encodeURIComponent(occ));
  if(reg)params.push("region="+encodeURIComponent(reg));
  url+=params.join("&");
  window.open(url);
}

function toggleUserAgents(uid,btn){
  var row=document.getElementById("ua-row-"+uid);
  if(!row)return;
  if(row.style.display!="none"){
    row.style.display="none";
    btn.textContent="🤖 Expand";
    return;
  }
  row.style.display="table-row";
  btn.textContent="🤖 Collapse";
  var content=document.getElementById("ua-content-"+uid);
  if(content.dataset.loaded)return;
  fetch("/admin/users/"+uid+"/user-agents",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data){content.innerHTML='<span style="color:var(--dim)">Load failed</span>';return}
      var agents=d.data.agents||[];
      if(agents.length===0){content.innerHTML='<span style="color:var(--dim)">This User Has No Agent</span> <span class="btn bp" style="padding:2px 8px;font-size:11px" onclick="event.stopPropagation();adminCreateAgent('+uid+')">+ Create</span>';return}
      var h='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px"><b>🤖 '+agents.length+' 个 Agent</b> <span class="btn bp" style="padding:2px 8px;font-size:11px" onclick="event.stopPropagation();adminCreateAgent('+uid+')">+ Create</span></div>';
      h+='<table style="font-size:12px"><tr><th>ID</th><th>Name</th><th>Type</th><th>Status</th><th>Key数</th><th>Last Active</th><th>Actions</th></tr>';
      agents.forEach(function(a){
        var stCls=a.status==='active'?'bdg on':'bdg off';
        var stText=a.status==='active'?'Active':(a.status==='suspended'?'Pause':'Inactive');
        h+='<tr><td>'+a.id+'</td><td>'+escAttr(a.agent_name)+'</td><td>'+a.agent_type+'</td>';
        h+='<td><span class="'+stCls+'">'+stText+'</span></td>';
        h+='<td>'+(a.active_keys||0)+'</td><td>'+(a.last_active_at||'-')+'</td>';
        h+='<td>';
        if(a.status==='active'){
          h+='<span class="btn bo bs" style="padding:2px 6px;font-size:10px" onclick="event.stopPropagation();setAgentStatus('+a.id+',&#39;suspended&#39;,\''+escAttr(a.agent_name)+'\')">Pause</span>';
        }else{
          h+='<span class="btn bp" style="padding:2px 6px;font-size:10px" onclick="event.stopPropagation();setAgentStatus('+a.id+',&#39;active&#39;,\''+escAttr(a.agent_name)+'\')">Activate</span>';
        }
        h+='</td></tr>';
      });
      h+='</table>';
      content.innerHTML=h;
      content.dataset.loaded="1";
    }).catch(function(){content.innerHTML='<span style="color:var(--dim)">Request Failed</span>'});
}

function adminCreateAgent(uid){
  var name=prompt("Please enter Agent Name：");
  if(!name||!name.trim())return;
  fetch("/admin/users/"+uid+"/user-agents",{
    method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({agent_name:name.trim()})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Agent created","success");
      // Reload agents for this user
      var content=document.getElementById("ua-content-"+uid);
      if(content)delete content.dataset.loaded;
      toggleUserAgents(uid,document.querySelector('#ua-row-'+uid+' .btn'));
    }else{showToast(d.error||"Creation Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function setAgentStatus(aid,status,name){
  var action=status==='suspended'?'Pause':'Activate';
  if(!confirm("Go"+action+" Agent \""+name+"\"？"))return;
  fetch("/admin/user-agents/"+aid+"/status",{
    method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({status:status})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Agent Done: "+action,"success");l_users()}
    else{showToast(d.error||"Operation Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

// ── User Details Popup（Edit Avatar） ──
var _avatarSelectedUserId = 0;
var _avatarDefaultsData = null;

function loadAvatarDefaults(cb) {
  if (_avatarDefaultsData) { cb(_avatarDefaultsData); return; }
  fetch("/admin/avatars/defaults",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success) { _avatarDefaultsData = d.data; cb(d.data); }
    }).catch(function(){});
}

function showUserDetail(uid) {
  _avatarSelectedUserId = uid;
  fetch("/admin/users/"+uid,{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data){showToast("Load failed","error");return}
      var u=d.data.user;
      renderUserDetail(u);
    }).catch(function(){showToast("Request Failed","error")});
}

function escAttr(s){
  return (s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function escJs(s){return (s||'').replace(/'/g,"\\'");}

// ── DiceBear Local Avatar Generation ──
function dicebearAvatar(seed, style, size) {
  style = style || 'initials';
  size = size || 72;
  seed = seed || '?';
  try {
    var avatar = window.dicebear.createAvatar(window.dicebear.styles[style], {
      seed: seed, size: size, backgroundColor: 'transparent'
    });
    return avatar.toString();
  } catch(e) {
    return '<img src="/avatar/gen/'+encodeURIComponent(seed)+'" width="'+size+'" height="'+size+'" style="border-radius:50%;object-fit:cover">';
  }
}
function dicebearImgTag(seed, style, size) {
  size = size || 72;
  seed = seed || '?';
  return '<img src="/avatar/gen/'+encodeURIComponent(seed)+'" width="'+size+'" height="'+size+'" style="border-radius:50%;object-fit:cover">';
}

function renderUserDetail(u) {
  var avaUrl = u.avatar_url||'';
  var agentAva = u.agent_avatar_url||'';
  var h = '<div class="modal-overlay" onclick="closeUserDetail(event)">';
  h += '<div class="modal-box" style="width:720px;max-width:95vw" onclick="event.stopPropagation()">';
  h += '<button onclick="closeUserDetail()" style="float:right;background:none;border:none;color:var(--dim);font-size:20px;cursor:pointer;line-height:1">✕</button>';
  h += '<h3 style="font-size:16px;margin-bottom:8px">User Details #'+u.id+' — '+(u.nickname||u.phone||'')+'</h3>';

  // Tab Navigation
  h += '<div style="display:flex;gap:0;margin-bottom:12px;border-bottom:1px solid var(--border)">';
  h += '<span id="dt-basic" class="dt-tab" onclick="switchDetailTab('+u.id+',\'basic\')" style="padding:6px 14px;cursor:pointer;font-size:13px;border-bottom:2px solid var(--accent);color:var(--accent)">Basic Info</span>';
  h += '<span id="dt-profile" class="dt-tab" onclick="switchDetailTab('+u.id+',\'profile\')" style="padding:6px 14px;cursor:pointer;font-size:13px;color:var(--dim)">Extended Profile</span>';
  h += '<span id="dt-address" class="dt-tab" onclick="switchDetailTab('+u.id+',\'address\')" style="padding:6px 14px;cursor:pointer;font-size:13px;color:var(--dim)">Shipping Address</span>';
  h += '</div>';

  // Tab 1: Basic Info
  h += '<div id="dt-content-basic" class="detail-tab-content">';
  h += '<div class="g2" style="margin-bottom:16px">';
  h += '<div><span style="color:var(--dim);font-size:11px">Phone</span><div style="font-size:13px">'+(u.phone||'-')+'</div></div>';
  h += '<div><span style="color:var(--dim);font-size:11px">Nickname</span><div style="font-size:13px">'+(u.nickname||'-')+'</div></div>';
  h += '<div><span style="color:var(--dim);font-size:11px">Agent ID</span><div style="font-size:13px">'+(u.agent_id||'-')+'</div></div>';
  h += '<div><span style="color:var(--dim);font-size:11px">Agent Nickname</span><div style="font-size:13px">'+(u.agent_nickname||'-')+'</div></div>';
  h += '</div>';
  // User Avatar
  h += '<div class="cd" style="margin-bottom:12px"><div class="st">User Avatar</div>';
  h += '<div style="display:flex;gap:16px;align-items:center;margin-bottom:12px">';
  h += '<div id="userAvaPreview" style="width:72px;height:72px;border-radius:50%;border:2px solid var(--border);overflow:hidden;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:var(--bg)">';
  if(avaUrl) {
    h += '<img src="'+escAttr(avaUrl)+'" style="width:72px;height:72px;object-fit:cover" onerror="this.style.display=\'none\';this.parentNode.innerHTML=dicebearAvatar(\''+escAttr(u.nickname||u.phone||u.id)+'\',\'initials\',72)">';
  } else {
    h += dicebearAvatar(u.nickname||u.phone||u.id,'initials',72);
  }
  h += '</div><div>';
  h += '<input type="file" id="userAvaFile" accept="image/*" style="display:none" onchange="uploadUserAvatar('+u.id+')">';
  h += '<button class="btn bp" onclick="document.getElementById(\'userAvaFile\').click()">📤 Upload Avatar</button> ';
  h += '<button class="btn bo" onclick="showDefaultAvatars(\'user\','+u.id+')">🎨 Select Default</button>';
  if(avaUrl) h += ' <button class="btn bo bs" onclick="removeUserAvatar('+u.id+')" style="color:#f85149">Remove</button>';
  h += '<div id="userAvaStatus" style="font-size:11px;color:var(--dim);margin-top:4px">512×512 / 512KB Within</div>';
  h += '</div></div>';
  h += '<div id="userDefaultGrid" style="display:none;margin-top:8px"><div class="st" style="font-size:12px">Select Default Avatar</div><div style="display:grid;grid-template-columns:repeat(auto-fill,48px);gap:6px" id="userDefaultGridInner"></div></div>';
  h += '</div>';
  // Agent Avatar
  h += '<div class="cd"><div class="st">Agent Avatar</div>';
  h += '<div style="display:flex;gap:16px;align-items:center;margin-bottom:12px">';
  h += '<div id="agentAvaPreview" style="width:72px;height:72px;border-radius:50%;border:2px solid var(--border);overflow:hidden;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:var(--bg)">';
  if(agentAva) {
    h += '<img src="'+escAttr(agentAva)+'" style="width:72px;height:72px;object-fit:cover" onerror="this.style.display=\'none\';this.parentNode.innerHTML=dicebearAvatar(\''+escAttr(u.agent_nickname||u.nickname||u.phone||u.id)+'\',\'identicon\',72)">';
  } else {
    h += dicebearAvatar(u.agent_nickname||u.nickname||u.phone||u.id,'identicon',72);
  }
  h += '</div><div>';
  h += '<input type="file" id="agentAvaFile" accept="image/*" style="display:none" onchange="uploadAgentAvatar('+u.id+')">';
  h += '<button class="btn bp" onclick="document.getElementById(\'agentAvaFile\').click()">📤 Upload Avatar</button> ';
  h += '<button class="btn bo" onclick="showDefaultAvatars(\'agent\','+u.id+')">🎨 Select Default</button>';
  if(agentAva) h += ' <button class="btn bo bs" onclick="removeAgentAvatar('+u.id+')" style="color:#f85149">Remove</button>';
  h += '<div style="font-size:11px;color:var(--dim);margin-top:4px">512×512 / 512KB Within</div>';
  h += '</div></div>';
  h += '<div id="agentDefaultGrid" style="display:none;margin-top:8px"><div class="st" style="font-size:12px">Select Default Avatar</div><div style="display:grid;grid-template-columns:repeat(auto-fill,48px);gap:6px" id="agentDefaultGridInner"></div></div>';
  h += '</div>';
  h += '</div>';  // end Tab 1

  // Tab 2: Extended Profile
  h += '<div id="dt-content-profile" class="detail-tab-content" style="display:none">';
  h += '<div class="lo" id="dt-profile-loading">Loading......</div>';
  h += '</div>';

  // Tab 3: Shipping Address
  h += '<div id="dt-content-address" class="detail-tab-content" style="display:none">';
  h += '<div class="lo" id="dt-address-loading">Loading......</div>';
  h += '</div>';

  h += '</div></div>';
  document.getElementById("mc").innerHTML = h;

  // Lazy-load profile + addresses
  fetch("/admin/users/"+u.id+"/profile",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success&&d.data){
        renderDetailProfile(d.data);
        renderDetailAddresses(d.data);
      } else {
        document.getElementById("dt-profile-loading").textContent="No data";
        document.getElementById("dt-address-loading").textContent="No data";
      }
    }).catch(function(){
      document.getElementById("dt-profile-loading").textContent="Load failed";
      document.getElementById("dt-address-loading").textContent="Load failed";
    });
}

function closeUserDetail(e) {
  if(e && e.target !== e.currentTarget) return;
  var m = document.querySelector('.modal-overlay');
  if(m) m.remove();
}

function switchDetailTab(uid, tab){
  // Update tab styles
  var tabs = document.querySelectorAll('.dt-tab');
  for(var i=0;i<tabs.length;i++){
    tabs[i].style.color = 'var(--dim)';
    tabs[i].style.borderBottom = '2px solid transparent';
  }
  var activeTab = document.getElementById('dt-'+tab);
  if(activeTab){
    activeTab.style.color = 'var(--accent)';
    activeTab.style.borderBottom = '2px solid var(--accent)';
  }
  // Show/hide content
  var contents = document.querySelectorAll('.detail-tab-content');
  for(var i=0;i<contents.length;i++){
    contents[i].style.display = 'none';
  }
  var target = document.getElementById('dt-content-'+tab);
  if(target) target.style.display = 'block';
}

function renderDetailProfile(data){
  var p = data.profile || {};
  var cont = document.getElementById('dt-profile-loading');
  if(!cont) return;
  var genderMap = {'male':'Male','female':'Female','other':'Other','secret':'Confidential'};
  var ints = Array.isArray(p.interests) ? p.interests : [];
  var intTags = ints.length>0 ? ints.map(function(t){return '<span style="display:inline-block;background:var(--accent);color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;margin:2px">'+t+'</span>'}).join('') : '<span style="color:var(--dim)">None</span>';
  var h = '<div class="cd"><div class="st">Extended Profile</div>';
  h += '<div class="g2">';
  h += '<div><span style="color:var(--dim);font-size:11px">Gender</span><div style="font-size:13px">'+(genderMap[p.gender]||'Not Filled')+'</div></div>';
  h += '<div><span style="color:var(--dim);font-size:11px">Date of Birth</span><div style="font-size:13px">'+(p.birth_date||'Not Filled')+'</div></div>';
  h += '<div><span style="color:var(--dim);font-size:11px">Career</span><div style="font-size:13px">'+(p.occupation||'Not Filled')+'</div></div>';
  h += '<div><span style="color:var(--dim);font-size:11px">Industry</span><div style="font-size:13px">'+(p.industry||'Not Filled')+'</div></div>';
  h += '</div>';
  h += '<div style="margin-top:8px"><span style="color:var(--dim);font-size:11px">Interest Tags</span><div style="margin-top:4px">'+intTags+'</div></div>';
  if(p.bio) h += '<div style="margin-top:8px"><span style="color:var(--dim);font-size:11px">Bio</span><div style="font-size:13px;margin-top:4px;line-height:1.6">'+p.bio+'</div></div>';
  h += '</div>';
  cont.innerHTML = h;
}

function renderDetailAddresses(data){
  var addrs = data.addresses || [];
  var cont = document.getElementById('dt-address-loading');
  if(!cont) return;
  if(addrs.length===0){
    cont.innerHTML = '<div class="cd"><div class="st">Shipping Address</div><div style="color:var(--dim);font-size:13px;padding:12px">No Shipping Address for This User</div></div>';
    return;
  }
  var h = '<div class="cd"><div class="st">Shipping Address ('+addrs.length+')</div>';
  for(var i=0;i<addrs.length;i++){
    var a = addrs[i];
    var star = a.is_default ? ' ★' : '';
    h += '<div style="background:var(--bg2);border-radius:6px;padding:10px;margin-bottom:8px;'+(a.is_default?'border:1px solid var(--accent)':'border:1px solid var(--border)')+'">';
    h += '<div style="font-size:12px;color:var(--muted);margin:4px 0">'+a.province+a.city+a.district+' '+a.street_address+star+'</div>';
    if(a.postal_code) h += '<div style="font-size:11px;color:var(--dim)">Postal Code: '+a.postal_code+'</div>';
    h += '</div>';
  }
  h += '</div>';
  cont.innerHTML = h;
}

function uploadUserAvatar(uid) {
  var f = document.getElementById("userAvaFile");
  if(!f.files||!f.files[0]) return;
  var fd = new FormData();
  fd.append("avatar", f.files[0]);
  var status = document.getElementById("userAvaStatus");
  if(status) status.textContent="Uploading...";
  fetch("/admin/users/"+uid+"/avatar", {
    method:"POST", headers:{"Authorization":"Bearer "+T},
    body:fd
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) {
      showToast("Avatar updated","success");
      showUserDetail(uid);
    } else {
      showToast(d.error||"Upload failed","error");
      if(status) status.textContent = d.error||"Upload failed";
    }
  }).catch(function(){
    showToast("Upload request failed","error");
    if(status) status.textContent="Upload request failed";
  });
}

function uploadAgentAvatar(uid) {
  var f = document.getElementById("agentAvaFile");
  if(!f.files||!f.files[0]) return;
  var fd = new FormData();
  fd.append("avatar", f.files[0]);
  fetch("/admin/users/"+uid+"/agent-avatar", {
    method:"POST", headers:{"Authorization":"Bearer "+T},
    body:fd
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) {
      showToast("Agent avatar updated","success");
      showUserDetail(uid);
    } else {
      showToast(d.error||"Upload failed","error");
    }
  }).catch(function(){showToast("Upload request failed","error")});
}

function showDefaultAvatars(type, uid) {
  var gridId = type==='user' ? 'userDefaultGrid' : 'agentDefaultGrid';
  var innerId = type==='user' ? 'userDefaultGridInner' : 'agentDefaultGridInner';
  var grid = document.getElementById(gridId);
  var inner = document.getElementById(innerId);
  if(!grid || !inner) return;
  grid.style.display = grid.style.display==='none'?'block':'none';
  if(grid.style.display==='block' && !inner.children.length) {
    // ── Existing Static SVG Default Avatar ──
    loadAvatarDefaults(function(data){
      var items = type==='user' ? data.users : data.agents;
      inner.innerHTML = '';
      items.forEach(function(item){
        var img = document.createElement('img');
        img.src = item.url;
        img.style.cssText = 'width:48px;height:48px;border-radius:8px;cursor:pointer;object-fit:cover;border:2px solid transparent';
        img.title = item.filename;
        img.onmouseover = function(){this.style.borderColor='var(--accent)'};
        img.onmouseout = function(){this.style.borderColor='transparent'};
        img.onclick = function(){
          var endpoint = type==='user' ? '/admin/users/'+uid+'/avatar/default' : '/admin/users/'+uid+'/agent-avatar/default';
          fetch(endpoint, {
            method:"PUT", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
            body:JSON.stringify({default: item.filename})
          }).then(function(r){return r.json()}).then(function(d){
            if(d.success) { showToast("Default avatar set","success"); showUserDetail(uid); }
            else { showToast(d.error||"Set Failed","error"); }
          }).catch(function(){showToast("Request Failed","error")});
        };
        inner.appendChild(img);
      });
    });
    // ── DiceBear Style Selector ──
    var dbSection = document.createElement('div');
    dbSection.style.cssText = 'margin-top:10px;border-top:1px solid var(--border);padding-top:10px';
    dbSection.innerHTML = '<div class="st" style="font-size:12px;margin-bottom:6px">DiceBear Generate</div>' +
      '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px" id="dbStyles_'+type+'"></div>' +
      '<div style="display:flex;gap:8px;align-items:center" id="dbPreview_'+type+'"></div>';
    inner.parentNode.appendChild(dbSection);
    // Render Style Previews
    var dbStyles = ['initials','identicon','avataaars','lorelei'];
    var dbStyleLabels = {initials:'First Letter',identicon:'Geometric',avataaars:'Cartoon',lorelei:'Style'};
    var dbContainer = document.getElementById('dbStyles_'+type);
    var dbPreview = document.getElementById('dbPreview_'+type);
    if(!dbContainer || !dbPreview) return;
    // Get Seed
    var seed = document.querySelector('#userAvaPreview span, #userAvaPreview img') ? 'user' : 'agent';
    var seedVal = ''+ uid;
    // Get Seed from User Details
    var uNick = document.querySelector('#userAvaPreview')?.getAttribute('data-seed') || '';
    if(!uNick) {
      // Try to Get from Currently Displayed User Info
      var modalTitle = document.querySelector('.modal-box h3');
      if(modalTitle) {
        var parts = modalTitle.textContent.match(/—\s*(.+)/);
        if(parts) seedVal = parts[1].trim();
      }
    }
    dbStyles.forEach(function(style){
      var btn = document.createElement('button');
      btn.className = 'btn bo';
      btn.textContent = dbStyleLabels[style];
      btn.style.cssText = 'padding:3px 10px;font-size:11px';
      btn.onclick = function(){
        // Preview Generation
        dbPreview.innerHTML = '';
        var sizes = [28, 46, 72];
        sizes.forEach(function(s){
          var wrap = document.createElement('div');
          wrap.style.cssText = 'display:inline-flex;flex-direction:column;align-items:center;gap:4px';
          wrap.innerHTML = dicebearAvatar(seedVal, style, s) +
            '<span style="font-size:9px;color:var(--dim)">'+s+'px</span>';
          dbPreview.appendChild(wrap);
        });
        // Apply Button
        var applyBtn = document.createElement('button');
        applyBtn.className = 'btn bp';
        applyBtn.textContent='Apply '+dbStyleLabels[style];
        applyBtn.style.cssText = 'padding:4px 12px;font-size:11px;margin-left:8px';
        applyBtn.onclick = function(){
          // Generate SVG → Upload
          var avatar = window.dicebear.createAvatar(window.dicebear.styles[style], {
            seed: seedVal, size: 256, backgroundColor: 'transparent'
          });
          var svgStr = avatar.toString();
          var blob = new Blob([svgStr], {type: 'image/svg+xml'});
          var file = new File([blob], 'dicebear_'+style+'.svg', {type: 'image/svg+xml'});
          var fd = new FormData();
          fd.append('avatar', file);
          var endpoint = type==='user' ? '/admin/users/'+uid+'/avatar' : '/admin/users/'+uid+'/agent-avatar';
          fetch(endpoint, {method:'POST', headers:{"Authorization":"Bearer "+T}, body:fd})
            .then(function(r){return r.json()}).then(function(d){
              if(d.success) { showToast("DiceBear avatar set","success"); showUserDetail(uid); }
              else { showToast(d.error||"Set Failed","error"); }
            }).catch(function(){showToast("Request Failed","error")});
        };
        dbPreview.appendChild(applyBtn);
      };
      dbContainer.appendChild(btn);
    });
  }
}

function removeUserAvatar(uid) {
  if(!confirm("Remove user avatar?")) return;
  fetch("/admin/users/"+uid+"/avatar/clear", {
    method:"POST", headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) { showToast("Avatar removed","success"); showUserDetail(uid); }
    else { showToast(d.error||"Operation Failed","error"); }
  }).catch(function(){showToast("Request Failed","error")});
}

function removeAgentAvatar(uid) {
  if(!confirm("Remove agent avatar?")) return;
  fetch("/admin/users/"+uid+"/agent-avatar/clear", {
    method:"POST", headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success) { showToast("Agent avatar removed","success"); showUserDetail(uid); }
    else { showToast(d.error||"Operation Failed","error"); }
  }).catch(function(){showToast("Request Failed","error")});
}


window.l_customers=function(){
  document.getElementById("pt").innerHTML="All Customers";
  var url="/admin/customers?limit=100";
  fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var ds=d.data;
    var h='<div class="cd">';
    h+='<div class="st" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px">';
    h+='<span style="font-size:12px">Customer List ('+ds.total+')</span>';
    h+='<input type="text" id="cSearch" placeholder="Search..." onchange="l_customers()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:11px;width:150px">';
    h+='<select id="cType" onchange="l_customers()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:11px"><option value="">All Types</option><option value="enterprise">Enterprise</option><option value="individual">Individual</option></select>';
    h+='<select id="cVerify" onchange="l_customers()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:11px"><option value="">All Verification Status</option><option value="verified">Verified</option><option value="unverified">Unverified</option></select>';
    h+='</div>';
    h+='<table><tr><th>ID</th><th>Nickname</th><th>Phone</th><th>Email</th><th>Certification</th><th>Company Name</th><th>Plan</th><th>Status</th><th>Registered</th></tr>';
    (ds.customers||[]).forEach(function(c){
      var st=c.active?'<span class="bdg on">Active</span>':'<span class="bdg off">Disabled</span>';
      var badge='<span class="bdg '+(c.cert_status==='enterprise'?'on':c.cert_status==='individual'?'bp':'dim')+'">'+esc(c.cert_badge)+'</span>';
      h+='<tr class="c" onclick="showCustomerDetail('+c.id+')"><td>'+c.id+'</td><td>'+esc(c.nickname||'-')+'</td><td>'+(c.phone||'-')+'</td><td>'+(c.email||'-')+'</td><td>'+badge+'</td><td>'+(c.enterprise_name?'<span class="t" title="'+esc(c.enterprise_name)+'">'+esc(c.enterprise_name.substring(0,12))+'…</span>':'-')+'</td><td>'+(c.plan_key||'free')+'</td><td>'+st+'</td><td style="font-size:11px">'+(c.created_at||'')+'</td></tr>';
    });
    h+="</table></div>";
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){document.getElementById("mc").innerHTML='<div class="em">Load failed，Please try again later</div>'})
}

function showCustomerDetail(uid){
  fetch("/admin/users/"+uid,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var u=d.data;
    var h='<div class="cd">';
    h+='<div class="st" style="display:flex;justify-content:space-between"><span>Customer Details</span> <span class="btn bo bs" style="padding:2px 8px;font-size:11px" onclick="l_customers()">← Back</span></div>';
    h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;font-size:12px">';
    h+='<div><b>User ID:</b> '+u.id+'</div>';
    h+='<div><b>Nickname:</b> '+(u.nickname||'-')+'</div>';
    h+='<div><b>Phone:</b> '+(u.phone||'-')+'</div>';
    h+='<div><b>Email:</b> '+(u.email||'-')+'</div>';
    h+='<div><b>Verification Status:</b> '+(u.verified_by?'<span class="bdg on">'+esc(u.verified_by)+'</span>':'<span class="bdg dim">Unverified</span>')+'</div>';
    h+='<div><b>Created:</b> '+(u.created_at||'')+'</div>';
    if(u.enterprise_name){
      h+='<div style="grid-column:1/-1;border-top:1px solid var(--border);padding-top:8px;margin-top:8px"><b>Enterprise Info</b></div>';
      h+='<div><b>Company Name:</b> '+esc(u.enterprise_name)+'</div>';
      h+='<div><b>Tax ID:</b> '+esc(u.enterprise_tax_id||'-')+'</div>';
      h+='<div style="grid-column:1/-1">';
      if(u.enterprise_verified){
        h+='<span class="bdg on">Enterprise Verified</span>';
      }else{
        h+='<span class="bdg dim">Enterprise Verification Pending</span>';
      }
      h+='</div>';
    }
    h+='</div></div>';
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){document.getElementById("mc").innerHTML='<div class="em">Load failed，Please try again later</div>'})
}


window.l_enterprise_verify=function(){
  document.getElementById("pt").innerHTML="Enterprise Verification";
  var status=document.getElementById("evStatus")?document.getElementById("evStatus").value:'pending';
  var url="/admin/enterprise-verifications?status="+status+"&limit=100";
  fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var ds=d.data;
    var h='<div class="cd">';
    h+='<div class="st" style="display:flex;align-items:center;gap:8px;margin-bottom:8px">';
    h+='<span style="font-size:12px">Enterprise Verification Review</span>';
    h+='<select id="evStatus" onchange="l_enterprise_verify()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:3px 6px;font-size:11px"><option value="pending" '+(status==='pending'?'selected':'')+' >Pending Review</option><option value="approved" '+(status==='approved'?'selected':'')+' >Approved</option><option value="rejected" '+(status==='rejected'?'selected':'')+' >Rejected</option></select>';
    h+='</div>';
    if(!ds.verifications||ds.verifications.length===0){
      h+='<div style="padding:20px;text-align:center;color:var(--dim);font-size:12px">No verification records</div></div>';
      document.getElementById("mc").innerHTML=h;return;
    }
    h+='<table><tr><th>ID</th><th>User</th><th>Company Name</th><th>Tax ID</th><th>Business License</th><th>Submitted</th><th>Notes</th><th>Actions</th></tr>';
    ds.verifications.forEach(function(ev){
      h+='<tr><td>'+ev.id+'</td><td>'+(ev.display_name||ev.phone||ev.user_id)+'</td><td>'+esc(ev.enterprise_name)+'</td><td>'+esc(ev.tax_id)+'</td>';
      h+='<td>'+(ev.license_url?'<a href="'+escAttr(ev.license_url)+'" target="_blank" class="btn bo bs" style="padding:2px 6px;font-size:10px">View</a>':'-')+'</td>';
      h+='<td style="font-size:11px">'+(ev.created_at||'')+'</td>';
      h+='<td>'+(ev.review_notes?esc(ev.review_notes):'-')+'</td>';
      h+='<td>';
      if(ev.status==='pending'){
        h+='<span class="btn bp" style="padding:2px 8px;font-size:10px" onclick="approveEnterpriseVerify('+ev.id+')">Approve</span> ';
        h+='<span class="btn br" style="padding:2px 8px;font-size:10px" onclick="rejectEnterpriseVerify('+ev.id+')">Reject</span>';
      }else{
        h+='<span class="bdg '+(ev.status==='approved'?'on':'off')+'">'+(ev.status==='approved'?'Approved':'Rejected')+'</span>';
      }
      h+='</td></tr>';
    });
    h+="</table></div>";
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){
    document.getElementById("mc").innerHTML='<div class="em">Load failed</div>';
  })
}

function approveEnterpriseVerify(evId){
  var notes=prompt("Review Notes (optional)：");
  if(notes===null)return;
  fetch("/admin/enterprise-verifications/"+evId+"/approve",{
    method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({notes:notes||''})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast(d.message||"Approved","success");l_enterprise_verify()}
    else{showToast(d.error||"Operation Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function rejectEnterpriseVerify(evId){
  var notes=prompt("Please enter the rejection reason：");
  if(!notes||!notes.trim()){showToast("Please enter a reason for rejection","error");return;}
  fetch("/admin/enterprise-verifications/"+evId+"/reject",{
    method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({notes:notes.trim()})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast(d.message||"Rejected","success");l_enterprise_verify()}
    else{showToast(d.error||"Operation Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}


window.l_customer_agents=function(){
  window.l_agents();
}

window.l_api_keys=function(){
  window.l_keys();
}


window.l_agents=function(){
  document.getElementById("pt").textContent="Agent Management";
  var h='<div class="cd"><div class="st" style="display:flex;justify-content:space-between;align-items:center">Agent List <span style="font-weight:400;font-size:11px;color:var(--dim)" id="uaTotal">Loading......</span></div>';
  h+='<div style="margin-bottom:12px;display:flex;gap:8px">';
  h+='<input id="uaSearch" placeholder="Search Name/User..." style="flex:1;padding:6px 10px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text);font-size:12px">';
  h+='<select id="uaStatusFilter" style="padding:6px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text);font-size:12px"><option value="">All Status</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="suspended">Pause</option></select>';
  h+='<span class="btn bp" style="padding:6px 12px;font-size:12px" onclick="loadUserAgents()">🔍 Search</span>';
  h+='</div>';
  h+='<div id="uaList"><div class="lo"><div class="s"></div>Loading......</div></div></div>';
  document.getElementById("mc").innerHTML=h;
  loadUserAgents();
}

function loadUserAgents(){
  var list=document.getElementById("uaList");
  if(!list)return;
  list.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  var search=document.getElementById("uaSearch")?.value||'';
  var status=document.getElementById("uaStatusFilter")?.value||'';
  var url='/admin/user-agents?limit=200';
  if(search)url+='&search='+encodeURIComponent(search);
  if(status)url+='&status='+status;
  fetch(url,{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data){list.innerHTML='<div class="em">Load failed</div>';return}
      var totalEl=document.getElementById("uaTotal");
      if(totalEl)totalEl.textContent='Total: '+d.data.total+' 个 Agent';
      var agents=d.data.agents||[];
      if(agents.length===0){list.innerHTML='<div class="em">None Agent Data</div>';return}
      var h='&lt;table&gt;&lt;tr&gt;&lt;th&gt;ID&lt;/th&gt;&lt;th&gt;Name&lt;/th&gt;&lt;th&gt;User&lt;/th&gt;&lt;th&gt;Type&lt;/th&gt;&lt;th&gt;Status&lt;/th&gt;&lt;th&gt;Keys&lt;/th&gt;&lt;th&gt;Last Active&lt;/th&gt;&lt;th&gt;Created&lt;/th&gt;&lt;/tr&gt;';
      agents.forEach(function(a){
        var stCls=a.status==='active'?'bdg on':(a.status==='suspended'?'bdg pd':'bdg off');
        var stText=a.status==='active'?'Active':(a.status==='suspended'?'Pause':'Inactive');
        h+='<tr><td>'+a.id+'</td><td>'+escAttr(a.agent_name)+'</td>';
        h+='<td><a href="#" onclick="go(&#39;users&#39;);setTimeout(function(){toggleUserAgents('+a.user_id+',document.querySelector(&#39;#ua-row-'+a.user_id+' .btn&#39;))},500)" style="color:var(--accent);text-decoration:none">'+(a.user_name||'#'+a.user_id)+'</a></td>';
        h+='<td>'+a.agent_type+'</td><td><span class="'+stCls+'">'+stText+'</span></td>';
        // Count agent api keys (not available in list, show '-')
        h+='<td>-</td>';
        h+='<td>'+(a.last_active_at||'-')+'</td><td>'+(a.created_at||'')+'</td></tr>';
      });
      h+='</table>';
      list.innerHTML=h;
    }).catch(function(){list.innerHTML='<div class="em">Request Failed</div>'});
}


window.l_keys=function(){
  document.getElementById("pt").textContent="API Key Management";
  fetch("/admin/api-keys?limit=100",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var ds=d.data;
    var h="<div class=\"cd\"><div class=\"st\">Global Key ("+ds.total+")</div><table><tr><th>Name</th><th>Key</th><th>User</th><th>Call</th><th>Status</th><th>Time</th></tr>";
    ds.keys.forEach(function(k){
      var st=k.active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Promoted</span>';
      h+="<tr><td>"+(k.name||"-")+"</td><td>"+k.key_prefix+"...</td><td>"+(k.user_name||"-")+"</td><td>"+k.calls_total+"</td><td>"+st+"</td><td>"+(k.created_at||"")+"</td></tr>";
    });
    h+="</table></div>";
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){document.getElementById("mc").innerHTML='<div class="em">Load failed，Please try again later</div>'})
}


window.l_posts=function(){
  document.getElementById("pt").textContent="Community Content";
  fetch("/admin/posts?limit=100",{headers:{"Authorization":"Bearer "+T}}).then(function(r){
    if(!r.ok)throw new Error("HTTP "+r.status);
    return r.json()
  }).then(function(d){
    if(!d.success||!d.data)throw new Error(d.error||"Data Error");
    var ds=d.data;
    var h="<div class=\"cd\"><div class=\"st\">Post ("+ds.total+")</div>";
    if(ds.posts.length===0){
      h+="<div class=\"lo\" style=\"padding:40px;color:var(--dim)\">No Posts — Community Content Will Agent Experience System Auto-Aggregates</div>";
    }else{
      h+="<table><tr><th>Title</th><th>Agent</th><th>Status</th><th>Like</th><th>Time</th></tr>";
      ds.posts.forEach(function(p){
        var st=p.status=="approved"?'<span class=\"bdg on\">Published</span>':(p.status=="pending"?'<span class=\"bdg pd\">Pending Review</span>':'<span class=\"bdg off\">Draft</span>');
        h+="<tr><td>"+(p.title||"-")+"</td><td>"+(p.agent_id||"-")+"</td><td>"+st+"</td><td>"+p.like_count+"</td><td>"+(p.created_at||"")+"</td></tr>";
      });
      h+="</table>";
    }
    h+="</div>";
    document.getElementById("mc").innerHTML=h;
  }).catch(function(e){
    document.getElementById("mc").innerHTML='<div class=\"cd\"><div class=\"em\">Load failed: '+(e.message||"Unknown Error")+' — <a href=\"javascript:l_posts()\">Retry</a></div></div>';
  })
}

// l_contacts removed (merged into l_tickets)

// ============================
// User Tickets — l_tickets（Pre-Sales Included/After-Sales/Complaint/Suggestion Category Filter）
// ============================
var _ticketFilter='';
var _ticketTypeFilter='';
var _ADM_TYPE_LABELS={presale:'\u{1f7e2} Pre-Sales',aftersale:'\u{1f7e1} After-Sales',complaint:'\u{1f534} Complaint',suggestion:'\u{1f7e3} Suggestion'};
var _ADM_TYPE_COLORS={presale:'#3b82f6',aftersale:'#f59e0b',complaint:'#ef4444',suggestion:'#8b5cf6'};

window.l_tickets=function(){
  document.getElementById("pt").textContent="User Tickets";
  ticketLoadList();
}
function ticketLoadList(){
  var url="/admin/tickets";
  var params=[];
  if(_ticketFilter)params.push("status="+_ticketFilter);
  if(_ticketTypeFilter)params.push("type="+_ticketTypeFilter);
  if(params.length)url+="?"+params.join("&");
  fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var h='<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap">';
    // Status Filter Row
    h+='<button class="btn btn-sm'+(d.open>0&&!_ticketFilter?' bp':'')+'" onclick="_ticketFilter=&#39;open&#39;;ticketLoadList()">Pending ('+(d.open||0)+')</button>';
    h+='<button class="btn btn-sm'+(d.replied!=null?'':'')+'" onclick="_ticketFilter=&#39;replied&#39;;ticketLoadList()">Replied ('+(d.replied||0)+')</button>';
    h+='<button class="btn btn-sm" onclick="_ticketFilter=&#39;&#39;;ticketLoadList()">All ('+(d.total||0)+')</button>';
    h+='<span style="color:var(--border);margin:0 4px">|</span>';
    // Type Filter Row
    h+='<button class="btn btn-sm'+(d.total!=null&&!_ticketTypeFilter?' bp':'')+'" onclick="_ticketTypeFilter=&#39;&#39;;ticketLoadList()">All Types</button>';
    ['presale','aftersale','complaint','suggestion'].forEach(function(tp){
      var cnt=d['cnt_'+tp]||0;
      h+='<button class="btn btn-sm'+(d.data&&_ticketTypeFilter===tp?' bp':'')+'" onclick="_ticketTypeFilter=&#39;'+tp+'&#39;;ticketLoadList()" style="color:'+_ADM_TYPE_COLORS[tp]+'">'+_ADM_TYPE_LABELS[tp]+' ('+cnt+')</button>';
    });
    h+='</div>';
    h+='<div class="cd"><div class="st">Tickets ('+d.data.length+')</div><table><tr><th>Type</th><th>User</th><th>Title</th><th>Status</th><th>Time</th><th>Actions</th></tr>';
    d.data.forEach(function(t){
      var u=t.username||t.phone||'User#'+t.user_id;
      var tl=_ADM_TYPE_LABELS[t.type]||'After-Sales';
      var tc=_ADM_TYPE_COLORS[t.type]||'#888';
      var tpBadge='<span style="display:inline-block;padding:2px 6px;border-radius:3px;font-size:10px;background:'+tc+'22;color:'+tc+';border:1px solid '+tc+'44;white-space:nowrap">'+tl+'</span>';
      var prioMark=t.priority==='high'?' <span style="color:#ef4444;font-size:10px">\u{1f534}</span>':'';
      var sb=t.status==='open'?'<span class="bdg pd">Pending</span>':t.status==='replied'?'<span class="bdg on">Replied</span>':'<span class="bdg">Closed</span>';
      var tm=(t.created_at||'').replace('T',' ').slice(0,16);
      h+='<tr><td>'+tpBadge+prioMark+'</td><td>'+eschtml(u)+'</td><td style="cursor:pointer" onclick="ticketAdminToggle(event,'+t.id+')">'+eschtml(t.title)+'</td><td>'+sb+'</td><td>'+tm+'</td><td>';
      h+='<button class="btn btn-sm" onclick="ticketAdminToggle(event,'+t.id+')">Details</button></td></tr>';
      h+='<tr id="ticketRow'+t.id+'" style="display:none"><td colspan="6" style="background:var(--bg2,#111);padding:16px">';
      h+='<div style="margin-bottom:4px;color:var(--dim);font-size:11px">'+tpBadge+' | '+eschtml(t.category||'')+'</div>';
      h+='<div style="margin-bottom:8px;color:var(--muted)"><b>User：</b>'+eschtml(u)+(t.contact?' <span style="color:var(--dim);font-size:11px">Contact: '+eschtml(t.contact)+'</span>':'')+'</div>';
      h+='<div style="margin-bottom:12px;white-space:pre-wrap;font-size:13px">'+eschtml(t.content||'')+'</div>';
      if(t.admin_reply){
        h+='<div style="background:rgba(34,211,238,.06);border-left:2px solid var(--accent2);padding:10px 12px;border-radius:4px;margin-bottom:12px;font-size:13px"><b style="color:var(--accent2)">Admin Reply：</b><br>'+eschtml(t.admin_reply)+'<br><span style="font-size:10px;color:var(--dim)">'+(t.replied_at||'').replace('T',' ').slice(0,16)+'</span></div>';
      }
      if(t.status!=='closed'){
        h+='<div style="display:flex;gap:8px;align-items:flex-start"><textarea id="ticketReply'+t.id+'" rows="2" placeholder="Enter Reply..." style="flex:1;padding:8px;border-radius:6px;border:1px solid var(--border);background:rgba(0,0,0,.3);color:var(--text);font-size:13px;font-family:inherit;resize:vertical"></textarea>';
        h+='<div style="display:flex;flex-direction:column;gap:4px"><button class="btn btn-sm bp" onclick="ticketAdminReply('+t.id+')">Reply</button>';
        h+='<button class="btn btn-sm" onclick="ticketAdminAction('+t.id+',&#39;close&#39;)">Close</button></div></div>';
      }else{
        h+='<button class="btn btn-sm" onclick="ticketAdminAction('+t.id+',&#39;reopen&#39;)">Reopen</button>';
      }
      h+='</td></tr>';
    });
    h+='</table></div>';
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){document.getElementById("mc").innerHTML='<div class="em">Load failed</div>'});
}
function ticketAdminToggle(e,tid){
  e.stopPropagation();
  var row=document.getElementById('ticketRow'+tid);
  if(row)row.style.display=row.style.display==='none'?'':'none';
}
function ticketAdminReply(tid){
  var reply=document.getElementById('ticketReply'+tid).value.trim();
  if(!reply){alert('Enter Reply Content');return}
  fetch('/admin/tickets/'+tid,{method:'PUT',headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({action:'reply',admin_reply:reply})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success)ticketLoadList();else alert('Failed: '+(d.error||''));
    }).catch(function(){alert('Request Failed')});
}
function ticketAdminAction(tid,action){
  fetch('/admin/tickets/'+tid,{method:'PUT',headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({action:action})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success)ticketLoadList();else alert('Failed: '+(d.error||''));
    }).catch(function(){alert('Request Failed')});
}
function eschtml(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

// Complaint/Suggestion Merged into User Ticket

// ============================
// Channel Management — l_channels
// ============================
var _chCurrentTab='feishu';
var _chSecrets={}; // {feishu: {app_secret: 'real', ...}}

function _chToggleSecret(ch, key){
  var el=document.getElementById('ch-f-'+ch+'-'+key);
  if(!el)return;
  var isMasked=el.type==='password';
  el.type=isMasked?'text':'password';
  var btn=document.getElementById('ch-f-'+ch+'-'+key+'-btn');
  if(btn)btn.textContent=isMasked?'Hide':'Show';
}

function _chLoadTab(ch){
  _chCurrentTab=ch;
  // tab Highlight
  document.querySelectorAll('.ch-tab').forEach(function(t){t.classList.remove('sel')});
  var tabEl=document.getElementById('ch-tab-'+ch);
  if(tabEl)tabEl.classList.add('sel');

  if(ch==='wecom'){ _wcLoadTab(); return; }
  _chLoadGenericTab(ch);
}

function _chLoadGenericTab(ch){
  var labelMap={feishu:'Feishu',qq:'QQ',dingtalk:'DingTalk'};
  var channelLabel=labelMap[ch]||ch;
  document.getElementById('ch-body').innerHTML='<div class="lo">'+esc(channelLabel)+'Config Loading...</div>';
  fetch('/admin/channels/'+ch,{headers:{'Authorization':'Bearer '+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){
      document.getElementById('ch-body').innerHTML='<div class="cd"><div class="em">Load failed: '+(d.error||'Unknown Error')+'</div></div>';
      return;
    }
    var cfg=d.data.config||{};
    var env=d.data.from_env||{};
    var isOn=d.data.is_enabled===1;

    var h='';
    h+='<div class="cdf"><label class="srv"><input type="checkbox" id="ch-enable" onchange="_chToggleEnable()"'+(isOn?' checked':'')+'><span>Enabled'+esc(channelLabel)+'Integration</span></label></div>';

    if(env&&Object.keys(env).length>0){
      h+='<div class="inf" style="margin:12px 0;padding:10px 14px;background:rgba(0,245,255,0.06);border-left:3px solid var(--cyan);border-radius:6px;font-size:13px;color:#8b8b8b;">';
      h+='<div style="color:var(--cyan);margin-bottom:6px;">Currently Read from Env Vars（Not Saved to Database）</div>';
      Object.keys(env).forEach(function(k){
        h+='<div style="margin:2px 0"><code style="color:#e0e0e0">'+esc(k)+'</code>: '+esc(env[k])+'</div>';
      });
      h+='</div>';
    }else if(isOn){
      h+='<div class="inf" style="margin:12px 0;padding:10px 14px;background:rgba(0,255,159,0.06);border-left:3px solid var(--green);border-radius:6px;font-size:13px;color:#8b8b8b;">';
      h+='<span style="color:var(--green)">Saved to Database</span> — '+esc(channelLabel)+'Config Reads DB First';
      h+='</div>';
    }

    h+='<div class="cdf">';
    // Official Field Set per Channel（Extensible）
    var fieldsMap={
      feishu:[
        ['app_id','App ID','text',cfg.app_id||env.app_id||''],
        ['app_secret','App Secret','password',cfg.app_secret||''],
        ['admin_open_id','Admin Open ID','text',cfg.admin_open_id||env.admin_open_id||''],
        ['verification_token','Verification Token','password',cfg.verification_token||''],
        ['encrypt_key','Encrypt Key','password',cfg.encrypt_key||''],
      ],
      wecom:[
        ['corp_id','Enterprise ID','text',cfg.corp_id||env.corp_id||''],
        ['agent_id','AgentId','text',cfg.agent_id||env.agent_id||''],
        ['secret','Secret','password',cfg.secret||''],
        ['touser','Default Recipient','text',cfg.touser||env.touser||''],
        ['token','Callback Token','password',cfg.token||''],
        ['encoding_aes_key','EncodingAESKey','password',cfg.encoding_aes_key||''],
      ],
      qq:[
        // QQ Apply/Common Bot Fields：app_id/app_key（Adjustable per Actual Scenario）
        ['app_id','App ID','text',cfg.app_id||env.app_id||''],
        ['app_key','App Key','password',cfg.app_key||''],
        ['admin_uin','Admin UIN','text',cfg.admin_uin||env.admin_uin||''],
      ],
      dingtalk:[
        // Common DingTalk Custom App Fields：app_key/app_secret/agent_id
        ['app_key','AppKey','text',cfg.app_key||env.app_key||''],
        ['app_secret','AppSecret','password',cfg.app_secret||''],
        ['agent_id','AgentId','text',cfg.agent_id||env.agent_id||''],
        ['corp_id','CorpId','text',cfg.corp_id||env.corp_id||''],
      ]
    };
    var fields=fieldsMap[ch]||[
      ['app_id','App ID','text',cfg.app_id||env.app_id||''],
      ['app_secret','App Secret','password',cfg.app_secret||''],
    ];
    fields.forEach(function(f){
      var key=f[0], label=f[1], type=f[2], val=f[3];
      h+='<label style="display:block;margin-bottom:14px">';
      h+='<div style="font-size:13px;color:#8b8b8b;margin-bottom:5px">'+esc(label)+'</div>';
      h+='<div style="display:flex;gap:8px;align-items:center">';
      h+='<input type="'+type+'" id="ch-f-'+ch+'-'+key+'" value="'+escAttr(val)+'" class="in" style="flex:1;min-width:0" placeholder="'+(type==='password'?'Not Set':'')+'">';
      if(type==='password'){
        h+='<button id="ch-f-'+ch+'-'+key+'-btn" class="btn bs" onclick="_chToggleSecret(\''+ch+'\',\''+key+'\')" style="white-space:nowrap">Show</button>';
      }
      h+='</div></label>';
    });
    h+='</div>';

    h+='<div class="cdf" style="margin-top:20px;display:flex;gap:10px;flex-wrap:wrap">';
    h+='<button class="btn bp" onclick="_chSave()">Save Config</button>';
    if(ch==='feishu'){
      h+='<button class="btn bs" onclick="_chTest()">Test Feishu Connection</button>';
    }else{
      h+='<button class="btn bs" disabled style="opacity:0.5;cursor:not-allowed">Test Not Supported Yet</button>';
    }
    h+='</div>';
    h+='<div id="ch-msg" style="margin-top:12px"></div>';

    document.getElementById('ch-body').innerHTML=h;
    _chSecrets[ch]=_chSecrets[ch]||{};
    if(cfg.app_secret)_chSecrets[ch].app_secret=cfg.app_secret;
    if(cfg.verification_token)_chSecrets[ch].verification_token=cfg.verification_token;
  }).catch(function(){
    document.getElementById('ch-body').innerHTML='<div class="cd"><div class="em">Request Failed</div></div>';
  })
}

function _chToggleEnable(){
  // handled at save time
}

function _chGetValue(key){
  var el=document.getElementById('ch-f-'+_chCurrentTab+'-'+key);
  return el?el.value.trim():'';
}

function _chSave(){
  if(_chCurrentTab==='wecom'){ _wcSave(); return; }
  var config={};
  ['app_id','app_secret','admin_open_id','verification_token','encrypt_key'].forEach(function(k){
    var v=_chGetValue(k);
    if(v.indexOf('●')>=0){
      if(_chSecrets[_chCurrentTab]&&_chSecrets[_chCurrentTab][k])v=_chSecrets[_chCurrentTab][k];
      else v='';
    }
    config[k]=v;
  });
  var enabled=document.getElementById('ch-enable')?document.getElementById('ch-enable').checked:false;
  var body={config:config,is_enabled:enabled};

  var msg=document.getElementById('ch-msg');
  msg.innerHTML='<span style="color:var(--cyan)">Saving...</span>';

  fetch('/admin/channels/'+_chCurrentTab,{
    method:'PUT',
    headers:{'Authorization':'Bearer '+T,'Content-Type':'application/json'},
    body:JSON.stringify(body)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      msg.innerHTML='<span style="color:var(--green)">'+esc(d.message||'Saved')+'</span>';
      _chSecrets[_chCurrentTab]={};
      ['app_secret','verification_token'].forEach(function(k){
        var v=_chGetValue(k);
        if(v&&v.indexOf('●')<0)_chSecrets[_chCurrentTab][k]=v;
      });
    }else{
      msg.innerHTML='<span style="color:var(--rose)">'+esc(d.error||'Save failed')+'</span>';
    }
  }).catch(function(e){
    msg.innerHTML='<span style="color:var(--rose)">Network error</span>';
  })
}

function _chTest(){
  if(_chCurrentTab!=='feishu'){
    alert('Current Channel Does Not Support Test');
    return;
  }
  var appId=_chGetValue('app_id');
  var appSecret=_chGetValue('app_secret');
  if(appSecret.indexOf('●')>=0){
    if(_chSecrets[_chCurrentTab]&&_chSecrets[_chCurrentTab].app_secret)appSecret=_chSecrets[_chCurrentTab].app_secret;
    else{alert('Please Enter First App Secret Save Then Test');return}
  }
  if(!appId||!appSecret){alert('App ID 和 App Secret Required');return}
  var msg=document.getElementById('ch-msg');
  msg.innerHTML='<span style="color:var(--cyan)">Testing...</span>';

  fetch('/admin/channels/'+_chCurrentTab+'/test',{
    method:'POST',
    headers:{'Authorization':'Bearer '+T,'Content-Type':'application/json'},
    body:JSON.stringify({app_id:appId,app_secret:appSecret})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      msg.innerHTML='<span style="color:var(--green)">'+esc(d.message||'Connection Successful')+'</span>';
    }else{
      msg.innerHTML='<span style="color:var(--rose)">'+esc(d.error||'Connection Failed')+'</span>';
    }
  }).catch(function(e){
    msg.innerHTML='<span style="color:var(--rose)">Network error</span>';
  })
}

// ============================
// WeCom Tab Helper Function
// ============================
function _wcToggleSecret(key){
  var el=document.getElementById('wc-f-'+key);
  if(!el)return;
  var isMasked=el.type==='password';
  el.type=isMasked?'text':'password';
  var btn=document.getElementById('wc-f-'+key+'-btn');
  if(btn)btn.textContent=isMasked?'Hide':'Show';
}

function _wcLoadTab(){
  document.getElementById('ch-body').innerHTML='<div class="lo">WeCom Config Loading...</div>';
  fetch('/admin/channels/wecom',{headers:{'Authorization':'Bearer '+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){
      document.getElementById('ch-body').innerHTML='<div class="cd"><div class="em">Load failed: '+(d.error||'Unknown Error')+'</div></div>';
      return;
    }
    var cfg=d.data.config||{};
    var env=d.data.from_env||{};
    var isOn=d.data.is_enabled===1;

    var h='';
    h+='<div class="cdf"><label class="srv"><input type="checkbox" id="wc-enable" onchange="_wcToggleEnable()"'+(isOn?' checked':'')+'><span>Enable WeCom Integration</span></label></div>';

    if(env&&Object.keys(env).length>0){
      h+='<div class="inf" style="margin:12px 0;padding:10px 14px;background:rgba(0,245,255,0.06);border-left:3px solid var(--cyan);border-radius:6px;font-size:13px;color:#8b8b8b;">';
      h+='<div style="color:var(--cyan);margin-bottom:6px;">Currently Read from Env Vars（Not Saved to Database）</div>';
      Object.keys(env).forEach(function(k){
        h+='<div style="margin:2px 0"><code style="color:#e0e0e0">'+esc(k)+'</code>: '+esc(env[k])+'</div>';
      });
      h+='</div>';
    }else if(isOn){
      h+='<div class="inf" style="margin:12px 0;padding:10px 14px;background:rgba(0,255,159,0.06);border-left:3px solid var(--green);border-radius:6px;font-size:13px;color:#8b8b8b;">';
      h+='<span style="color:var(--green)">Saved to Database</span> — wecom.py Priority Read from DB Settings';
      h+='</div>';
    }

    h+='<div class="cdf">';
    var fields=[
      ['corp_id','Enterprise ID','text',cfg.corp_id||env.corp_id||''],
      ['agent_id','AgentId','text',cfg.agent_id||env.agent_id||''],
      ['secret','Secret','password',cfg.secret||''],
      ['touser','Default Recipient','text',cfg.touser||env.touser||''],
      ['token','Callback Token','password',cfg.token||''],
      ['encoding_aes_key','EncodingAESKey','password',cfg.encoding_aes_key||''],
    ];
    fields.forEach(function(f){
      var key=f[0], label=f[1], type=f[2], val=f[3];
      h+='<label style="display:block;margin-bottom:14px">';
      h+='<div style="font-size:13px;color:#8b8b8b;margin-bottom:5px">'+esc(label)+'</div>';
      h+='<div style="display:flex;gap:8px;align-items:center">';
      h+='<input type="'+type+'" id="wc-f-'+key+'" value="'+escAttr(val)+'" class="in" style="flex:1;min-width:0" placeholder="'+(type==='password'?'Not Set':'')+'">';
      if(type==='password'){
        h+='<button id="wc-f-'+key+'-btn" class="btn bs" onclick="_wcToggleSecret(\''+key+'\')" style="white-space:nowrap">Show</button>';
      }
      h+='</div></label>';
    });
    h+='</div>';

    h+='<div class="cdf" style="margin-top:20px;display:flex;gap:10px;flex-wrap:wrap">';
    h+='<button class="btn bp" onclick="_wcSave()">Save Config</button>';
    h+='<button class="btn bs" onclick="_wcTest()">Test WeCom Connection</button>';
    h+='</div>';
    h+='<div id="wc-msg" style="margin-top:12px"></div>';

    document.getElementById('ch-body').innerHTML=h;

    if(cfg.secret)_wcSecrets.wecom={secret:cfg.secret};
    if(cfg.token)_wcSecrets.wecom=_wcSecrets.wecom||{};
    if(cfg.token)_wcSecrets.wecom.token=cfg.token;
    if(cfg.encoding_aes_key)_wcSecrets.wecom=_wcSecrets.wecom||{};
    if(cfg.encoding_aes_key)_wcSecrets.wecom.encoding_aes_key=cfg.encoding_aes_key;
  }).catch(function(e){
    document.getElementById('ch-body').innerHTML='<div class="cd"><div class="em">Network error: '+e.message+'</div></div>';
  })
}

function _wcToggleEnable(){}

function _wcGetValue(key){
  var el=document.getElementById('wc-f-'+key);
  return el?el.value.trim():'';
}

function _wcSave(){
  var config={};
  ['corp_id','agent_id','secret','touser','token','encoding_aes_key'].forEach(function(k){
    var v=_wcGetValue(k);
    if(v.indexOf('●')>=0){
      if(_wcSecrets.wecom&&_wcSecrets.wecom[k])v=_wcSecrets.wecom[k];
      else v='';
    }
    config[k]=v;
  });
  var enabled=document.getElementById('wc-enable')?document.getElementById('wc-enable').checked:false;
  var body={config:config,is_enabled:enabled};

  var msg=document.getElementById('wc-msg');
  msg.innerHTML='<span style="color:var(--cyan)">Saving...</span>';

  fetch('/admin/channels/wecom',{
    method:'PUT',
    headers:{'Authorization':'Bearer '+T,'Content-Type':'application/json'},
    body:JSON.stringify(body)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      msg.innerHTML='<span style="color:var(--green)">'+esc(d.message||'Saved')+'</span>';
      _wcSecrets.wecom={};
      ['secret','token','encoding_aes_key'].forEach(function(k){
        var v=_wcGetValue(k);
        if(v&&v.indexOf('●')<0)_wcSecrets.wecom[k]=v;
      });
    }else{
      msg.innerHTML='<span style="color:var(--rose)">'+esc(d.error||'Save failed')+'</span>';
    }
  }).catch(function(e){
    msg.innerHTML='<span style="color:var(--rose)">Network error</span>';
  })
}

function _wcTest(){
  var corpId=_wcGetValue('corp_id');
  var secret=_wcGetValue('secret');
  if(secret.indexOf('●')>=0){
    if(_wcSecrets.wecom&&_wcSecrets.wecom.secret)secret=_wcSecrets.wecom.secret;
    else{alert('Please Enter First Secret Save Then Test');return}
  }
  if(!corpId||!secret){alert('Enterprise ID 和 Secret Required');return}
  var msg=document.getElementById('wc-msg');
  msg.innerHTML='<span style="color:var(--cyan)">Testing...</span>';

  fetch('/admin/channels/wecom/test',{
    method:'POST',
    headers:{'Authorization':'Bearer '+T,'Content-Type':'application/json'},
    body:JSON.stringify({corp_id:corpId,secret:secret})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      msg.innerHTML='<span style="color:var(--green)">'+esc(d.message||'Connection Successful')+'</span>';
    }else{
      msg.innerHTML='<span style="color:var(--rose)">'+esc(d.error||'Connection Failed')+'</span>';
    }
  }).catch(function(e){
    msg.innerHTML='<span style="color:var(--rose)">Network error</span>';
  })
}


window.l_channels=function(){
  document.getElementById('pt').textContent='Channel Management';

  // Tab bar
  var tabs=[
    ['feishu','Feishu',true],
    ['wecom','WeCom',true],
    ['qq','QQ',true],
    ['dingtalk','DingTalk',true],
  ];
  var h='<div class="cd"><div class="st">Channel Management</div>';
  h+='<div style="display:flex;gap:4px;margin-bottom:20px;overflow-x:auto">';
  tabs.forEach(function(t){
    var ch=t[0],label=t[1],active=t[2];
    var cls='ch-tab'+(active?' sel':'');
    var style=active?'':'color:#555;cursor:not-allowed';
    var click=active?'onclick="_chLoadTab(\''+ch+'\')"':'';
    var suffix=active?'':' <span style="font-size:10px;color:#444">(Coming Soon)</span>';
    h+='<button id="ch-tab-'+ch+'" class="btn bs '+cls+'" style="'+style+'" '+click+'>'+esc(label)+suffix+'</button>';
  });
  h+='</div>';
  h+='<div id="ch-body">Loading......</div>';
  h+='</div>';
  document.getElementById('mc').innerHTML=h;

  _chCurrentTab='feishu';
  _chLoadTab('feishu');
}

// ============================
// Site Group Management — Cluster Services (2026-05-15)
// ============================
var csEditingId=null; // null=create mode, number=edit mode


window.l_cluster_services=function(){
  document.getElementById('pt').textContent='Site Group Management';
  var mc=document.getElementById('mc');
  mc.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  csEditingId=null;

  fetch('/admin/cluster/services',{headers:{'Authorization':'Bearer '+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success||!d.data){mc.innerHTML='<div class="em">'+esc(d.error||'Load failed')+'</div>';return}
    render(d.data);
  })
  .catch(function(e){mc.innerHTML='<div class="em">Request Failed: '+esc(e.message)+'</div>'});

  function render(services){
    var h='<div class="cd"><div class="st" style="display:flex;justify-content:space-between;align-items:center">';
    h+='Site Group Management <span style="font-weight:400;font-size:11px;color:var(--dim)">共 '+services.length+' Services</span>';
    h+='<span>';
    h+='<button class="btn bs bp" onclick="csShowForm(null)" style="font-size:11px">+ Add Service</button> ';
    h+='<button class="btn bs" onclick="l_cluster_services()" style="font-size:11px">Refresh</button>';
    h+='</span>';
    h+='</div>';

    // Form area (hidden by default)
    h+='<div id="cs-form" style="display:none;margin-bottom:16px;padding:16px 20px;border:1px solid var(--border);border-radius:10px;background:var(--bg-card)">';
    h+='<div id="cs-form-title" style="font-size:14px;font-weight:600;margin-bottom:14px">Add Service</div>';
    h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 16px">';
    // row 1
    h+='<div><label style="font-size:11px;color:var(--dim)">Service ID *</label><input id="cs-f-sn" class="in" placeholder="例: myapp" style="width:100%"></div>';
    h+='<div><label style="font-size:11px;color:var(--dim)">Display Name *</label><input id="cs-f-dn" class="in" placeholder="例: My App" style="width:100%"></div>';
    // row 2
    h+='<div><label style="font-size:11px;color:var(--dim)">Domain *</label><input id="cs-f-dom" class="in" placeholder="例: app.easykai.cn" style="width:100%"></div>';
    h+='<div><label style="font-size:11px;color:var(--dim)">Port *</label><input id="cs-f-port" class="in" type="number" placeholder="8080" style="width:100%"></div>';
    // row 3
    h+='<div><label style="font-size:11px;color:var(--dim)">Type Management</label><select id="cs-f-mt" class="in" style="width:100%"><option value="tmux">tmux</option><option value="systemd">systemd</option></select></div>';
    h+='<div><label style="font-size:11px;color:var(--dim)">Name Management</label><input id="cs-f-mn" class="in" placeholder="tmux session 或 systemd unit" style="width:100%"></div>';
    // row 4
    h+='<div><label style="font-size:11px;color:var(--dim)">Working Directory</label><input id="cs-f-wd" class="in" placeholder="/home/easykai/.../myservice" style="width:100%"></div>';
    h+='<div><label style="font-size:11px;color:var(--dim)">Start Command</label><input id="cs-f-cmd" class="in" placeholder="python3 -B app.py 8080" style="width:100%"></div>';
    // row 5
    h+='<div><label style="font-size:11px;color:var(--dim)">Health Check Path</label><input id="cs-f-hu" class="in" placeholder="/health" style="width:100%"></div>';
    h+='<div><label style="font-size:11px;color:var(--dim)">Sort</label><input id="cs-f-so" class="in" type="number" placeholder="0" style="width:100%"></div>';
    h+='</div>';
    h+='<div style="margin-top:12px;display:flex;gap:8px">';
    h+='<button class="btn bp" onclick="csSaveService()" style="font-size:11px">Save</button>';
    h+='<button class="btn bs" onclick="document.getElementById(\'cs-form\').style.display=\'none\';csEditingId=null" style="font-size:11px">Cancel</button>';
    h+='<span id="cs-form-msg" style="font-size:11px;align-self:center"></span>';
    h+='</div>';
    h+='</div>';

    for(var i=0;i<services.length;i++){
      var s=services[i];
      var st=s.status||{};
      var running=st.running;
      var dot=running?'<span style="color:#00ff9f;font-size:14px">●</span>':'<span style="color:#ff4444;font-size:14px">●</span>';
      var statusText=running?'Running':'Stopped';
      var statusColor=running?'var(--green)':'var(--rose)';

      h+='<div class="svc-card" style="margin-bottom:16px;padding:18px 20px;border:1px solid var(--border);border-radius:10px;background:var(--bg-card)">';

      // Header row
      h+='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">';
      h+='<div style="display:flex;align-items:center;gap:10px">';
      h+=dot+' ';
      h+='<span style="font-size:15px;font-weight:600">'+esc(s.display_name)+'</span>';
      h+='<span style="font-size:12px;color:var(--dim)">'+esc(s.domain)+' :'+s.port+'</span>';
      h+='<span style="font-size:11px;padding:2px 8px;border-radius:4px;background:'+statusColor+'15;color:'+statusColor+'">'+statusText+'</span>';
      h+='</div>';
      // CRUD buttons (right)
      h+='<div style="display:flex;gap:6px">';
      h+='<button class="btn bs" style="font-size:10px;padding:2px 8px" onclick="csShowForm('+s.id+')">Edit</button>';
      h+='<button class="btn bs" style="font-size:10px;padding:2px 8px;color:var(--rose)" onclick="csDeleteService('+s.id+',\''+escAttr(s.display_name)+'\')">Delete</button>';
      h+='</div>';
      h+='</div>';

      // Info row
      h+='<div style="font-size:11px;color:var(--dim);margin-bottom:14px;display:flex;gap:20px;flex-wrap:wrap">';
      if(st.pid) h+='<span>PID: '+st.pid+'</span>';
      if(st.uptime) h+='<span>Started At: '+esc(st.uptime)+'</span>';
      if(st.cpu) h+='<span>CPU: '+esc(st.cpu)+'%</span>';
      if(st.mem) h+='<span>MEM: '+esc(st.mem)+'%</span>';
      h+='<span>Management: '+esc(s.manager_type)+' · '+esc(s.manager_name)+'</span>';
      h+='</div>';

      // Action buttons
      h+='<div style="display:flex;gap:8px;flex-wrap:wrap">';
      h+='<button class="btn bs bp" onclick="csAction('+s.id+',\'start\')" style="font-size:11px" '+(!running?'':'disabled')+'>Launch</button>';
      h+='<button class="btn bs" style="font-size:11px;color:var(--rose)" onclick="csAction('+s.id+',\'stop\')" '+(!running?'disabled':'')+'>Stop</button>';
      h+='<button class="btn bs" style="font-size:11px" onclick="csAction('+s.id+',\'restart\')">Restart</button>';
      h+='<button class="btn bs" style="font-size:11px" onclick="csLogs('+s.id+',\''+escAttr(s.display_name)+'\')">Log</button>';
      h+='<button class="btn bs" style="font-size:11px" onclick="csHealth('+s.id+',\''+escAttr(s.display_name)+'\')">Health Check</button>';
      h+='</div>';

      // Status feedback area
      h+='<div id="cs-msg-'+s.id+'" style="margin-top:10px;font-size:11px"></div>';

      h+='</div>';
    }
    h+='</div>';
    mc.innerHTML=h;
  }
}

// ── Show create/edit form ──
function csShowForm(sid){
  var form=document.getElementById('cs-form');
  if(!form) return;
  form.style.display='block';
  var title=document.getElementById('cs-form-title');
  document.getElementById('cs-form-msg').innerHTML='';

  if(sid===null){
    // Create mode
    csEditingId=null;
    if(title) title.textContent='Add Service';
    document.getElementById('cs-f-sn').value='';
    document.getElementById('cs-f-dn').value='';
    document.getElementById('cs-f-dom').value='';
    document.getElementById('cs-f-port').value='';
    document.getElementById('cs-f-mt').value='tmux';
    document.getElementById('cs-f-mn').value='';
    document.getElementById('cs-f-wd').value='';
    document.getElementById('cs-f-cmd').value='';
    document.getElementById('cs-f-hu').value='/health';
    document.getElementById('cs-f-so').value='0';
    document.getElementById('cs-f-sn').disabled=false;
    form.scrollIntoView({behavior:'smooth'});
    return;
  }

  // Edit mode: fetch service data
  csEditingId=sid;
  if(title) title.textContent='Edit Service';
  fetch('/admin/cluster/services',{headers:{'Authorization':'Bearer '+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success||!d.data) return;
    for(var i=0;i<d.data.length;i++){
      if(d.data[i].id===sid){
        var s=d.data[i];
        document.getElementById('cs-f-sn').value=s.service_name||'';
        document.getElementById('cs-f-sn').disabled=true; // can't change service_name
        document.getElementById('cs-f-dn').value=s.display_name||'';
        document.getElementById('cs-f-dom').value=s.domain||'';
        document.getElementById('cs-f-port').value=s.port||'';
        document.getElementById('cs-f-mt').value=s.manager_type||'tmux';
        document.getElementById('cs-f-mn').value=s.manager_name||'';
        document.getElementById('cs-f-wd').value=s.workdir||'';
        document.getElementById('cs-f-cmd').value=s.start_cmd||'';
        document.getElementById('cs-f-hu').value=s.health_url||'/health';
        document.getElementById('cs-f-so').value=s.sort_order||0;
        break;
      }
    }
    form.scrollIntoView({behavior:'smooth'});
  });
}

// ── Save (create or update) ──
function csSaveService(){
  var msgEl=document.getElementById('cs-form-msg');
  if(!msgEl) return;
  msgEl.innerHTML='<span style="color:var(--dim)">Saving...</span>';

  var body={
    display_name: document.getElementById('cs-f-dn').value.trim(),
    domain: document.getElementById('cs-f-dom').value.trim(),
    port: parseInt(document.getElementById('cs-f-port').value)||0,
    manager_type: document.getElementById('cs-f-mt').value,
    manager_name: document.getElementById('cs-f-mn').value.trim(),
    workdir: document.getElementById('cs-f-wd').value.trim(),
    start_cmd: document.getElementById('cs-f-cmd').value.trim(),
    health_url: document.getElementById('cs-f-hu').value.trim(),
    sort_order: parseInt(document.getElementById('cs-f-so').value)||0
  };

  var isEdit=(csEditingId!==null);
  if(!isEdit){
    body.service_name=document.getElementById('cs-f-sn').value.trim();
    if(!body.service_name||!body.display_name||!body.domain||!body.port){
      msgEl.innerHTML='<span style="color:var(--rose)">Identifier/Name/Domain/Port is Required</span>';return;
    }
  }

  var method=isEdit?'PUT':'POST';
  var url=isEdit?'/admin/cluster/services/'+csEditingId:'/admin/cluster/services';

  fetch(url,{method:method,headers:{'Authorization':'Bearer '+T,'Content-Type':'application/json'},body:JSON.stringify(body)})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){
      msgEl.innerHTML='<span style="color:var(--green)">'+esc(d.message||'Saved')+'</span>';
      document.getElementById('cs-form').style.display='none';
      csEditingId=null;
      setTimeout(function(){l_cluster_services()},800);
    }else{
      msgEl.innerHTML='<span style="color:var(--rose)">'+esc(d.error||'Save failed')+'</span>';
    }
  })
  .catch(function(e){
    msgEl.innerHTML='<span style="color:var(--rose)">Request Failed: '+esc(e.message)+'</span>';
  });
}

// ── Delete service ──
function csDeleteService(sid, name){
  if(!confirm('Confirm Delete Service「'+name+'」？\nThis Operation Cannot Be Recovered。')) return;
  var mc=document.getElementById('mc');
  mc.innerHTML='<div class="lo"><div class="s"></div>Deleting...</div>';

  fetch('/admin/cluster/services/'+sid,{method:'DELETE',headers:{'Authorization':'Bearer '+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){
      l_cluster_services();
    }else{
      mc.innerHTML='<div class="em">'+esc(d.error||'Delete failed')+' <button class="btn bs" onclick="l_cluster_services()">Back</button></div>';
    }
  })
  .catch(function(e){
    l_cluster_services();
  });
}

// ── Helper: action buttons ──
function csAction(sid, action){
  var labels={start:'Launch',stop:'Stop',restart:'Restart'};
  var msgEl=document.getElementById('cs-msg-'+sid);
  if(!msgEl) return;
  msgEl.innerHTML='<span style="color:var(--dim)">⏳ '+labels[action]+'In Progress...</span>';

  fetch('/admin/cluster/services/'+sid+'/'+action,{method:'POST',headers:{'Authorization':'Bearer '+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){
      var st=d.status||{};
      var ok=action==='stop'?!st.running:st.running;
      msgEl.innerHTML='<span style="color:'+(ok?'var(--green)':'var(--amber)')+'">'+(d.message||labels[action]+'Complete')+'</span>';
      // Refresh after 1.5s
      setTimeout(function(){l_cluster_services()},1500);
    }else{
      msgEl.innerHTML='<span style="color:var(--rose)">'+esc(d.error||'Operation Failed')+'</span>';
    }
  })
  .catch(function(e){
    msgEl.innerHTML='<span style="color:var(--rose)">Request Failed: '+esc(e.message)+'</span>';
  });
}

function csLogs(sid, name){
  var mc=document.getElementById('mc');
  mc.innerHTML='<div class="cd"><div class="st">'+esc(name)+' — Log <button class="btn bs" onclick="l_cluster_services()" style="font-size:11px">← Back</button> <button class="btn bs" onclick="csLogs('+sid+',\''+escAttr(name)+'\')" style="font-size:11px">Refresh</button></div>';
  mc.innerHTML+='<div id="cs-log-area" style="background:#0a0a0e;border:1px solid var(--border);border-radius:8px;padding:14px;max-height:500px;overflow-y:auto;font-family:monospace;font-size:11px;line-height:1.5;white-space:pre-wrap;color:#aaa">Loading......</div>';
  mc.innerHTML+='</div>';

  fetch('/admin/cluster/services/'+sid+'/logs?lines=200',{headers:{'Authorization':'Bearer '+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    var el=document.getElementById('cs-log-area');
    if(!el) return;
    if(d.success){
      var src=d.source?'<div style="color:var(--dim);margin-bottom:8px">Source: '+esc(d.source)+'</div>':'';
      el.innerHTML=src+(d.log||'(No Logs)');
    }else{
      el.innerHTML='<span style="color:var(--rose)">'+esc(d.error||'Load failed')+'</span>';
    }
  })
  .catch(function(e){
    var el=document.getElementById('cs-log-area');
    if(el) el.innerHTML='<span style="color:var(--rose)">Request Failed: '+esc(e.message)+'</span>';
  });
}

function csHealth(sid, name){
  var mc=document.getElementById('mc');
  mc.innerHTML='<div class="cd"><div class="st">'+esc(name)+' — Health Check <button class="btn bs" onclick="l_cluster_services()" style="font-size:11px">← Back</button></div>';
  mc.innerHTML+='<div id="cs-health-area" style="margin-top:12px">Checking...</div>';
  mc.innerHTML+='</div>';

  fetch('/admin/cluster/services/'+sid+'/health',{headers:{'Authorization':'Bearer '+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    var el=document.getElementById('cs-health-area');
    if(!el) return;
    var h='';
    h+='<div style="margin-bottom:10px">';
    h+='<span style="padding:4px 12px;border-radius:6px;font-size:12px;';
    if(d.healthy) h+='background:rgba(0,255,159,0.12);color:#00ff9f';
    else h+='background:rgba(255,68,68,0.12);color:#ff4444';
    h+='">'+(d.healthy?'● Health':'● Abnormal')+'</span>';
    h+=' <span style="font-size:11px;color:var(--dim)">HTTP '+d.http_code+'</span>';
    h+='</div>';
    h+='<div style="font-size:11px;color:var(--dim);margin-bottom:8px">URL: '+esc(d.url)+'</div>';
    if(d.error) h+='<div style="color:var(--rose);font-size:11px;margin-bottom:8px">Error: '+esc(d.error)+'</div>';
    if(d.parsed){
      h+='<div style="background:#0a0a0e;border:1px solid var(--border);border-radius:6px;padding:12px;max-height:300px;overflow-y:auto;font-family:monospace;font-size:11px;white-space:pre-wrap;color:#aaa">'+esc(JSON.stringify(d.parsed,null,2))+'</div>';
    }else if(d.body){
      h+='<div style="background:#0a0a0e;border:1px solid var(--border);border-radius:6px;padding:12px;max-height:300px;overflow-y:auto;font-family:monospace;font-size:11px;white-space:pre-wrap;color:#aaa">'+esc(d.body)+'</div>';
    }
    el.innerHTML=h;
  })
  .catch(function(e){
    var el=document.getElementById('cs-health-area');
    if(el) el.innerHTML='<span style="color:var(--rose)">Request Failed: '+esc(e.message)+'</span>';
  });
}
// Plan Management — l_plans
// ============================

window.l_plans=function(){
  document.getElementById("pt").textContent="Subscription";
  var h='<div style="margin-bottom:12px"><button class="btn bp" onclick="showPlanForm()">+ Add Plan</button></div>';
  h+='<div id="planForm" style="display:none;margin-bottom:16px" class="cd"><div class="st" id="planFormTitle">Add Plan</div>';
  h+='<div class="g2">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Identifier (plan_key)</div><input class="in" id="pk" placeholder="如：pro_max" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Name</div><input class="in" id="pn" placeholder="如：Pro Max" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Monthly (元)</div><input class="in" id="ppm" type="number" step="0.01" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Quarterly (元)</div><input class="in" id="ppq" type="number" step="0.01" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Semi-Annual (元)</div><input class="in" id="ppsa" type="number" step="0.01" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Annual (元)</div><input class="in" id="ppy" type="number" step="0.01" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Daily Limit</div><input class="in" id="pdl" type="number" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Sort</div><input class="in" id="pso" type="number" value="0" style="width:100%"></div>';
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Description</div><textarea class="ta" id="pdesc" rows="2" placeholder="Plan Description..."></textarea></div>';
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Feature (One Per Line)</div><textarea class="ta" id="pfeat" rows="5" placeholder="AISmart Site Building&#10;AISmart Customer Service&#10;SEOAuto Optimize"></textarea></div>';
  h+='</div><div style="margin-top:10px"><button class="btn bp" onclick="savePlan()">Save</button> <button class="btn bo" onclick="hidePlanForm()">Cancel</button><input type="hidden" id="planEditId" value=""></div></div>';
  h+='<div id="planList"><div class="lo"><div class="s"></div></div></div>';
  document.getElementById("mc").innerHTML=h;
  loadPlans();
};

var plansData=[];

function loadPlans(){
  fetch("/subscription/admin/plans",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("planList").innerHTML='<div class="em">Load failed</div>';return}
    plansData=(d.data&&d.data.plans)||[];
    var h='<div class="cd"><div class="st">Plans ('+plansData.length+')</div><table><tr><th>Sort</th><th>Identifier</th><th>Name</th><th>Monthly</th><th>Quarterly</th><th>Semi-Annual</th><th>Annual</th><th>Daily Limit</th><th>Feature</th><th>Description</th><th>Status</th><th>Actions</th></tr>';
    if(!plansData.length){h+='<tr><td colspan="9"><div class="em">No Plans</div></td></tr>'}
    else{
      plansData.forEach(function(p){
        var st=p.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Disable</span>';
        // DBIn Minutes，Show in Yuan
        var fen2yuan=function(v){return (v>0?(v/100).toFixed(2):'0')};
        var monthly=(p.price_month>0?'¥'+fen2yuan(p.price_month):'Free');
        var yearly=(p.price_year>0?'¥'+fen2yuan(p.price_year):'-');
        var quarterly=(p.price_quarter>0?'¥'+fen2yuan(p.price_quarter):'-');
        var semiAnnual=(p.price_semi_annual>0?'¥'+fen2yuan(p.price_semi_annual):'-');
        // Feature Display：前3项 + ...
        var feats=[];
        try{feats=JSON.parse(p.features_json||p.features||'[]')}catch(e){}
        var featText=feats.length>0?feats.slice(0,3).join('、')+(feats.length>3?'…':''):'-';
        h+='<tr><td>'+p.sort_order+'</td><td style="font-family:monospace">'+esc(p.plan_key)+'</td><td style="font-weight:600">'+esc(p.name)+'</td>'+
          '<td>'+monthly+'</td><td>'+quarterly+'</td><td>'+semiAnnual+'</td><td>'+yearly+'</td><td>'+p.daily_limit+'</td>'+
          '<td style="color:var(--dim);max-width:180px;font-size:11px">'+esc(featText)+'</td>'+
          '<td style="color:var(--dim);max-width:150px;overflow:hidden;text-overflow:ellipsis">'+esc(p.description)+'</td><td>'+st+'</td>'+
          '<td><button class="btn bo bs" onclick="togglePlan('+p.id+','+p.is_active+')">'+(p.is_active?'Disable':'Enabled')+'</button> '+
          '<button class="btn bo bs" onclick="editPlan('+p.id+')">Edit</button> '+
          '<button class="btn bo bs" onclick="deletePlan('+p.id+')">Delete</button></td></tr>';
      });
    }
    h+='</table></div>';
    document.getElementById("planList").innerHTML=h;
  }).catch(function(){document.getElementById("planList").innerHTML='<div class="em">Load failed</div>'});
}

function showPlanForm(){
  document.getElementById("planForm").style.display="block";
  document.getElementById("planFormTitle").textContent="Add Plan";
  document.getElementById("planEditId").value="";
  document.getElementById("pk").value="";
  document.getElementById("pn").value="";
  document.getElementById("ppm").value="0";
  document.getElementById("ppq").value="0";
  document.getElementById("ppsa").value="0";
  document.getElementById("ppy").value="0";
  document.getElementById("pdl").value="0";
  document.getElementById("pso").value="0";
  document.getElementById("pdesc").value="";
  document.getElementById("pfeat").value="";
}

function hidePlanForm(){
  document.getElementById("planForm").style.display="none";
}

function savePlan(){
  var eid=document.getElementById("planEditId").value;
  var plan_key=document.getElementById("pk").value.trim();
  var name=document.getElementById("pn").value.trim();
  if(!plan_key||!name){showToast("ID and name cannot be empty","error");return}
  var body={
    plan_key:plan_key, name:name,
    price_month:Math.round((parseFloat(document.getElementById("ppm").value)||0)*100),
    price_quarter:Math.round((parseFloat(document.getElementById("ppq").value)||0)*100),
    price_semi_annual:Math.round((parseFloat(document.getElementById("ppsa").value)||0)*100),
    price_year:Math.round((parseFloat(document.getElementById("ppy").value)||0)*100),
    daily_limit:parseInt(document.getElementById("pdl").value)||0,
    sort_order:parseInt(document.getElementById("pso").value)||0,
    description:document.getElementById("pdesc").value.trim(),
    features: (function(){var t=document.getElementById("pfeat").value.trim();return t?JSON.stringify(t.split('\n').map(function(s){return s.trim()}).filter(function(s){return s})):'[]'})(),
    is_active:1
  };
  var method=eid?"PUT":"POST";
  var url="/subscription/admin/plans"+(eid?"/"+eid:"");
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){hidePlanForm();loadPlans();showToast("Saved","success")}
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function editPlan(id){
  var p=null;
  for(var i=0;i<plansData.length;i++){if(plansData[i].id===id){p=plansData[i];break}}
  if(!p){showToast("Plan not found","error");return}
  document.getElementById("planForm").style.display="block";
  document.getElementById("planFormTitle").textContent="Edit Plan";
  document.getElementById("planEditId").value=p.id;
  document.getElementById("pk").value=p.plan_key;
  document.getElementById("pn").value=p.name;
  document.getElementById("ppm").value=p.price_month/100;
  document.getElementById("ppq").value=(p.price_quarter||0)/100;
  document.getElementById("ppsa").value=(p.price_semi_annual||0)/100;
  document.getElementById("ppy").value=p.price_year/100;
  document.getElementById("pdl").value=p.daily_limit;
  document.getElementById("pso").value=p.sort_order;
  document.getElementById("pdesc").value=p.description||"";
  // Feature JSONConvert to One Per Line
  var feats=[];
  try{feats=JSON.parse(p.features_json||p.features||'[]')}catch(e){}
  document.getElementById("pfeat").value=feats.join('\n');
}

function deletePlan(id){
  if(!confirm("Delete this plan?"))return;
  fetch("/subscription/admin/plans/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){loadPlans();showToast("Deleted","success")}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function togglePlan(id,current){
  fetch("/subscription/admin/plans/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({is_active:current?0:1})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){loadPlans();showToast("Updated","success")}
    else{showToast(d.error||"Update Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

// ============================
// Subscription List — l_subscriptions
// ============================

window.l_subscriptions=function(){
  document.getElementById("pt").textContent="Subscription List";
  var h='<div style="margin-bottom:12px;display:flex;gap:8px">';
  h+='<input class="in" id="subSearch" placeholder="Search Users..." style="flex:1" onkeyup="searchSub(event)">';
  h+='<select class="in" id="subStatusFilter" onchange="loadSubs()" style="width:140px">';
  h+='<option value="">All Status</option><option value="active">Active</option><option value="trialing">Trial</option>';
  h+='<option value="past_due">Overdue</option><option value="canceled">Cancelled</option><option value="expired">Expired</option>';
  h+='</select></div><div id="subList"><div class="lo"><div class="s"></div></div></div>';
  document.getElementById("mc").innerHTML=h;
  loadSubs();
};
function loadSubs(){
  var search=document.getElementById("subSearch").value;
  var status=document.getElementById("subStatusFilter").value;
  var query='?limit=100';
  if(search)query+='&search='+encodeURIComponent(search);
  if(status)query+='&status='+status;
  fetch("/subscription/admin/subscriptions"+query,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("subList").innerHTML='<div class="em">Load failed</div>';return}
    var list=d.data||d;
    var subs=list.subscriptions||[];
    var h='<div class="cd"><div class="st">Subscribe ('+(list.total||subs.length)+')</div><table><tr><th>ID</th><th>User</th><th>Plan</th><th>Billing Cycle</th><th>Status</th><th>Expired</th><th>Auto-Renew</th><th>Payment Method</th><th>Actions</th></tr>';
    if(!subs.length)h+='<tr><td colspan="9"><div class="em">No Subscriptions</div></td></tr>';
    else subs.forEach(function(s){
      var stCls={active:'on',trialing:'pd',past_due:'off',canceled:'off',expired:'off'};
      var sc=s.status=='past_due'||s.status=='canceled'||s.status=='expired'?'off':'on';
      if(s.status=='trialing')sc='pd';
      h+='<tr><td>'+s.id+'</td><td>'+esc(s.nickname||s.phone||'UID:'+s.user_id)+'</td>';
      h+='<td>'+esc(s.plan_key)+'</td><td>'+s.period+'</td>';
      h+='<td><span class="bdg '+sc+'">'+s.status+'</span></td>';
      h+='<td>'+(s.current_period_end||'-').slice(0,10)+'</td>';
      h+='<td>'+(s.auto_renew?'✅':'❌')+'</td>';
      h+='<td>'+(s.payment_method||'-')+'</td>';
      h+='<td><button class="btn bs bo" onclick="manualRenew('+s.id+')">Renew</button> ';
      h+='<button class="btn bs bo" onclick="forceCancel('+s.id+')" style="color:#f85149">Cancel</button></td></tr>';
    });
    h+='</table></div>';
    document.getElementById("subList").innerHTML=h;
  }).catch(function(){document.getElementById("subList").innerHTML='<div class="em">Request Failed</div>'});
}
function searchSub(e){if(e.key=='Enter')loadSubs()}
function manualRenew(sid){
  if(!confirm('Manually renew this subscription?'))return;
  fetch("/subscription/admin/subscriptions/"+sid+"/manual-renew",{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ Renewed","success");loadSubs()}
    else showToast(d.error||"Operation Failed","error");
  }).catch(function(){showToast("Request Failed","error")});
}
function forceCancel(sid){
  if(!confirm('⚠️ User will be downgraded to free. Confirm?'))return;
  fetch("/subscription/admin/subscriptions/"+sid+"/force-cancel",{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ Force cancelled","success");loadSubs()}
    else showToast(d.error||"Operation Failed","error");
  }).catch(function(){showToast("Request Failed","error")});
}

// ============================
// Order Management — l_sub_orders
// ============================

window.l_sub_orders=function(){
  document.getElementById("pt").textContent="Subscription Order Management";
  var h='<div id="subOrderList"><div class="lo"><div class="s"></div></div></div>';
  document.getElementById("mc").innerHTML=h;
  fetch("/subscription/admin/orders?limit=100",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var orders=d.data&&d.data.orders?d.data.orders:(d.orders||[]);
    var h='<div class="cd"><div class="st">Subscription Orders ('+(d.data&&d.data.total||orders.length)+')</div><table><tr><th>Order No.</th><th>User</th><th>Amount</th><th>Type</th><th>Plan</th><th>Payment</th><th>Status</th><th>Time</th></tr>';
    orders.forEach(function(o){
      var st=o.status=='paid'?'<span class="bdg on">Paid</span>':'<span class="bdg pd">'+o.status+'</span>';
      h+='<tr><td style="font-size:11px">'+esc(o.order_no)+'</td><td>'+esc(o.nickname||'UID:'+o.user_id)+'</td>';
      h+='<td>¥'+(o.amount_fen/100).toFixed(2)+'</td><td>'+esc(o.item_type)+'</td>';
      h+='<td>'+esc(o.plan_key)+'/'+o.period+'</td><td>'+(o.payment_method||'-')+'</td>';
      h+='<td>'+st+'</td><td style="font-size:11px">'+(o.paid_at||o.created_at||'').slice(0,16)+'</td></tr>';
    });
    h+='</table></div>';
    document.getElementById("subOrderList").innerHTML=h;
  });
};

// ============================
// Coupon Management — l_coupons
// ============================

window.l_coupons=function(){
  document.getElementById("pt").textContent="Coupon Management";
  var h='<div style="margin-bottom:12px"><button class="btn bp" onclick="showCouponForm()">+ Create Coupons</button></div>';
  h+='<div id="couponForm" style="display:none;margin-bottom:16px" class="cd"><div class="st">Create Coupons</div>';
  h+='<div class="g3">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Coupon Code</div><input class="in" id="cc" placeholder="如：WELCOME50" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Name</div><input class="in" id="cname" placeholder="Optional" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Type</div><select class="in" id="ct" style="width:100%">';
  h+='<option value="fixed">Fixed Discount(分)</option><option value="percent">Percentage(%)</option><option value="first_month_percent">First Month Special(%)</option>';
  h+='</select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Discount Value</div><input class="in" id="cv" type="number" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Max Usage Count(0=Unlimited)</div><input class="in" id="cmu" type="number" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Per User Limit</div><input class="in" id="cmpu" type="number" value="1" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Min. Spend(分)</div><input class="in" id="cmaf" type="number" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Applicable Plans(Comma Separated)</div><input class="in" id="caplans" placeholder="如: premium,pro" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Expiry Time</div><input class="in" id="ce" type="date" style="width:100%"></div>';
  h+='</div>';
  h+='<div class="g3" style="margin-top:8px">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Effective Start</div><input class="in" id="caf" type="datetime-local" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Effective End</div><input class="in" id="cat" type="datetime-local" style="width:100%"></div>';
  h+='<div style="display:flex;align-items:center;gap:16px;padding-top:16px">';
  h+='<label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="checkbox" id="cstack"> Stackable</label>';
  h+='</div></div>';
  h+='<div style="margin-top:10px"><button class="btn bp" onclick="saveCoupon()">Save</button> <button class="btn bo" onclick="hideCouponForm()">Cancel</button></div></div>';
  h+='<div id="couponList"><div class="lo"><div class="s"></div></div></div>';
  document.getElementById("mc").innerHTML=h;
  loadCoupons();
};
function loadCoupons(){
  fetch("/subscription/admin/coupons",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var coupons=d.data&&d.data.coupons?d.data.coupons:(d.coupons||[]);
    var typeLabels={fixed:'Fixed Amount(分)','percent':'Percentage','first_month_percent':'First Month Special'};
    var h='<div class="cd"><div class="st">Coupon ('+coupons.length+')</div><div style="overflow-x:auto"><table><tr><th>Coupon Code</th><th>Name</th><th>Type</th><th>值</th><th>Used/Upper Limit</th><th>Limited Time Window</th><th>Stackable</th><th>Categories</th><th>Expired</th><th>Status</th></tr>';
    if(!coupons.length)h+='<tr><td colspan="10"><div class="em">No Coupons</div></td></tr>';
    else coupons.forEach(function(c){
      var st=c.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Disable</span>';
      var ct=c.coupon_type||c.type||'fixed';
      var valStr=ct==='percent'||ct==='first_month_percent'?c.value+'%':'¥'+(c.value/100).toFixed(2);
      var windowStr='';
      if(c.active_from||c.active_to)windowStr=(c.active_from||'Unlimited')+' ~ '+(c.active_to||'Unlimited');
      else windowStr='-';
      windowStr=windowStr.replace(/^Unlimited ~ /,'').replace(/ ~ Unlimited$/,'');
      h+='<tr><td><strong>'+esc(c.code)+'</strong></td><td style="font-size:11px">'+esc(c.name||'-')+'</td>';
      h+='<td>'+(typeLabels[ct]||ct)+'</td><td>'+valStr+'</td>';
      h+='<td>'+c.used_count+'/'+(c.max_uses||'∞')+'</td>';
      h+='<td style="font-size:10px">'+windowStr+'</td>';
      h+='<td>'+(c.stackable?'✅':'❌')+'</td>';
      h+='<td style="font-size:11px">'+esc(c.coupon_category||'general')+'</td>';
      h+='<td>'+(c.expires_at?c.expires_at.slice(0,10):'-')+'</td><td>'+st+'</td></tr>';
    });
    h+='</table></div></div>';
    document.getElementById("couponList").innerHTML=h;
  });
}
function showCouponForm(){
  document.getElementById("couponForm").style.display="block";
}
function hideCouponForm(){
  document.getElementById("couponForm").style.display="none";
}
function saveCoupon(){
  var data={
    code: document.getElementById("cc").value,
    name: document.getElementById("cname").value,
    coupon_type: document.getElementById("ct").value,
    value: parseInt(document.getElementById("cv").value)||0,
    max_uses: parseInt(document.getElementById("cmu").value)||0,
    max_per_user: parseInt(document.getElementById("cmpu").value)||1,
    min_amount_fen: parseInt(document.getElementById("cmaf").value)||0,
    applicable_plans: document.getElementById("caplans").value,
    expires_at: document.getElementById("ce").value||null,
    active_from: document.getElementById("caf").value||null,
    active_to: document.getElementById("cat").value||null,
    stackable: document.getElementById("cstack").checked?1:0,
  };
  if(!data.code){showToast("Enter coupon code","error");return}
  fetch("/subscription/admin/coupons",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ Coupon created","success");hideCouponForm();loadCoupons()}
    else showToast(d.error||"Creation Failed","error");
  }).catch(function(){showToast("Request Failed","error")});
}

// ============================
// Ad Management — l_ads
// ============================

window.l_ads=function(){
  document.getElementById("pt").textContent="Ad Management";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/admin/ads",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var ads=d.data||[];
    var pages={"*":"Entire Site","plaza":"Plaza","guilds":"Camp","debates":"Debate","alerts":"Alert","ranking":"Ranking","arena":"Competitive","cognition":"Cognitive Map"};
    var h='<div class="sbar"><input id="adSearch" placeholder="Search Ads..." oninput="filterAds()"><button class="btn bp" onclick="showAdForm()">+ New Ad</button></div>';
    h+='<div class="cd"><div class="st">Ad List ('+ads.length+')</div><table id="adTable"><tr><th>ID</th><th>Name</th><th>Page</th><th>Position</th><th>Type</th><th>Status</th><th>Sort</th><th>Actions</th></tr>';
    if(!ads.length)h+='<tr><td colspan="8"><div class="em">No Ads</div></td></tr>';
    else ads.forEach(function(a){
      var st=a.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Disable</span>';
      h+='<tr data-search="'+esc(a.name)+' '+esc(a.page)+'">';
      h+='<td>'+a.id+'</td><td>'+esc(a.name)+'</td><td>'+(pages[a.page]||a.page)+'</td><td>'+a.position+'</td>';
      h+='<td>'+(a.ad_type=='image'?'🖼 Image':'📝 Code')+'</td><td>'+st+'</td><td>'+a.sort_order+'</td>';
      h+='<td><button class="btn bs bo" onclick="editAd('+a.id+')">Edit</button> ';
      h+='<button class="btn bs bo" onclick="toggleAd('+a.id+','+(a.is_active?0:1)+')">'+(a.is_active?'Disable':'Enabled')+'</button> ';
      h+='<button class="btn bs bo" style="color:#f85149" onclick="deleteAd('+a.id+')">Delete</button></td></tr>';
    });
    h+='</table></div>';
    h+='<div class="cd" id="adForm" style="display:none;margin-top:16px"><div class="st" id="adFormTitle">New Ad</div>';
    h+='<div class="g2"><div><label style="font-size:12px;color:var(--dim)">Name</label><input class="in" id="adName" style="width:100%"></div>';
    h+='<div><label style="font-size:12px;color:var(--dim)">Page</label><select class="sl" id="adPage" style="width:100%">';
    Object.keys(pages).forEach(function(k){h+='<option value="'+k+'">'+pages[k]+'</option>'});
    h+='</select></div></div>';
    h+='<div class="g2"><div><label style="font-size:12px;color:var(--dim)">Position</label><select class="sl" id="adPos" style="width:100%"><option value="sidebar">Sidebar</option></select></div>';
    h+='<div><label style="font-size:12px;color:var(--dim)">Type</label><select class="sl" id="adType" style="width:100%" onchange="toggleAdType()"><option value="image">Image Ad</option><option value="code">Ad Code</option></select></div></div>';
    h+='<div id="adImageFields"><div class="g2"><div><label style="font-size:12px;color:var(--dim)">ImageURL</label><input class="in" id="adImageUrl" style="width:100%" placeholder="https://..."></div>';
    h+='<div><label style="font-size:12px;color:var(--dim)">Redirect Link</label><input class="in" id="adLinkUrl" style="width:100%" placeholder="https://..."></div></div></div>';
    h+='<div id="adCodeField" style="display:none"><label style="font-size:12px;color:var(--dim)">Ad Code</label><textarea class="ta" id="adCode" style="width:100%;height:120px;font-family:monospace;font-size:11px" placeholder="Paste AdSense Or Other Ad Code..."></textarea></div>';
    h+='<div class="g2"><div><label style="font-size:12px;color:var(--dim)">Sort</label><input class="in" id="adSort" style="width:80px" value="0" type="number"></div>';
    h+='<div style="display:flex;align-items:flex-end;gap:8px"><button class="btn bp" onclick="saveAd()">Save</button><button class="btn bo" onclick="hideAdForm()">Cancel</button></div></div>';
    h+='<input type="hidden" id="adEditId" value="">';
    document.getElementById("mc").innerHTML=h;
  });
};
var _adsCache=[];
function filterAds(){
  var q=(document.getElementById("adSearch")?.value||"").toLowerCase();
  document.querySelectorAll("#adTable tr[data-search]").forEach(function(r){
    r.style.display=(!q||(r.getAttribute("data-search")||"").toLowerCase().includes(q))?"":"none";
  });
}
function showAdForm(id){
  document.getElementById("adEditId").value=id||"";
  document.getElementById("adFormTitle").textContent=id?"Edit Ad":"New Ad";
  if(id){
    fetch("/admin/ads",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
      var a=(d.data||[]).find(function(x){return x.id==id});
      if(!a)return;
      document.getElementById("adName").value=a.name||"";
      document.getElementById("adPage").value=a.page||"*";
      document.getElementById("adPos").value=a.position||"sidebar";
      document.getElementById("adType").value=a.ad_type||"image";
      document.getElementById("adImageUrl").value=a.image_url||"";
      document.getElementById("adLinkUrl").value=a.link_url||"";
      document.getElementById("adCode").value=a.ad_code||"";
      document.getElementById("adSort").value=a.sort_order||0;
      toggleAdType();
    });
  }else{
    document.getElementById("adName").value="";
    document.getElementById("adImageUrl").value="";
    document.getElementById("adLinkUrl").value="";
    document.getElementById("adCode").value="";
    document.getElementById("adSort").value="0";
    toggleAdType();
  }
  document.getElementById("adForm").style.display="block";
}
function hideAdForm(){
  document.getElementById("adForm").style.display="none";
  document.getElementById("adEditId").value="";
}
function toggleAdType(){
  var t=document.getElementById("adType").value;
  document.getElementById("adImageFields").style.display=t=="image"?"":"none";
  document.getElementById("adCodeField").style.display=t=="code"?"":"none";
}
function editAd(id){showAdForm(id)}
function saveAd(){
  var id=document.getElementById("adEditId").value;
  var data={
    name:document.getElementById("adName").value.trim(),
    page:document.getElementById("adPage").value,
    position:document.getElementById("adPos").value,
    ad_type:document.getElementById("adType").value,
    image_url:document.getElementById("adImageUrl").value.trim(),
    link_url:document.getElementById("adLinkUrl").value.trim(),
    ad_code:document.getElementById("adCode").value.trim(),
    sort_order:parseInt(document.getElementById("adSort").value)||0
  };
  if(!data.name){showToast("Enter ad name","error");return}
  var url=id?"/admin/ads/"+id:"/admin/ads";
  var method=id?"PUT":"POST";
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast(id?"✅ Updated":"✅ Created","success");hideAdForm();l_ads()}
    else showToast(d.error||"Save failed","error");
  }).catch(function(){showToast("Request Failed","error")});
}
function toggleAd(id,v){
  fetch("/admin/ads/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({is_active:v})}).then(function(r){return r.json()}).then(function(d){
    if(d.success)l_ads();
    else showToast(d.error||"Operation Failed","error");
  });
}
function deleteAd(id){
  if(!confirm("Delete this ad?"))return;
  fetch("/admin/ads/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ Deleted","success");l_ads()}
    else showToast(d.error||"Delete failed","error");
  });
}

// ============================
// 📦 Shop — l_shop_products (Product Management)
// ============================

window.l_shop_products=function(){
  document.getElementById("pt").textContent="📦 Product Management";
  loadShopProducts();
};

function loadShopProducts(){
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  // Collect Filter Conditions
  var params = [];
  var searchInput = document.getElementById("spSearch");
  var catFilter = document.getElementById("spCategory");
  var statusFilter = document.getElementById("spStatus");
  var search = searchInput ? searchInput.value.trim() : '';
  var catId = catFilter ? parseInt(catFilter.value) : 0;
  var status = statusFilter ? parseInt(statusFilter.value) : -1;
  if(search) params.push('search='+encodeURIComponent(search));
  if(catId > 0) params.push('category_id='+catId);
  if(status >= 0) params.push('is_active='+status);
  var qs = params.length ? '?'+params.join('&') : '';

  fetch("/shop/products"+qs,{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success)return;
    var ps=d.data||[];
    var types={"vip":"VIPPlan","template":"Templates","token":"Usage Packs","service":"Services","plugin":"Plugins"};
    var h = '';

    // Filter Bar
    h += '<div class="sbar" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">';
    h += '<input class="in" id="spSearch" placeholder="Search Product Name..." style="flex:1;min-width:120px;font-size:12px;padding:6px 10px" onkeyup="if(event.key===\'Enter\')loadShopProducts()" value="'+esc(searchInput?searchInput.value:'')+'">';
    h += '<select class="sl" id="spCategory" style="font-size:12px;padding:6px 10px" onchange="loadShopProducts()"><option value="0">All Categories</option></select>';
    h += '<select class="sl" id="spStatus" style="font-size:12px;padding:6px 10px" onchange="loadShopProducts()">';
    h += '<option value="-1">All Status</option><option value="1">List</option><option value="0">Unlist</option>';
    h += '</select>';
    h += '<button class="btn bp bs" onclick="showProductForm()">+ New Product</button>';
    h += '</div>';

    h+='<div class="cd"><div class="st">Product List ('+ps.length+')</div><table><tr><th>ID</th><th>Title</th><th>Type</th><th>Categories</th><th>Price</th><th>Stock</th><th>Sales</th><th>Status</th><th>Sort</th><th>Actions</th></tr>';
    if(!ps.length)h+='<tr><td colspan="10"><div class="em">No Products</div></td></tr>';
    else ps.forEach(function(p){
      var st=p.is_active?'<span class="bdg on">List</span>':'<span class="bdg off">Unlist</span>';
      h+='<tr>';
      h+='<td>'+p.id+'</td><td>'+esc(p.title)+(p.subtitle?'<br><span style="font-size:10px;color:var(--dim)">'+esc(p.subtitle)+'</span>':'')+'</td>';
      h+='<td>'+(types[p.product_type]||p.product_type)+'</td>';
      h+='<td style="font-size:11px;color:var(--dim)">'+esc(p.category_name||p.category||'-')+'</td>';
      h+='<td style="color:var(--accent)">¥'+p.price+'</td>';
      h+='<td>'+p.stock+'</td><td>'+p.sales_count+'</td><td>'+st+'</td><td>'+p.sort_order+'</td>';
      h+='<td><button class="btn bs bo" onclick="editProduct('+p.id+')">Edit</button> ';
      h+='<button class="btn bs bo" onclick="toggleProduct('+p.id+','+(p.is_active?0:1)+')">'+(p.is_active?'Unlist':'List')+'</button> ';
      h+='<button class="btn bs bo" style="color:#f85149" onclick="deleteProduct('+p.id+')">Delete</button></td></tr>';
    });
    h+='</table></div>';
    // Form
    h+='<div class="cd" id="productForm" style="display:none;margin-top:16px"><div class="st" id="productFormTitle">New Product</div>';
    h+='<div class="g2"><div><label>Title</label><input class="in" id="pTitle" style="width:100%"></div>';
    h+='<div><label>Subtitle</label><input class="in" id="pSubtitle" style="width:100%"></div></div>';
    h+='<div class="g2"><div><label>Type</label><select class="sl" id="pType" style="width:100%"><option value="service">Services</option><option value="vip">VIPPlan</option><option value="template">Templates</option><option value="token">Usage Packs</option><option value="plugin">Plugins</option></select></div>';
    h+='<div><label>Categories <span style="font-size:10px;color:var(--dim);cursor:pointer" onclick="l_shop_categories()">Category Management →</span></label><select class="sl" id="pCategory" style="width:100%"><option value="">Select Category...</option></select></div></div>';
    h+='<div class="g2"><div><label>Price (¥)</label><input class="in" id="pPrice" type="number" step="0.01" style="width:100%"></div>';
    h+='<div><label>Original Price (¥)</label><input class="in" id="pOrigPrice" type="number" step="0.01" style="width:100%"></div></div>';
    h+='<div class="g2"><div><label>Stock</label><input class="in" id="pStock" type="number" style="width:100%"></div>';
    h+='<div><label>Sort</label><input class="in" id="pSort" type="number" style="width:60px"></div></div>';
    h+='<div><label>Thumbnail</label><div style="display:flex;gap:6px">';
    h+='<input class="in" id="pThumb" style="flex:1" placeholder="ImageURLOr Upload/Auto-fill After Selection">';
    h+='<input type="file" id="pUploadFile" accept="image/*" style="display:none" onchange="uploadProductImage()">';
    h+='<button class="btn bp bs" onclick="document.getElementById(\'pUploadFile\').click()" title="Local Upload">📤 Upload</button>';
    h+='<button class="btn bo bs" onclick="openMediaPicker()" title="Choose from Library">🖼 Select Image</button>';
    h+='<button class="btn bo bs" onclick="openAIImageGen()" title="AIGenerate Image &amp; Auto-fill">🤖 AIGenerate</button>';
    h+='</div></div>';
    h+='<div id="pGallery" style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;min-height:0"></div>';
    h+='<div style="margin-top:4px;font-size:11px;color:var(--dim)">First Image is Main Product Image，Click Image to Set as Thumbnail，Drag to Sort</div>';
    h+='<div style="margin-top:8px"><label>Features (One Per Line)</label><textarea class="ta" id="pFeatures" style="width:100%;height:80px;font-size:12px" placeholder="AISmart Chat&#10;Generate Site in One Click&#10;SEOAuto Optimize"></textarea></div>';
    h+='<div style="margin-top:8px"><label>Description <span style="font-size:11px;color:var(--dim);font-weight:400">（Supports Mixed Media）</span></label><div id="pDescEditor" style="min-height:200px;background:var(--bg);border-radius:8px;border:1px solid var(--border)"></div></div>';
    h+='<div style="margin-top:8px;display:flex;gap:8px"><button class="btn bp" onclick="saveProduct()">Save</button><button class="btn bs bo" id="previewProductBtn" onclick="previewProduct()" style="display:none">🔍 Preview</button><button class="btn bo" onclick="hideProductForm()">Cancel</button></div>';
    h+='<input type="hidden" id="pEditId" value="">';
    h+='</div>'; // close productForm
    // Spec Management Panel（Show Only When Editing）
    h+='<div class="cd" id="specPanel" style="display:none;margin-top:16px">';
    h+='<div class="st">📏 Spec/SKU Management</div>';
    h+='<div id="specContent" style="margin-top:8px"><div class="lo"><div class="s"></div></div></div>';
    h+='</div>';

    document.getElementById("mc").innerHTML = h;

    // Loading Category Dropdown
    fetch("/shop/categories", {headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d2){
      if(!d2.success) return;
      var list = d2.data && d2.data.list ? d2.data.list : (d2.data||[]);
      if(!Array.isArray(list)) list = [];

      // Filter Bar Category Dropdown
      var spCat = document.getElementById("spCategory");
      if(spCat){
        spCat.innerHTML = '<option value="0">All Categories</option>';
        list.forEach(function(c){
          var opt = document.createElement("option");
          opt.value = c.id;
          opt.textContent = c.name;
          if(catId === c.id) opt.selected = true;
          spCat.appendChild(opt);
        });
      }

      // Form Category Dropdown
      var formCat = document.getElementById("pCategory");
      if(formCat){
        formCat.innerHTML = '<option value="">Select Category...</option>';
        list.forEach(function(c){
          var opt = document.createElement("option");
          opt.value = c.name;
          opt.textContent = c.name;
          formCat.appendChild(opt);
        });
      }

      // Restore Status Filter
      var spSt = document.getElementById("spStatus");
      if(spSt && status >= 0) spSt.value = String(status);
    });
  });
}

var _shopProds=[];
function showProductForm(id){
  document.getElementById("pEditId").value=id||"";
  document.getElementById("productFormTitle").textContent=id?"Edit Product":"New Product";

  // Show the Form First，Otherwise Quill Initializing in Hidden Element Crashes
  document.getElementById("productForm").style.display="block";

  // Initialize Quill Editor（Initialize After Element is Displayed）
  setTimeout(function(){
    var editorEl = document.getElementById("pDescEditor");
    if(editorEl && !window._pQuill){
      window._pQuill = new Quill('#pDescEditor', {
        theme: 'snow',
        placeholder: 'Enter Product Description，Supports Mixed Media...',
        modules: {
          toolbar: {
            container: [
              ['bold','italic','underline','strike'],
              [{list:'ordered'},{list:'bullet'}],
              ['link','blockquote','code-block'],
              [{size:['small',false,'large','huge']}],
              [{color:[]},{background:[]}],
              ['image','clean']
            ],
            handlers: {
              image: function(){
                openMediaPickerForQuill(window._pQuill);
              }
            }
          }
        }
      });
    }
    // Loading Category Dropdown Options
    loadCategorySelect(function(){
      // Load or Clear Content
      if(id){
        document.getElementById("previewProductBtn").style.display="inline-flex";
        fetch("/shop/products/"+id,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
          if(!d.success||!d.data)return;
          var p=d.data;
          document.getElementById("pTitle").value=p.title||"";
          document.getElementById("pSubtitle").value=p.subtitle||"";
          document.getElementById("pType").value=p.product_type||"service";
          document.getElementById("pCategory").value=p.category||"";
          document.getElementById("pPrice").value=p.price||"";
          document.getElementById("pOrigPrice").value=p.original_price||"";
          document.getElementById("pStock").value=p.stock||"";
          document.getElementById("pSort").value=p.sort_order||"0";
          document.getElementById("pThumb").value=p.thumbnail||"";
          renderProductGallery(p.images||[]);
          var fs=p.features;if(typeof fs==="string")try{fs=JSON.parse(fs)}catch(e){fs=[]}
          document.getElementById("pFeatures").value=(fs||[]).join("\\n");
          if(window._pQuill) window._pQuill.root.innerHTML = p.description||"";
          // Show Spec Panel &amp; Load Data
          var sp = document.getElementById("specPanel");
          if(sp){sp.style.display="block"; loadSpecManagement(id);}
        });
      }else{
        document.getElementById("pCategory").value="";
        ["pTitle","pSubtitle","pPrice","pOrigPrice","pStock","pThumb","pFeatures"].forEach(function(i){
          var el=document.getElementById(i);if(el)el.value="";
        });
        if(window._pQuill) window._pQuill.root.innerHTML = "";
        document.getElementById("pSort").value="0";
        document.getElementById("pType").value="service";
        renderProductGallery([]);
        var sp = document.getElementById("specPanel");
        if(sp) sp.style.display = "none";
      }
    });
  }, 50);
}
function hideProductForm(){
  document.getElementById("productForm").style.display="none";
  document.getElementById("pEditId").value="";
}
function previewProduct(){
  var id=document.getElementById("pEditId").value;
  if(id) window.open('/shop/preview/'+id,'_blank');
}
function saveProduct(){
  var id=document.getElementById("pEditId").value;
  var data={
    title: document.getElementById("pTitle").value.trim(),
    subtitle: document.getElementById("pSubtitle").value.trim(),
    product_type: document.getElementById("pType").value,
    category: document.getElementById("pCategory").value.trim(),
    price: parseFloat(document.getElementById("pPrice").value)||0,
    original_price: parseFloat(document.getElementById("pOrigPrice").value)||0,
    stock: parseInt(document.getElementById("pStock").value)||0,
    sort_order: parseInt(document.getElementById("pSort").value)||0,
    thumbnail: document.getElementById("pThumb").value.trim(),
    images: _shopImages,
    category_id: 0,
    features: document.getElementById("pFeatures").value.split("\\n").map(function(s){return s.trim()}).filter(function(s){return s}),
    description: window._pQuill ? window._pQuill.root.innerHTML : ""
  };
  if(!data.title){showToast("Enter a title","error");return;}
  var url=id?"/shop/products/"+id:"/shop/products";
  var method=id?"PUT":"POST";
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success){showToast(id?"✅ Updated":"✅ Created","success");hideProductForm();l_shop_products()}
      else showToast(d.error||"Failed","error");
    });
}

// ── Loading Category Dropdown ──
function loadCategorySelect(callback){
  var sel = document.getElementById("pCategory");
  if(!sel) return;
  fetch("/shop/categories", {headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success){if(callback)callback();return}
     var list = d.data && d.data.list ? d.data.list : (d.data||[]);
     if(!Array.isArray(list)) list = [];
     // Retain"Select Category"Options
     sel.innerHTML = '<option value="">Select Category...</option>';
     list.forEach(function(c){
      var opt = document.createElement("option");
      opt.value = c.name;
      opt.textContent = c.name;
      sel.appendChild(opt);
    });
    if(callback) callback();
  })
  .catch(function(){if(callback)callback()});
}

// ── Product Categories Management ──

window.l_shop_categories = function(){
  document.getElementById("pt").textContent="🏷️ Product Categories";
  var h = '';
  h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">';
  h += '<div class="st" style="margin:0">Category List</div>';
  h += '<button class="btn bp bs" onclick="showCategoryForm()">+ New Category</button></div>';
  h += '<div class="cd" id="catList"><div class="lo"><div class="s"></div></div></div>';

  // Form（New/Edit）
  h += '<div class="cd" id="catForm" style="display:none;margin-top:16px">';
  h += '<div class="st" id="catFormTitle">New Category</div>';
  h += '<div class="g2"><div><label>Name</label><input class="in" id="catName" style="width:100%" placeholder="如: AITools"></div>';
  h += '<div><label>Identifier (slug)</label><input class="in" id="catSlug" style="width:100%" placeholder="如: ai-tools, Auto Generate if Empty"></div></div>';
  h += '<div class="g2"><div><label>Parent Category</label><select class="sl" id="catParent" style="width:100%"><option value="0">无（Level 1 Category）</option></select></div>';
  h += '<div><label>Icon</label><input class="in" id="catIcon" style="width:100%" placeholder="如: 🤖"></div></div>';
  h += '<div class="g2"><div><label>Sort</label><input class="in" id="catSort" type="number" style="width:60px" value="0"></div><div></div></div>';
  h += '<div style="display:flex;gap:8px;margin-top:12px">';
  h += '<button class="btn bp" onclick="saveCategory()">Save</button>';
  h += '<button class="btn bo" onclick="hideCategoryForm()">Cancel</button></div>';
  h += '<input type="hidden" id="catEditId" value="">';
  h += '</div>';
  document.getElementById("mc").innerHTML = h;
  loadCategoryList();
};

function loadCategoryList(){
  var list = document.getElementById("catList");
  if(!list) return;
  list.innerHTML = '<div class="lo"><div class="s"></div></div>';
  fetch("/shop/categories", {headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success){list.innerHTML = '<div class="em">Load failed</div>';return}
     var cats = d.data && d.data.list ? d.data.list : (d.data||[]);
     if(!Array.isArray(cats)) cats = [];
     if(!cats.length){
      list.innerHTML = '<div style="text-align:center;padding:40px;color:var(--dim)">No Categories，Click Above"New Category"Create</div>';
      return;
    }
    var h = '<table class="tb"><tr><th>Name</th><th>Identifier</th><th>Sort</th><th>Icon</th><th>Products</th><th>Status</th><th>Actions</th></tr>';
     cats.forEach(function(c){
      var st = c.is_active ? '<span style="color:var(--green)">Enabled</span>' : '<span style="color:var(--rose)">Disable</span>';
      h += '<tr><td>'+esc(c.name)+'</td><td style="font-size:11px;color:var(--dim)">'+esc(c.slug||'-')+'</td>';
      h += '<td>'+c.sort_order+'</td><td>'+(c.icon||'-')+'</td><td>'+(c.product_count||0)+'</td><td>'+st+'</td>';
      h += '<td style="white-space:nowrap">';
      h += '<button class="btn bo bs" onclick="editCategory('+c.id+')">Edit</button> ';
      h += '<button class="btn bo bs" onclick="toggleCategory('+c.id+','+(c.is_active?0:1)+')">'+(c.is_active?'Disable':'Enabled')+'</button> ';
      h += '<button class="btn bo bs" style="color:#f85149" onclick="deleteCategory('+c.id+',\''+esc(c.name)+'\')">Delete</button>';
      h += '</td></tr>';
    });
    // Tree Render
    function renderCat(c, depth){
      var indent = '';
      for(var i=0;i<depth;i++) indent += '&nbsp;&nbsp;&nbsp;&nbsp;';
      var prefix = depth > 0 ? '└ ' : '';
      var st = c.is_active ? '<span style="color:var(--green)">Enabled</span>' : '<span style="color:var(--rose)">Disable</span>';
      h += '<tr><td>'+indent+prefix+esc(c.name)+'</td>';
      h += '<td style="font-size:11px;color:var(--dim)">'+esc(c.slug||'-')+'</td>';
      h += '<td>'+c.sort_order+'</td><td>'+(c.icon||'-')+'</td><td>'+(c.product_count||0)+'</td><td>'+st+'</td>';
      h += '<td style="white-space:nowrap">';
      h += '<button class="btn bo bs" onclick="editCategory('+c.id+')">Edit</button> ';
      h += '<button class="btn bo bs" onclick="toggleCategory('+c.id+','+(c.is_active?0:1)+')">'+(c.is_active?'Disable':'Enabled')+'</button> ';
      h += '<button class="btn bo bs" style="color:#f85149" onclick="deleteCategory('+c.id+',\''+esc(c.name)+'\')">Delete</button>';
      h += '</td></tr>';
      if(c.children && c.children.length){
        c.children.forEach(function(child){renderCat(child, depth+1)});
      }
    }
    var tree = d.data && d.data.tree ? d.data.tree : cats;
    tree.forEach(function(c){renderCat(c, 0)});
    h += '</table>';
    list.innerHTML = h;

    // Refresh Parent Category Dropdown
    var parentSel = document.getElementById("catParent");
    if(parentSel){
      var curVal = parentSel.value;
      parentSel.innerHTML = '<option value="0">无（Level 1 Category）</option>';
      function addOpts(items, depth){
        items.forEach(function(c){
          var indent = '';
          for(var i=0;i<depth;i++) indent += '&nbsp;&nbsp;';
          var opt = document.createElement("option");
          opt.value = c.id;
          opt.innerHTML = indent + esc(c.name);
          parentSel.appendChild(opt);
          if(c.children && c.children.length) addOpts(c.children, depth+1);
        });
      }
      addOpts(tree, 0);
      parentSel.value = curVal;
    }
  })
  .catch(function(){list.innerHTML = '<div class="em">Request Failed</div>'});
}

function showCategoryForm(data){
  document.getElementById("catForm").style.display = "block";
  document.getElementById("catFormTitle").textContent = data ? "Edit Category" : "New Category";
  document.getElementById("catEditId").value = data ? data.id : "";
  document.getElementById("catName").value = data ? data.name : "";
  document.getElementById("catSlug").value = data ? (data.slug||"") : "";
  document.getElementById("catSort").value = data ? data.sort_order : 0;
  document.getElementById("catIcon").value = data ? (data.icon||"") : "";
  // Set Parent Category，Cannot Select Self
  var parentSel = document.getElementById("catParent");
  if(parentSel){
    if(data && data.id){
      var editId = data.id;
      for(var i=0;i<parentSel.options.length;i++){
        var opt = parentSel.options[i];
        if(parseInt(opt.value) === data.parent_id) opt.selected = true;
        if(parseInt(opt.value) === editId) opt.disabled = true;
      }
    } else {
      parentSel.value = "0";
    }
  }
}

function hideCategoryForm(){
  document.getElementById("catForm").style.display = "none";
  document.getElementById("catEditId").value = "";
}

function editCategory(id){
  fetch("/shop/categories", {headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success) return;
    var list = d.data && d.data.list ? d.data.list : (d.data||[]);
    var c = list.find(function(x){return x.id === id});
    if(c) showCategoryForm(c);
  });
}

function saveCategory(){
  var id = document.getElementById("catEditId").value;
  var data = {
    name: document.getElementById("catName").value.trim(),
    slug: document.getElementById("catSlug").value.trim(),
    sort_order: parseInt(document.getElementById("catSort").value)||0,
    icon: document.getElementById("catIcon").value.trim(),
    parent_id: parseInt(document.getElementById("catParent").value)||0
  };
  if(!data.name){showToast("Enter category name","error");return}
  var url = id ? "/shop/categories/"+id : "/shop/categories";
  var method = id ? "PUT" : "POST";
  fetch(url, {method:method, headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify(data)})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){
      showToast(id?"✅ Updated":"✅ Created","success");
      hideCategoryForm();
      loadCategoryList();
      loadCategorySelect();
    } else {
      showToast(d.error||"Failed","error");
    }
  });
}

function toggleCategory(id, active){
  fetch("/shop/categories/"+id, {method:"PUT", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify({is_active: active})})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast(active?"✅ Enabled":"✅ Disabled","success");loadCategoryList()}
  });
}

function deleteCategory(id, name){
  if(!confirm("Confirm Delete Category「"+name+"」吗？")) return;
  fetch("/shop/categories/"+id, {method:"DELETE", headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("✅ Deleted","success");loadCategoryList();loadCategorySelect()}
    else showToast(d.error||"Delete failed","error");
  });
}

// ── Spec/SKUManagement ──
function loadSpecManagement(pid){
  var cont = document.getElementById("specContent");
  if(!cont) return;
  cont.innerHTML = '<div class="lo"><div class="s"></div></div>';

  // Load Specs andSKUData
  Promise.all([
    fetch("/shop/products/"+pid+"/specs", {headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}),
    fetch("/shop/products/"+pid+"/skus", {headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()})
  ]).then(function(results){
    var specsData = results[0], skusData = results[1];
    var specs = (specsData.success ? specsData.data : []) || [];
    var skus = (skusData.success ? skusData.data : []) || [];
    renderSpecManagement(pid, specs, skus);
  }).catch(function(){
    cont.innerHTML = '<div style="color:#f85149">Load failed</div>';
  });
}

function renderSpecManagement(pid, specs, skus){
  var cont = document.getElementById("specContent");
  if(!cont) return;
  var h = '';

  // Spec List
  h += '<div style="margin-bottom:16px">';
  h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
  h += '<strong style="font-size:13px">Spec Definition</strong>';
  h += '<div style="display:flex;gap:4px">';
  h += '<input class="in" id="newSpecName" placeholder="如: Color" style="font-size:12px;padding:4px 8px;width:120px">';
  h += '<button class="btn bp bs" onclick="addSpec('+pid+')" style="font-size:11px;padding:4px 10px">+ Add Spec</button>';
  h += '</div></div>';

  if(!specs.length){
    h += '<div style="font-size:12px;color:var(--dim);padding:12px;text-align:center;background:var(--bg);border-radius:6px">No Specs，After Adding, Set Different Variants（e.g. Color、Size）</div>';
  } else {
    specs.forEach(function(s){
      h += '<div style="background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;margin-bottom:8px">';
      h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">';
      h += '<strong style="font-size:13px">'+esc(s.spec_name)+'</strong>';
      h += '<button class="btn bs bo" style="font-size:10px;padding:2px 6px;color:#f85149" onclick="deleteSpec('+pid+','+s.id+')">Delete</button>';
      h += '</div><div style="display:flex;gap:4px;flex-wrap:wrap">';
      (s.values||[]).forEach(function(v){
        h += '<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;background:var(--card);border:1px solid var(--border);border-radius:4px;font-size:11px">';
        h += esc(v.spec_value);
        h += '<span style="cursor:pointer;color:#f85149;font-size:10px" onclick="deleteSpecValue('+pid+','+v.id+',this)">✕</span></span>';
      });
      h += '<span style="display:inline-flex;gap:2px">';
      h += '<input class="in" id="svInput_'+s.id+'" placeholder="Value" style="font-size:11px;width:60px;padding:2px 6px">';
      h += '<button class="btn bs bo" style="font-size:10px;padding:2px 6px" onclick="addSpecValue('+pid+','+s.id+')">+</button>';
      h += '</span></div></div>';
    });
  }
  h += '</div>';

  // SKUList
  h += '<div style="margin-top:12px">';
  h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
  h += '<strong style="font-size:13px">SKU Stock (&#1635;'+skus.length+')</strong>';
  if(specs.length){
    h += '<button class="btn bs bo" onclick="generateSkus('+pid+')" style="font-size:11px;padding:4px 10px">⚡ Auto GenerateSKU</button>';
  }
  h += '</div>';

  if(!skus.length){
    h += '<div style="font-size:12px;color:var(--dim);padding:12px;text-align:center;background:var(--bg);border-radius:6px">';
    if(specs.length) h += 'Has Specs But Not GeneratedSKU，Click"Auto GenerateSKU"';
    else h += 'NoneSKU（Products Without Specs Auto-create DefaultSKU）';
    h += '</div>';
  } else {
    h += '<div style="overflow-x:auto"><table class="tb" style="font-size:12px">';
    h += '<tr><th>Spec Combination</th><th>Price</th><th>Original Price</th><th>Stock</th><th>SKUEncode</th><th>Actions</th></tr>';
    skus.forEach(function(sk){
      var label = '';
      if(sk.spec_path){
        try{
          var sp = JSON.parse(sk.spec_path);
          label = Object.values(sp).join(' / ');
        }catch(e){label = sk.spec_path;}
      } else {
        label = 'Default';
      }
      h += '<tr>';
      h += '<td>'+esc(label)+'</td>';
      h += '<td><input class="in" id="skuPrice_'+sk.id+'" value="'+sk.price+'" style="width:60px;font-size:11px;padding:2px 4px"></td>';
      h += '<td><input class="in" id="skuOrig_'+sk.id+'" value="'+(sk.original_price||'')+'" style="width:60px;font-size:11px;padding:2px 4px"></td>';
      h += '<td><input class="in" id="skuStock_'+sk.id+'" value="'+sk.stock+'" style="width:50px;font-size:11px;padding:2px 4px"></td>';
      h += '<td style="font-size:10px;color:var(--dim)">'+(sk.sku_code||'-')+'</td>';
      h += '<td><button class="btn bs bo" onclick="saveSku('+pid+','+sk.id+')" style="font-size:10px;padding:2px 6px">Save</button></td>';
      h += '</tr>';
    });
    h += '</table></div>';
  }
  h += '</div>';

  cont.innerHTML = h;
}

function addSpec(pid){
  var name = document.getElementById("newSpecName").value.trim();
  if(!name){showToast("Enter spec name","error");return}
  fetch("/shop/products/"+pid+"/specs", {method:"POST", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify({spec_name: name})})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("✅ Spec added","success");loadSpecManagement(pid)}
    else showToast(d.error||"Failed","error");
  });
}

function deleteSpec(pid, sid){
  if(!confirm("Delete this spec and all its values?")) return;
  fetch("/shop/products/"+pid+"/specs/"+sid, {method:"DELETE", headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("✅ Deleted","success");loadSpecManagement(pid)}
    else showToast(d.error||"Failed","error");
  });
}

function addSpecValue(pid, sid){
  var input = document.getElementById("svInput_"+sid);
  if(!input) return;
  var val = input.value.trim();
  if(!val){showToast("Enter spec value","error");return}
  fetch("/shop/products/"+pid+"/specs/"+sid+"/values", {method:"POST", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify({spec_value: val})})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){input.value="";showToast("✅ Added","success");loadSpecManagement(pid)}
    else showToast(d.error||"Failed","error");
  });
}

function deleteSpecValue(pid, vid, el){
  fetch("/shop/products/"+pid+"/specs/values/"+vid, {method:"DELETE", headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("✅ Deleted","success");loadSpecManagement(pid)}
    else showToast(d.error||"Failed","error");
  });
}

function generateSkus(pid){
  if(!confirm("Auto-generate all SKU combinations from current specs. Continue?")) return;
  fetch("/shop/products/"+pid+"/skus/generate", {method:"POST", headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("✅ Generated "+d.count+" 个SKU","success");loadSpecManagement(pid)}
    else showToast(d.error||"Generation Failed","error");
  });
}

function saveSku(pid, skuid){
  var data = {};
  var priceEl = document.getElementById("skuPrice_"+skuid);
  var origEl = document.getElementById("skuOrig_"+skuid);
  var stockEl = document.getElementById("skuStock_"+skuid);
  if(priceEl) data.price = parseFloat(priceEl.value)||0;
  if(origEl) data.original_price = parseFloat(origEl.value)||0;
  if(stockEl) data.stock = parseInt(stockEl.value)||0;
  fetch("/shop/products/"+pid+"/skus/"+skuid, {method:"PUT", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify(data)})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success) showToast("✅ SKU updated","success");
    else showToast(d.error||"Update Failed","error");
  });
}

function toggleProduct(id,active){
  fetch("/shop/products/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({is_active:active})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success){showToast(active?"✅ Published":"✅ Unpublished","success");l_shop_products()}
    });
}
function deleteProduct(id){
  if(!confirm("Delete this product?"))return;
  fetch("/shop/products/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success){showToast("✅ Deleted","success");l_shop_products()}
    });
}

// ── Product Image Management ──
var _shopImages = [];

function uploadProductImage(){
  var f = document.getElementById("pUploadFile");
  if(!f.files||!f.files[0]) return;
  var fd = new FormData();
  fd.append("file", f.files[0]);
  fetch("/shop/products/upload-image", {method:"POST", headers:{"Authorization":"Bearer "+T}, body:fd})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){
      var url = d.data.url;
      document.getElementById("pThumb").value = url;
      addProductImage(url);
      showToast("✅ Image uploaded","success");
    } else {
      showToast(d.error||"Upload failed","error");
    }
  })
  .catch(function(){showToast("Upload request failed","error")});
  f.value = "";
}

function renderProductGallery(images){
  _shopImages = images || [];
  var g = document.getElementById("pGallery");
  if(!g) return;
  var h = "";
  if(!_shopImages.length){
    h = '<span style="font-size:12px;color:var(--dim);padding:8px 0">No Images，Upload or Choose from Library</span>';
  } else {
    _shopImages.forEach(function(img,i){
      var url = typeof img==="object" ? (img.url||img) : img;
      h += '<div style="position:relative;width:80px;height:80px;border-radius:8px;overflow:hidden;border:2px solid var(--border);cursor:pointer;flex-shrink:0"';
      h += ' onclick="setAsThumb(\''+esc(url)+'\')"';
      h += ' title="Click to Set as Thumbnail">';
      h += '<img src="'+esc(url)+'" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.style.display=\'none\'">';
      h += '<div style="position:absolute;top:2px;right:2px;width:18px;height:18px;border-radius:50%;background:rgba(248,81,73,.9);color:#fff;font-size:11px;display:flex;align-items:center;justify-content:center;cursor:pointer"';
      h += ' onclick="event.stopPropagation();removeGalleryImage('+i+')">✕</div>';
      if(i === 0) h += '<div style="position:absolute;bottom:2px;left:2px;font-size:9px;background:rgba(99,102,241,.8);color:#fff;padding:1px 4px;border-radius:3px">Main Image</div>';
      h += '</div>';
    });
  }
  g.innerHTML = h;
}

function addProductImage(url){
  if(!url) return;
  _shopImages.push({url: url, sort_order: _shopImages.length});
  renderProductGallery(_shopImages);
}

function setAsThumb(url){
  document.getElementById("pThumb").value = url;
  showToast("✅ Set as thumbnail","success");
}

function removeGalleryImage(idx){
  _shopImages.splice(idx, 1);
  renderProductGallery(_shopImages);
}

// ── Media Library Image Picker ──
function openMediaPicker(){
  var overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "mediaPickerOverlay";
  overlay.innerHTML = '<div class="modal-box" style="width:800px;max-width:90vw;max-height:85vh">';
  overlay.innerHTML += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">';
  overlay.innerHTML += '<h3 style="margin:0">🖼 Choose Image from Library</h3>';
  overlay.innerHTML += '<button class="btn bo bs" onclick="closeMediaPicker()">✕ Close</button></div>';
  overlay.innerHTML += '<div id="mediaPickerGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;max-height:60vh;overflow-y:auto;padding:4px"><div class="lo"><div class="s"></div></div></div>';
  overlay.innerHTML += '</div>';
  document.body.appendChild(overlay);

  fetch("/admin/media-library/list", {headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success){document.getElementById("mediaPickerGrid").innerHTML='<div style="color:#f85149">Load failed</div>';return}
    var items = (d.data||[]).filter(function(f){return f.mime_type && f.mime_type.startsWith("image/")});
    var grid = document.getElementById("mediaPickerGrid");
    if(!grid) return;
    var h = "";
    if(!items.length){
      h = '<div style="text-align:center;padding:40px;color:var(--dim);grid-column:1/-1">Media LibraryNo Images，Please Upload First</div>';
    } else {
      items.forEach(function(f){
        var src = "/static/"+f.file_path;
        h += '<div style="background:var(--card);border:1px solid var(--border);border-radius:8px;overflow:hidden;cursor:pointer" onclick="selectMediaImage(\''+esc(src)+'\')">';
        h += '<img src="'+esc(src)+'" style="width:100%;height:100px;object-fit:cover" onerror="this.style.display=\'none\'">';
        h += '<div style="padding:4px 6px;font-size:10px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc(f.original_name)+'</div>';
        h += '</div>';
      });
    }
    grid.innerHTML = h;
  })
  .catch(function(){
    var grid = document.getElementById("mediaPickerGrid");
    if(grid) grid.innerHTML = '<div style="color:#f85149">Request Failed</div>';
  });
}

function closeMediaPicker(){
  var el = document.getElementById("mediaPickerOverlay");
  if(el) el.remove();
}

function selectMediaImage(url){
  document.getElementById("pThumb").value = url;
  addProductImage(url);
  closeMediaPicker();
  showToast("✅ Image added","success");
}

// ── Rich Text Product Description with Media Images ──
function openMediaPickerForQuill(quill){
  var overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "mediaPickerQuillOverlay";
  overlay.innerHTML = '<div class="modal-box" style="width:800px;max-width:90vw;max-height:85vh">';
  overlay.innerHTML += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">';
  overlay.innerHTML += '<h3 style="margin:0">🖼 Select Image to Insert Description</h3>';
  overlay.innerHTML += '<button class="btn bo bs" onclick="document.getElementById(\'mediaPickerQuillOverlay\').remove()">✕ Close</button></div>';
  overlay.innerHTML += '<div id="mediaPickerQuillGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;max-height:60vh;overflow-y:auto;padding:4px"><div class="lo"><div class="s"></div></div></div>';
  overlay.innerHTML += '</div>';
  document.body.appendChild(overlay);

  fetch("/admin/media-library/list", {headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success){document.getElementById("mediaPickerQuillGrid").innerHTML='<div style="color:#f85149">Load failed</div>';return}
    var items = (d.data||[]).filter(function(f){return f.mime_type && f.mime_type.startsWith("image/")});
    var grid = document.getElementById("mediaPickerQuillGrid");
    if(!grid) return;
    var h = "";
    if(!items.length){
      h = '<div style="text-align:center;padding:40px;color:var(--dim);grid-column:1/-1">Media LibraryNo Images，Please Upload First</div>';
    } else {
      items.forEach(function(f){
        var src = "/static/"+f.file_path;
        h += '<div style="background:var(--card);border:1px solid var(--border);border-radius:8px;overflow:hidden;cursor:pointer" onclick="insertToQuill(\''+esc(src)+'\')">';
        h += '<img src="'+esc(src)+'" style="width:100%;height:100px;object-fit:cover" onerror="this.style.display=\'none\'">';
        h += '<div style="padding:4px 6px;font-size:10px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc(f.original_name)+'</div>';
        h += '</div>';
      });
    }
    grid.innerHTML = h;
  })
  .catch(function(){
    var grid = document.getElementById("mediaPickerQuillGrid");
    if(grid) grid.innerHTML = '<div style="color:#f85149">Request Failed</div>';
  });
}

function insertToQuill(url){
  if(window._pQuill){
    var range = window._pQuill.getSelection(true);
    window._pQuill.insertEmbed(range.index, 'image', url, 'user');
    window._pQuill.setSelection(range.index + 1);
  }
  var overlay = document.getElementById("mediaPickerQuillOverlay");
  if(overlay) overlay.remove();
}

// ── AIImage Generation Popup ──
function openAIImageGen(){
  var overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "aiGenOverlay";
  overlay.innerHTML = '<div class="modal-box" style="width:560px;max-width:90vw">';
  overlay.innerHTML += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">';
  overlay.innerHTML += '<h3 style="margin:0">🤖 AI Generate Picture</h3>';
  overlay.innerHTML += '<button class="btn bo bs" onclick="closeAIImageGen()">✕ Close</button></div>';
  overlay.innerHTML += '<div style="margin-bottom:12px">';
  overlay.innerHTML += '<label style="display:block;margin-bottom:4px;font-size:13px;color:var(--text)">Image Description</label>';
  overlay.innerHTML += '<textarea id="aiGenPrompt" style="width:100%;min-height:80px;padding:8px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--fg);font-size:13px;resize:vertical" placeholder="Describe the Image Content You Want，e.g.：A Blue Tech StyleAIBot Avatar，Flat Style"></textarea>';
  overlay.innerHTML += '</div>';
  overlay.innerHTML += '<div style="margin-bottom:12px">';
  overlay.innerHTML += '<label style="display:block;margin-bottom:4px;font-size:13px;color:var(--text)">Size</label>';
  overlay.innerHTML += '<select id="aiGenSize" style="padding:6px 10px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--fg)">';
  overlay.innerHTML += '<option value="1024x1024">1024×1024 (Square)</option><option value="1280x720">1280×720 (Landscape)</option>';
  overlay.innerHTML += '</select></div>';
  overlay.innerHTML += '<button class="btn bp" onclick="doAIImageGen()" id="aiGenBtn" style="width:100%;padding:10px">🎨 Generate Picture</button>';
  overlay.innerHTML += '<div id="aiGenResult" style="margin-top:12px"></div>';
  overlay.innerHTML += '</div>';
  document.body.appendChild(overlay);
  document.getElementById("aiGenPrompt").focus();
}

function closeAIImageGen(){
  var el = document.getElementById("aiGenOverlay");
  if(el) el.remove();
}

function doAIImageGen(){
  var prompt = document.getElementById("aiGenPrompt").value.trim();
  if(!prompt){showToast("Enter image description","error");return}
  var size = document.getElementById("aiGenSize").value;
  var btn = document.getElementById("aiGenBtn");
  var result = document.getElementById("aiGenResult");
  btn.disabled = true;
  btn.textContent="⏳ Generating...";
  result.innerHTML = '<div class="lo"><div class="s"></div>Generating Image...</div>';

  fetch("/admin/agent-matrix/generate-image", {
    method: "POST",
    headers: {"Authorization":"Bearer "+T, "Content-Type":"application/json"},
    body: JSON.stringify({prompt: prompt, size: size, cover: false})
  })
  .then(function(r){return r.json()})
  .then(function(d){
    btn.disabled = false;
    btn.textContent="🎨 Generate Picture";
    if(d.success){
      var imgUrl = d.data.image_url;
      result.innerHTML = '<div style="text-align:center">';
      result.innerHTML += '<img src="'+esc(imgUrl)+'" style="max-width:100%;max-height:300px;border-radius:8px;margin-bottom:10px;border:1px solid var(--border)">';
      result.innerHTML += '<div style="display:flex;gap:8px;justify-content:center">';
      result.innerHTML += '<button class="btn bp" onclick="useAIGenImage(\''+esc(imgUrl)+'\')">✅ Use This Image</button>';
      result.innerHTML += '<button class="btn bo" onclick="doAIImageGen()">🔄 Regenerate</button>';
      result.innerHTML += '</div></div>';
      // Also Save Image to Media Library
      saveToMediaLibrary(imgUrl, prompt);
    } else {
      result.innerHTML = '<div style="color:#f85149;text-align:center">Generation Failed: '+esc(d.error||'Unknown Error')+'</div>';
    }
  })
  .catch(function(){
    btn.disabled = false;
    btn.textContent="🎨 Generate Picture";
    result.innerHTML = '<div style="color:#f85149;text-align:center">Request Failed，Check Network</div>';
  });
}

function useAIGenImage(url){
  document.getElementById("pThumb").value = url;
  addProductImage(url);
  closeAIImageGen();
  showToast("✅ Image added","success");
}

function saveToMediaLibrary(imgUrl, prompt){
  // DownloadAIGenerated Images &amp; Upload to Media Library
  fetch(imgUrl).then(function(r){return r.blob()}).then(function(blob){
    var fd = new FormData();
    var ext = imgUrl.split('.').pop().split('?')[0] || 'png';
    fd.append("file", blob, "ai_gen_"+Date.now()+"."+ext);
    fetch("/admin/media-library/upload", {
      method:"POST", headers:{"Authorization":"Bearer "+T}, body:fd
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success) showToast("Image synced to media library","success");
    });
  }).catch(function(){});
}

// ============================
// 📦 Shop — l_shop_orders (Order Management)
// ============================

window.l_shop_orders=function(){
  document.getElementById("pt").textContent="📦 Order Management";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/shop/orders",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var os=d.data||[];
    var h='<div class="cd"><div class="st">Order List ('+os.length+')</div><div style="overflow-x:auto"><table><tr><th>ID</th><th>User</th><th>Product</th><th>Count</th><th>Amount</th><th>Discount</th><th>Payment</th><th>Logistics</th><th>Time</th><th>Actions</th></tr>';
    if(!os.length)h+='<tr><td colspan="10"><div class="em">No orders yet</div></td></tr>';
    else os.forEach(function(o){
      var stt={pending:'<span class="bdg pd">Pending Payment</span>',paid:'<span class="bdg on">Paid</span>',refunded:'<span class="bdg off">Refunded</span>'};
      // Logistics Status
      var shipHtml='<span style="font-size:11px;color:var(--dim)">Pending Shipment</span>';
      if(o.shipping_status==='shipped') shipHtml='<span style="font-size:11px;color:var(--accent3)">Shipped</span>';
      // Action Button
      var act='';
      if(o.status==='pending'){
        act+='<button class="btn bs bo" style="color:var(--green);font-size:11px;padding:2px 8px" onclick="confirmOrder('+o.id+')">✅ Confirm Payment</button> ';
      }
      if(o.status==='paid' && o.shipping_status!=='shipped'){
        act+='<button class="btn bs bo" onclick="showShipForm('+o.id+',\''+esc(o.prod_title||o.product_title)+'\')" style="font-size:11px;padding:2px 8px">📦 Ship</button> ';
      }
      if(o.status==='paid'){
        act+='<button class="btn bs bo" style="color:#f85149;font-size:11px;padding:2px 8px" onclick="refundOrder('+o.id+')">Refund</button>';
      }
      if(o.shipping_status==='shipped'){
        act+='<button class="btn bs bo" onclick="showTrackInfo('+o.id+')" style="font-size:11px;padding:2px 8px">🚚 Logistics</button>';
      }
      act+='<button class="btn bs bo" onclick="showOrderDetail('+o.id+')" style="font-size:11px;padding:2px 8px">📋 Details</button>';
      h+='<tr><td>'+o.id+'</td><td>'+(o.username||o.phone||'#'+o.user_id)+'</td>';
      h+='<td>'+esc(o.prod_title||o.product_title)+'</td><td>'+o.quantity+'</td>';
      h+='<td style="color:var(--accent)">¥'+o.subtotal+'</td><td>¥'+(o.discount||0)+'</td>';
      h+='<td>'+(stt[o.status]||o.status)+'</td><td>'+shipHtml+'</td>';
      h+='<td style="font-size:10px;color:var(--dim)">'+(o.paid_at||o.created_at||'').slice(0,16)+'</td>';
      h+='<td style="white-space:nowrap">'+act+'</td></tr>';
    });
    h+='</table></div></div>';
    // Shipping Popup
    h+='<div id="shipModal" class="modal" style="display:none"><div class="modal-c" style="max-width:400px">';
    h+='<div class="st" id="shipModalTitle">Ship</div>';
    h+='<div style="margin:12px 0;font-size:13px;color:var(--dim)" id="shipModalProduct"></div>';
    h+='<div class="fl"><span style="width:80px;font-size:12px">Courier</span><select class="in" id="shipCompany" style="width:250px"></select></div>';
    h+='<div class="fl" style="margin-top:8px"><span style="width:80px;font-size:12px">Tracking No.</span><input class="in" id="shipNumber" style="width:250px" placeholder="Tracking No."></div>';
    h+='<div style="margin-top:12px;display:flex;gap:8px">';
    h+='<button class="btn bp" onclick="submitShip()">Confirm Shipment</button>';
    h+='<button class="btn bo" onclick="document.getElementById(\'shipModal\').style.display=\'none\'">Cancel</button></div>';
    h+='</div></div>';
    // Logistics Tracking Popup
    h+='<div id="trackModal" class="modal" style="display:none"><div class="modal-c" style="max-width:450px">';
    h+='<div class="st">🚚 Logistics Tracking</div>';
    h+='<div id="trackContent" style="margin-top:12px;max-height:400px;overflow-y:auto;font-size:13px"></div>';
    h+='<div style="margin-top:12px"><button class="btn bo" onclick="document.getElementById(\'trackModal\').style.display=\'none\'">Close</button></div>';
    h+='</div></div>';
    // Order Detail Popup
    h+='<div id="orderDetailModal" class="modal" style="display:none"><div class="modal-c" style="max-width:600px">';
    h+='<div class="st">📋 Order Details</div>';
    h+='<div id="orderDetailContent" style="margin-top:12px;font-size:13px;max-height:500px;overflow-y:auto"></div>';
    h+='<div style="margin-top:12px"><button class="btn bo" onclick="document.getElementById(\'orderDetailModal\').style.display=\'none\'">Close</button></div>';
    h+='</div></div>';
    document.getElementById("mc").innerHTML=h;
    // Loading Courier List
    fetch("/shop/express-companies",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
      if(!d.success)return;
      var sel=document.getElementById("shipCompany");
      if(!sel)return;
      sel.innerHTML='<option value="">-- Select Courier --</option>';
      (d.data||[]).forEach(function(c){sel.innerHTML+='<option value="'+c.code+'">'+esc(c.name)+'</option>'});
    });
  });
};
var _shipOid=0;
function showShipForm(oid,prodTitle){
  _shipOid=oid;
  document.getElementById("shipModalTitle").textContent="📦 Ship - Order #"+oid;
  document.getElementById("shipModalProduct").textContent="Product: "+prodTitle;
  document.getElementById("shipNumber").value="";
  document.getElementById("shipModal").style.display="block";
}
function submitShip(){
  var oid=_shipOid,co=document.getElementById("shipCompany").value,tr=document.getElementById("shipNumber").value.trim();
  if(!co||!tr){showToast("Select courier and enter tracking number","error");return}
  fetch("/shop/orders/"+oid+"/ship",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({company:co,tracking_number:tr})})
  .then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ "+d.message,"success");document.getElementById("shipModal").style.display="none";l_shop_orders()}
    else showToast(d.error||"Ship Failed","error");
  });
}
function showTrackInfo(oid){
  document.getElementById("trackContent").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  document.getElementById("trackModal").style.display="block";
  fetch("/shop/orders/"+oid+"/track",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("trackContent").innerHTML='<div style="color:#f85149">Query failed</div>';return}
    var data=d.data||{};
    var h='<div style="margin-bottom:10px;padding:8px 12px;background:var(--bg-glass);border-radius:8px;border:1px solid var(--border)">';
    h+='<div style="font-size:12px;color:var(--dim)">Express: '+esc(data.tracking_company||'')+'</div>';
    h+='<div style="font-size:12px;color:var(--dim)">Order No.: <span style="font-family:monospace">'+esc(data.tracking_number||'')+'</span></div>';
    if(data.shipped_at)h+='<div style="font-size:12px;color:var(--dim)">Ship Time: '+data.shipped_at.slice(0,16)+'</div>';
    if(data.state_text)h+='<div style="font-size:12px;margin-top:4px">Status: <span style="color:var(--accent3);font-weight:600">'+esc(data.state_text)+'</span></div>';
    h+='</div>';
    var traces=data.traces||[];
    if(data.track_error){
      h+='<div style="padding:8px 12px;color:#f85149;font-size:12px;background:rgba(248,81,73,.08);border-radius:6px">⚠️ '+esc(data.track_error)+'</div>';
    }
    if(traces.length===0){
      h+='<div style="text-align:center;padding:24px;color:var(--dim);font-size:13px">No tracking info available</div>';
    }else{
      h+='<div style="position:relative;padding-left:20px">';
      traces.forEach(function(t,i){
        var isLast=(i===traces.length-1);
        h+='<div style="position:relative;padding:0 0 16px 16px;border-left:2px solid '+(isLast?'var(--accent3)':'var(--border)')+'">';
        h+='<div style="position:absolute;left:-7px;top:0;width:12px;height:12px;border-radius:50%;background:'+(isLast?'var(--accent3)':'var(--border)')+'"></div>';
        h+='<div style="font-size:12px;font-weight:600;color:'+(isLast?'var(--accent3)':'var(--text)')+'">'+esc(t.station||'')+'</div>';
        h+='<div style="font-size:11px;color:var(--dim);margin-top:2px">'+(t.time||'')+'</div>';
        if(t.remark)h+='<div style="font-size:11px;color:var(--dim);margin-top:2px">'+esc(t.remark)+'</div>';
        h+='</div>';
      });
      h+='</div>';
    }
    document.getElementById("trackContent").innerHTML=h;
  });
}
function confirmOrder(id){
  if(!confirm("Confirm Order #"+id+" Mark as Paid？"))return;
  fetch("/shop/orders/"+id+"/confirm",{method:"POST",headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success){showToast("✅ Payment confirmed","success");l_shop_orders()}
      else showToast(d.error||"Confirm Failed","error");
    });
}
function showOrderDetail(id){
  var el=document.getElementById("orderDetailContent");
  el.innerHTML='<div class="lo"><div class="s"></div></div>';
  document.getElementById("orderDetailModal").style.display="block";
  fetch("/shop/orders/"+id+"/detail",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()}).then(function(d){
      if(!d.success){el.innerHTML='<div style="color:#f85149">Load failed</div>';return}
      var o=d.data;
      var stLabels={pending:'Pending Payment',paid:'Paid',refunded:'Refunded',cancelled:'Cancelled'};
      var shipLabels={'pending':'Pending Shipment','shipped':'Shipped','delivered':'Signed'};
      var h='';
      h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">';
      h+='<div><span style="color:var(--dim);font-size:11px">Order No.</span><div style="font-weight:600;font-family:monospace">'+o.order_no+'</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">Status</span><div>'+esc(stLabels[o.status]||o.status)+'</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">User</span><div>'+esc(o.display_name||o.username||o.phone||'#'+o.user_id)+' (ID: '+o.user_id+')</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">Phone</span><div>'+esc(o.phone||'-')+'</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">Product</span><div>'+esc(o.prod_title||'-')+' × '+o.quantity+'</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">Amount</span><div style="color:var(--accent);font-weight:700">¥'+o.subtotal+'</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">Discount</span><div>¥'+(o.discount||0)+'</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">Created</span><div>'+(o.created_at||'').slice(0,16)+'</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">Payment Time</span><div>'+(o.paid_at||'-')+'</div></div>';
      h+='<div><span style="color:var(--dim);font-size:11px">Logistics Status</span><div>'+(shipLabels[o.shipping_status]||'Pending Shipment')+'</div></div>';
      if(o.tracking_number){
        h+='<div><span style="color:var(--dim);font-size:11px">Tracking No.</span><div>'+esc(o.tracking_number||'')+'</div></div>';
        h+='<div><span style="color:var(--dim);font-size:11px">Courier</span><div>'+esc(o.shipping_company||'')+'</div></div>';
      }
      h+='</div>';
      // Payment History
      if(o.payments && o.payments.length>0){
        h+='<div style="font-weight:600;font-size:13px;margin-bottom:8px">💳 Payment History</div>';
        o.payments.forEach(function(p){
          h+='<div style="background:var(--bg-elevated);border-radius:8px;padding:10px;margin-bottom:6px;font-size:12px">';
          h+='<div style="display:flex;justify-content:space-between">';
          h+='<span>Method: '+esc(p.channel||p.payment_method||p.method||'-')+'</span>';
          h+='<span style="color:var(--accent)">¥'+(p.amount_fen?(p.amount_fen/100).toFixed(2):p.amount||'-')+'</span>';
          h+='</div><div style="color:var(--dim);margin-top:4px">'+(p.created_at||'').slice(0,16)+' · '+esc(p.status||'')+'</div>';
          h+='</div>';
        });
      }
      // Logistics Info
      if(o.shipping && o.shipping.length>0){
        h+='<div style="font-weight:600;font-size:13px;margin:12px 0 8px">🚚 Logistics Info</div>';
        o.shipping.forEach(function(s){
          h+='<div style="background:var(--bg-elevated);border-radius:8px;padding:10px;font-size:12px">';
          h+='<div>'+esc(s.company)+' · '+esc(s.tracking_number)+'</div>';
          h+='<div style="color:var(--dim);margin-top:4px">'+(s.created_at||'').slice(0,16)+'</div>';
          h+='</div>';
        });
      }
      el.innerHTML=h;
    });
}
function refundOrder(id){
  if(!confirm("Refund this order?"))return;
  fetch("/shop/orders/"+id+"/refund",{method:"POST",headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success){showToast("✅ Refunded","success");l_shop_orders()}
    });
}

// ============================
// 📦 Coupon Management — l_shop_coupons
// ============================

window.l_shop_coupons=function(){
  document.getElementById("pt").textContent="📦 Coupons";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  loadCouponView();
};
function loadCouponView(){
  fetch("/shop/coupons",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var cs=d.data||[];
    var h='<div class="sbar"><button class="btn bp" onclick="showCouponForm()">+ New Coupons</button>';
    h+='<button class="btn bs bo" onclick="loadCouponStats()">📊 Statistics</button>';
    h+='<input id="couponSearch" placeholder="Search Code/Name..." oninput="filterCoupons()" style="flex:1;max-width:200px;height:30px;padding:0 10px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text)"></div>';
    // Stats Summary
    h+='<div class="gr" id="couponSummary"></div>';
    // Coupon Form
    h+='<div class="cd" id="couponForm" style="display:none;margin-top:16px"><div class="st" id="couponFormTitle">New Coupons</div>';
    h+='<div class="g2"><div><label>Coupon Code</label><input class="in" id="cCode" style="width:100%;font-family:monospace" placeholder="SUMMER2026"></div>';
    h+='<div><label>Name</label><input class="in" id="cName" style="width:100%" placeholder="Summer Sale"></div></div>';
    h+='<div class="g3"><div><label>Categories</label><select class="sl" id="cCategory"><option value="general">General Coupon</option><option value="new_user">New User Offer</option><option value="threshold">Discount Coupon</option><option value="promotion">Promo Coupon</option></select></div>';
    h+='<div><label>Discount Type</label><select class="sl" id="cType" onchange="toggleCouponType()"><option value="fixed">Fixed Amount</option><option value="percent">Percentage</option><option value="free_shipping">Free Shipping</option><option value="first_month_percent">First Month Special</option></select></div>';
    h+='<div><label>Face Value</label><input class="in" id="cValue" type="number" step="0.01" placeholder="0.00" style="width:100%"></div></div>';
    h+='<div class="g3"><div><label>Min. Spend (¥)</label><input class="in" id="cMin" type="number" step="0.01" value="0" style="width:100%"></div>';
    h+='<div><label>Minimum Purchase Qty</label><input class="in" id="cMinQty" type="number" value="0" style="width:100%"></div>';
    h+='<div><label>Per User Limit</label><input class="in" id="cPerUser" type="number" value="1" style="width:100%"></div></div>';
    h+='<div class="g2"><div><label>Usage Count Limit (0=Unlimited)</label><input class="in" id="cLimit" type="number" value="0" style="width:100%"></div>';
    h+='<div><label>Expiry Time</label><input class="in" id="cExpire" type="date" style="width:100%"></div></div>';
    h+='<div><label>Description</label><textarea class="ta" id="cDesc" style="width:100%;height:50px;font-size:11px" placeholder="Optional：Coupon Description，Display to User"></textarea></div>';
    h+='<div><label>Applicable ProductsID (Comma Separated，Leave Empty=All)</label><input class="in" id="cProducts" style="width:100%;font-family:monospace" placeholder="1,5,12"></div>';
    h+='<div style="margin-top:8px;display:flex;gap:8px"><button class="btn bp" onclick="saveCoupon()">Save</button><button class="btn bo" onclick="hideCouponForm()">Cancel</button></div>';
    h+='<input type="hidden" id="cEditId" value=""></div>';
    // Coupon table
    h+='<div class="cd"><div class="st">Coupons List ('+cs.length+')</div><div style="overflow-x:auto"><table id="couponTable"><tr><th>ID</th><th>Code</th><th>Name</th><th>Categories</th><th>Type</th><th>Face Value</th><th>Min. Spend</th><th>Used/Total</th><th>Usage Rate</th><th>Expired</th><th>Status</th><th>Actions</th></tr>';
    if(!cs.length)h+='<tr><td colspan="12"><div class="em">No Coupons</div></td></tr>';
    else cs.forEach(function(c){
      var st=c.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Disable</span>';
      var catMap={general:'General',new_user:'New User',threshold:'Discount',promotion:'Promotion'};
      var typeMap={fixed:'Fixed',percent:'Percentage',free_shipping:'Free Shipping'};
      h+='<tr class="couponRow" data-search="'+esc(c.code+' '+c.name).toLowerCase()+'"><td>'+c.id+'</td>';
      h+='<td style="font-family:monospace">'+esc(c.code)+'</td>';
      h+='<td>'+esc(c.name||'-')+'</td>';
      h+='<td>'+(catMap[c.coupon_category]||c.coupon_category)+'</td>';
      h+='<td>'+(typeMap[c.coupon_type]||c.coupon_type)+'</td>';
      h+='<td>'+(c.coupon_type==='percent'?c.value+'%':'¥'+c.value)+'</td>';
      h+='<td>¥'+(c.min_amount||0)+'</td>';
      h+='<td>'+c.used_count+'/'+(c.usage_limit||'∞')+'</td>';
      h+='<td>'+(c.usage_rate||0)+'%</td>';
      h+='<td style="font-size:10px;white-space:nowrap">'+(c.expire_at?c.expire_at.slice(0,10):'Permanent')+'</td><td>'+st+'</td>';
      h+='<td style="white-space:nowrap"><button class="btn bs bo" onclick="showCouponForm('+c.id+')">Edit</button> ';
      h+='<button class="btn bs bo" onclick="toggleCoupon('+c.id+','+(c.is_active?0:1)+')">'+(c.is_active?'Disable':'Enabled')+'</button> ';
      h+='<button class="btn bs bo" onclick="showDistributeForm('+c.id+',\''+esc(c.code)+'\')">Issue</button> ';
      h+='<button class="btn bs bo" onclick="showRedemptions('+c.id+')">Record</button></td></tr>';
    });
    h+='</table></div></div>';
    // Distribute form
    h+='<div class="cd" id="distributeForm" style="display:none;margin-top:16px"><div class="st">Issue Coupons <span id="distCode"></span></div>';
    h+='<div style="margin-bottom:8px"><label><input type="radio" name="distMode" value="all" checked onchange="toggleDistMode()"> Issue to All Users</label>';
    h+='<label style="margin-left:16px"><input type="radio" name="distMode" value="specific" onchange="toggleDistMode()"> Specific UserID</label></div>';
    h+='<div id="distUserIds" style="display:none"><textarea class="ta" id="distUserIdsInput" placeholder="One Per Line UsersID" style="width:100%;height:80px;font-size:11px"></textarea></div>';
    h+='<div style="margin-top:8px"><button class="btn bp" onclick="doDistribute()">Confirm Issuance</button> <button class="btn bo" onclick="document.getElementById(\'distributeForm\').style.display=\'none\'">Cancel</button></div>';
    h+='<input type="hidden" id="distCouponId"></div>';
    // Redemption log
    h+='<div class="cd" id="redemptionLog" style="display:none;margin-top:16px"><div class="st">Usage History</div><div id="redemptionContent"></div></div>';
    document.getElementById("mc").innerHTML=h;
    // Load summary stats
    loadCouponStats(true);
  });
}
function filterCoupons(){
  var q=(document.getElementById("couponSearch")?.value||"").toLowerCase();
  document.querySelectorAll(".couponRow").forEach(function(r){
    r.style.display=(!q||r.getAttribute("data-search").includes(q))?"":"none";
  });
}
function loadCouponStats(summaryOnly){
  fetch("/shop/coupons/stats",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var s=d.data;
    var summaryEl=document.getElementById("couponSummary");
    if(summaryEl){
      summaryEl.innerHTML=hk("Total Coupons",s.total_coupons,"")+hk("Enabling",s.active_coupons,"#3fb950")+hk("Total Usage Count",s.total_used,"#58a6ff")+hk("Total Saved","¥"+s.total_discount,"#d2a8ff");
    }
    if(!summaryOnly){
      // Show full stats view
      var h='<div class="gr">'+hk("Total Coupons",s.total_coupons,"")+hk("Enabling",s.active_coupons,"#3fb950")+hk("Total Usage Count",s.total_used,"#58a6ff")+hk("Total Saved","¥"+s.total_discount,"#d2a8ff")+'</div>';
      if(s.by_category&&s.by_category.length){
        h+='<div class="cd"><div class="st">Statistics by Category</div><table><tr><th>Categories</th><th>Count</th></tr>';
        s.by_category.forEach(function(x){h+='<tr><td>'+esc(x.coupon_category)+'</td><td>'+x.c+'</td></tr>'});
        h+='</table></div>';
      }
      if(s.top_used&&s.top_used.length){
        h+='<div class="cd"><div class="st">Usage Rank Top 10</div><table><tr><th>Code</th><th>Name</th><th>Usage Count</th></tr>';
        s.top_used.forEach(function(x){h+='<tr><td>'+esc(x.code)+'</td><td>'+esc(x.name||'-')+'</td><td>'+x.used_count+'</td></tr>'});
        h+='</table></div>';
      }
      h+='<div style="margin-top:8px"><button class="btn bo" onclick="l_shop_coupons()">← Back to List</button></div>';
      document.getElementById("mc").innerHTML=h;
    }
  });
}
// ── Form helpers ──
window.couponCategoryMap={general:'General',new_user:'New User Offer',threshold:'Discount',promotion:'Promotion'};
window.couponTypeMap={fixed:'Fixed Amount',percent:'Percentage',free_shipping:'Free Shipping',first_month_percent:'First Month Special'};
function toggleCouponType(){
  var t=document.getElementById("cType").value;
  document.getElementById("cValue").disabled=(t==='free_shipping');
  if(t==='free_shipping')document.getElementById("cValue").value=0;
}
function showCouponForm(id){
  document.getElementById("cEditId").value=id||"";
  document.getElementById("couponFormTitle").textContent=id?"Edit Coupons":"New Coupons";
  if(id){
    fetch("/shop/coupons",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
      var c=(d.data||[]).find(function(x){return x.id==id});if(!c)return;
      document.getElementById("cCode").value=c.code||"";
      document.getElementById("cName").value=c.name||"";
      document.getElementById("cCategory").value=c.coupon_category||"general";
      document.getElementById("cType").value=c.coupon_type||"fixed";
      document.getElementById("cValue").value=c.value||"";
      document.getElementById("cMin").value=c.min_amount||"";
      document.getElementById("cMinQty").value=c.min_quantity||0;
      document.getElementById("cPerUser").value=c.per_user_limit||1;
      document.getElementById("cLimit").value=c.usage_limit||"";
      document.getElementById("cExpire").value=(c.expire_at||"").slice(0,10);
      document.getElementById("cDesc").value=c.description||"";
      document.getElementById("cProducts").value=c.applicable_products||"";
      toggleCouponType();
    });
  }else{
    ["cCode","cName","cValue","cMin","cLimit","cExpire","cDesc","cProducts"].forEach(function(i){
      var el=document.getElementById(i);if(el)el.value=""
    });
    document.getElementById("cCategory").value="general";
    document.getElementById("cType").value="fixed";
    document.getElementById("cMinQty").value=0;
    document.getElementById("cPerUser").value=1;
  }
  document.getElementById("couponForm").style.display="block";
  document.getElementById("couponForm").scrollIntoView({behavior:"smooth"});
}
function hideCouponForm(){
  document.getElementById("couponForm").style.display="none";
  document.getElementById("cEditId").value="";
}
function saveCoupon(){
  var id=document.getElementById("cEditId").value;
  var data={
    code: document.getElementById("cCode").value.trim().toUpperCase(),
    name: document.getElementById("cName").value.trim(),
    coupon_category: document.getElementById("cCategory").value,
    coupon_type: document.getElementById("cType").value,
    value: parseFloat(document.getElementById("cValue").value)||0,
    min_amount: parseFloat(document.getElementById("cMin").value)||0,
    min_quantity: parseInt(document.getElementById("cMinQty").value)||0,
    per_user_limit: parseInt(document.getElementById("cPerUser").value)||1,
    usage_limit: parseInt(document.getElementById("cLimit").value)||0,
    expire_at: document.getElementById("cExpire").value||"",
    description: document.getElementById("cDesc").value.trim(),
    applicable_products: document.getElementById("cProducts").value.trim()
  };
  if(!data.code){showToast("Enter coupon code","error");return;}
  var url=id?"/shop/coupons/"+id:"/shop/coupons";
  var method=id?"PUT":"POST";
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success){showToast(id?"✅ Updated":"✅ Created","success");hideCouponForm();l_shop_coupons()}
      else showToast(d.error||"Failed","error");
    });
}
function toggleCoupon(id,active){
  fetch("/shop/coupons/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({is_active:active})})
    .then(function(r){return r.json()}).then(function(d){if(d.success){showToast("✅ Completed","success");l_shop_coupons()}});
}
// ── Distribute ──
function showDistributeForm(cid,code){
  document.getElementById("distCouponId").value=cid;
  document.getElementById("distCode").textContent="— "+code;
  document.getElementById("distributeForm").style.display="block";
  document.getElementById("distributeForm").scrollIntoView({behavior:"smooth"});
}
function toggleDistMode(){
  var mode=document.querySelector('input[name="distMode"]:checked').value;
  document.getElementById("distUserIds").style.display=mode==="specific"?"block":"none";
}
function doDistribute(){
  var cid=document.getElementById("distCouponId").value;
  var mode=document.querySelector('input[name="distMode"]:checked').value;
  var data={coupon_id:parseInt(cid),all_users:mode==="all"};
  if(mode==="specific"){
    var ids=document.getElementById("distUserIdsInput").value.trim().split("\n").map(function(x){return parseInt(x.trim())}).filter(function(x){return!isNaN(x)});
    if(!ids.length){showToast("Enter user ID","error");return}
    data.user_ids=ids;
  }
  fetch("/shop/coupons/distribute",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success){showToast(d.message||"✅ Issued","success");document.getElementById("distributeForm").style.display="none";l_shop_coupons()}
      else showToast(d.error||"Failed","error");
    });
}
// ── Redemption Log ──
function showRedemptions(cid){
  var el=document.getElementById("redemptionLog");
  var content=document.getElementById("redemptionContent");
  el.style.display="block";
  content.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  el.scrollIntoView({behavior:"smooth"});
  fetch("/shop/coupons/"+cid+"/redemptions",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var rs=d.data;
    var h='<div style="margin-bottom:6px;color:var(--dim)">共 '+rs.total+' Records</div><table><tr><th>ID</th><th>User</th><th>Order No.</th><th>Discount(分)</th><th>Time</th></tr>';
    if(!rs.redemptions||!rs.redemptions.length)h+='<tr><td colspan="5"><div class="em">No Usage History</div></td></tr>';
    else rs.redemptions.forEach(function(r){
      h+='<tr><td>'+r.id+'</td><td>'+(r.nickname||r.phone||'#'+r.user_id)+'</td><td style="font-size:10px">'+esc(r.order_no)+'</td><td>'+(r.discount_fen/100).toFixed(2)+'</td><td style="font-size:10px;color:var(--dim)">'+(r.created_at||'').slice(0,16)+'</td></tr>';
    });
    h+='</table>';
    content.innerHTML=h;
  });
}

// ============================
// 📦 Shop — l_shop_purchases (Purchases)
// ============================

window.l_shop_purchases=function(){
  document.getElementById("pt").textContent="📦 Purchase History";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/shop/purchases",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var ps=d.data||[];
    var h='<div class="cd"><div class="st">Purchases</div><table><tr><th>ID</th><th>User</th><th>Product</th><th>Type</th><th>Expired</th><th>Status</th><th>Time</th></tr>';
    if(!ps.length)h+='<tr><td colspan="7"><div class="em">No Records</div></td></tr>';
    else ps.forEach(function(p){
      var stt={active:'<span class="bdg on">Active</span>',expired:'<span class="bdg off">Expired</span>',cancelled:'<span class="bdg pd">Cancelled</span>'};
      var tp={once:'One-Time Purchase',subscription:'Subscribe'};
      h+='<tr><td>'+p.id+'</td><td>'+(p.username||p.phone||'#'+p.user_id)+'</td>';
      h+='<td>'+esc(p.prod_title)+'</td><td>'+(tp[p.purchase_type]||p.purchase_type)+'</td>';
      h+='<td style="font-size:10px">'+(p.expire_at?p.expire_at.slice(0,10):'--')+'</td>';
      h+='<td>'+(stt[p.status]||p.status)+'</td><td style="font-size:10px;color:var(--dim)">'+(p.created_at||'').slice(0,16)+'</td></tr>';
    });
    h+='</table></div>';
    document.getElementById("mc").innerHTML=h;
  });
};

// ============================
// Revenue Dashboard — l_sub_stats
// ============================

window.l_sub_stats=function(){
  document.getElementById("pt").textContent="Revenue Dashboard";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/admin/revenue/dashboard",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return _fallback_sub_stats();
    var ds=d.data;
    var h='<div class="g2">';
    h+=hk("Today Revenue","¥"+ds.summary.today_revenue,"#d2a8ff");
    h+=hk("Monthly Revenue","¥"+ds.summary.this_month,"#f0883e");
    h+=hk("Last Month Revenue","¥"+ds.summary.last_month,"");
    h+=hk("MoM",(ds.summary.month_change>=0?'+':'')+ds.summary.month_change_pct+'%',ds.summary.month_change>=0?'#3fb950':'#f85149');
    h+=hk("MRR","¥"+ds.mrr,"#00d4aa");
    h+=hk("Active Subscriptions",ds.active_subscriptions,"#58a6ff");
    h+=hk("Paid Users",ds.total_paid_users,"");
    h+=hk("This Year","¥"+ds.summary.this_year,"#58a6ff");
    h+='</div>';

    // 30-day trend bar chart
    var trend=ds.trend_30d||[];
    if(trend.length){
      var maxRev=0;
      trend.forEach(function(t){if(t.revenue>maxRev)maxRev=t.revenue});
      maxRev=maxRev||1;
      h+='<div class="cd" style="margin-top:16px"><div class="st">近30Daily Revenue Trend</div><div style="display:flex;align-items:flex-end;gap:2px;height:140px;padding-top:10px">';
      trend.forEach(function(t){
        var pct=Math.max(3,t.revenue/maxRev*100);
        h+='<div style="flex:1;display:flex;flex-direction:column;align-items:center;height:140px;justify-content:flex-end">';
        h+='<div style="width:100%;background:'+(t.revenue>0?'var(--accent)':'var(--border)')+';height:'+pct+'%;border-radius:2px 2px 0 0;min-height:2px" title="'+esc(t.day)+': ¥'+t.revenue+'"></div>';
        h+='<div style="font-size:7px;color:var(--dim);margin-top:2px;transform:rotate(-45deg);white-space:nowrap">'+t.day.slice(5)+'</div></div>';
      });
      h+='</div></div>';
    }

    // Revenue by type
    var byType=ds.by_type||[];
    if(byType.length){
      h+='<div class="cd" style="margin-top:16px"><div class="st">Revenue Type Distribution</div><table><tr><th>Type</th><th>Amount</th><th>Percentage</th></tr>';
      var totalType=0;
      byType.forEach(function(t){totalType+=t.revenue});
      totalType=totalType||1;
      byType.forEach(function(t){
        var pct=(t.revenue/totalType*100).toFixed(1);
        h+='<tr><td>'+esc(t.type)+'</td><td>¥'+t.revenue+'</td><td><div style="display:flex;align-items:center;gap:6px"><div style="background:var(--accent);width:'+pct+'px;max-width:100px;height:8px;border-radius:4px"></div>'+pct+'%</div></td></tr>';
      });
      h+='</table></div>';
    }

    // 12-month revenue
    var monthly=ds.monthly_12m||[];
    if(monthly.length){
      h+='<div class="cd" style="margin-top:16px"><div class="st">近12Monthly Revenue</div><table><tr><th>Month</th><th>Revenue</th></tr>';
      monthly.forEach(function(m){
        h+='<tr><td>'+esc(m.ym)+'</td><td>¥'+m.revenue+'</td></tr>';
      });
      h+='</table></div>';
    }

    // Payment methods
    var pm=ds.pay_methods||[];
    if(pm.length){
      h+='<div class="cd" style="margin-top:16px"><div class="st">Payment Method Distribution</div><table><tr><th>Method</th><th>Amount</th></tr>';
      pm.forEach(function(p){
        var mn={'wechat':'WeChat Pay','alipay':'Alipay','wxpay':'WeChat Pay'}[p.method]||p.method;
        h+='<tr><td>'+mn+'</td><td>¥'+p.revenue+'</td></tr>';
      });
      h+='</table></div>';
    }

    document.getElementById("mc").innerHTML=h;
  }).catch(function(e){
    _fallback_sub_stats();
  });
}
function _fallback_sub_stats(){
  fetch("/subscription/admin/stats",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var ds=d.data||d;
    var h='<div class="g2">';
    h+=hk("MRR",ds.mrr_yuan||('¥'+(ds.mrr/100).toFixed(2)),"#00d4aa");
    h+=hk("Active Subscriptions",ds.active_subscriptions||0,"#58a6ff");
    h+=hk("Monthly New",ds.new_this_month||0,"#3fb950");
    h+=hk("Monthly Cancellations",ds.canceled_this_month||0,"#f85149");
    h+=hk("Today Revenue","¥"+(ds.today_revenue_fen/100).toFixed(2),"#d2a8ff");
    h+=hk("Monthly Revenue","¥"+(ds.month_revenue_fen/100).toFixed(2),"#f0883e");
    h+='</div>';
    if(ds.distribution&&ds.distribution.length){
      h+='<div class="cd" style="margin-top:16px"><div class="st">Plan Distribution</div><table><tr><th>Plan</th><th>Active Count</th></tr>';
      ds.distribution.forEach(function(x){
        h+='<tr><td>'+esc(x.name||x.plan_key)+'</td><td>'+x.c+'</td></tr>';
      });
      h+='</table></div>';
    }
    document.getElementById("mc").innerHTML=h;
  });
}

// ============================
// Billing Log — l_sub_events
// ============================

window.l_sub_events=function(){
  document.getElementById("pt").textContent="Billing Log";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/subscription/admin/events?limit=100",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var events=d.data&&d.data.events?d.data.events:(d.events||[]);
    var h='<div class="cd"><div class="st">Debit Event ('+events.length+')</div><table><tr><th>User</th><th>Type</th><th>Channel</th><th>Amount</th><th>Result</th><th>Reason</th><th>Time</th></tr>';
    if(!events.length)h+='<tr><td colspan="7"><div class="em">No Events</div></td></tr>';
    else events.forEach(function(e){
      var rcls=e.result=='success'?'on':'off';
      h+='<tr><td>'+esc(e.nickname||'UID:'+e.user_id)+'</td><td>'+esc(e.event_type)+'</td>';
      h+='<td>'+esc(e.channel)+'</td>';
      h+='<td>'+(e.amount_fen?'¥'+(e.amount_fen/100).toFixed(2):'-')+'</td>';
      h+='<td><span class="bdg '+rcls+'">'+(e.result||'unk')+'</span></td>';
      h+='<td style="font-size:11px">'+esc(e.fail_reason||'-')+'</td>';
      h+='<td style="font-size:11px">'+(e.created_at||'').slice(0,16)+'</td></tr>';
    });
    h+='</table></div>';
    document.getElementById("mc").innerHTML=h;
  }).catch(function(e){
    document.getElementById("mc").innerHTML='<div class="em">Request Failed — Check Network or<a href="javascript:go(\'model_providers\')">Refresh &amp; Retry</a><br><span style="font-size:10px;color:var(--dim)">'+esc(String(e))+'</span></div>';
  });
}


window.l_orders=function(){
  document.getElementById("pt").textContent="Order Management";
  fetch("/admin/orders?limit=100",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var ds=d.data;
    var h="<div class=\"cd\"><div class=\"st\">Order ("+ds.total+")</div><table><tr><th>Order No.</th><th>User</th><th>Amount</th><th>Type</th><th>Status</th><th>Time</th></tr>";
    ds.orders.forEach(function(o){
      var st=o.status=="paid"?'<span class="bdg on">Paid</span>':'<span class="bdg pd">'+o.status+'</span>';
      h+="<tr><td>"+o.order_no+"</td><td>"+(o.user_name||"-")+"</td><td>\u00a5"+o.amount+"</td><td>"+o.item_type+"</td><td>"+st+"</td><td>"+(o.created_at||"")+"</td></tr>";
    });
    h+="</table></div>";
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){})
}


window.l_oauth=function(){
  document.getElementById("pt").textContent="OAuth Login Config";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/admin/oauth/configs?provider=all",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){mc.innerHTML='<div class="em">Load failed</div>';return}
    var h='';
    h+='<div class="cd" style="margin-bottom:12px"><div class="st">Add/Edit Site OAuth Config</div>';
    h+='<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:8px">';
    h+='<div><div style="font-size:11px;color:var(--dim)">Site Domain</div><input class="in" id="oaDomain" placeholder="shop.abc.com" style="width:100%"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Login Platform</div><select class="in" id="oaProvider" style="width:100%" onchange="oaProviderChange()">';
    h+='<option value="douyin">Douyin</option>';
    h+='<option value="wechat">WeChat</option>';
    h+='<option value="alipay">Alipay</option>';
    h+='</select></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Client Key (AppID)</div><input class="in" id="oaKey" placeholder="Open Platform App ID" style="width:100%"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Client Secret</div><input class="in" id="oaSecret" type="password" placeholder="Required on First Entry，Edit (Optional)" style="width:100%"></div>';
    h+='</div>';
    h+='<div style="color:var(--dim);font-size:11px;margin-bottom:8px">Callback URL Auto-Generated: <code style="color:var(--accent)" id="oaCallbackPreview">https://<span id="oaDomainPreview">Your Domain</span>/auth/douyin/callback</code></div>';
    h+='<button class="btn bp" onclick="oaSave()">Save</button></div>';
    h+='<div class="cd"><div class="st">Configured Sites</div>';
    h+='<table><tr><th>Domain</th><th>Platform</th><th>Client Key</th><th>Client Secret</th><th>Status</th><th>Callback URL</th><th>Actions</th></tr>';
    (d.data||[]).forEach(function(c){
      var providerLabel={'douyin':'Douyin','wechat':'WeChat','alipay':'Alipay'}[c.provider]||c.provider;
      var callbackPath={'douyin':'/auth/douyin/callback','wechat':'/auth/wechat/callback','alipay':'/auth/alipay/callback'}[c.provider]||'/auth/douyin/callback';
      h+='<tr><td>'+esc(c.site_domain)+'</td>';
      h+='<td><span class="bdg">'+providerLabel+'</span></td>';
      h+='<td><code>'+esc(c.client_key)+'</code></td>';
      h+='<td><code style="color:var(--dim)">'+(c.has_secret?esc(c.client_secret_masked):'<span style="color:#f85149">Not Configured</span>')+'</code></td>';
      h+='<td>'+(c.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Disable</span>')+'</td>';
      h+='<td><code style="font-size:10px">https://'+esc(c.site_domain)+callbackPath+'</code></td>';
      h+='<td><button class="btn bo bs" onclick="oaEdit('+c.id+',\''+c.provider+'\')">Edit</button> <button class="btn bo bs" style="color:#f85149" onclick="oaDelete('+c.id+')">Delete</button></td></tr>';
    });
    h+='</table></div>';
    mc.innerHTML=h;
  }).catch(function(){mc.innerHTML='<div class="em">Request Failed</div>'});
};
function oaProviderChange(){
  var provider=document.getElementById("oaProvider").value;
  var domain=document.getElementById("oaDomain").value.trim()||'Your Domain';
  var paths={'douyin':'/auth/douyin/callback','wechat':'/auth/wechat/callback','alipay':'/auth/alipay/callback'};
  document.getElementById("oaCallbackPreview").innerHTML='https://<span id="oaDomainPreview">'+domain+'</span>'+paths[provider];
}
function oaEdit(id,provider){
  fetch("/admin/oauth/configs?provider=all",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var cfg=d.data.find(function(x){return x.id===id});
    if(!cfg)return;
    document.getElementById("oaDomain").value=cfg.site_domain;
    document.getElementById("oaProvider").value=provider;
    document.getElementById("oaKey").value=cfg.client_key;
    document.getElementById("oaSecret").value="";
    document.getElementById("oaSecret").placeholder=cfg.has_secret?"Configured（Leave Empty to Keep Original）":"Please enter Secret";
    document.getElementById("oaDomain").dataset.editId=id;
    document.getElementById("oaDomainPreview").textContent=cfg.site_domain;
    oaProviderChange();
  });
}
function oaSave(){
  var domain=document.getElementById("oaDomain").value.trim();
  var provider=document.getElementById("oaProvider").value;
  var key=document.getElementById("oaKey").value.trim();
  var secret=document.getElementById("oaSecret").value.trim();
  if(!domain||!key){showToast("Please fill in domain and Client Key","error");return}
  fetch("/admin/oauth/configs",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({site_domain:domain,provider:provider,client_key:key,client_secret:secret})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ Saved，Callback URL: "+d.data.callback_url,"success");window.l_oauth()}
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}
function oaDelete(id){
  if(!confirm("Delete this config?"))return;
  fetch("/admin/oauth/configs/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Deleted");window.l_oauth()}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

window.l_config=function(){
  document.getElementById("pt").textContent="Basic Settings";
  var h='<div class="cd">';
  h+='<div id="config-tab-content"></div>';
  h+='</div>';
  document.getElementById("mc").innerHTML=h;
  loadSystemConfig();
}
function loadSystemConfig(){
  fetch("/user/config",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("config-tab-content").innerHTML='<div class="em">Cannot Load</div>';return}
    var cats=d.categories||[{id:"other",title:"System Settings"}];
    var data=d.data||[];
    var schema=d.schema||{};
    var c="";
    cats.forEach(function(cat){
      var items=data.filter(function(k){return k.category==cat.id});
      if(!items.length)return;
      c+='<div class="cd" style="margin-bottom:12px">';
      c+='<div class="st">'+cat.title+'</div>';
      items.forEach(function(k){
        var isSensitive=k.sensitive;
        var displayVal=k.sensitive?k.masked_value:k.value;
        var safeVal=(k.value||"").replace(/"/g,"&quot;");
        var safeMasked=(k.masked_value||"").replace(/"/g,"&quot;");
        var label=k.label||k.key;
        var ph=k.placeholder||"";
        c+='<div class="fl">';
        c+='<div style="flex:1;min-width:0">';
        c+='<div style="font-size:12px;font-weight:600">'+label+'</div>';
        c+='<div style="font-size:10px;color:var(--dim)">'+(k.description||"")+'</div></div>';
        if(isSensitive){
          c+='<input class="in" id="cf-'+k.key+'" type="password" value="'+safeMasked+'" placeholder="'+ph+'" style="width:180px" onfocus="this.value=\'\'" onblur="if(!this.value)this.value=\''+safeMasked+'\'">';
        }else{
          c+='<input class="in" id="cf-'+k.key+'" value="'+safeVal+'" placeholder="'+ph+'" style="width:200px">';
        }
        c+='<button class="btn bp bs" onclick="scfg(\''+k.key+'\')">Save</button></div>';
      });
      c+='</div>';
    });
    document.getElementById("config-tab-content").innerHTML=c||'<div class="em">No Config Item</div>';
    loadSmsTemplatesConfig();
  }).catch(function(){document.getElementById("config-tab-content").innerHTML='<div class="em">Load failed</div>'})
}
function loadSmsTemplatesConfig(){
  var ct=document.getElementById("config-tab-content");
  ct.insertAdjacentHTML("beforeend",'<div id="sms-config-loader" style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div>Encoding Loading...</div>');
  fetch("/admin/sms/templates",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById("sms-config-loader");if(loader)loader.remove();
    var h='<div class="cd" style="margin-top:12px" id="sms-config-section"><div class="st">Encoding Settings</div>';
    h+='<div style="margin-bottom:12px"><button class="btn bp" onclick="showSmsForm()">+ Add Template</button></div>';
    h+='<div id="smsForm" style="display:none;margin-bottom:16px" class="cd"><div class="st" id="smsFormTitle">Add Template</div>';
    h+='<div class="g2">';
    h+='<div><div style="font-size:11px;color:var(--dim)">Categories</div><select class="sl" id="smsCat" style="width:100%"><option value="captcha">Verification Code</option><option value="notice">SMS Notification</option><option value="promo">SMS Promotion</option></select></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Name</div><input class="in" id="smsName" placeholder="如：New User Registration" style="width:100%"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Templates CODE</div><input class="in" id="smsCode" placeholder="SMS_xxxxxxxxx" style="width:100%"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Notes</div><input class="in" id="smsNote" placeholder="Usage Description" style="width:100%"></div>';
    h+='</div>';
    h+='<div style="margin-top:10px"><button class="btn bp" onclick="saveSmsTemplate()">Save</button> <button class="btn bo" onclick="document.getElementById(\'smsForm\').style.display=\'none\'">Cancel</button><input type="hidden" id="smsEditId" value=""></div></div>';
    if(!d.success||!d.data){h+='<div class="em">Load failed</div>'}
    else{
      var cats=d.data.categories;
      h+='<div id="smsTemplates">';
      var order=["captcha","notice","promo"];
      var hasItems=false;
      order.forEach(function(k){
        var c=cats[k];
        if(!c||!c.items||!c.items.length)return;
        hasItems=true;
        h+='<div class="cd" style="margin-bottom:12px"><div class="st">'+c.title+' ('+c.items.length+')</div><table><tr><th>Name</th><th>Templates CODE</th><th>Notes</th><th>Actions</th></tr>';
        c.items.forEach(function(t){
          h+='<tr><td>'+esc(t.name)+'</td><td style="font-family:monospace;color:var(--accent)">'+esc(t.template_code)+'</td><td style="color:var(--dim)">'+esc(t.note)+'</td>';
          h+='<td><button class="btn bo bs" onclick="editSmsTemplate('+t.id+',\''+t.category+'\',\''+esc(t.name)+'\',\''+esc(t.template_code)+'\',\''+esc(t.note)+'\')">Edit</button> ';
          h+='<button class="btn bo bs" onclick="deleteSmsTemplate('+t.id+')">Delete</button></td></tr>';
        });
        h+='</table></div>';
      });
      if(!hasItems)h+='<div class="em">No Templates，Click「+ Add Template」Create</div>';
      h+='</div>';
    }
    h+='</div>';
    ct.insertAdjacentHTML("beforeend",h);
  }).catch(function(){
    var loader=document.getElementById("sms-config-loader");if(loader)loader.remove();
    ct.insertAdjacentHTML("beforeend",'<div class="em">Encoding Load Failed</div>');
  })
}
function loadNavConfig(){
  var ct=document.getElementById("config-tab-content");
  ct.insertAdjacentHTML("beforeend",'<div id="hn-loader" style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div>Main Nav Loading...</div>');
  fetch("/admin/footer-nav",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById("hn-loader");if(loader)loader.remove();
    if(!d.success){ct.insertAdjacentHTML("beforeend",'<div class="em">Load failed</div>');loadFooterLinksConfig();return}
    var h='<div class="cd" style="margin-top:24px"><div class="st">Main Nav Management</div>';
    h+='<div style="margin-bottom:12px"><button class="btn bp" onclick="hnShowAddForm()">+ Add Nav</button></div>';
    h+='<div id="hn-list"><table><tr><th style="width:50px">Sort</th><th>Title</th><th style="width:240px">URL</th><th style="width:50px">Status</th><th style="width:100px">Actions</th></tr>';
    if(!d.data.length){h+='<tr><td colspan="5" class="em">No Nav Items</td></tr>'}
    else{d.data.forEach(function(m,i){
      h+='<tr data-hn-id="'+m.id+'" data-hn-title="'+escAttr(m.title)+'" data-hn-url="'+escAttr(m.url)+'" data-hn-enabled="'+(m.is_enabled?1:0)+'"><td style="display:flex;gap:2px;align-items:center;justify-content:center">';
      if(i>0)h+='<button class="btn bo bs" style="padding:2px 4px;font-size:10px" onclick="hnMove('+m.id+',\'up\')">▲</button>';
      else h+='<span style="width:22px"></span>';
      if(i<d.data.length-1)h+='<button class="btn bo bs" style="padding:2px 4px;font-size:10px" onclick="hnMove('+m.id+',\'down\')">▼</button>';
      else h+='<span style="width:22px"></span>';
      h+='</td><td>'+esc(m.title)+'</td><td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="hnEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="hnDelete('+m.id+',\''+escAttr(m.title)+'\')">Delete</button></td></tr>'
    })}
    h+='</table></div></div>';ct.insertAdjacentHTML("beforeend",h);
    loadFooterLinksConfig();
  }).catch(function(){ct.insertAdjacentHTML("beforeend",'<div class="em">Request Failed</div>');loadFooterLinksConfig()})
}
function hnShowAddForm(){
  var ct=document.getElementById("hn-list");
  var existing=document.getElementById("hn-add-row");if(existing)existing.remove();
  var h='<tr id="hn-add-row" style="background:rgba(0,245,255,0.05)"><td colspan="5">';
  h+='<div style="display:flex;gap:8px;align-items:center;padding:6px 0"><input class="in" id="hn-add-title" placeholder="Title" style="width:100px"><input class="in" id="hn-add-url" placeholder="URL" style="flex:1"><button class="btn bp" onclick="hnDoAdd()">Add</button><button class="btn bo" onclick="document.getElementById(\'hn-add-row\').remove()">Cancel</button></div>';
  h+='</td></tr>';
  ct.querySelector("table").insertAdjacentHTML("beforeend",h);
}
function hnDoAdd(){
  var title=document.getElementById("hn-add-title").value.trim();
  var url=document.getElementById("hn-add-url").value.trim();
  if(!title||!url){showToast("Title and URL required","error");return}
  fetch("/admin/footer-nav",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({title:title,url:url,is_enabled:true})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Added");loadConfigs()}
    else{showToast(d.error||"Add Failed","error")}
  }).catch(function(){showToast("Request Failed","error")})
}
function hnEditForm(id){
  var row=document.querySelector("#hn-list tr[data-hn-id=\""+id+"\"]");
  if(!row)return;
  var title=row.getAttribute("data-hn-title");
  var url=row.getAttribute("data-hn-url");
  var enabled=row.getAttribute("data-hn-enabled")==="1";
  row.outerHTML='<tr id="hn-edit-row" style="background:rgba(0,245,255,0.05)"><td colspan="5">'+
    '<div style="display:flex;gap:8px;align-items:center;padding:6px 0">'+
    '<input class="in" id="hn-edit-title" value="'+escAttr(title)+'" style="width:100px">'+
    '<input class="in" id="hn-edit-url" value="'+escAttr(url)+'" style="flex:1">'+
    '<label style="font-size:12px;display:flex;align-items:center;gap:4px;white-space:nowrap"><input type="checkbox" id="hn-edit-enabled"'+(enabled?' checked':'')+'>Enabled</label>'+
    '<button class="btn bp" onclick="hnDoEdit('+id+')">Save</button>'+
    '<button class="btn bo" onclick="loadConfigs()">Cancel</button></div></td></tr>';
}
function hnDoEdit(id){
  var title=document.getElementById("hn-edit-title").value.trim();
  var url=document.getElementById("hn-edit-url").value.trim();
  var enabled=document.getElementById("hn-edit-enabled").checked;
  if(!title||!url){showToast("Title and URL required","error");return}
  fetch("/admin/footer-nav/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({title:title,url:url,is_enabled:enabled})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Saved");loadConfigs()}
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")})
}
function hnDelete(id,title){
  if(!confirm("Confirm Deletion of Nav Item「"+title+"」？"))return;
  fetch("/admin/footer-nav/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Deleted");loadConfigs()}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){showToast("Request Failed","error")})
}
function hnMove(id,direction){
  fetch("/admin/footer-nav",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var items=d.data;
    var idx=-1;
    for(var i=0;i<items.length;i++){if(items[i].id===id){idx=i;break}}
    if(idx<0)return;
    var swapIdx=direction==="up"?idx-1:idx+1;
    if(swapIdx<0||swapIdx>=items.length)return;
    var a=items[idx],b=items[swapIdx];
    Promise.all([
      fetch("/admin/footer-nav/"+a.id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({title:a.title,url:a.url,is_enabled:a.is_enabled?true:false,sort_order:b.sort_order})}),
      fetch("/admin/footer-nav/"+b.id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({title:b.title,url:b.url,is_enabled:b.is_enabled?true:false,sort_order:a.sort_order})})
    ]).then(function(){loadConfigs()}).catch(function(){showToast("Sort failed","error")})
  })
}
function loadFooterLinksConfig(){
  var ct=document.getElementById("config-tab-content");
  ct.insertAdjacentHTML("beforeend",'<div id="fl-loader" style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div>Footer Loading...</div>');
  fetch("/admin/footer-links",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById("fl-loader");if(loader)loader.remove();
    if(!d.success){ct.insertAdjacentHTML("beforeend",'<div class="em">Load failed</div>');loadSocialMediaConfig();return}
    var h='<div class="cd" style="margin-top:24px"><div class="st">Footer Columns</div>';
    h+='<div style="margin-bottom:12px"><button class="btn bp" onclick="flShowAddForm()">+ Add Link</button></div>';
    h+='<div id="fl-list"><table><tr><th style="width:80px">Column</th><th>Title</th><th style="width:200px">URL</th><th style="width:50px">Status</th><th style="width:60px">Actions</th></tr>';
    if(!d.data.length){h+='<tr><td colspan="5" class="em">No Records</td></tr>'}
    else{d.data.forEach(function(m){h+='<tr><td>'+esc(m.section)+'</td><td>'+esc(m.title)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="flEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="flDelete('+m.id+',\''+escAttr(m.title)+'\')">Delete</button></td></tr>'})}
    h+='</table></div></div>';ct.insertAdjacentHTML("beforeend",h);
    loadSocialMediaConfig();
  }).catch(function(){ct.insertAdjacentHTML("beforeend",'<div class="em">Request Failed</div>');loadSocialMediaConfig()})
}
function loadSocialMediaConfig(){
  var ct=document.getElementById("config-tab-content");
  ct.insertAdjacentHTML("beforeend",'<div id="sm-loader" style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div>Social Media Loading...</div>');
  fetch("/admin/social-media",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById("sm-loader");if(loader)loader.remove();
    if(!d.success||!d.data){ct.insertAdjacentHTML("beforeend",'<div class="em">Social Media Load Failed</div>');return}
    var items=d.data;
    var h='<div class="cd" style="margin-top:24px"><div class="st">Social Media Management</div>';
    h+='<div style="margin-bottom:12px"><button class="btn bp" onclick="smShowAddForm()">+ Add Social Media</button></div>';
    h+='<div id="sm-list"><div style="font-size:12px;color:var(--dim);margin-bottom:8px">Social Media Links ('+items.length+')</div>';
    if(!items.length){
      h+='<div class="em">No Records</div>';
      ct.insertAdjacentHTML("beforeend",h);
      return;
    }
    h+='<table id="sm-table"><tr><th style="width:30px">#</th><th style="width:80px">Icon</th><th>Platform Name</th><th style="width:200px">URL</th><th>HoverText</th><th style="width:60px">Enabled</th><th style="width:80px">Actions</th></tr>';
    items.forEach(function(item,idx){
      var enableIcon=item.is_enabled?'✓':'○';
      var enableCls=item.is_enabled?'on':'off';
      var iconHtml=smRenderIcon(item.icon_type,item.icon_value);
      h+='<tr id="sm-row-'+item.id+'" data-id="'+item.id+'" data-order="'+item.display_order+'"';
      h+=' data-platform_name="'+escAttr(item.platform_name)+'" data-icon_type="'+escAttr(item.icon_type||'')+'"';
      h+=' data-icon_value="'+escAttr(item.icon_value||'')+'" data-url="'+escAttr(item.url)+'"';
      h+=' data-hover_text="'+escAttr(item.hover_text||'')+'" data-is_enabled="'+item.is_enabled+'">';
      h+='<td style="text-align:center;color:var(--dim)">'+item.display_order+'</td>';
      h+='<td style="text-align:center">'+iconHtml+'</td>';
      h+='<td>'+esc(item.platform_name)+'</td>';
      h+='<td><span style="font-size:11px;color:var(--muted);word-break:break-all">'+esc(item.url)+'</span></td>';
      h+='<td style="font-size:11px">'+esc(item.hover_text||'-')+'</td>';
      h+='<td><span class="bdg '+enableCls+'">'+enableIcon+'</span></td>';
      h+='<td style="display:flex;gap:4px"><button class="btn bo bs" onclick="smEditForm('+item.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="smDelete('+item.id+',\''+escAttr(item.platform_name)+'\')">Delete</button></td>';
      h+='</tr>';
    });
    h+='</table></div>';
    ct.insertAdjacentHTML("beforeend",h);
    loadPartnersConfig();
  }).catch(function(){ct.insertAdjacentHTML("beforeend",'<div class="em">Social Media Request Failed</div>');loadPartnersConfig()})
}
function loadPartnersConfig(){
  var ct=document.getElementById("config-tab-content");
  ct.insertAdjacentHTML("beforeend",'<div id="pt-loader" style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div>Partner Loading...</div>');
  fetch("/admin/partners",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById("pt-loader");if(loader)loader.remove();
    if(!d.success){ct.insertAdjacentHTML("beforeend",'<div class="em">Load failed</div>');return}
    var h='<div class="cd" style="margin-top:12px"><div class="st">Ecosystem Partners</div>';
    h+='<div style="margin-bottom:12px"><button class="btn bp" onclick="ptShowAddForm()">+ Add Partner</button></div>';
    h+='<div id="pt-list"><table><tr><th>Name</th><th style="width:200px">URL</th><th style="width:50px">Status</th><th style="width:60px">Actions</th></tr>';
    if(!d.data.length){h+='<tr><td colspan="4" class="em">No Records</td></tr>'}
    else{d.data.forEach(function(m){h+='<tr><td>'+esc(m.name)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="ptEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="ptDelete('+m.id+',\''+escAttr(m.name)+'\')">Delete</button></td></tr>'})}
    h+='</table></div></div>';ct.insertAdjacentHTML("beforeend",h);
  }).catch(function(){ct.insertAdjacentHTML("beforeend",'<div class="em">Request Failed</div>')})
}
// ── Page Footer CRUD Functions ──
function escAttr(s){if(!s)return'';return s.replace(/\\\\/g,'\\\\\\\\').replace(/'/g,"\\\\'").replace(/\\n/g,'\\\\n')}
// Internal Links CRUD
function flShowAddForm(){var h='<div class="cd" style="margin-top:12px" id="fl-form"><div class="st">Add Internal Link</div>';h+='<div style="display:flex;flex-direction:column;gap:8px">';h+='<input class="in" id="fl-section" placeholder="Column Name (如: Products、Community)">';h+='<input class="in" id="fl-title" placeholder="Link Title">';h+='<input class="in" id="fl-url" placeholder="Link URL">';h+='</div><div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="flSubmitCreate()">Create</button><button class="btn bo" onclick="flCancelForm()">Cancel</button></div></div>';document.getElementById("fl-list").insertAdjacentHTML("beforebegin",h)}
function flEditForm(id){fetch("/admin/footer-links",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var m=d.data.find(function(x){return x.id==id});if(!m)return;var h='<div class="cd" style="margin-top:12px" id="fl-form"><div class="st">Edit Site Link</div>';h+='<div style="display:flex;flex-direction:column;gap:8px">';h+='<input class="in" id="fl-section" value="'+escAttr(m.section)+'" placeholder="Column Name">';h+='<input class="in" id="fl-title" value="'+escAttr(m.title)+'" placeholder="Link Title">';h+='<input class="in" id="fl-url" value="'+escAttr(m.url)+'" placeholder="Link URL">';h+='<label><input type="checkbox" id="fl-enabled"'+(m.is_enabled?' checked':'')+'> Enabled</label>';h+='</div><div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="flSubmitUpdate('+id+')">Save</button><button class="btn bo" onclick="flCancelForm()">Cancel</button></div></div>';document.getElementById("fl-list").insertAdjacentHTML("beforebegin",h)})}
function flSubmitCreate(){var d={section:document.getElementById("fl-section").value.trim(),title:document.getElementById("fl-title").value.trim(),url:document.getElementById("fl-url").value.trim(),is_enabled:true};fetch("/admin/footer-links",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){if(d.success){flCancelForm();flRefresh()}else{alert(d.error||"Creation Failed")}}).catch(function(){alert("Request Failed")})}
function flSubmitUpdate(id){var d={section:document.getElementById("fl-section").value.trim(),title:document.getElementById("fl-title").value.trim(),url:document.getElementById("fl-url").value.trim(),is_enabled:document.getElementById("fl-enabled").checked};fetch("/admin/footer-links/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){if(d.success){flCancelForm();flRefresh()}else{alert(d.error||"Update Failed")}}).catch(function(){alert("Request Failed")})}
function flDelete(id,name){if(!confirm("Confirm Delete「"+name+"」？"))return;fetch("/admin/footer-links/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(d.success){flRefresh()}else{alert(d.error||"Delete failed")}}).catch(function(){alert("Request Failed")})}
function flCancelForm(){var f=document.getElementById("fl-form");if(f)f.remove()}
function flRefresh(){flCancelForm();var el=document.getElementById("fl-list");el.innerHTML='<div style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div></div>';fetch("/admin/footer-links",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var h='<table><tr><th style="width:80px">Column</th><th>Title</th><th style="width:200px">URL</th><th style="width:50px">Status</th><th style="width:60px">Actions</th></tr>';if(!d.data.length){h+='<tr><td colspan="5" class="em">No Records</td></tr>'}else{d.data.forEach(function(m){h+='<tr><td>'+esc(m.section)+'</td><td>'+esc(m.title)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="flEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="flDelete('+m.id+',\''+escAttr(m.title)+'\')">Delete</button></td></tr>'})}h+='</table>';el.innerHTML=h})}
// Site Navigation CRUD
function fnShowAddForm(){var h='<div class="cd" style="margin-top:12px" id="fn-form"><div class="st">Add Site Nav</div>';h+='<div style="display:flex;flex-direction:column;gap:8px">';h+='<input class="in" id="fn-title" placeholder="Link Title">';h+='<input class="in" id="fn-url" placeholder="Link URL">';h+='</div><div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="fnSubmitCreate()">Create</button><button class="btn bo" onclick="fnCancelForm()">Cancel</button></div></div>';document.getElementById("fn-list").insertAdjacentHTML("beforebegin",h)}
function fnEditForm(id){fetch("/admin/footer-nav",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var m=d.data.find(function(x){return x.id==id});if(!m)return;var h='<div class="cd" style="margin-top:12px" id="fn-form"><div class="st">Edit Site Navigation</div>';h+='<div style="display:flex;flex-direction:column;gap:8px">';h+='<input class="in" id="fn-title" value="'+escAttr(m.title)+'" placeholder="Link Title">';h+='<input class="in" id="fn-url" value="'+escAttr(m.url)+'" placeholder="Link URL">';h+='<label><input type="checkbox" id="fn-enabled"'+(m.is_enabled?' checked':'')+'> Enabled</label>';h+='</div><div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="fnSubmitUpdate('+id+')">Save</button><button class="btn bo" onclick="fnCancelForm()">Cancel</button></div></div>';document.getElementById("fn-list").insertAdjacentHTML("beforebegin",h)})}
function fnSubmitCreate(){var d={title:document.getElementById("fn-title").value.trim(),url:document.getElementById("fn-url").value.trim(),is_enabled:true};fetch("/admin/footer-nav",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){if(d.success){fnCancelForm();fnRefresh()}else{alert(d.error||"Creation Failed")}}).catch(function(){alert("Request Failed")})}
function fnSubmitUpdate(id){var d={title:document.getElementById("fn-title").value.trim(),url:document.getElementById("fn-url").value.trim(),is_enabled:document.getElementById("fn-enabled").checked};fetch("/admin/footer-nav/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){if(d.success){fnCancelForm();fnRefresh()}else{alert(d.error||"Update Failed")}}).catch(function(){alert("Request Failed")})}
function fnDelete(id,name){if(!confirm("Confirm Delete「"+name+"」？"))return;fetch("/admin/footer-nav/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(d.success){fnRefresh()}else{alert(d.error||"Delete failed")}}).catch(function(){alert("Request Failed")})}
function fnCancelForm(){var f=document.getElementById("fn-form");if(f)f.remove()}
function fnRefresh(){fnCancelForm();var el=document.getElementById("fn-list");el.innerHTML='<div style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div></div>';fetch("/admin/footer-nav",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var h='<table><tr><th>Title</th><th style="width:200px">URL</th><th style="width:50px">Status</th><th style="width:60px">Actions</th></tr>';if(!d.data.length){h+='<tr><td colspan="4" class="em">No Records</td></tr>'}else{d.data.forEach(function(m){h+='<tr><td>'+esc(m.title)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="fnEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="fnDelete('+m.id+',\''+escAttr(m.title)+'\')">Delete</button></td></tr>'})}h+='</table>';el.innerHTML=h})}
// Footer Articles CRUD
function faShowAddForm(){var h='<div class="cd" style="margin-top:12px" id="fa-form"><div class="st">Add Footer Article</div>';h+='<div style="display:flex;flex-direction:column;gap:8px">';h+='<input class="in" id="fa-title" placeholder="Article Title">';h+='<input class="in" id="fa-url" placeholder="Article URL">';h+='</div><div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="faSubmitCreate()">Create</button><button class="btn bo" onclick="faCancelForm()">Cancel</button></div></div>';document.getElementById("fa-list").insertAdjacentHTML("beforebegin",h)}
function faEditForm(id){fetch("/admin/footer-articles",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var m=d.data.find(function(x){return x.id==id});if(!m)return;var h='<div class="cd" style="margin-top:12px" id="fa-form"><div class="st">Edit Footer Article</div>';h+='<div style="display:flex;flex-direction:column;gap:8px">';h+='<input class="in" id="fa-title" value="'+escAttr(m.title)+'" placeholder="Article Title">';h+='<input class="in" id="fa-url" value="'+escAttr(m.url)+'" placeholder="Article URL">';h+='<label><input type="checkbox" id="fa-enabled"'+(m.is_enabled?' checked':'')+'> Enabled</label>';h+='</div><div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="faSubmitUpdate('+id+')">Save</button><button class="btn bo" onclick="faCancelForm()">Cancel</button></div></div>';document.getElementById("fa-list").insertAdjacentHTML("beforebegin",h)})}
function faSubmitCreate(){var d={title:document.getElementById("fa-title").value.trim(),url:document.getElementById("fa-url").value.trim(),is_enabled:true};fetch("/admin/footer-articles",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){if(d.success){faCancelForm();faRefresh()}else{alert(d.error||"Creation Failed")}}).catch(function(){alert("Request Failed")})}
function faSubmitUpdate(id){var d={title:document.getElementById("fa-title").value.trim(),url:document.getElementById("fa-url").value.trim(),is_enabled:document.getElementById("fa-enabled").checked};fetch("/admin/footer-articles/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){if(d.success){faCancelForm();faRefresh()}else{alert(d.error||"Update Failed")}}).catch(function(){alert("Request Failed")})}
function faDelete(id,name){if(!confirm("Confirm Delete「"+name+"」？"))return;fetch("/admin/footer-articles/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(d.success){faRefresh()}else{alert(d.error||"Delete failed")}}).catch(function(){alert("Request Failed")})}
function faCancelForm(){var f=document.getElementById("fa-form");if(f)f.remove()}
function faRefresh(){faCancelForm();var el=document.getElementById("fa-list");el.innerHTML='<div style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div></div>';fetch("/admin/footer-articles",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var h='<table><tr><th>Title</th><th style="width:200px">URL</th><th style="width:50px">Status</th><th style="width:60px">Actions</th></tr>';if(!d.data.length){h+='<tr><td colspan="4" class="em">No Records</td></tr>'}else{d.data.forEach(function(m){h+='<tr><td>'+esc(m.title)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="faEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="faDelete('+m.id+',\''+escAttr(m.title)+'\')">Delete</button></td></tr>'})}h+='</table>';el.innerHTML=h})}
// Ecosystem Partners CRUD
function ptShowAddForm(){var h='<div class="cd" style="margin-top:12px" id="pt-form"><div class="st">Add Partner</div>';h+='<div style="display:flex;flex-direction:column;gap:8px">';h+='<input class="in" id="pt-name" placeholder="Partner Name">';h+='<input class="in" id="pt-url" placeholder="Partner URL">';h+='<input class="in" id="pt-icon" placeholder="Icon URL (Optional)">';h+='</div><div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="ptSubmitCreate()">Create</button><button class="btn bo" onclick="ptCancelForm()">Cancel</button></div></div>';document.getElementById("pt-list").insertAdjacentHTML("beforebegin",h)}
function ptEditForm(id){fetch("/admin/partners",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var m=d.data.find(function(x){return x.id==id});if(!m)return;var h='<div class="cd" style="margin-top:12px" id="pt-form"><div class="st">Edit Partner</div>';h+='<div style="display:flex;flex-direction:column;gap:8px">';h+='<input class="in" id="pt-name" value="'+escAttr(m.name)+'" placeholder="Partner Name">';h+='<input class="in" id="pt-url" value="'+escAttr(m.url)+'" placeholder="Partner URL">';h+='<input class="in" id="pt-icon" value="'+escAttr(m.icon_url||'')+'" placeholder="Icon URL (Optional)">';h+='<label><input type="checkbox" id="pt-enabled"'+(m.is_enabled?' checked':'')+'> Enabled</label>';h+='</div><div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="ptSubmitUpdate('+id+')">Save</button><button class="btn bo" onclick="ptCancelForm()">Cancel</button></div></div>';document.getElementById("pt-list").insertAdjacentHTML("beforebegin",h)})}
function ptSubmitCreate(){var d={name:document.getElementById("pt-name").value.trim(),url:document.getElementById("pt-url").value.trim(),icon_url:document.getElementById("pt-icon").value.trim(),is_enabled:true};fetch("/admin/partners",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){if(d.success){ptCancelForm();ptRefresh()}else{alert(d.error||"Creation Failed")}}).catch(function(){alert("Request Failed")})}
function ptSubmitUpdate(id){var d={name:document.getElementById("pt-name").value.trim(),url:document.getElementById("pt-url").value.trim(),icon_url:document.getElementById("pt-icon").value.trim(),is_enabled:document.getElementById("pt-enabled").checked};fetch("/admin/partners/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(d){if(d.success){ptCancelForm();ptRefresh()}else{alert(d.error||"Update Failed")}}).catch(function(){alert("Request Failed")})}
function ptDelete(id,name){if(!confirm("Confirm Delete「"+name+"」？"))return;fetch("/admin/partners/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(d.success){ptRefresh()}else{alert(d.error||"Delete failed")}}).catch(function(){alert("Request Failed")})}
function ptCancelForm(){var f=document.getElementById("pt-form");if(f)f.remove()}
function ptRefresh(){ptCancelForm();var el=document.getElementById("pt-list");el.innerHTML='<div style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div></div>';fetch("/admin/partners",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(!d.success)return;var h='<table><tr><th>Name</th><th style="width:200px">URL</th><th style="width:50px">Status</th><th style="width:60px">Actions</th></tr>';if(!d.data.length){h+='<tr><td colspan="4" class="em">No Records</td></tr>'}else{d.data.forEach(function(m){h+='<tr><td>'+esc(m.name)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="ptEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="ptDelete('+m.id+',\''+escAttr(m.name)+'\')">Delete</button></td></tr>'})}h+='</table>';el.innerHTML=h})}
// ── Social Media Management CRUD Functions ──
function smRenderIcon(icon_type,icon_value){
  if(!icon_value)return '<span style="color:var(--dim)">?</span>';
  if(icon_type==='svg')return '<span style="width:22px;height:22px;display:inline-flex;vertical-align:middle;color:var(--accent)">'+icon_value+'</span>';
  if(icon_type==='url')return '<img src="'+escAttr(icon_value)+'" style="width:22px;height:22px;border-radius:3px;object-fit:contain">';
  return '<i class="'+escAttr(icon_value)+'" style="font-size:18px;color:var(--accent)"></i>';
}
function smRefresh(){
  var el=document.getElementById("sm-list");if(el)el.remove();
  var fm=document.getElementById("sm-form");if(fm)fm.remove();
  var ld=document.getElementById("sm-loader");if(ld)ld.remove();
  var ct=document.getElementById("config-tab-content");
  ct.insertAdjacentHTML("beforeend",'<div id="sm-loader" style="text-align:center;padding:12px;color:var(--dim)"><div class="s" style="display:inline-block"></div>Refreshing...</div>');
  fetch("/admin/social-media",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById("sm-loader");if(loader)loader.remove();
    if(!d.success||!d.data){return}
    var items=d.data;
    var h='';
    if(!items.length){h='<div class="em">No Records</div>';ct.insertAdjacentHTML("beforeend",'<div id="sm-list">'+h+'</div>');return}
    h+='<table id="sm-table"><tr><th style="width:30px">#</th><th style="width:80px">Icon</th><th>Platform Name</th><th style="width:200px">URL</th><th>HoverText</th><th style="width:60px">Enabled</th><th style="width:80px">Actions</th></tr>';
    items.forEach(function(item,idx){
      var enableIcon=item.is_enabled?'✓':'○';
      var enableCls=item.is_enabled?'on':'off';
      var iconHtml=smRenderIcon(item.icon_type,item.icon_value);
      h+='<tr id="sm-row-'+item.id+'" data-id="'+item.id+'" data-order="'+item.display_order+'"';
      h+=' data-platform_name="'+escAttr(item.platform_name)+'" data-icon_type="'+escAttr(item.icon_type)+'"';
      h+=' data-icon_value="'+escAttr(item.icon_value)+'" data-url="'+escAttr(item.url)+'"';
      h+=' data-hover_text="'+escAttr(item.hover_text||'')+'" data-is_enabled="'+item.is_enabled+'">';
      h+='<td style="text-align:center;color:var(--dim)">'+item.display_order+'</td>';
      h+='<td style="text-align:center">'+iconHtml+'</td>';
      h+='<td>'+esc(item.platform_name)+'</td>';
      h+='<td><span style="font-size:11px;color:var(--muted);word-break:break-all">'+esc(item.url)+'</span></td>';
      h+='<td style="font-size:11px">'+esc(item.hover_text||'-')+'</td>';
      h+='<td><span class="bdg '+enableCls+'">'+enableIcon+'</span></td>';
      h+='<td style="display:flex;gap:4px"><button class="btn bo bs" onclick="smEditForm('+item.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="smDelete('+item.id+',\''+escAttr(item.platform_name)+'\')">Delete</button></td>';
      h+='</tr>';
    });
    h+='</table>';
    ct.insertAdjacentHTML("beforeend",'<div id="sm-list">'+h+'</div>');
  }).catch(function(){var ld=document.getElementById("sm-loader");if(ld)ld.remove()});
}
function smShowAddForm(){
  var fm=document.getElementById("sm-form");if(fm)fm.remove();
  var h='<div id="sm-form" class="cd" style="margin-top:12px;padding:16px;background:var(--bg2);border-radius:8px;border:1px solid var(--accent)">';
  h+='<div class="st" style="margin-bottom:12px">Add Social Media</div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Platform Name</span><input class="in" id="sf-platform_name" style="width:200px" placeholder="如：WeChat"></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Icon Type</span><select class="in" id="sf-icon_type" style="width:200px" onchange="smToggleIconInput()"><option value="svg">SVG</option><option value="url">URLImage</option></select></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Icon Content</span><input class="in" id="sf-icon_value" style="width:400px" placeholder="SVGCode or ImageURL"></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Link URL</span><input class="in" id="sf-url" style="width:400px" placeholder="https://"></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Hover Text</span><input class="in" id="sf-hover_text" style="width:200px" placeholder="Tooltip"></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Enabled</span><label style="font-size:12px"><input type="checkbox" id="sf-is_enabled" checked> Enabled</label></div>';
  h+='<div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="smSubmitCreate()">Create</button><button class="btn bo" onclick="smCancelForm()">Cancel</button></div>';
  h+='</div>';
  var ref=document.getElementById("sm-list")||document.getElementById("sm-loader");
  if(ref){ref.insertAdjacentHTML("beforebegin",h)}else{var ct=document.getElementById("config-tab-content");ct.insertAdjacentHTML("beforeend",h)}
}
function smEditForm(id){
  var row=document.getElementById("sm-row-"+id);if(!row)return;
  var fm=document.getElementById("sm-form");if(fm)fm.remove();
  var d=row.dataset;
  var h='<div id="sm-form" class="cd" style="margin-top:12px;padding:16px;background:var(--bg2);border-radius:8px;border:1px solid var(--accent)">';
  h+='<div class="st" style="margin-bottom:12px">Edit '+esc(d.platform_name)+'</div>';
  h+='<input type="hidden" id="sf-edit-id" value="'+id+'">';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Platform Name</span><input class="in" id="sf-platform_name" style="width:200px" value="'+escAttr(d.platform_name)+'"></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Icon Type</span><select class="in" id="sf-icon_type" style="width:200px" onchange="smToggleIconInput()"><option value="svg"'+(d.icon_type==='svg'?' selected':'')+'>SVG</option><option value="url"'+(d.icon_type==='url'?' selected':'')+'>URLImage</option></select></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Icon Content</span><input class="in" id="sf-icon_value" style="width:400px" value="'+escAttr(d.icon_value)+'"></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Link URL</span><input class="in" id="sf-url" style="width:400px" value="'+escAttr(d.url)+'"></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Hover Text</span><input class="in" id="sf-hover_text" style="width:200px" value="'+escAttr(d.hover_text)+'"></div>';
  h+='<div class="fl"><span style="width:80px;font-size:12px">Enabled</span><label style="font-size:12px"><input type="checkbox" id="sf-is_enabled"'+(d.is_enabled==='1'?' checked':'')+'> Enabled</label></div>';
  h+='<div style="margin-top:12px;display:flex;gap:8px"><button class="btn bp" onclick="smSubmitUpdate('+id+')">Save</button><button class="btn bo" onclick="smCancelForm()">Cancel</button></div>';
  h+='</div>';
  var ref=document.getElementById("sm-list");
  if(ref){ref.insertAdjacentHTML("beforebegin",h)}else{var ct=document.getElementById("config-tab-content");ct.insertAdjacentHTML("beforeend",h)}
}
function smToggleIconInput(){
  var sel=document.getElementById("sf-icon_type");if(!sel)return;
  var inp=document.getElementById("sf-icon_value");if(!inp)return;
  if(sel.value==='url'){inp.placeholder='Image URL (e.g., https://...)'}else{inp.placeholder='SVG Code'}
}
function smCancelForm(){var fm=document.getElementById("sm-form");if(fm)fm.remove()}
function smSubmitCreate(){
  var d={platform_name:document.getElementById("sf-platform_name").value.trim(),icon_type:document.getElementById("sf-icon_type").value,icon_value:document.getElementById("sf-icon_value").value.trim(),url:document.getElementById("sf-url").value.trim(),hover_text:document.getElementById("sf-hover_text").value.trim(),is_enabled:document.getElementById("sf-is_enabled").checked};
  if(!d.platform_name||!d.icon_value||!d.url){alert("Platform Name、Icon and Link are Required");return}
  fetch("/admin/social-media",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)})
  .then(function(r){return r.json()}).then(function(d){if(d.success){smCancelForm();smRefresh()}else{alert(d.error||"Creation Failed")}})
  .catch(function(){alert("Request Failed")});
}
function smSubmitUpdate(id){
  var d={platform_name:document.getElementById("sf-platform_name").value.trim(),icon_type:document.getElementById("sf-icon_type").value,icon_value:document.getElementById("sf-icon_value").value.trim(),url:document.getElementById("sf-url").value.trim(),hover_text:document.getElementById("sf-hover_text").value.trim(),is_enabled:document.getElementById("sf-is_enabled").checked};
  if(!d.platform_name||!d.icon_value||!d.url){alert("Platform Name、Icon and Link are Required");return}
  fetch("/admin/social-media/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(d)})
  .then(function(r){return r.json()}).then(function(d){if(d.success){smCancelForm();smRefresh()}else{alert(d.error||"Update Failed")}})
  .catch(function(){alert("Request Failed")});
}
function smDelete(id,name){
  if(!confirm("Confirm Delete「"+name+"」？"))return;
  fetch("/admin/social-media/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()}).then(function(d){if(d.success){smRefresh()}else{alert(d.error||"Delete failed")}})
  .catch(function(){alert("Request Failed")});
}
// ── Social Media Icons (platform-based) ──
var PLATFORMS={
  wechat:{label:'WeChat',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/></svg>'},
  weibo:{label:'Weibo',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M8 10c1-1 3-1 4 0M7 14c1 2 3 3 5 3s4-1 5-3M15 5c2 .5 3 2 3 2"/></svg>'},
  douyin:{label:'Douyin',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 18V5l12-1v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>'},
  github:{label:'GitHub',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.73c-2.78.6-3.37-1.34-3.37-1.34-.45-1.15-1.1-1.46-1.1-1.46-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02.8-.22 1.65-.33 2.5-.33s1.7.11 2.5.33c1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.94.36.31.68.92.68 1.85v2.74c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0 0 12 2z"/></svg>'},
  x:{label:'X / Twitter',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 4l16 16M20 4L4 20"/></svg>'},
  telegram:{label:'Telegram',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>'},
  bilibili:{label:_('Bilibili'),svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 4l-2 3M15 4l2 3"/><circle cx="12" cy="12" r="2"/><path d="M12 14v2"/></svg>'},
  zhihu:{label:'Zhihu',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 16v.01"/><path d="M9 10a3 3 0 1 1 3 3v1"/></svg>'},
  xiaohongshu:{label:'Xiaohongshu',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 8l9 6 9-6"/></svg>'},
  linkedin:{label:'LinkedIn',svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="2" width="20" height="20" rx="2"/><path d="M6 9v7M6 6v.01M10 16v-5"/><path d="M14 16v-3a2 2 0 0 1 4 0v3M10 11v5"/></svg>'}
};

function loadSocLinks(){
  fetch("/admin/social-links",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var el=document.getElementById("cl");
    var items=d.data||[];
    var added={};
    items.forEach(function(s){if(s.platform)added[s.platform]=true});
    var h='<div class="cd" style="margin-top:12px"><div class="st">Social Media Management</div>';
    h+='<div style="margin-bottom:10px"><div style="font-size:11px;color:var(--dim);margin-bottom:6px">Click to Add</div>';
    h+='<div style="display:flex;flex-wrap:wrap;gap:6px">';
    for(var pk in PLATFORMS){
      if(added[pk])continue;
      var p=PLATFORMS[pk];
      h+='<div data-pk="'+escAttr(pk)+'" onclick="socAddPlatform(this)" style="cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px;padding:8px;border-radius:6px;border:1px solid var(--border);background:var(--bg-elevated);width:56px" onmouseover="this.style.borderColor=\'var(--accent)\'" onmouseout="this.style.borderColor=\'var(--border)\'">'
        +'<span style="width:22px;height:22px;color:var(--dim)">'+p.svg+'</span>'
        +'<span style="font-size:9px;color:var(--dim)">'+p.label+'</span></div>';
    }
    h+='</div></div>';
    h+='<div id="socList">';
    items.forEach(function(s){
      var pk=s.platform||'';
      var pkg=pk&&PLATFORMS[pk]?PLATFORMS[pk]:null;
      var iconHtml=pkg
        ?'<span style="width:20px;height:20px;display:inline-block;vertical-align:middle;color:var(--text)">'+pkg.svg+'</span>'
        :(s.icon_url
          ?'<img src="'+escAttr(s.icon_url)+'" style="width:20px;height:20px;border-radius:3px" onerror="this.style.display=\'none\'">'
          :'<span style="width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;font-size:10px;color:var(--dim);border-radius:3px;background:var(--bg-elevated)">?</span>');
      h+='<div class="socRow" style="display:flex;align-items:center;gap:8px;padding:6px 8px;margin-bottom:4px;border-radius:6px;border:1px solid var(--border)">';
      h+=iconHtml;
      h+='<span style="font-size:12px;min-width:50px;color:var(--text)">'+(pkg?pkg.label:esc(s.name))+'</span>';
      h+='<input class="in" id="socUrl-'+s.id+'" value="'+escAttr(s.url)+'" placeholder="Link URL" style="flex:1;min-width:100px;font-size:11px">';
      h+='<label style="font-size:11px;color:var(--dim);white-space:nowrap"><input type="checkbox" id="socAct-'+s.id+'" '+(s.is_active?'checked':'')+' onchange="socToggle('+s.id+')"> Show</label>';
      h+='<button class="btn bo bs" data-id="'+s.id+'" data-label="'+escAttr(pkg?pkg.label:s.name)+'" onclick="socDelete(this)" style="font-size:10px;padding:2px 6px;color:#f85149">Delete</button>';
      h+='</div>';
    });
    h+='</div></div>';
    el.innerHTML+=h;
    items.forEach(function(s){
      var inp=document.getElementById("socUrl-"+s.id);
      if(inp)inp.onblur=function(){socSaveUrl(s.id)};
    });
  }).catch(function(){})
}
function socAddPlatform(el){
  var pk=el.getAttribute("data-pk");
  var p=PLATFORMS[pk];if(!p)return;
  fetch("/admin/social-links",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({name:p.label,url:"#",icon_url:"",platform:pk})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){loadSocLinks()}else{alert(d.error||"Add Failed")}
  })
}
function socSaveUrl(id){
  var url=document.getElementById("socUrl-"+id).value.trim()||"#";
  fetch("/admin/social-links/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({url:url})}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)alert(d.error||"Save failed")
  })
}
function socToggle(id){
  var act=document.getElementById("socAct-"+id).checked?1:0;
  fetch("/admin/social-links/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({is_active:act})}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)alert(d.error||"Save failed")
  })
}
function socDelete(el){
  var id=parseInt(el.getAttribute("data-id"));
  var label=el.getAttribute("data-label");
  if(!confirm("Delete "+label+"？"))return;
  fetch("/admin/social-links/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){loadSocLinks()}else{alert(d.error||"Delete failed")}
  })
}
// ════════════════════════════════════════════════════════
// Navigation Settings — Main Nav + Sub-site Navigation Unified Management
// ════════════════════════════════════════════════════════

window.l_nav_settings=function(){
  document.getElementById("pt").textContent="Navigation Settings";
  var mc=document.getElementById("mc");
  var currentTab='main';
  renderNavSettings(mc,currentTab);
};
function renderNavSettings(mc,tab){
  var tabs=[
    {key:'main',label:'Main Nav'},
    {key:'platform',label:'Sub-Site · Portal'},
    // {key:'community',label:'Sub-Site · Community'}, (Offline)
    {key:'trademind',label:'Sub-Site · TradeMind'}
  ];
  var h='<div style="display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap">';
  tabs.forEach(function(t){
    h+='<button class="btn '+(tab===t.key?'bp':'')+'" onclick="navSettingsSwitch(\''+t.key+'\')">'+t.label+'</button>';
  });
  h+='</div><div id="ns-content" style="min-height:200px"><div class="lo"><div class="s"></div>Loading......</div></div>';
  mc.innerHTML=h;
  if(tab==='main'){
    loadMainNavInto('ns-content');
  } else {
    var c=document.getElementById('ns-content');
    c.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
    renderHeaderNav(c,tab);
  }
}
function navSettingsSwitch(tab){
  renderNavSettings(document.getElementById('mc'),tab);
}
function loadMainNavInto(targetId){
  var el=document.getElementById(targetId);
  fetch("/admin/footer-nav",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){el.innerHTML='<div class="em">Load failed</div>';return}
    var h='<div class="cd"><div class="st" style="display:flex;justify-content:space-between;align-items:center">Main Nav Management';
    h+='<button class="btn bs bp" onclick="hnShowAddForm()" style="font-size:11px">+ Add Nav</button></div>';
    h+='<div id="hn-list"><table><tr><th style="width:50px">Sort</th><th>Title</th><th style="width:240px">URL</th><th style="width:50px">Status</th><th style="width:100px">Actions</th></tr>';
    if(!d.data.length){h+='<tr><td colspan="5" class="em">No Nav Items</td></tr>'}
    else{d.data.forEach(function(m,i){
      h+='<tr data-hn-id="'+m.id+'" data-hn-title="'+escAttr(m.title)+'" data-hn-url="'+escAttr(m.url)+'" data-hn-enabled="'+(m.is_enabled?1:0)+'"><td style="display:flex;gap:2px;align-items:center;justify-content:center">';
      if(i>0)h+='<button class="btn bo bs" style="padding:2px 4px;font-size:10px" onclick="hnMove('+m.id+',\'up\')">▲</button>';
      else h+='<span style="width:22px"></span>';
      if(i<d.data.length-1)h+='<button class="btn bo bs" style="padding:2px 4px;font-size:10px" onclick="hnMove('+m.id+',\'down\')">▼</button>';
      else h+='<span style="width:22px"></span>';
      h+='</td><td>'+esc(m.title)+'</td><td style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="hnEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="hnDelete('+m.id+',\''+escAttr(m.title)+'\')">Delete</button></td></tr>'
    })}
    h+='</table></div></div>';el.innerHTML=h;
    loadFooterLinksConfigInto(targetId);
  }).catch(function(){el.innerHTML='<div class="em">Request Failed</div>'})
}
function loadFooterLinksConfigInto(targetId){
  var el=document.getElementById(targetId);
  var ld=document.createElement('div');ld.id='fl-loader';ld.style.cssText='text-align:center;padding:12px;color:var(--dim)';ld.innerHTML='<div class="s" style="display:inline-block"></div>Footer Loading...';el.appendChild(ld);
  fetch("/admin/footer-links",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById('fl-loader');if(loader)loader.remove();
    if(!d.success){el.insertAdjacentHTML('beforeend','<div class="em">Load failed</div>');loadSocialMediaConfigInto(targetId);return}
    var h='<div class="cd" style="margin-top:24px"><div class="st">Footer Columns</div>';
    h+='<div style="margin-bottom:12px"><button class="btn bp" onclick="flShowAddForm()">+ Add Link</button></div>';
    h+='<div id="fl-list"><table><tr><th style="width:80px">Column</th><th>Title</th><th style="width:200px">URL</th><th style="width:50px">Status</th><th style="width:60px">Actions</th></tr>';
    if(!d.data.length){h+='<tr><td colspan="5" class="em">No Records</td></tr>'}
    else{d.data.forEach(function(m){h+='<tr><td>'+esc(m.section)+'</td><td>'+esc(m.title)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="flEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="flDelete('+m.id+',\''+escAttr(m.title)+'\')">Delete</button></td></tr>'})}
    h+='</table></div></div>';el.insertAdjacentHTML('beforeend',h);
    loadSocialMediaConfigInto(targetId);
  }).catch(function(){el.insertAdjacentHTML('beforeend','<div class="em">Request Failed</div>');loadSocialMediaConfigInto(targetId)})
}
function loadSocialMediaConfigInto(targetId){
  var el=document.getElementById(targetId);
  var ld=document.createElement('div');ld.id='sm-loader';ld.style.cssText='text-align:center;padding:12px;color:var(--dim)';ld.innerHTML='<div class="s" style="display:inline-block"></div>Social Media Loading...';el.appendChild(ld);
  fetch("/admin/social-media",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById('sm-loader');if(loader)loader.remove();
    if(!d.success||!d.data){el.insertAdjacentHTML('beforeend','<div class="em">Social Media Load Failed</div>');loadPartnersConfigInto(targetId);return}
    var items=d.data;
    var h='<div class="cd" style="margin-top:24px"><div class="st">Social Media Management</div>';
    h+='<div style="margin-bottom:12px"><button class="btn bp" onclick="smShowAddForm()">+ Add Social Media</button></div>';
    h+='<div id="sm-list"><table id="sm-table"><tr><th style="width:30px">#</th><th style="width:80px">Icon</th><th>Platform Name</th><th style="width:200px">URL</th><th>HoverText</th><th style="width:60px">Enabled</th><th style="width:80px">Actions</th></tr>';
    if(!items.length){h+='<tr><td colspan="7" class="em">No Records</td></tr>'}
    else{items.forEach(function(item,idx){
      var enableIcon=item.is_enabled?'✓':'○';
      var enableCls=item.is_enabled?'on':'off';
      var iconHtml=smRenderIcon(item.icon_type,item.icon_value);
      h+='<tr id="sm-row-'+item.id+'">';
      h+='<td style="text-align:center;color:var(--dim)">'+item.display_order+'</td>';
      h+='<td style="text-align:center">'+iconHtml+'</td>';
      h+='<td>'+esc(item.platform_name)+'</td>';
      h+='<td><span style="font-size:11px;color:var(--muted);word-break:break-all">'+esc(item.url)+'</span></td>';
      h+='<td style="font-size:11px">'+esc(item.hover_text||'-')+'</td>';
      h+='<td><span class="bdg '+enableCls+'">'+enableIcon+'</span></td>';
      h+='<td style="display:flex;gap:4px"><button class="btn bo bs" onclick="smEditForm('+item.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="smDelete('+item.id+',\''+escAttr(item.platform_name)+'\')">Delete</button></td>';
      h+='</tr>'
    })}
    h+='</table></div></div>';el.insertAdjacentHTML('beforeend',h);
    loadPartnersConfigInto(targetId);
  }).catch(function(){el.insertAdjacentHTML('beforeend','<div class="em">Social Media Request Failed</div>');loadPartnersConfigInto(targetId)})
}
function loadPartnersConfigInto(targetId){
  var el=document.getElementById(targetId);
  var ld=document.createElement('div');ld.id='pt-loader';ld.style.cssText='text-align:center;padding:12px;color:var(--dim)';ld.innerHTML='<div class="s" style="display:inline-block"></div>Partner Loading...';el.appendChild(ld);
  fetch("/admin/partners",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var loader=document.getElementById('pt-loader');if(loader)loader.remove();
    if(!d.success){el.insertAdjacentHTML('beforeend','<div class="em">Load failed</div>');return}
    var h='<div class="cd" style="margin-top:24px"><div class="st">Ecosystem Partners</div>';
    h+='<div style="margin-bottom:12px"><button class="btn bp" onclick="ptShowAddForm()">+ Add Partner</button></div>';
    h+='<div id="pt-list"><table><tr><th>Name</th><th style="width:200px">URL</th><th style="width:50px">Status</th><th style="width:60px">Actions</th></tr>';
    d.data.forEach(function(m){h+='<tr><td>'+esc(m.name)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(m.url)+'</td><td>'+(m.is_enabled?'✅':'⛔')+'</td><td style="display:flex;gap:4px"><button class="btn bo bs" onclick="ptEditForm('+m.id+')">Edit</button><button class="btn bo bs" style="color:#f85149" onclick="ptDelete('+m.id+',\''+escAttr(m.name)+'\')">Delete</button></td></tr>'})
    h+='</table></div></div>';el.insertAdjacentHTML('beforeend',h);
  }).catch(function(){el.insertAdjacentHTML('beforeend','<div class="em">Request Failed</div>')})
}
function scfg(k){
  var v=document.getElementById("cf-"+k).value.trim();
  if(!v)return;
  fetch("/user/config",{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({key:k,value:v})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){alert("Saved");loadConfigs()}else{alert(d.error||"Save failed")}
  }).catch(function(){alert("Save failed")})
}
function seedConfig(){
  if(!confirm("Initialize all email/SMS config (existing kept)?"))return;
  fetch("/user/config/seed",{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){alert(d.message);loadConfigs()}else{alert(d.error||"Initialize Failed")}
  })
}
function uploadConfig(){
  document.getElementById("csvFile").click();
}
function doUpload(){
  var file=document.getElementById("csvFile").files[0];
  if(!file)return;
  var fd=new FormData();fd.append("file",file);
  fetch("/user/config/upload",{method:"POST",headers:{"Authorization":"Bearer "+T},body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.success){alert(d.message+" ("+d.access_key_prefix+")");loadConfigs()}else{alert(d.error||"Import Failed")}
  }).catch(function(){alert("Upload failed")});
  document.getElementById("csvFile").value="";
}


window.l_logs=function(){
  document.getElementById("pt").textContent="Operation Log";
  fetch("/admin/logs",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var h="<div class=\"cd\"><div class=\"st\">Audit Log</div><table><tr><th>Admin</th><th>Actions</th><th>Target</th><th>Details</th><th>IP</th><th>Time</th></tr>";
    d.data.forEach(function(l){h+="<tr><td>"+(l.admin_name||"-")+"</td><td>"+l.action+"</td><td>"+l.target_type+"/"+l.target_id+"</td><td>"+(l.detail||"")+"</td><td>"+l.ip_address+"</td><td>"+l.created_at+"</td></tr>"});
    h+="</table></div>";
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){})
}


window.l_matrix=function(){
  document.getElementById("pt").textContent="Agent Matrix";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Load Matrix Data...</div>';
  fetch("/admin/agent-matrix/dashboard",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success){mc.innerHTML='<div class="em">Load failed</div>';return}
      var dat=d.data;
      var stats=dat.stats;
      var agents=dat.active_agents;
      var recent=dat.recent_tasks;
      var master=agents.filter(function(a){return a.role_type=="master"});
      var subs=agents.filter(function(a){return a.role_type=="sub"});
      var h='';

      // Stats cards
      h+='<div class="gr">';
      h+=sc("🧠","Agent",stats.agents.active+"/"+stats.agents.total);
      h+=sc("📋","Total Tasks",stats.tasks.total);
      h+=sc("✅","Success Rate",stats.tasks.success_rate+"%");
      h+=sc("⚡","Today",stats.tasks.today);
      h+='</div>';

      // Master Agent card
      if(master.length){
        var ma=master[0];
        h+='<div class="cd" style="margin-bottom:12px;border-color:rgba(0,212,170,.3)">';
        h+='<div style="display:flex;justify-content:space-between;align-items:center">';
        h+='<div class="st" style="border:none;margin:0;padding:0">🤖 主 Agent: '+ma.name+' <span class="bdg on">Running</span></div>';
        h+='<div style="display:flex;gap:6px">';
        h+='<button class="btn bo bs" onclick="l_matrix()">Refresh</button>';
        h+='<button class="btn bo bs" onclick="matEditAgent('+ma.id+')">✏️ Edit</button>';
        h+='<button class="btn bo bs" onclick="matAIServices()">🤖 AIServices</button>';
        h+='<button class="btn bp bs" onclick="go(\'ai_chat\')">💬 AI Chat</button>';
        h+='</div></div>';
        h+='<div style="font-size:11px;color:var(--muted);margin-top:4px">'+ma.description+'</div>';
        h+='<div style="font-size:11px;color:var(--dim);margin-top:2px">'+ma.provider+'/'+ma.model_name+' | Tasks: '+ma.tasks_total+' | Success Rate: '+(ma.tasks_total?(Math.round(ma.tasks_success/ma.tasks_total*100)):'0')+'%</div>';
        h+='</div>';
      }

      // Sub Agents
      h+='<div class="cd">';
      h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">';
      h+='<div class="st" style="border:none;margin:0;padding:0">🧠 Agent Matrix ('+subs.length+')</div>';
      h+='<button class="btn bp bs" onclick="matNewSub()">+ Create Agent</button>';
      h+='</div>';
      h+='<div id="matNewForm" style="display:none"></div>';
      if(subs.length){
        h+='<table><tr><th>Name</th><th>Domain</th><th>Managed Modules</th><th>Models</th><th>Tasks</th><th>Status</th><th>Actions</th></tr>';
        subs.forEach(function(a){
          var modules='';
          try{modules=JSON.parse(a.managed_modules||'[]').join(", ")}catch(e){}
          var st=a.is_active?'<span class="bdg on">Active</span>':'<span class="bdg off">Deactivate</span>';
          var sr=a.tasks_total?Math.round(a.tasks_success/a.tasks_total*100)+'%':'—';
          h+='<tr><td>'+esc(a.name)+'</td><td>'+esc(a.domain)+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">'+esc(modules)+'</td><td>'+esc(a.model_name)+'</td><td>'+a.tasks_total+' ('+sr+')</td><td>'+st+'</td><td>';
          h+=matTgBtn(a);
          h+=matEditBtn(a);
          h+=matTestBtn(a);
          h+='</td></tr>';
        });
        h+='</table>';
      }else{
        h+='<div class="em">No Sub Agent，Click「+ Create Agent」Create</div>';
      }
      h+='</div>';

      // Recent tasks
      if(recent&&recent.length){
        h+='<div class="cd" style="margin-top:12px">';
        h+='<div class="st">Recent Tasks</div>';
        h+='<table><tr><th>TasksID</th><th>Title</th><th>Executor</th><th>Status</th><th>Confidence</th></tr>';
        recent.forEach(function(t){
          var ic=t.status=="completed"?"✅":t.status=="failed"?"❌":t.status=="running"?"🔄":"⏳";
          h+='<tr><td style="font-size:10px;color:var(--dim)">'+esc(t.task_id||"")+'</td><td>'+esc(t.title||"").slice(0,30)+'</td><td>'+(t.target_name||"")+'</td><td>'+ic+' '+esc(t.status)+'</td><td>'+(t.confidence||"—")+'</td></tr>';
        });
        h+='</table></div>';
      }

      mc.innerHTML=h;
    }).catch(function(){
      mc.innerHTML='<div class="em">Connection Failed，Please Confirm Service is Running</div>';
    });
};

// =============================================
// AI Chat — Independent Athena Full Page Chat（Split from Matrix Page）
// =============================================

window.l_ai_chat=function(){
  document.getElementById("pt").textContent="AI Chat — Athena";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Load Chats...</div>';
  var h='';

  // Stats summary
  h+='<div class="cd" style="margin-bottom:12px;border-color:rgba(0,212,170,.3)">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center">';
  h+='<div class="st" style="border:none;margin:0;padding:0">🤖 主 Agent: Athena <span class="bdg on">Running</span></div>';
  h+='<button class="btn bo bs" onclick="l_ai_chat()">🔄 Refresh</button>';
  h+='</div></div>';

  // Session controls
  h+='<div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap">';
  h+='<button class="btn bo bs" id="aiBtnFast" style="font-size:11px;padding:3px 10px;border-color:var(--accent);background:rgba(0,245,255,0.1)" onclick="aiSetMode(\'fast\')">⚡ Fast</button>';
  h+='<button class="btn bo bs" id="aiBtnDeep" style="font-size:11px;padding:3px 10px" onclick="aiSetMode(\'deep\')">🧠 Deep Thinking</button>';
  h+='<button class="btn bo bs" id="aiBtnImage" style="font-size:11px;padding:3px 10px" onclick="aiSetMode(\'image\')">🎨 Image Processing</button>';
  h+='<span style="flex:1"></span>';
  h+='<button class="btn bo bs" style="font-size:11px;padding:3px 10px" onclick="aiNewSession()">🆕 New Chat</button>';
  h+='<button class="btn bo bs" style="font-size:11px;padding:3px 10px;color:#f85149" onclick="aiResetSession()">🔄 Reset</button>';
  h+='</div>';

  // Chat messages area
  h+='<div id="aiChatMsgs" style="min-height:300px;max-height:420px;overflow-y:auto;margin-bottom:8px;padding:8px;background:rgba(0,0,0,.2);border-radius:6px;font-size:12px;line-height:1.6">';
  h+='<div style="color:var(--dim);text-align:center;padding:20px">💬 Send Command to Start Athena Chat</div>';
  h+='</div>';

  // Input area
  h+='<div style="display:flex;gap:4px;margin-bottom:12px">';
  h+='<input type="file" id="aiFileInput" style="display:none" onchange="aiUpload(this)">';
  h+='<button class="btn bo bs" onclick="document.getElementById(\'aiFileInput\').click()" title="Upload File(Image/Docs)" style="font-size:14px;padding:3px 8px">📎</button>';
  h+='<textarea class="in" id="aiChatInput" placeholder="Enter Command，e.g.「Post for MeCMSArticle」" style="flex:1;font-size:12px;resize:none;min-height:36px;max-height:120px;line-height:1.4;padding-top:8px;padding-bottom:8px" onkeydown="if(event.key===\'Enter\'&&!event.ctrlKey&&!event.shiftKey){event.preventDefault();aiSend()}" oninput="aiAutoResize(this)"></textarea>';
  h+='<button class="btn bp" onclick="aiSend()">Send</button>';
  h+='</div>';

  // Session history
  h+='<div class="cd">';
  h+='<div class="st">💬 Chat History</div>';
  h+='<div style="display:flex;gap:4px;margin-bottom:6px">';
  h+='<input class="in" id="aiSearchInput" placeholder="Search Keywords..." style="flex:1;font-size:11px;padding:4px 6px" onkeydown="if(event.key===\'Enter\')aiSearchSessions()">';
  h+='<button class="btn bo bs" style="font-size:10px;padding:2px 6px" onclick="aiSearchSessions()">🔍 Search</button>';
  h+='<button class="btn bo bs" style="font-size:10px;padding:2px 6px;color:#f85149" onclick="aiBatchDelete()">🗑️ Batch Delete</button>';
  h+='</div>';
  h+='<div id="aiSessions"><div class="lo"><div class="s"></div></div></div>';
  h+='</div>';

  mc.innerHTML=h;

  // Load session history
  fetch("/admin/agent-matrix/chat/history",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data)return;
      var sl=d.data;
      var el=document.getElementById("aiSessions");
      if(!el)return;
      if(!sl.length){el.innerHTML='<div class="em">No Chat History</div>';return}
      var sh='<table><tr><th style="width:30px"><input type="checkbox" id="aiSelAll" onchange="aiToggleAll(this)"></th><th>Session Title</th><th>Last Time</th><th>Actions</th></tr>';
      sl.forEach(function(s){
        var title=s.session_name||s.first_query||s.session_id;
        sh+='<tr onclick="aiLoadSession(this.dataset.sid)" data-sid="'+esc(s.session_id)+'" style="cursor:pointer">';
        sh+='<td style="width:30px;text-align:center" onclick="event.stopPropagation()"><input type="checkbox" class="aiSel" value="'+esc(s.session_id)+'"></td>';
        sh+='<td>'+esc(title.slice(0,50))+'</td>';
        sh+='<td style="font-size:10px;color:var(--dim)">'+esc(s.last_msg||"")+'</td>';
        sh+='<td style="width:40px" onclick="event.stopPropagation()"><button class="btn bs" style="font-size:10px;padding:1px 4px" onclick="aiDeleteSession(this)">🗑️</button></td></tr>';
      });
      sh+='</table>';
      el.innerHTML=sh;
    }).catch(function(){});
};

// ── AI Chat helper functions ──
var aiMode="fast";
var aiSessionId="";
var aiUploadedFiles=[];

function aiSetMode(m){
  aiMode=m;
  ["aiBtnFast","aiBtnDeep","aiBtnImage","aiBtnTool"].forEach(function(id){
    var b=document.getElementById(id);
    if(b){b.style.borderColor="";b.style.background=""}
  });
  var btn=document.getElementById("aiBtn"+m.charAt(0).toUpperCase()+m.slice(1));
  if(btn){btn.style.borderColor="var(--accent)";btn.style.background="rgba(0,245,255,0.1)"}
}

function aiNewSession(){
  aiSessionId="";
  aiUploadedFiles=[];
  var msgs=document.getElementById("aiChatMsgs");
  if(msgs)msgs.innerHTML='<div style="color:var(--dim);text-align:center;padding:20px">🆕 New Chat Created，Send Command to Start Chat</div>';
  fetch("/admin/agent-matrix/chat/history",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()}).then(function(d){
      if(!d.success||!d.data)return;
      var el=document.getElementById("aiSessions");
      if(!el)return;
      var sl=d.data;
      if(!sl.length){el.innerHTML='<div class="em">No Chat History</div>';return}
      var sh='<table><tr><th style="width:30px"><input type="checkbox" id="aiSelAll" onchange="aiToggleAll(this)"></th><th>Session Title</th><th>Last Time</th><th>Actions</th></tr>';
      sl.forEach(function(s){
        var title=s.session_name||s.first_query||s.session_id;
        sh+='<tr onclick="aiLoadSession(this.dataset.sid)" data-sid="'+esc(s.session_id)+'" style="cursor:pointer">';
        sh+='<td style="width:30px;text-align:center" onclick="event.stopPropagation()"><input type="checkbox" class="aiSel" value="'+esc(s.session_id)+'"></td>';
        sh+='<td>'+esc(title.slice(0,50))+'</td>';
        sh+='<td style="font-size:10px;color:var(--dim)">'+esc(s.last_msg||"")+'</td>';
        sh+='<td style="width:40px" onclick="event.stopPropagation()"><button class="btn bs" style="font-size:10px;padding:1px 4px" onclick="aiDeleteSession(this)">🗑️</button></td></tr>';
      });
      sh+='</table>';
      el.innerHTML=sh;
    }).catch(function(){});
}

function aiResetSession(){
  if(!aiSessionId){aiNewSession();return}
  if(!confirm("Reset current session? All messages will be cleared."))return;
  fetch("/admin/agent-matrix/chat/"+encodeURIComponent(aiSessionId)+"/clear",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    aiNewSession();
  }).catch(function(){aiNewSession();});
}

function aiDeleteSession(btn){
  var sid=btn.closest('tr').dataset.sid;
  if(!sid||!confirm("Delete this session history?"))return;
  fetch("/admin/agent-matrix/chat/"+encodeURIComponent(sid)+"/clear",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(d&&d.success){aiNewSession()}
    else{alert("Delete failed: "+(d&&d.error||"Unknown Error"))}
  }).catch(function(){alert("Network error")});
}

function aiToggleAll(cb){
  var chks=document.querySelectorAll(".aiSel");
  chks.forEach(function(c){c.checked=cb.checked});
}

function aiSearchSessions(){
  var q=document.getElementById("aiSearchInput").value.trim();
  if(!q||q.length<2){alert("At Least Keywords 2 Characters");return}
  fetch("/admin/agent-matrix/chat/search?q="+encodeURIComponent(q),{
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var el=document.getElementById("aiSessions");
    if(!el)return;
    var rows=d.data;
    if(!rows.length){el.innerHTML='<div class="em">No Match 「'+esc(q)+'」 Message</div>';return}
    var sh='<table><tr><th style="width:30px"></th><th>Content</th><th>Session</th><th>Time</th></tr>';
    rows.forEach(function(r){
      var title=r.session_name||r.session_id;
      var excerpt=(r.content||"").slice(0,100);
      sh+='<tr onclick="aiLoadSession(this.dataset.sid)" data-sid="'+esc(r.session_id)+'" style="cursor:pointer">';
      sh+='<td style="width:30px;text-align:center">'+(r.role=='user'?'👤':'🤖')+'</td>';
      sh+='<td>'+esc(excerpt)+'</td>';
      sh+='<td style="font-size:10px;color:var(--dim)">'+esc(title.slice(0,30))+'</td>';
      sh+='<td style="font-size:10px;color:var(--dim)">'+esc(r.created_at||"")+'</td></tr>';
    });
    sh+='</table><div style="margin-top:6px;font-size:10px;color:var(--dim)">Found '+rows.length+' Matching Messages，Click Row to Jump to Chat</div>';
    el.innerHTML=sh;
  }).catch(function(){});
}

function aiBatchDelete(){
  var chks=document.querySelectorAll(".aiSel:checked");
  var ids=[];
  chks.forEach(function(c){ids.push(c.value)});
  if(!ids.length){alert("Please Select Chats to Delete");return}
  if(!confirm("Confirm Batch Delete "+ids.length+" Sessions？This Operation Cannot Be Recovered。"))return;
  fetch("/admin/agent-matrix/chat/batch-delete",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({session_ids:ids})
  }).then(function(r){return r.json()}).then(function(d){
    if(d&&d.success){aiNewSession()}
    else{alert("Delete failed: "+(d&&d.error||"Unknown Error"))}
  }).catch(function(){alert("Network error")});
}

function aiAutoResize(el){
  el.style.height="auto";
  el.style.height=Math.min(el.scrollHeight,120)+"px";
}

function aiUpload(input){
  var file=input.files[0];
  if(!file)return;
  var msgs=document.getElementById("aiChatMsgs");
  var uploadMsgId="aiUploadMsg_"+Date.now();
  msgs.innerHTML+='<div style="color:var(--dim);margin:4px 0;font-size:11px" id="'+uploadMsgId+'">📎 Upload '+esc(file.name)+' ('+Math.round(file.size/1024)+'KB)...</div>';
  msgs.scrollTop=msgs.scrollHeight;
  var fd=new FormData();
  fd.append("file",file);
  fetch("/admin/agent-matrix/upload",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T},
    body:fd
  }).then(function(r){return r.json()}).then(function(d){
    var el=document.getElementById(uploadMsgId);
    if(!el)return;
    if(!d.success){el.innerHTML='❌ Upload failed: '+esc(d.error||"Unknown Error");return}
    var u=d.data;
    el.innerHTML='📎 <a href="'+u.url+'" download target="_blank" style="color:var(--accent)">'+esc(u.original_name)+'</a> ('+u.size_display+')';
    aiUploadedFiles.push(u);
    if(file.type&&file.type.startsWith("image/")){
      el.innerHTML+='<br><img src="'+u.url+'" style="max-width:200px;max-height:120px;border-radius:4px;margin-top:4px;cursor:pointer" onclick="window.open(this.src)" alt="'+esc(u.original_name)+'">';
    }
  }).catch(function(){
    var el=document.getElementById(uploadMsgId);
    if(el)el.innerHTML='❌ Network error';
  });
  input.value="";
}

function aiSend(){
  var inp=document.getElementById("aiChatInput");
  var msg=inp.value.trim();
  if(!msg)return;
  inp.value="";
  var msgs=document.getElementById("aiChatMsgs");
  msgs.innerHTML+='<div style="color:var(--accent);margin:4px 0">👤 Me: '+esc(msg)+'</div>';
  msgs.scrollTop=msgs.scrollHeight;
  msgs.innerHTML+='<div style="color:var(--muted)">🤖 Athena: Thinking...</div>';

  var body={message:msg,mode:aiMode};
  if(aiUploadedFiles.length){
    var fileCtx="\n\n[Uploaded Files]:\n";
    aiUploadedFiles.forEach(function(f,i){
      fileCtx+=(i+1)+". "+f.original_name+" → "+f.url+"\n";
    });
    body.message=msg+fileCtx;
    msgs.innerHTML+='<div style="color:var(--dim);margin:4px 0;font-size:11px">📎 Attached '+aiUploadedFiles.length+' Use Files as Reference</div>';
    aiUploadedFiles=[];
  }
  if(aiSessionId)body.session_id=aiSessionId;
  var modeNames={fast:"⚡Fast",deep:"🧠Deep Thinking",image:"🎨Image Understanding",tool:"🔧Tool Call"};
  var modeLabel=modeNames[aiMode]||"Fast";
  msgs.innerHTML=msgs.innerHTML.replace(
    '<div style="color:var(--muted)">🤖 Athena: Thinking...</div>',
    '<div style="color:var(--muted)">🤖 Athena ['+modeLabel+']: Thinking...</div>'
  );

  var endpoint=aiMode==="tool"?"/admin/agent-matrix/chat/tool":"/admin/agent-matrix/chat";
  fetch(endpoint,{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(body)
  }).then(function(r){return r.json()}).then(function(d){
    if(!d.success){
      msgs.innerHTML=msgs.innerHTML.replace('Thinking...','<span style="color:#f85149">Request Failed: '+esc(d.error||"")+'</span>');
      return;
    }
    if(d.data.session_id)aiSessionId=d.data.session_id;
    var summary=d.data.summary||"";
    msgs.innerHTML=msgs.innerHTML.replace('Thinking...','');
    var block='<div style="background:rgba(0,212,170,.05);border-left:2px solid var(--accent);padding:6px 8px;margin:4px 0;white-space:pre-wrap">'+esc(summary)+'</div>';
    var results=d.data.sub_task_results||[];
    for(var i=0;i<results.length;i++){
      var r=results[i];
      var imgUrl=r.image_url;
      if(imgUrl)block+='<div style="margin:6px 0;text-align:center"><img src="'+imgUrl+'" style="max-width:100%;max-height:400px;border-radius:8px;border:1px solid rgba(255,255,255,.1)" onerror="this.style.display=\'none\'"></div>';
    }
    // Tool actions (PPT download, etc.)
    var actions=d.data.actions||[];
    if(actions.length){
      block+='<div style="margin-top:8px">';
      actions.forEach(function(a){
        if(a.type==="ppt_download"){
          block+='<a href="'+a.url+'" download class="btn bp" style="display:inline-block;margin:3px;font-size:11px;text-decoration:none">⬇ Download PPT</a>';
        }else if(a.type==="image"){
          block+='<div style="margin:6px 0;text-align:center"><img src="'+a.url+'" style="max-width:100%;max-height:400px;border-radius:8px;border:1px solid rgba(255,255,255,.1)" onerror="this.style.display=\'none\'"><br><a href="'+a.url+'" download class="btn bo bs" style="font-size:10px;margin-top:4px">⬇ Download Image</a></div>';
        }else if(a.type==="audio"){
          block+='<div style="margin:6px 0"><audio controls src="'+a.url+'" style="width:100%;max-width:400px"></audio><br><a href="'+a.url+'" download class="btn bo bs" style="font-size:10px">⬇ Download Audio</a></div>';
        }else if(a.type==="video"){
          block+='<div style="margin:6px 0"><video controls src="'+a.url+'" style="max-width:100%;max-height:300px;border-radius:6px"></video><br><a href="'+a.url+'" download class="btn bo bs" style="font-size:10px">⬇ Download Video</a></div>';
        }
      });
      block+='</div>';
    }
    msgs.innerHTML+=block;
    msgs.scrollTop=msgs.scrollHeight;
  }).catch(function(){
    msgs.innerHTML=msgs.innerHTML.replace('Thinking...','<span style="color:#f85149">Network error</span>');
  });
}

function aiLoadSession(sid){
  aiSessionId=sid;
  fetch("/admin/agent-matrix/chat/"+encodeURIComponent(sid),{
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var msgs=document.getElementById("aiChatMsgs");
    msgs.innerHTML="";
    d.data.forEach(function(m){
      var nm=esc(m.content||"");
      if(m.role=="user")msgs.innerHTML+='<div style="color:var(--accent);margin:4px 0">👤 Me: '+nm+'</div>';
      else if(m.role=="master")msgs.innerHTML+='<div style="background:rgba(0,212,170,.05);border-left:2px solid var(--accent);padding:6px 8px;margin:4px 0;white-space:pre-wrap">🤖 Athena: '+nm+'</div>';
      else if(m.role=="sub")msgs.innerHTML+='<div style="color:var(--muted);margin:2px 0;font-size:11px">🔄 '+m.agent_name+': '+nm+'</div>';
      else if(m.role=="system")msgs.innerHTML+='<div style="color:var(--dim);margin:2px 0;font-size:11px">'+nm+'</div>';
    });
    msgs.scrollTop=msgs.scrollHeight;
  });
}

// =============================================

function fm(){return '<div id="cf" style="display:none;margin-bottom:16px" class="cd"><div class="st">Create Agent（Legacy API）</div>...Old Feature Migrated</div>'}
function sc(ic,lb,vl){return '<div class="cd"><div class="l">'+ic+' '+lb+'</div><div class="v g">'+vl+'</div></div>'}
function esc(s){if(!s)return'';return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}

// Chat UI toggle
var matMode="fast";
var matSessionId="";
var matUploadedFiles=[];
function matChat(){
  var a=document.getElementById("matChatArea");
  a.style.display=a.style.display=="none"?"block":"none";
  if(a.style.display=="block"){document.getElementById("matChatInput").focus();matSetMode(matMode)}
}

// Set chat mode and highlight active button
function matSetMode(m){
  matMode=m;
  document.querySelectorAll("#matChatArea > div:first-child + div button").forEach(function(b){b.style.borderColor="";b.style.background=""});
  var btn=document.getElementById("matBtn"+m.charAt(0).toUpperCase()+m.slice(1));
  if(btn){btn.style.borderColor="var(--accent)";btn.style.background="rgba(0,245,255,0.1)"}
}

// New session — clear session and messages
function matNewSession(){
  matSessionId="";
  matUploadedFiles=[];
  var msgs=document.getElementById("matChatMsgs");
  if(msgs)msgs.innerHTML='<div style="color:var(--dim);text-align:center;padding:20px">🆕 New Chat Created，Send Command to Start Chat</div>';
  fetch("/admin/agent-matrix/chat/history",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()}).then(function(d){
      if(!d.success||!d.data)return;
      var el=document.getElementById("matSessions");
      if(!el)return;
      var sl=d.data;
      if(!sl.length){el.innerHTML='<div class="em">No Chat History</div>';return}
      var sh='&lt;table&gt;&lt;tr&gt;&lt;th&gt;Session&lt;/th&gt;&lt;th&gt;First Msg&lt;/th&gt;&lt;th&gt;Last Time&lt;/th&gt;&lt;/tr&gt;';
      sl.forEach(function(s){
        sh+='<tr onclick="matLoadSession(this.dataset.sid)" data-sid="'+esc(s.session_id)+'" style="cursor:pointer">';
        sh+='<td style="font-size:10px;color:var(--dim)">'+esc(s.session_id)+'</td>';
        sh+='<td>'+esc((s.first_query||"").slice(0,40))+'</td>';
        sh+='<td style="font-size:10px;color:var(--dim)">'+esc(s.last_msg||"")+'</td></tr>';
      });
      sh+='</table>';
      el.innerHTML=sh;
    }).catch(function(){});
}

// Reset session — clear current session on server too
function matResetSession(){
  if(!matSessionId){matNewSession();return}
  if(!confirm("Reset current session? All messages will be cleared."))return;
  fetch("/admin/agent-matrix/chat/"+encodeURIComponent(matSessionId)+"/clear",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    matNewSession();
  }).catch(function(){
    matNewSession();
  });
}

// Auto-resize textarea
function matAutoResize(el){
  el.style.height="auto";
  el.style.height=Math.min(el.scrollHeight,120)+"px";
}

// Upload file to temp storage
function matUpload(input){
  var file=input.files[0];
  if(!file)return;
  var msgs=document.getElementById("matChatMsgs");
  var uploadMsgId="matUploadMsg_"+Date.now();
  msgs.innerHTML+='<div style="color:var(--dim);margin:4px 0;font-size:11px" id="'+uploadMsgId+'">📎 Upload '+esc(file.name)+' ('+Math.round(file.size/1024)+'KB)...</div>';
  msgs.scrollTop=msgs.scrollHeight;
  var fd=new FormData();
  fd.append("file",file);
  fetch("/admin/agent-matrix/upload",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T},
    body:fd
  }).then(function(r){return r.json()}).then(function(d){
    var el=document.getElementById(uploadMsgId);
    if(!el)return;
    if(!d.success){
      el.innerHTML='❌ Upload failed: '+esc(d.error||"Unknown Error");
      return;
    }
    var u=d.data;
    el.innerHTML='📎 <a href="'+u.url+'" download target="_blank" style="color:var(--accent)">'+esc(u.original_name)+'</a> ('+u.size_display+')';
    matUploadedFiles.push(u);
    // If It Is an Image，Show Thumbnail
    if(file.type&&file.type.startsWith("image/")){
      el.innerHTML+='<br><img src="'+u.url+'" style="max-width:200px;max-height:120px;border-radius:4px;margin-top:4px;cursor:pointer" onclick="window.open(this.src)" alt="'+esc(u.original_name)+'">';
    }
  }).catch(function(){
    var el=document.getElementById(uploadMsgId);
    if(el)el.innerHTML='❌ Network error';
  });
  input.value='';
}

// Send message to Master Agent
function matSend(){
  var inp=document.getElementById("matChatInput");
  var msg=inp.value.trim();
  if(!msg)return;
  inp.value="";
  var msgs=document.getElementById("matChatMsgs");
  msgs.innerHTML+='<div style="color:var(--accent);margin:4px 0">👤 Me: '+esc(msg)+'</div>';
  msgs.scrollTop=msgs.scrollHeight;
  msgs.innerHTML+='<div style="color:var(--muted)">🤖 Athena: Thinking...</div>';

  var body={message:msg,mode:matMode};
  // If There Are Uploaded Files，Append to Message
  if(matUploadedFiles.length){
    var fileCtx="\n\n[Uploaded Files]:\n";
    matUploadedFiles.forEach(function(f,i){
      fileCtx+=(i+1)+". "+f.original_name+" → "+f.url+"\n";
    });
    body.message=msg+fileCtx;
    // Show Uploaded File Reference in Chat
    msgs.innerHTML+='<div style="color:var(--dim);margin:4px 0;font-size:11px">📎 Attached '+
      matUploadedFiles.length+' Use Files as Reference</div>';
    matUploadedFiles=[];
  }
  if(matSessionId)body.session_id=matSessionId;
  // Show mode indicator in thinking message
  var modeNames={fast:"⚡Fast",deep:"🧠Deep Thinking",image:"🎨Image Processing"};
  var modeLabel=modeNames[matMode]||"Fast";
  msgs.innerHTML=msgs.innerHTML.replace(
    '<div style="color:var(--muted)">🤖 Athena: Thinking...</div>',
    '<div style="color:var(--muted)">🤖 Athena ['+modeLabel+']: Thinking...</div>'
  );

  fetch("/admin/agent-matrix/chat",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(body)
  }).then(function(r){return r.json()}).then(function(d){
    if(!d.success){
      msgs.innerHTML=msgs.innerHTML.replace('Thinking...','<span style="color:#f85149">Request Failed</span>');
      return;
    }
    if(d.data.session_id)matSessionId=d.data.session_id;
    var summary=d.data.summary||"No Response";
    msgs.innerHTML=msgs.innerHTML.replace('Thinking...','');
    var block='<div style="background:rgba(0,212,170,.05);border-left:2px solid var(--accent);padding:6px 8px;margin:4px 0;white-space:pre-wrap">'+esc(summary)+'</div>';
    // Render Sub-task Images to Chat
    var results=d.data.sub_task_results||[];
    for(var i=0;i<results.length;i++){
      var imgUrl=results[i].image_url;
      if(imgUrl)block+='<div style="margin:6px 0;text-align:center"><img src="'+imgUrl+'" style="max-width:100%;max-height:400px;border-radius:8px;border:1px solid rgba(255,255,255,.1)" onerror="this.style.display=\'none\'"></div>';
    }
    msgs.innerHTML+=block;
    msgs.scrollTop=msgs.scrollHeight;
  }).catch(function(){
    msgs.innerHTML=msgs.innerHTML.replace('Thinking...','<span style="color:#f85149">Network error</span>');
  });
}

// Load a past session
function matLoadSession(sid){
  matSessionId=sid;
  fetch("/admin/agent-matrix/chat/"+encodeURIComponent(sid),{
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var msgs=document.getElementById("matChatMsgs");
    msgs.innerHTML='';
    d.data.forEach(function(m){
      var nm=esc(m.content||"");
      if(m.role=="user")msgs.innerHTML+='<div style="color:var(--accent);margin:4px 0">👤 Me: '+nm+'</div>';
      else if(m.role=="master")msgs.innerHTML+='<div style="background:rgba(0,212,170,.05);border-left:2px solid var(--accent);padding:6px 8px;margin:4px 0;white-space:pre-wrap">🤖 Athena: '+nm+'</div>';
      else if(m.role=="sub")msgs.innerHTML+='<div style="color:var(--muted);margin:2px 0;font-size:11px">🔄 '+m.agent_name+': '+nm+'</div>';
      else if(m.role=="system")msgs.innerHTML+='<div style="color:var(--dim);margin:2px 0;font-size:11px">'+nm+'</div>';
    });
    msgs.scrollTop=msgs.scrollHeight;
    matChat();
  });
}

// Create new Sub Agent — Enhanced（Contains Prompt、Multiple Providers）
function matNewSub(){
  var f=document.getElementById("matNewForm");
  if(f.style.display=="block"){f.style.display="none";return}
  f.style.display="block";
  var h='<div class="cd" style="margin-bottom:12px">';
  h+='<div class="st">+ Add Sub Agent <span style="font-size:10px;color:var(--dim);font-weight:400">｜<a href="javascript:matPromptHelp()" style="color:var(--accent)">📖 Prompt Management Description</a></span></div>';
  h+='<div class="g2">';
  // Row 1: Name + Domain
  h+='<div><div style="font-size:11px;color:var(--dim)">Name *</div><input class="in" id="matNewName" placeholder="如：CMS Agent" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Domain</div><input class="in" id="matNewDomain" placeholder="如：cms" style="width:100%"></div>';
  // Row 2: Description (full width)
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Description</div><input class="in" id="matNewDesc" placeholder="Role Description" style="width:100%"></div>';
  // Row 3: Provider → Model cascade
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Model Config <span style="color:var(--muted);font-size:10px">（Provider → Cascading Model Select）</span></div>';
  h+='<div style="display:flex;gap:8px">';
  h+='<select class="sl" id="matNewProv" onchange="matNewProvChange()" style="flex:1"><option value="">— Select Provider —</option></select>';
  h+='<select class="sl" id="matNewMpId" onchange="matMpChange()" style="flex:2"><option value="">— Select Model —</option></select>';
  h+='</div>';
  h+='<div id="matNewMpInfo" style="font-size:10px;color:var(--dim);margin-top:4px"></div>';
  h+='</div>';
  // Row 4: Prompt Template Selector
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">System Prompt Templates <span style="color:var(--muted);font-size:10px">（Auto-fill After Selection，Modify Below）</span></div>';
  h+='<select class="sl" id="matNewPromptTmpl" onchange="matPromptSelect()" style="width:100%">';
  h+='<option value="">— Select Template（Optional）—</option>';
  h+='</select></div>';
  // Row 6: System Prompt
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">System Prompt <span style="color:var(--muted);font-size:10px">（Paste or Write Prompt Content）</span></div>';
  h+='<textarea class="ta" id="matNewPrompt" rows="5" placeholder="Write This Agent System Prompt（Or Select Template Above）" style="width:100%;min-height:120px;font-family:monospace;font-size:11px"></textarea></div>';
  // Row 7: Managed Modules
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Managed Modules（Comma Separated）</div>';
  h+='<input class="in" id="matNewMods" placeholder="e.g.: cms, comments, contentfactory" style="width:100%"></div>';
  h+='</div>'; // close g2
  h+='<div style="margin-top:10px;display:flex;gap:8px;align-items:center">';
  h+='<button class="btn bp" onclick="matCreate()">✅ Confirm Creation</button>';
  h+='<button class="btn bo" onclick="document.getElementById(\'matNewForm\').style.display=\'none\'">Cancel</button>';
  h+='</div></div>';
  f.innerHTML=h;
  // Load prompt templates and model providers
  matLoadPrompts();
  matLoadModelProviders();
}

// Load providers into dropdown
function matLoadProviders(ddId, onSelect){
  var dd=document.getElementById(ddId);
  if(!dd)return;
  fetch("/admin/providers",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success||!d.data)return;
    dd.innerHTML='<option value="">— Select Provider —</option>';
    d.data.forEach(function(p){
      var o=document.createElement("option");
      o.value=p.id;
      o.textContent=p.name+" ("+p.slug+")";
      dd.appendChild(o);
    });
    if(onSelect)onSelect();
  }).catch(function(){});
}

// Load models for a provider
function matLoadModels(ddId, providerId, preselectedId){
  var dd=document.getElementById(ddId);
  if(!dd)return;
  var url="/admin/provider-models";
  if(providerId)url+="?provider_id="+providerId;
  fetch(url,{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success||!d.data)return;
    dd.innerHTML='<option value="">— Select Model —</option>';
    d.data.forEach(function(m){
      if(!m.is_active)return;
      var o=document.createElement("option");
      o.value=m.id;
      o.textContent=m.name+" — "+m.model_name+" ("+(m.capabilities||'text')+")";
      o.setAttribute("data-provider",m.provider_slug);
      o.setAttribute("data-model",m.model_name);
      o.setAttribute("data-url",m.endpoint_url);
      o.setAttribute("data-keyref",m.api_key_ref||"");
      o.setAttribute("data-caps",m.capabilities||"text");
      if(m.id==preselectedId)o.selected=true;
      dd.appendChild(o);
    });
    // Trigger change to show info
    if(dd.id==="matNewMpId")matMpChange();
    if(dd.id==="matEditMpId")matEditMpChange();
  }).catch(function(){});
}

// Provider changed → reload models
function matNewProvChange(){
  var pid=document.getElementById("matNewProv").value;
  matLoadModels("matNewMpId", pid);
}

// Load providers into create form
function matLoadModelProviders(){
  matLoadProviders("matNewProv", function(){
    matNewProvChange();
  });
}

function matMpChange(){
  var sel=document.getElementById("matNewMpId");
  var info=document.getElementById("matNewMpInfo");
  if(!sel||!info)return;
  var opt=sel.options[sel.selectedIndex];
  if(!opt||!opt.value){
    info.textContent="";
    return;
  }
  var keyref=opt.getAttribute("data-keyref")||'';
  info.innerHTML='<span style="color:var(--accent)">'+esc(opt.getAttribute("data-model"))+'</span>'+
    ' | Ability: <code>'+esc(opt.getAttribute("data-caps")||'text')+'</code>'+
    (keyref?' | KeyReference: <code>'+esc(keyref)+'</code> <span style="color:var(--warn);font-size:9px">（Please「Basic Settings」Configure Actual Key Values）</span>':'');
}

// Load prompt templates from API
function matLoadPrompts(){
  var sel=document.getElementById("matNewPromptTmpl");
  if(!sel)return;
  fetch("/admin/agent-matrix/prompts",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data)return;
      d.data.forEach(function(p){
        var o=document.createElement("option");
        o.value=p.id;
        o.textContent=p.name+" — "+p.description.slice(0,60);
        sel.appendChild(o);
      });
    }).catch(function(){});
}

// On provider change, auto-fill base URL
function matProvChange(){
  var urls={
    dashscope:"https://dashscope.aliyuncs.com/compatible-mode/v1",
    openai:"https://api.openai.com/v1",
    deepseek:"https://api.deepseek.com",
    openrouter:"https://openrouter.ai/api/v1",
    ollama:"http://localhost:11434/v1"
  };
  var models={
    dashscope:"qwen-turbo",
    openai:"gpt-4o",
    deepseek:"deepseek-chat",
    openrouter:"openai/gpt-4o-mini",
    ollama:"llama3"
  };
  var p=document.getElementById("matNewProv").value;
  if(urls[p]){var el=document.getElementById("matNewBaseUrl");el.value=urls[p];el.selectionStart=el.selectionEnd=0}
  if(models[p]){var el2=document.getElementById("matNewModel");el2.value=models[p];el2.selectionStart=el2.selectionEnd=0}
}

// Edit form: on provider change, auto-fill base URL + model
function matEditProvChange(){
  var urls={
    dashscope:"https://dashscope.aliyuncs.com/compatible-mode/v1",
    openai:"https://api.openai.com/v1",
    deepseek:"https://api.deepseek.com",
    openrouter:"https://openrouter.ai/api/v1",
    ollama:"http://localhost:11434/v1"
  };
  var models={
    dashscope:"qwen-turbo",
    openai:"gpt-4o",
    deepseek:"deepseek-chat",
    openrouter:"openai/gpt-4o-mini",
    ollama:"llama3"
  };
  var p=document.getElementById("matEditProv").value;
  if(urls[p]){var el=document.getElementById("matEditBaseUrl");el.value=urls[p];el.selectionStart=el.selectionEnd=0}
  if(models[p]){var el2=document.getElementById("matEditModel");el2.value=models[p];el2.selectionStart=el2.selectionEnd=0}
}

// Edit form: load prompt templates
function matEditLoadPrompts(){
  var sel=document.getElementById("matEditPromptTmpl");
  if(!sel)return;
  fetch("/admin/agent-matrix/prompts",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data)return;
      d.data.forEach(function(p){
        var o=document.createElement("option");
        o.value=p.id;
        o.textContent=p.name+" — "+p.description.slice(0,60);
        sel.appendChild(o);
      });
    }).catch(function(){});
}

// Edit form: on template select, load prompt content
function matEditPromptSelect(){
  var sel=document.getElementById("matEditPromptTmpl");
  var ta=document.getElementById("matEditPrompt");
  if(!sel||!ta)return;
  var val=sel.value;
  if(!val||val=="custom")return;
  fetch("/admin/agent-matrix/prompts/load?path="+encodeURIComponent(val),{
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success&&d.data)ta.value=d.data;
  }).catch(function(){});
}

// Clear API Key button handler
function matClearApiKey(){
  var el=document.getElementById("matEditApiKey");
  var btn=document.getElementById("matClearKeyBtn");
  if(el){el.value="__CLEAR__"}
  if(btn){btn.style.background="rgba(255,80,80,0.3)";btn.textContent="✓ Marked clean"}
}

// On template select, load prompt content
function matPromptSelect(){
  var sel=document.getElementById("matNewPromptTmpl");
  var ta=document.getElementById("matNewPrompt");
  if(!sel||!ta)return;
  var val=sel.value;
  if(!val||val=="custom")return;
  // Load prompt file content via API
  fetch("/admin/agent-matrix/prompts/load?path="+encodeURIComponent(val),{
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success&&d.data)ta.value=d.data;
  }).catch(function(){});
}

// API: create Sub Agent
function matCreate(){
  var name=document.getElementById("matNewName").value.trim();
  if(!name){alert("Enter Name");return}
  var mods=document.getElementById("matNewMods").value.trim();
  var modules=mods?mods.split(",").map(function(s){return s.trim()}):[];
  var prompt=document.getElementById("matNewPrompt").value.trim();
  var tmpl=document.getElementById("matNewPromptTmpl").value;
  var body={
    name:name,
    role_type:"sub",
    domain:document.getElementById("matNewDomain").value.trim()||"general",
    description:document.getElementById("matNewDesc").value.trim(),
    managed_modules:modules,
    provider_model_id:parseInt(document.getElementById("matNewMpId").value)||null,
    system_prompt:prompt||tmpl||"",
    is_active:1
  };
  fetch("/admin/agent-matrix/agents",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(body)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){l_matrix()}else{alert(d.error||"Creation Failed")}
  });
}

// Prompt management help dialog
function matPromptHelp(){
  var mc=document.getElementById("mc");
  var h='<div class="cd" style="margin-bottom:12px">';
  h+='<div class="st">📖 Prompt Management Description</div>';
  h+='<div style="font-size:12px;line-height:1.8;color:var(--muted)">';
  h+='<p><b>Prompt（System Prompt）</b>是 Agent Core Instructions，Decided Agent Action、Roles &amp; Abilities。</p>';
  h+='<br><b>Built-in Templates（8 Presets）：</b>';
  h+='<br>Located on Server <code>agent_matrix/prompts/</code> Directory，Includes Full Role Definition、Managed Modules、API Reference、Quality Standard。';
  h+='<br>Create Sub Agent Pass When「System Prompt Templates」Dropdown Select，Auto-fill to Text Field。';
  h+='<br><br><b>Custom Prompt：</b>';
  h+='<br>Selecting「Custom Prompt」后，Directly System Prompt Write in Text Box。';
  h+='<br>Supported Fields：Role Definition、Managed Modules、Core Capabilities、Quality Standard、Code of Conduct、Available API Reference。';
  h+='<br><br><b>Prompt Storage：</b>';
  h+='<br>• If Built-in Templates Selected，Store as File Path（如 prompts/sub_cms_prompt.md）';
  h+='<br>• If Writing Manually，Store Full Text Content Directly';
  h+='<br>• Auto-load at Runtime，Supports Dynamic Editing';
  h+='<br><br><b>Modify Prompt：</b>';
  h+='<br>Click Agent Line End「✏️ Edit」Button，Edit in Popup Window。';
  h+='<br>Or Directly SSH Edit on Server <code>agent_matrix/prompts/</code> Under .md File。';
  h+='</div>';
  h+='<div style="margin-top:10px"><button class="btn bp" onclick="l_matrix()">Back</button></div>';
  h+='</div>';
  mc.innerHTML=h;
}

// Edit agent dialog — unified with create form layout
function matEditAgent(id){
  fetch("/admin/agent-matrix/agents/"+id,{
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){alert("Load failed");return}
    var a=d.data;
    var modules="";
    try{modules=JSON.parse(a.managed_modules||"[]").join(", ")}catch(e){}
    var h='<div class="cd" style="margin-bottom:12px">';
    h+='<div class="st">✏️ Edit Agent: '+esc(a.name)+' <span style="font-size:10px;color:var(--dim);font-weight:400">｜<a href="javascript:matPromptHelp()" style="color:var(--accent)">📖 Prompt Management Description</a></span></div>';
    h+='<div class="g2">';
    // Row 1: Name + Domain
    h+='<div><div style="font-size:11px;color:var(--dim)">Name *</div><input class="in" id="matEditName" value="'+esc(a.name)+'" style="width:100%"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Domain</div><input class="in" id="matEditDomain" value="'+esc(a.domain)+'" style="width:100%"></div>';
    // Row 2: Description (full width)
    h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Description</div><input class="in" id="matEditDesc" value="'+esc(a.description)+'" style="width:100%"></div>';
    // Row 3: Provider → Model cascade
    h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Model Config <span style="color:var(--muted);font-size:10px">（Provider → Cascading Model Select）</span></div>';
    h+='<div style="display:flex;gap:8px">';
    h+='<select class="sl" id="matEditProv" onchange="matEditProvChange()" style="flex:1"><option value="">— Select Provider —</option></select>';
    h+='<select class="sl" id="matEditMpId" onchange="matEditMpChange()" style="flex:2"><option value="">— Select Model —</option></select>';
    h+='</div>';
    h+='<div id="matEditMpInfo" style="font-size:10px;color:var(--dim);margin-top:4px"></div>';
    h+='</div>';
    // Row 4: Prompt Template Selector
    h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">System Prompt Templates <span style="color:var(--muted);font-size:10px">（Auto-fill After Selection，Modify Below）</span></div>';
    h+='<select class="sl" id="matEditPromptTmpl" onchange="matEditPromptSelect()" style="width:100%">';
    h+='<option value="">— Select Template（Optional）—</option>';
    h+='</select></div>';
    // Row 6: System Prompt
    h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">System Prompt <span style="color:var(--muted);font-size:10px">（Paste or Write Prompt Content）</span></div>';
    h+='<textarea class="ta" id="matEditPrompt" rows="5" placeholder="Write This Agent System Prompt（Or Select Template Above）" style="width:100%;min-height:120px;font-family:monospace;font-size:11px">'+esc(a.system_prompt||"")+'</textarea></div>';
    // Row 7: Managed Modules
    h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Managed Modules（Comma Separated）</div>';
    h+='<input class="in" id="matEditMods" value="'+esc(modules)+'" style="width:100%"></div>';
    h+='</div>';
    h+='<div style="margin-top:10px;display:flex;gap:8px;align-items:center">';
    h+='<button class="btn bp" onclick="matSaveEdit('+id+')">💾 Save</button>';
    h+='<button class="btn bo" onclick="l_matrix()">Cancel</button>';
    h+='</div></div>';
    document.getElementById("mc").innerHTML=h;
    // Load prompt templates and model providers
    matEditLoadPrompts();
    matEditLoadModelProviders(a.model_provider_id);
  });
}

// Load providers + models for edit form
function matEditLoadModelProviders(currentMpId){
  // First load all models to find the provider for currentMpId
  fetch("/admin/provider-models",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success||!d.data)return;
    // Find provider_id for the current model
    var provId=null;
    d.data.forEach(function(m){
      if(m.id==currentMpId)provId=m.provider_id;
    });
    // Load providers first
    matLoadProviders("matEditProv", function(){
      if(provId){
        document.getElementById("matEditProv").value=provId;
      }
      matEditProvChange(currentMpId);
    });
  }).catch(function(){});
}

function matEditProvChange(preselectedId){
  var pid=document.getElementById("matEditProv").value;
  matLoadModels("matEditMpId", pid, preselectedId);
}

function matEditMpChange(){
  var sel=document.getElementById("matEditMpId");
  var info=document.getElementById("matEditMpInfo");
  if(!sel||!info)return;
  var opt=sel.options[sel.selectedIndex];
  if(!opt||!opt.value){info.textContent="";return;}
  var keyref=opt.getAttribute("data-keyref")||'';
  info.innerHTML='<span style="color:var(--accent)">'+esc(opt.getAttribute("data-model"))+'</span>'+
    ' | Ability: <code>'+esc(opt.getAttribute("data-caps")||'text')+'</code>'+
    (keyref?' | KeyReference: <code>'+esc(keyref)+'</code> <span style="color:var(--warn);font-size:9px">（Please「Basic Settings」Configure Actual Key Values）</span>':'');
}

// Save agent edit
function matSaveEdit(id){
  var mods=document.getElementById("matEditMods").value.trim();
  var modules=mods?mods.split(",").map(function(s){return s.trim()}):[];
  var body={
    name:document.getElementById("matEditName").value.trim(),
    domain:document.getElementById("matEditDomain").value.trim(),
    description:document.getElementById("matEditDesc").value.trim(),
    managed_modules:modules,
    provider_model_id:parseInt(document.getElementById("matEditMpId").value)||null,
    system_prompt:document.getElementById("matEditPrompt").value,
  };
  fetch("/admin/agent-matrix/agents/"+id,{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(body)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){l_matrix()}else{alert(d.error||"Save failed")}
  });
}

// Add prompt loading endpoint in backend
// We need GET /admin/agent-matrix/agents/<id>/prompt?path=... for loading prompt content
// Actually let me modify matPromptSelect to load via a different method

// Toggle agent
function matTg(id,v){
  fetch("/admin/agent-matrix/agents/"+id+"/toggle",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success)l_matrix()
  });
}

// Test agent — Pro Version，Show Full Results
function matTest(id){
  var q=prompt("📩 Send Test Message to Agent：\n（e.g.：\"Analyze Recent Stock Market Trends\"）");
  if(!q)return;
  fetch("/admin/agent-matrix/agents/"+id+"/test",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({query:q})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success&&d.data){
      var msg="🧠 Test Results" + "\n━━━━━━━━━━━━━━━━\n";
      msg+="Status: "+d.data.status+"\n";
      msg+="Confidence: "+d.data.confidence+"\n";
      if(d.data.logs&&d.data.logs.length){
        msg+="\n📋 Execution Log:\n";
        d.data.logs.slice(-5).forEach(function(l){msg+="  "+l+"\n"});
      }
      msg+="\n💬 Response:\n"+d.data.response.slice(0,1500);
      alert(msg);
    }else{alert(d.error||"Test Failed")}
  });
}

// Button helpers for agent table
function matTgBtn(a){
  return '<button class="btn bo bs" onclick="matTg('+a.id+','+(a.is_active?0:1)+')">'+(a.is_active?"Deactivate":"Enabled")+'</button> ';
}
function matEditBtn(a){
  return '<button class="btn bo bs" onclick="matEditAgent('+a.id+')" title="Edit Prompts &amp; Settings">✏️</button> ';
}
function matTestBtn(a){
  return '<button class="btn bp bs" onclick="matTest('+a.id+')">Test</button>';
}

// =============================================
// AI Service Panel
// =============================================
function matAIServices(){
  document.getElementById("pt").textContent="AI Capabilities";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Loading AI Services...</div>';
  fetch("/admin/agent-matrix/ai-services",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success){mc.innerHTML='<div class="em">Load failed</div>';return}
      var svcs=d.data;
      var h='<div style="margin-bottom:10px"><button class="btn bo bs" onclick="l_matrix()">← Back to Matrix</button></div>';
      h+='<div class="gr">';
      h+=sc("🤖","AI Services",svcs.length);
      h+=sc("🔑","Configured",svcs.filter(function(s){return s.key_status=="configured"}).length);
      h+=sc("❌","Not Configured",svcs.filter(function(s){return s.key_status=="missing"}).length);
      h+='</div>';
      svcs.forEach(function(s){
        var bg=s.key_status=="configured"?"rgba(0,212,170,.05)":"rgba(248,81,73,.05)";
        var bd=s.key_status=="configured"?"rgba(0,212,170,.2)":"rgba(248,81,73,.2)";
        h+='<div class="cd" style="margin-bottom:10px;border-color:'+bd+'">';
        h+='<div style="display:flex;justify-content:space-between;align-items:center">';
        h+='<div class="st" style="border:none;margin:0;padding:0">'+esc(s.name)+' <span class="bdg '+(s.key_status=="configured"?"on":"off")+'">'+(s.key_status=="configured"?"Configured":"Not Configured Key")+'</span></div>';
        h+='<span style="font-size:10px;color:var(--dim)">'+esc(s.type)+' | '+esc(s.provider)+'</span>';
        h+='</div>';
        // Key status
        h+='<div style="font-size:11px;color:var(--muted);margin-top:4px">';
        h+='Reference Config: <code style="background:rgba(0,0,0,.3);padding:1px 4px;border-radius:3px;font-size:10px">'+esc(s.key_ref)+'</code>';
        h+=' | Models: '+s.models.join(", ");
        h+='</div>';
        // Used by agents
        if(s.used_by_agents&&s.used_by_agents.length){
          h+='<div style="font-size:11px;color:var(--muted);margin-top:4px">';
          h+='Users of This Service Agent: ';
          s.used_by_agents.forEach(function(a,i){
            h+='<span class="bdg on" style="font-size:10px;margin-right:4px">'+esc(a.name)+'</span>';
          });
          h+='</div>';
        }
        // Endpoints
        if(s.endpoints&&s.endpoints.length){
          h+='<div style="font-size:10px;color:var(--dim);margin-top:4px">';
          h+='Endpoint: ';
          s.endpoints.forEach(function(e){
            h+='<div style="margin-left:12px">• '+esc(e)+'</div>';
          });
          h+='</div>';
        }
        // Note for unmanaged services
        if(s.note){
          h+='<div style="font-size:10px;color:#f85149;margin-top:4px;background:rgba(248,81,73,.08);padding:4px 8px;border-radius:4px">⚠️ '+esc(s.note)+'</div>';
        }
        // Test button for services that have configured keys
        if(s.key_status=="configured"){
          h+='<div style="margin-top:8px"><button class="btn bp bs" data-svc="'+s.id+'" onclick="matServiceTest(this.dataset.svc)">Quick Test</button></div>';
        }else{
          h+='<div style="margin-top:8px"><button class="btn bo bs" onclick="showToast(&#39;Please Configure in System Settings&#39;,&#39;error&#39;)">Config Key</button></div>';
        }
        h+='</div>';
      });
      mc.innerHTML=h;
    }).catch(function(){
      mc.innerHTML='<div class="em">Load failed</div>';
    });
}

// Quick test AI service
function matServiceTest(svcId){
  var tests={
    qwen_text:{name:"Text Generation",q:"Describe Agent Tech in One Sentence"},
    wanx_image:{name:"Text to Image",q:"Draw a Blue Cat"},
    matrix_chat:{name:"Matrix Chat",q:"List Your Agent Available"},
    trademind_chat:{name:"Chat Window",q:"Hello"}
  };
  var t=tests[svcId];
  if(!t){alert("Unknown Service");return}
  var msg="⏳ Test "+t.name+"... Please wait...";
  showToast(msg,"info");
  if(svcId=="qwen_text"){
    fetch("/admin/content-factory/ai-format",{
      method:"POST",
      headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
      body:JSON.stringify({content:t.q})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success)alert("✅ Test Passed!\n\nResponse:\n"+d.data.slice(0,500));
      else alert("❌ Test Failed: "+(d.error||"Unknown"));
    });
  }else if(svcId=="wanx_image"){
    fetch("/admin/social/generate-image",{
      method:"POST",
      headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
      body:JSON.stringify({prompt:t.q})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success)alert("✅ Test Passed!\nImageURL: "+(d.data.url||d.data||""));
      else alert("❌ Test Failed: "+(d.error||"Unknown"));
    });
  }else if(svcId=="trademind_chat"){
    matEditKnowledge();
  }else{
    alert("Please Use Matrix Chat to Test");
  }
}

// =============================================
// Chat Window KB Management
// =============================================
function matEditKnowledge(){
  document.getElementById("pt").textContent="Chat Window Management";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Loading Knowledge Base...</div>';
  fetch("/admin/agent-matrix/chat/knowledge",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success){mc.innerHTML='<div class="em">Load failed</div>';return}
      var content=d.data||"";
      var h='<div style="margin-bottom:10px"><button class="btn bo bs" onclick="matAIServices()">← Back AI Services</button></div>';
      h+='<div class="cd">';
      h+='<div class="st">💬 Chat Window Management <span style="font-size:10px;color:var(--dim);font-weight:400">｜ 由 Agent Matrix Ticket Agent Management</span></div>';
      h+='<div style="display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap">';
      h+='<div class="cd" style="flex:1;min-width:120px;padding:10px"><div class="l" style="font-size:10px">Status</div><div class="v g">Connected to Matrix</div></div>';
      h+='<div class="cd" style="flex:1;min-width:120px;padding:10px"><div class="l" style="font-size:10px">Management Agent</div><div class="v" style="font-size:14px">Ticket Agent</div></div>';
      h+='</div>';
      h+='<div style="font-size:11px;color:var(--dim);margin-bottom:4px">📖 Knowledge Base Content（As System Prompt Injected into Chat Window）</div>';
      h+='<textarea class="ta" id="matKnowledgeContent" rows="12" style="width:100%;font-family:monospace;font-size:12px;min-height:300px">'+esc(content)+'</textarea>';
      h+='<div style="margin-top:10px;display:flex;gap:8px;align-items:center">';
      h+='<button class="btn bp" onclick="matSaveKnowledge()">💾 Save Knowledge Base</button>';
      h+='<button class="btn bo" onclick="matAIServices()">Cancel</button>';
      h+='<span id="matKbStatus" style="font-size:11px;color:var(--dim)"></span>';
      h+='</div></div>';

      // Test area
      h+='<div class="cd" style="margin-top:12px">';
      h+='<div class="st">🔍 Quick Test Chat Window</div>';
      h+='<div style="display:flex;gap:8px;margin-bottom:8px">';
      h+='<input class="in" id="matTestChatQ" placeholder="Enter Test Question..." style="flex:1;font-size:12px">';
      h+='<button class="btn bp" onclick="matTestChatStream()">Send</button>';
      h+='</div>';
      h+='<div id="matTestChatResult" style="background:rgba(0,0,0,.3);border-radius:6px;padding:10px;min-height:80px;font-size:12px;color:var(--muted);white-space:pre-wrap"></div>';
      h+='</div>';

      mc.innerHTML=h;
    }).catch(function(){
      mc.innerHTML='<div class="em">Load failed</div>';
    });
}

// Save knowledge base
function matSaveKnowledge(){
  var content=document.getElementById("matKnowledgeContent").value;
  var st=document.getElementById("matKbStatus");
  st.textContent="Saving...";
  st.style.color="var(--muted)";
  fetch("/admin/agent-matrix/chat/knowledge",{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({content:content})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      st.textContent="✅ Saved ("+content.length+" Characters)";
      st.style.color="var(--accent)";
    }else{
      st.textContent="❌ Save failed";
      st.style.color="#f85149";
    }
  });
}

// Test chat with streaming
function matTestChatStream(){
  var q=document.getElementById("matTestChatQ").value.trim();
  if(!q)return;
  var result=document.getElementById("matTestChatResult");
  result.textContent="";
  fetch("/admin/agent-matrix/chat/stream",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({message:q,history:[]})
  }).then(function(r){
    var reader=r.body.getReader();
    var decoder=new TextDecoder();
    function read(){
      reader.read().then(function(result){
        var text=decoder.decode(result.value,{stream:!result.done});
        var lines=text.split("\\n");
        lines.forEach(function(line){
          line=line.trim();
          if(!line||!line.startsWith("data: "))return;
          var payload=line.slice(6);
          if(payload=="[DONE]")return;
          try{
            var data=JSON.parse(payload);
            if(data.role)return;
            result.textContent+=data;
          }catch(e){}
        });
        if(!result.done)read();
      });
    }
    read();
    return null;
  });
}



window.l_email=function(){
  document.getElementById("pt").textContent="Email Management";
  var h='<div style="margin-bottom:12px"><button class="btn bp" onclick="se()">Write Email</button></div>';
  h+='<div id="sendForm" style="display:none;margin-bottom:16px" class="cd"><div class="st">Write Email</div>';
  h+='<div style="margin-bottom:10px">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px"><span style="font-size:12px;color:var(--dim)">Recipient</span><span style="font-size:11px;color:var(--dim)">Separate Multiple Addresses with Commas</span></div>';
  h+='<input class="in" id="em-to" placeholder="email1@example.com, email2@example.com" style="width:100%">';
  h+='<div id="em-recipients" style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px"></div></div>';
  h+='<div style="margin-bottom:10px"><div style="font-size:12px;color:var(--dim);margin-bottom:4px">Theme</div><input class="in" id="em-sub" placeholder="Email Subject" style="width:100%"></div>';
  h+='<div style="margin-bottom:10px"><div style="font-size:12px;color:var(--dim);margin-bottom:4px">Content</div><div id="em-editor" style="min-height:200px;background:rgba(0,0,0,.3);border-radius:8px;border:1px solid var(--border)"></div></div>';
  h+='<div style="margin-bottom:10px"><div style="font-size:12px;color:var(--dim);margin-bottom:4px">Attachment</div>';
  h+='<input type="file" id="em-file" multiple onchange="addAttach()" style="display:none">';
  h+='<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><button class="btn bo bs" onclick="document.getElementById(\'em-file\').click()">+ Add Attachment</button><div id="em-attach-list" style="display:flex;gap:6px;flex-wrap:wrap"></div></div></div>';
  h+='<div style="margin-top:10px;display:flex;gap:8px"><button class="btn bp" onclick="ds()">Send</button> <button class="btn bo" onclick="hsf()">Cancel</button></div></div>';
  h+='<div class="cd"><div class="st">Inbox</div><div id="inboxList"><div class="lo"><div class="s"></div></div></div></div>';
  // Contacts panel
  h+='<div class="cd" style="margin-top:12px"><div class="st" style="cursor:pointer" onclick="toggleContacts()">📇 Contact Person <span id="contactToggle" style="font-size:10px;color:var(--dim)">[Expand]</span></div>';
  h+='<div id="contactsPanel" style="display:none">';
  h+='<div style="display:flex;gap:8px;margin-bottom:8px;align-items:center">';
  h+='<button class="btn bp bs" onclick="selectAllContacts()">Select All</button>';
  h+='<button class="btn bo bs" onclick="deselectAllContacts()">Deselect All</button>';
  h+='<button class="btn bp" onclick="sendBulk()" style="font-size:11px">📤 Broadcast to Selected Contacts</button>';
  h+='<span id="contactCount" style="font-size:11px;color:var(--dim)">0 Contact Person(s)</span>';
  h+='</div><div id="contactsList"><div class="lo"><div class="s"></div></div></div></div></div>';
  document.getElementById("mc").innerHTML=h;
  // Prepare Quill
  window.emEditor=null;
  window.emAttachments=[];
  // Load contacts
  loadContacts();
  // Auto-parse recipients on input
  document.getElementById("em-to").addEventListener("input",parseRecipients);
  fetch("/admin/email/inbox",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){document.getElementById("inboxList").innerHTML='<div class="em">Load failed</div>';return}
    var lst=d.data.items||d.data;
    if(!lst.length){document.getElementById("inboxList").innerHTML='<div class="em">No Emails</div>';return}
    var tbl='&lt;table&gt;&lt;tr&gt;&lt;th&gt;From&lt;/th&gt;&lt;th&gt;Subject&lt;/th&gt;&lt;th&gt;Attachment&lt;/th&gt;&lt;th&gt;Time&lt;/th&gt;&lt;th&gt;Action&lt;/th&gt;&lt;/tr&gt;';
    lst.forEach(function(e){
      var attIcon=e.has_attachments?' <span style="color:var(--accent)">📎</span>':'';
      tbl+='<tr><td>'+(e.from||'-')+'</td><td>'+(e.subject||'(No Subject)')+attIcon+'</td><td>'+(e.has_attachments?'<span style="color:var(--accent)">有</span>':'')+'</td><td>'+(e.date||'')+'</td>';
      tbl+='<td><button class="btn bo bs" onclick="re('+e.uid+',\''+e.from.replace(/'/g,'')+'\',\''+(e.subject||'').replace(/'/g,'')+'\')">Reply</button> <button class="btn bo" onclick="viewEmail('+e.uid+')">View</button></td></tr>';
    });
    tbl+='</table>';
    document.getElementById("inboxList").innerHTML=tbl;
  }).catch(function(){})
}

var emContacts=[];
var emSelectedContacts=[];
function loadContacts(){
  fetch("/admin/email/contacts",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success&&d.data){emContacts=d.data;renderContacts()}
  }).catch(function(){})
}
function renderContacts(){
  var el=document.getElementById("contactsList");
  if(!el)return;
  var total=emContacts.length;
  document.getElementById("contactCount").textContent=total+" Contact Person(s)";
  if(!total){el.innerHTML='<div class="em">No Contact Person（Auto-collect After Sending Email）</div>';return}
  var h='<table><tr><th style="width:36px"><input type="checkbox" onchange="toggleAllContacts(this.checked)"></th><th>Name</th><th>Email</th><th>Source</th><th>Count</th></tr>';
  emContacts.forEach(function(c,i){
    var checked=emSelectedContacts.indexOf(c.email)>=0?' checked':'';
    var src=c.source==='contact'?'<span class="bdg pd">Form</span>':'<span class="bdg on">Sent</span>';
    h+='<tr><td><input type="checkbox" class="contact-cb" data-email="'+c.email+'" data-name="'+c.name+'"'+checked+' onchange="toggleContact(this)"></td>'+
      '<td>'+(c.name||'-')+'</td><td style="color:var(--accent)">'+c.email+'</td><td>'+src+'</td><td>'+c.count+'</td></tr>';
  });
  h+='</table>';
  el.innerHTML=h;
}
function toggleAllContacts(checked){
  var cbs=document.querySelectorAll("#contactsList .contact-cb");
  cbs.forEach(function(cb){cb.checked=checked;toggleContact(cb)});
}
function toggleContact(cb){
  var email=cb.getAttribute("data-email");
  if(cb.checked){
    if(emSelectedContacts.indexOf(email)<0)emSelectedContacts.push(email);
  }else{
    emSelectedContacts=emSelectedContacts.filter(function(e){return e!==email});
  }
}
function selectAllContacts(){
  var cbs=document.querySelectorAll("#contactsList .contact-cb");
  cbs.forEach(function(cb){cb.checked=true;if(emSelectedContacts.indexOf(cb.getAttribute("data-email"))<0)emSelectedContacts.push(cb.getAttribute("data-email"))});
}
function deselectAllContacts(){
  var cbs=document.querySelectorAll("#contactsList .contact-cb");
  cbs.forEach(function(cb){cb.checked=false});
  emSelectedContacts=[];
}
function toggleContacts(){
  var p=document.getElementById("contactsPanel");
  var t=document.getElementById("contactToggle");
  if(p.style.display==="none"||!p.style.display){
    p.style.display="block";
    t.textContent="[Collapse]";
    renderContacts();
  }else{
    p.style.display="none";
    t.textContent="[Expand]";
  }
}
function sendBulk(){
  if(!emSelectedContacts.length){alert("Please Select Contacts to Send");return}
  var count=emSelectedContacts.length;
  var el=document.getElementById("em-to");
  el.value=emSelectedContacts.join(", ");
  parseRecipients();
  se();
  emSelectedContacts=[];
  document.querySelectorAll("#contactsList .contact-cb").forEach(function(cb){cb.checked=false});
  showToast("Filled In "+count+" Recipient(s)，Edit Content &amp; Send","success");
}
function parseRecipients(){
  var el=document.getElementById("em-to");
  var raw=el.value;
  // Extract all emails from comma-separated input
  var addrs=raw.split(",").map(function(a){return a.trim()}).filter(function(a){return a.length>0&&a.includes("@")});
  var container=document.getElementById("em-recipients");
  if(!addrs.length){container.innerHTML="";return}
  var h='';
  addrs.forEach(function(a){
    // Find matching contact name
    var name='';
    for(var i=0;i<emContacts.length;i++){
      if(emContacts[i].email.toLowerCase()===a.toLowerCase()){name=emContacts[i].name;break}
    }
    var label=name||a.split("@")[0];
    h+='<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 8px;background:rgba(0,212,170,.1);border:1px solid rgba(0,212,170,.3);border-radius:4px;font-size:12px">'+label+' <span style="color:var(--dim);font-size:10px">'+a+'</span></span>';
  });
  container.innerHTML=h;
}
var emAttachments=[];
function addAttach(){
  var files=document.getElementById("em-file").files;
  for(var i=0;i<files.length;i++){
    var f=files[i];
    if(f.size>10*1024*1024){alert('Attachment '+f.name+' Exceeds 10MB Limit');continue}
    var reader=new FileReader();
    reader.onload=function(fn,fsize){return function(e){
      emAttachments.push({filename:fn,data:e.target.result.split(',')[1],content_type:fn.split('.').pop()==='pdf'?'application/pdf':'application/octet-stream',size:fsize});
      renderAttachList();
    }}(f.name,f.size);
    reader.readAsDataURL(f);
  }
  document.getElementById("em-file").value='';
}
function renderAttachList(){
  var el=document.getElementById("em-attach-list");
  if(!emAttachments.length){el.innerHTML='';return}
  var h='';
  emAttachments.forEach(function(a,i){
    var size=(a.size/1024).toFixed(1)+'KB';
    if(a.size>1024*1024)size=(a.size/1024/1024).toFixed(1)+'MB';
    h+='<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 8px;background:var(--bg);border-radius:4px;font-size:11px">📎 '+a.filename+' ('+size+') <span onclick="removeAttach('+i+')" style="cursor:pointer;color:var(--dim)">✕</span></span>';
  });
  el.innerHTML=h;
}
function removeAttach(i){emAttachments.splice(i,1);renderAttachList()}
function se(){
  document.getElementById("sendForm").style.display="block";
  if(!window.emEditor){
    window.emEditor=new Quill('#em-editor',{theme:'snow',placeholder:'Email Body...',modules:{toolbar:[['bold','italic','underline','strike'],[{list:'ordered'},{list:'bullet'}],['link','blockquote','code-block'],[{size:['small',false,'large','huge']}],[{color:[]},{background:[]}],['clean']]}});
  }
  setTimeout(function(){window.emEditor&&window.emEditor.focus()},100)
}
function hsf(){document.getElementById("sendForm").style.display="none"}
function ds(){
  var to=document.getElementById("em-to").value.trim();
  var sub=document.getElementById("em-sub").value.trim();
  var html=window.emEditor?window.emEditor.root.innerHTML:'';
  var text=window.emEditor?window.emEditor.getText().trim():'';
  if(!to||!sub||(!html&&!text)){showToast('Please fill in completely','error');return}
  var body=text||'';
  fetch("/admin/email/send",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({to:to,subject:sub,body:body,body_html:html||null,attachments:emAttachments.length?emAttachments:null})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast('✅ Sent','success');emAttachments=[];renderAttachList();hsf();l_email()}else{showToast('❌ '+(d.error||'Failed to send'),'error')}
  }).catch(function(){showToast('❌ Send failed','error')})
}
function re(uid,from,sub){
  document.getElementById("em-to").value=from;
  var rsub=sub.startsWith("Re:")?sub:"Re: "+sub;
  document.getElementById("em-sub").value=rsub;
  if(window.emEditor)window.emEditor.root.innerHTML='';
  se();
}

// ════════════════════════════════════════════════════════════════
function escAttr(s){
  if(!s)return '';
  return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;');
}


window.l_downloads=function(){
  document.getElementById("pt").textContent="Download Management";
  fetch("/admin/downloads",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var h='<div style="margin-bottom:12px"><button class="btn bp" onclick="dlForm()">+ Upload Download</button></div>';
    h+='<div id="dlForm" style="display:none;margin-bottom:16px" class="cd"><div class="st" id="dlFormTitle">Upload Download</div><div class="g2">';
    h+='<div><div style="font-size:11px;color:var(--dim)">Installer *</div><input type="file" id="dlFile" style="width:100%;font-size:12px;padding:4px 0" onchange="dlFC()"><div id="dlFI" style="font-size:10px;color:var(--dim);margin-top:2px"></div></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Name *</div><input class="in" id="dlName" style="width:100%" placeholder="Hermes Agent"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Slug *</div><input class="in" id="dlSlug" style="width:100%" placeholder="hermes-agent"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Categories</div><select class="sl" id="dlCat" style="width:100%"><option value="core">Core Framework</option><option value="skills" selected>Skills</option><option value="sdk">SDK</option><option value="plugin">Plugins</option><option value="model">Models</option></select></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Version</div><input class="in" id="dlVer" style="width:100%" value="1.0.0"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Bio</div><input class="in" id="dlTagline" style="width:100%" placeholder="One-Line Description"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">External Links (Optional)</div><input class="in" id="dlUrl" style="width:100%" placeholder="GitHub Release URL..."></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">GitHub</div><input class="in" id="dlRepo" style="width:100%" placeholder="https://github.com/user/repo"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Size (Leave Empty for Auto)</div><input class="in" id="dlSize" style="width:100%" placeholder="Auto Detect"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Tags</div><input class="in" id="dlTags" style="width:100%" placeholder="stable, official"></div>';
    h+='<div style="grid-column:1/3"><label style="font-size:12px;color:var(--muted)"><input type="checkbox" id="dlPub" checked> Publish</label></div>';
    h+='<input type="hidden" id="dlEditId" value="">';
    h+='</div><div style="margin-top:10px"><button class="btn bp" onclick="dlSave()">Save</button> <button class="btn bo" onclick="dlH()">Cancel</button></div></div>';
    h+='<div class="cd"><div class="st">Download List ('+d.data.length+')</div><table><tr><th>Name</th><th>Categories</th><th>Version</th><th>Status</th><th>Download</th><th>Actions</th></tr>';
    d.data.forEach(function(dl){
      var st=dl.is_published?'<span class="bdg on">Published</span>':'<span class="bdg off">Hide</span>';
      h+='<tr><td>'+esc(dl.name||'-')+'</td><td>'+dl.category+'</td><td>'+dl.version+'</td><td>'+st+'</td><td>'+dl.download_count+'</td><td>';
      h+='<button class="btn bo bs" onclick="dlE('+dl.id+')">Edit</button> ';
      h+='<button class="btn bo bs" onclick="dlD('+dl.id+')">Delete</button></td></tr>';
    });
    h+='</table></div>';
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){})
};
var dlFileData=null;
function dlFC(){var f=document.getElementById("dlFile").files[0];if(!f){dlFileData=null;document.getElementById("dlFI").textContent="";return}dlFileData=f;var s=f.size<1048576?(f.size/1024).toFixed(1)+" KB":(f.size/1048576).toFixed(1)+" MB";document.getElementById("dlFI").textContent=f.name+" ("+s+")";if(!document.getElementById("dlSize").value)document.getElementById("dlSize").value=s}
function dlForm(){document.getElementById("dlForm").style.display="block";document.getElementById("dlFormTitle").textContent="Upload Download";document.getElementById("dlEditId").value="";document.getElementById("dlName").value="";document.getElementById("dlSlug").value="";document.getElementById("dlTagline").value="";document.getElementById("dlVer").value="1.0.0";document.getElementById("dlUrl").value="";document.getElementById("dlRepo").value="";document.getElementById("dlSize").value="";document.getElementById("dlTags").value="";document.getElementById("dlPub").checked=true;document.getElementById("dlFile").value="";dlFileData=null;document.getElementById("dlFI").textContent=""}
function dlH(){document.getElementById("dlForm").style.display="none"}
function dlSave(){
  var id=document.getElementById("dlEditId").value;
  var fd=new FormData();
  fd.append("name",document.getElementById("dlName").value);
  fd.append("slug",document.getElementById("dlSlug").value);
  fd.append("tagline",document.getElementById("dlTagline").value);
  fd.append("category",document.getElementById("dlCat").value);
  fd.append("version",document.getElementById("dlVer").value);
  fd.append("download_url",document.getElementById("dlUrl").value);
  fd.append("repo_url",document.getElementById("dlRepo").value);
  fd.append("file_size",document.getElementById("dlSize").value);
  var tags=document.getElementById("dlTags").value.split(",").map(function(s){return s.trim()}).filter(function(s){return s});
  fd.append("tags",JSON.stringify(tags));
  fd.append("is_published",document.getElementById("dlPub").checked?"1":"0");
  if(dlFileData)fd.append("file",dlFileData);
  var url="/admin/downloads",method="POST";
  if(id){url+="?id="+id;method="PUT"}
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T},body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.success){dlH();l_downloads();showToast("Saved","success");dlFileData=null}
    else{alert(d.error||"Save failed")}
  }).catch(function(){alert("Save failed")})
}
function dlE(id){
  fetch("/admin/downloads/"+id,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var dl=d.data;
    document.getElementById("dlForm").style.display="block";
    document.getElementById("dlFormTitle").textContent="Edit — "+dl.name;
    document.getElementById("dlEditId").value=dl.id;
    document.getElementById("dlName").value=dl.name||"";
    document.getElementById("dlSlug").value=dl.slug||"";
    document.getElementById("dlTagline").value=dl.tagline||"";
    document.getElementById("dlCat").value=dl.category||"skills";
    document.getElementById("dlVer").value=dl.version||"1.0.0";
    document.getElementById("dlUrl").value=dl.download_url||"";
    document.getElementById("dlRepo").value=dl.repo_url||"";
    document.getElementById("dlSize").value=dl.file_size||"";
    document.getElementById("dlTags").value=(dl.tags||[]).join(", ");
    document.getElementById("dlPub").checked=dl.is_published===1;
    document.getElementById("dlFile").value="";dlFileData=null;document.getElementById("dlFI").textContent="";
  })
}
function dlD(id){
  if(!confirm("Delete?"))return;
  fetch("/admin/downloads/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){l_downloads();showToast("Deleted","success")}
    else{alert(d.error||"Delete failed")}
  }).catch(function(){alert("Delete failed")})
}
function showToast(msg,type){
  var t=document.getElementById("adminToast");
  t.textContent=msg;
  t.className="toast show "+(type||"");
  setTimeout(function(){t.classList.remove("show")},3000);
}
function viewEmail(uid){
  fetch("/admin/email/read/"+uid,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){showToast("Load failed: "+(d.error||""),"error");return}
    var m=d.data;
    var bodyHtml=m.body_html||"";
    var bodyText=(m.body||"(No Content)").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\n/g,"<br>");
    var h='<div class="modal-overlay" onclick="closeEmailModal(event)">';
    h+='<div class="modal-box" onclick="event.stopPropagation()">';
    h+='<button onclick="closeEmailModal()" style="float:right;background:none;border:none;color:var(--dim);font-size:20px;cursor:pointer;line-height:1">✕</button>';
    h+='<h3>'+(m.subject||"(No Subject)")+'</h3>';
    h+='<div class="modal-meta">';
    h+='<div><span>Sender</span> '+(m.from||"-")+'</div>';
    h+='<div><span>Recipient</span> '+(m.to||"-")+'</div>';
    h+='<div><span>Time</span> '+(m.date||"-")+'</div>';
    h+='</div>';
    h+='<div class="modal-body">';
    if(bodyHtml){h+=bodyHtml}
    else{h+=bodyText}
    h+='</div>';
    // Attachments
    if(m.attachments&&m.attachments.length){
      h+='<div class="modal-attach"><span style="font-size:12px;color:var(--dim)">📎 Attachment</span>';
      m.attachments.forEach(function(a){
        var fn=a.filename||a.name||"file";
        h+=' <a href="/admin/email/attachment/'+uid+'/'+encodeURIComponent(fn)+'" target="_blank">📎 '+fn+'</a>';
      });
      h+='</div>';
    }
    h+='<div style="margin-top:16px;display:flex;gap:8px">';
    h+='<button class="btn bp" onclick="re('+uid+',\''+(m.from||"").replace(/'/g,"")+'\',\''+(m.subject||"").replace(/'/g,"")+'\');closeEmailModal()">↩ Reply</button>';
    h+='<button class="btn bo" onclick="closeEmailModal()">Close</button></div></div></div>';
    // Remove any existing modal
    var old=document.querySelector(".modal-overlay");
    if(old)old.remove();
    document.body.insertAdjacentHTML("beforeend",h);
  }).catch(function(){showToast("Load failed","error")});
}
function closeEmailModal(e){
  if(e&&e.target!==e.currentTarget)return;
  var m=document.querySelector(".modal-overlay");
  if(m)m.remove();
}


window.l_sms=function(){
  document.getElementById("pt").textContent="SMS Management";
  var h='<div class="cd"><div class="st">📱 SMS Template Management</div><div style="margin-bottom:12px"><button class="btn bp" onclick="showSmsForm()">+ Add Template</button></div>';
  h+='<div id="smsForm" style="display:none;margin-bottom:16px" class="cd"><div class="st" id="smsFormTitle">Add Template</div>';
  h+='<div class="g2">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Categories</div><select class="sl" id="smsCat" style="width:100%"><option value="captcha">Verification Code</option><option value="notice">SMS Notification</option><option value="promo">SMS Promotion</option></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Name</div><input class="in" id="smsName" placeholder="如：New User Registration" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Templates CODE</div><input class="in" id="smsCode" placeholder="SMS_xxxxxxxxx" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Notes</div><input class="in" id="smsNote" placeholder="Usage Description" style="width:100%"></div>';
  h+='</div>';
  h+='<div style="margin-top:10px"><button class="btn bp" onclick="saveSmsTemplate()">Save</button> <button class="btn bo" onclick="document.getElementById(\'smsForm\').style.display=\'none\'">Cancel</button><input type="hidden" id="smsEditId" value=""></div></div>';
  h+='<div id="smsTemplates"></div></div>';
  document.getElementById("mc").innerHTML=h;
  loadSmsTemplates();
};

function loadSmsTemplates(){
  fetch("/admin/sms/templates",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){document.getElementById("smsTemplates").innerHTML='<div class="em">Load failed</div>';return}
    var cats=d.data.categories;
    var h="";
    var order=["captcha","notice","promo"];
    order.forEach(function(k){
      var c=cats[k];
      if(!c||!c.items||!c.items.length){return}
      h+='<div class="cd" style="margin-bottom:12px"><div class="st">'+c.title+' ('+c.items.length+')</div><table><tr><th>Name</th><th>Templates CODE</th><th>Notes</th><th>Actions</th></tr>';
      c.items.forEach(function(t){
        h+='<tr><td>'+esc(t.name)+'</td><td style="font-family:monospace;color:var(--accent)">'+esc(t.template_code)+'</td><td style="color:var(--dim)">'+esc(t.note)+'</td>';
        h+='<td><button class="btn bo bs" onclick="editSmsTemplate('+t.id+',\''+t.category+'\',\''+esc(t.name)+'\',\''+esc(t.template_code)+'\',\''+esc(t.note)+'\')">Edit</button> ';
        h+='<button class="btn bo bs" onclick="deleteSmsTemplate('+t.id+')">Delete</button></td></tr>';
      });
      h+='</table></div>';
    });
    if(!h){h='<div class="em">No Templates，Click Above「Add Template」Create</div>'}
    document.getElementById("smsTemplates").innerHTML=h;
  }).catch(function(){document.getElementById("smsTemplates").innerHTML='<div class="em">Load failed</div>'})
}

function showSmsForm(){
  document.getElementById("smsForm").style.display="block";
  document.getElementById("smsFormTitle").textContent="Add Template";
  document.getElementById("smsEditId").value="";
  document.getElementById("smsCat").value="captcha";
  document.getElementById("smsName").value="";
  document.getElementById("smsCode").value="";
  document.getElementById("smsNote").value="";
}

function saveSmsTemplate(){
  var eid=document.getElementById("smsEditId").value;
  var cat=document.getElementById("smsCat").value;
  var name=document.getElementById("smsName").value.trim();
  var code=document.getElementById("smsCode").value.trim();
  var note=document.getElementById("smsNote").value.trim();
  if(!name||!code){alert("Name &amp; Template CODE Required");return}
  var url="/admin/sms/templates";
  var method="POST";
  var body={category:cat,name:name,template_code:code,note:note};
  if(eid){
    url+="/"+eid;
    method="PUT";
    body={name:name,template_code:code,note:note};
  }
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){document.getElementById("smsForm").style.display="none";loadSmsTemplates();showToast("Saved","success")}
    else{alert(d.error||"Save failed")}
  }).catch(function(){alert("Save failed")})
}

function editSmsTemplate(id,cat,name,code,note){
  document.getElementById("smsForm").style.display="block";
  document.getElementById("smsFormTitle").textContent="Edit Template";
  document.getElementById("smsEditId").value=id;
  document.getElementById("smsCat").value=cat;
  document.getElementById("smsName").value=name;
  document.getElementById("smsCode").value=code;
  document.getElementById("smsNote").value=note;
}

function deleteSmsTemplate(id){
  if(!confirm("Delete this template?"))return;
  fetch("/admin/sms/templates/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){loadSmsTemplates();showToast("Deleted","success")}
    else{alert(d.error||"Delete failed")}
  }).catch(function(){alert("Delete failed")})
}

// ── Omni-Media Creation（Posts Only）──

window.l_cms=function(){
  document.getElementById("pt").textContent="Omni-Media Creation";
  document.getElementById("mc").innerHTML='<div id="cmsContent"></div>';
  cmsTabArticle();
};

// ── Tab 0: Article Edit（原 CMS）──
function cmsTabArticle(){
  var h='';
  h+='<div style="margin-bottom:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">';
  h+='<button class="btn bp" onclick="cmsFilterPosts(\'all\')" id="cmsF-all">All</button>';
  h+='<button class="btn bo" onclick="cmsFilterPosts(\'draft\')" id="cmsF-draft">📝 Drafts</button>';
  h+='<button class="btn bo" onclick="cmsFilterPosts(\'published\')" id="cmsF-published">✅ Published</button>';
  h+='<span style="flex:1"></span>';
  h+='<button class="btn bp" onclick="cmsNewPost()">+ New Article</button>';
  h+='<button class="btn bo" onclick="cmsManageCategories()">Column Management</button>';
  h+='<button class="btn bo" onclick="cmsGenerateAllStatic()">🗂 Generate Full Site Static Pages</button>';
  h+='</div>';
  h+='<div id="cmsPostForm" style="display:none;margin-bottom:14px" class="cd">';
  h+='<div class="st" id="cmsFormTitle">New Article</div>';
  h+='<div class="g2">';
  h+='<div><div style="font-size:11px;color:var(--dim);margin-bottom:3px">Title</div><input class="in" id="cmsPTitle" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim);margin-bottom:3px">Column</div><select class="sl" id="cmsPCat" style="width:100%"></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim);margin-bottom:3px">Author</div><input class="in" id="cmsPAuthor" style="width:100%"></div>';
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim);margin-bottom:3px">Summary</div><input class="in" id="cmsPSummary" style="width:100%"></div>';
  h+='</div>';
  h+='<div style="margin-top:8px"><div style="font-size:11px;color:var(--dim);margin-bottom:3px">Body</div>';
  h+='<div id="cmsPBody" style="min-height:350px;background:var(--bg);color:var(--text)"></div></div>';
  h+='<div style="margin-top:8px;display:flex;gap:6px">';
  h+='<button class="btn bo" onclick="cmsAiformat()">🤖 AILayout</button> ';
  h+='<button class="btn bo" onclick="cmsAicover()">🎨 AIAdd Image</button></div>';
  h+='<div style="margin-top:12px;padding:10px;background:var(--bg);border-radius:6px;border:1px solid var(--border)">';
  h+='<div style="font-size:12px;font-weight:600;margin-bottom:6px;color:var(--text)">📤 Publish Channel（Multi-Select）</div>';
  h+='<div id="cmsChannelLocal" style="margin-bottom:6px"><div style="font-size:10px;color:var(--dim);margin-bottom:3px">Local Column</div><div id="cmsChLocalList"></div></div>';
  h+='<div id="cmsChannelSocial"><div style="font-size:10px;color:var(--dim);margin-bottom:3px">Social Media Platform</div><div id="cmsChSocialList"></div></div>';
  h+='</div>';
  h+='<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">';
  h+='<button class="btn bo" onclick="cmsSaveDraft()">💾 Save Draft</button> ';
  h+='<button class="btn bo bs" onclick="cmsPreviewPost()" id="cmsPreviewBtn" style="display:none">👁 Preview</button> ';
  h+='<button class="btn bp" onclick="cmsPublishPost()">📤 Publish to Selected Channels</button> ';
  h+='<button class="btn bo" onclick="cmsGenerateStatic()">🗂 Generate Static Pages</button> ';
  h+='<button class="btn bo" onclick="cmsCloseForm()">Cancel</button><input type="hidden" id="cmsPEid"></div></div>';
  h+='<div class="cd"><div class="st">Article List</div><table><tr><th>ID</th><th>Title</th><th>Column</th><th>Author</th><th>Status</th><th>Publish Channel</th><th>👀</th><th>Time</th><th>Actions</th></tr><tbody id="cmsPostBody"></tbody></table></div>';
  h+='<button class="btn bo" style="margin-top:12px" onclick="cmsToggleSocialHistory()">📤 Publish History</button>';
  h+='<div id="cmsSocialHistoryWrap" style="display:none;margin-top:8px"></div>';
  document.getElementById("cmsContent").innerHTML=h;
  cmsLoadCategories();
  cmsLoadSocialPlatforms();
  cmsFilterPosts('all');
}

// ── Tab 1: AI Chat（Original Command Console）──
function cmsTabChat(){
  var h='<div class="cd" style="margin-bottom:12px;border-color:rgba(0,212,170,.3)">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center">';
  h+='<div class="st" style="border:none;margin:0;padding:0">🤖 主 Agent: Athena <span class="bdg on">Running</span></div>';
  h+='<button class="btn bo bs" onclick="cmsTabChat()">🔄 Refresh</button>';
  h+='</div></div>';
  h+='<div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap">';
  h+='<button class="btn bo bs" id="aiBtnFast" style="font-size:11px;padding:3px 10px;border-color:var(--accent);background:rgba(0,245,255,0.1)" onclick="aiSetMode(\'fast\')">⚡ Fast</button>';
  h+='<button class="btn bo bs" id="aiBtnDeep" style="font-size:11px;padding:3px 10px" onclick="aiSetMode(\'deep\')">🧠 Deep Thinking</button>';
  h+='<button class="btn bo bs" id="aiBtnImage" style="font-size:11px;padding:3px 10px" onclick="aiSetMode(\'image\')">🎨 Image Understanding</button>';
  h+='<button class="btn bo bs" style="font-size:11px;padding:3px 10px;color:#f0ad4e" id="aiBtnTool" onclick="aiSetMode(\'tool\')">🔧 Tool Call</button>';
  h+='<span style="flex:1"></span>';
  h+='<button class="btn bo bs" style="font-size:11px;padding:3px 10px" onclick="aiNewSession()">🆕 New Chat</button>';
  h+='<button class="btn bo bs" style="font-size:11px;padding:3px 10px;color:#f85149" onclick="aiResetSession()">🔄 Reset</button>';
  h+='</div>';
  h+='<div id="aiChatMsgs" style="min-height:280px;max-height:380px;overflow-y:auto;margin-bottom:8px;padding:8px;background:rgba(0,0,0,.2);border-radius:6px;font-size:12px;line-height:1.6">';
  h+='<div style="color:var(--dim);text-align:center;padding:20px">💬 Send Command to Start Chat。Try：「Generate AboutAI的10页PPT」或「Draw a Cyberpunk Cat」</div>';
  h+='</div>';
  h+='<div style="display:flex;gap:4px;margin-bottom:12px">';
  h+='<input type="file" id="aiFileInput" style="display:none" onchange="aiUpload(this)" accept="image/*,audio/*,video/*">';
  h+='<button class="btn bo bs" onclick="document.getElementById(\'aiFileInput\').click()" title="Upload File(Image/Audio/Video)" style="font-size:14px;padding:3px 8px">📎</button>';
  h+='<textarea class="in" id="aiChatInput" placeholder="Enter Command，如「GeneratePPT」「Draw」「Analyze Image」「Clone Voice」" style="flex:1;font-size:12px;resize:none;min-height:36px;max-height:120px;line-height:1.4;padding-top:8px;padding-bottom:8px" onkeydown="if(event.key===\'Enter\'&&!event.ctrlKey&&!event.shiftKey){event.preventDefault();aiSend()}" oninput="aiAutoResize(this)"></textarea>';
  h+='<button class="btn bp" onclick="aiSend()">Send</button>';
  h+='</div>';
  h+='<div class="cd"><div class="st">💬 Chat History</div>';
  h+='<div style="display:flex;gap:4px;margin-bottom:6px">';
  h+='<input class="in" id="aiSearchInput" placeholder="Search Keywords..." style="flex:1;font-size:11px;padding:4px 6px" onkeydown="if(event.key===\'Enter\')aiSearchSessions()">';
  h+='<button class="btn bo bs" style="font-size:10px;padding:2px 6px" onclick="aiSearchSessions()">🔍</button>';
  h+='<button class="btn bo bs" style="font-size:10px;padding:2px 6px;color:#f85149" onclick="aiBatchDelete()">🗑️</button>';
  h+='</div><div id="aiSessions"><div class="lo"><div class="s"></div></div></div></div>';
  document.getElementById("cmsContent").innerHTML=h;
  fetch("/admin/agent-matrix/chat/history",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data)return;
      var sl=d.data,el=document.getElementById("aiSessions");
      if(!el)return;
      if(!sl.length){el.innerHTML='<div class="em">No Chat History</div>';return}
      var sh='<table><tr><th style="width:30px"><input type="checkbox" id="aiSelAll" onchange="aiToggleAll(this)"></th><th>Session Title</th><th>Last Time</th><th>Actions</th></tr>';
      sl.forEach(function(s){
        var title=s.session_name||s.first_query||s.session_id;
        sh+='<tr onclick="aiLoadSession(this.dataset.sid)" data-sid="'+esc(s.session_id)+'" style="cursor:pointer">';
        sh+='<td style="width:30px;text-align:center" onclick="event.stopPropagation()"><input type="checkbox" class="aiSel" value="'+esc(s.session_id)+'"></td>';
        sh+='<td>'+esc((title||'').slice(0,50))+'</td>';
        sh+='<td style="font-size:10px;color:var(--dim)">'+esc(s.last_msg||"")+'</td>';
        sh+='<td style="width:40px" onclick="event.stopPropagation()"><button class="btn bs" style="font-size:10px;padding:1px 4px" onclick="aiDeleteSession(this)">🗑️</button></td></tr>';
      });
      sh+='</table>';el.innerHTML=sh;
    }).catch(function(){});
};

// ── Tab 2: PPT Generate ──
function cmsTabPPT(){
  var h='<div class="cd"><div class="st">📊 Generate PPT</div>';
  h+='<div class="g2" style="margin-bottom:8px">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Theme *</div><input class="in" id="pptTopic" placeholder="如：Quantum Computing Frontier Tech" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Pages</div><select class="sl" id="pptPages" style="width:100%"><option value="5">5页</option><option value="8">8页</option><option value="10" selected>10页</option><option value="15">15页</option><option value="20">20页</option></select></div>';
  h+='</div>';
  h+='<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--dim)">Style Description</div><input class="in" id="pptStyle" placeholder="Default：Dark Tech Style，16:9" style="width:100%"></div>';
  h+='<button class="btn bp" id="pptGenBtn" onclick="pptGenerate()">🤖 AI Generate PPT</button>';
  h+='<div id="pptResult" style="margin-top:8px"></div></div>';
  document.getElementById("cmsContent").innerHTML=h;
}

// ── Tab 3: Image Gen ──
function cmsTabImage(){
  var h='<div class="cd"><div class="st">🎨 Image Gen</div>';
  h+='<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--dim)">Prompt *</div>';
  h+='<textarea class="in" id="imgPrompt" placeholder="Describe the Image You Want in Chinese..." style="width:100%;min-height:80px"></textarea></div>';
  h+='<div class="g2" style="margin-bottom:8px">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Style</div><select class="sl" id="imgStyle" style="width:100%"><option value="realistic">Realistic</option><option value="anime">Anime</option><option value="oil-painting">Oil Painting</option><option value="cyberpunk">Cyberpunk</option><option value="watercolor">Watercolor</option><option value="3d-render">3DRender</option></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Count</div><select class="sl" id="imgCount" style="width:100%"><option value="1">1张</option><option value="2">2张</option><option value="4">4张</option></select></div>';
  h+='</div>';
  h+='<button class="btn bp" id="imgGenBtn" onclick="imgGenerate()">🎨 Generate Image</button>';
  h+='<div id="imgResult" style="margin-top:10px;display:flex;flex-wrap:wrap;gap:8px"></div></div>';
  document.getElementById("cmsContent").innerHTML=h;
}

// ── Tab 4: Multimedia ──
var mvTab=0;
function cmsTabMedia(){
  var h='<div style="margin-bottom:10px;display:flex;gap:4px">';
  h+='<button class="btn '+(mvTab===0?'bp':'bo')+'" onclick="mvSwitchTab(0)">🎙️ Audio Source Management</button>';
  h+='<button class="btn '+(mvTab===1?'bp':'bo')+'" onclick="mvSwitchTab(1)">🎬 Video Creation</button>';
  h+='<button class="btn '+(mvTab===2?'bp':'bo')+'" onclick="mvSwitchTab(2)">📋 Publish Management</button>';
  h+='</div><div id="mvContent"></div>';
  document.getElementById("cmsContent").innerHTML=h;
  mvSwitchTab(mvTab);
}

var cmsPosts=[];
var cmsQuill=null;
var cmsStatusFilter='all';
var cmsCategories=[];

function cmsInitQuill(content){
  if(cmsQuill){cmsQuill.root.innerHTML=content||'';return}
  cmsQuill=new Quill("#cmsPBody",{theme:"snow",placeholder:"Edit Body Here...",modules:{toolbar:[["bold","italic","underline","strike"],[{header:1},{header:2}],[{list:"ordered"},{list:"bullet"}],["link","image","code-block"],["clean"]]}});
  if(content)cmsQuill.root.innerHTML=content;
}

// ── Categories ──

function cmsLoadCategories(callback){
  fetch("/admin/cms/categories",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success&&d.data){
      cmsCategories=d.data;
      cmsPopulateCategorySelect();
      cmsPopulateChannelList();
    }
    if(callback)callback();
  }).catch(function(){if(callback)callback()});
}

function cmsPopulateCategorySelect(){
  var sel=document.getElementById("cmsPCat");
  if(!sel)return;
  sel.innerHTML='';
  cmsCategories.forEach(function(c){
    var o=document.createElement("option");
    o.value=c.name;
    o.textContent=c.icon+' '+c.name;
    sel.appendChild(o);
  });
}

function cmsPopulateChannelList(){
  var localDiv=document.getElementById("cmsChLocalList");
  if(!localDiv)return;
  var h='';
  cmsCategories.forEach(function(c){
    h+='<label style="font-size:12px;display:inline-flex;align-items:center;gap:4px;margin:2px 6px 2px 0;cursor:pointer">';
    h+='<input type="checkbox" class="cmsChLocal" value="local:'+c.name+'" checked>';
    h+=c.icon+' '+c.name+'</label>';
  });
  localDiv.innerHTML=h;
}

function cmsLoadSocialPlatforms(){
  var socialDiv=document.getElementById("cmsChSocialList");
  if(!socialDiv)return;
  fetch("/admin/social/check-config",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var h='';
    d.data.platforms.forEach(function(p){
      var disabled=p.configured?'':'disabled';
      var opacity=p.configured?1:0.4;
      h+='<label style="font-size:12px;display:inline-flex;align-items:center;gap:4px;margin:2px 6px 2px 0;cursor:pointer;opacity:'+opacity+'">';
      h+='<input type="checkbox" class="cmsChSocial" value="'+p.id+'" '+disabled+'>';
      h+=p.icon+' '+p.name;
      if(!p.configured)h+=' <span style="font-size:9px;color:var(--dim)">(Not Configured)</span>';
      h+='</label>';
    });
    socialDiv.innerHTML=h;
  }).catch(function(){});
}

// ── Filter ──

function cmsFilterPosts(status){
  cmsStatusFilter=status;
  document.querySelectorAll('[id^="cmsF-"]').forEach(function(e){e.className="btn bo"});
  var el=document.getElementById("cmsF-"+status);
  if(el)el.className="btn bp";
  cmsLoadPosts();
}

function cmsLoadPosts(){
  var url="/admin/cms/posts?limit=50";
  if(cmsStatusFilter&&cmsStatusFilter!=='all')url+="&status="+cmsStatusFilter;
  fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){document.getElementById("cmsPostBody").innerHTML='<tr><td colspan="9"><div class="em">None</div></td></tr>';return}
    cmsPosts=d.data||[];
    var h='';
    if(!cmsPosts.length){h='<tr><td colspan="9"><div class="em">No Articles Yet</div></td></tr>'}
    else{cmsPosts.forEach(function(p){
      var st=p.is_published?'<span class="bdg on">Published</span>':'<span class="bdg pd">Draft</span>';
      // Build channel display
      var chText='—';
      if(p.publish_channels&&p.publish_channels.length){
        chText=p.publish_channels.map(function(ch){
          if(ch.startsWith('local:'))return ch.replace('local:','');
          var map={wechat:'💬WeChat',weibo:'📢Weibo',toutiao:'📰Headline'};
          return map[ch]||ch;
        }).join(' · ');
      }
      h+='<tr><td style="font-size:10px">'+p.id+'</td>';
      h+='<td style="font-weight:600;cursor:pointer;color:var(--accent)" onclick="cmsEditPost('+p.id+')">'+esc(p.title||'-')+'</td>';
      h+='<td>'+esc(p.category||'')+'</td><td>'+esc(p.author||'-')+'</td><td>'+st+'</td>';
      h+='<td style="font-size:10px">'+chText+'</td>';
      h+='<td style="font-size:10px;color:var(--dim)">'+(p.views||0)+'</td>';
      h+='<td style="font-size:10px">'+(p.created_at||'').slice(0,10)+'</td>';
      h+='<td><button class="btn bo bs" onclick="cmsEditPost('+p.id+')">Edit</button> ';
      if(p.slug)h+='<button class="btn bo bs" onclick="window.open(\'//easykai.cn/preview/'+p.slug+'\',\'_blank\')">👁 Preview</button> ';
      h+='<button class="btn bo bs" onclick="cmsDelPost('+p.id+')">Delete</button></td></tr>';
    })}
    document.getElementById("cmsPostBody").innerHTML=h;
  }).catch(function(){document.getElementById("cmsPostBody").innerHTML='<tr><td colspan="9"><div class="em">Request Failed</div></td></tr>'});
}

// ── New / Edit / Close ──

function cmsNewPost(){
  document.getElementById("cmsFormTitle").textContent="New Article";
  document.getElementById("cmsPEid").value="";
  document.getElementById("cmsPTitle").value="";
  document.getElementById("cmsPAuthor").value="";
  document.getElementById("cmsPSummary").value="";
  if(cmsCategories.length)document.getElementById("cmsPCat").value=cmsCategories[0].name;
  document.getElementById("cmsPostForm").style.display="block";
  document.getElementById("cmsPTitle")._previewSlug='';
  var pbtn=document.getElementById("cmsPreviewBtn");
  if(pbtn){pbtn.style.display="none"}
  // Reset channels: all local checked, social unchecked
  document.querySelectorAll(".cmsChLocal").forEach(function(cb){cb.checked=true});
  document.querySelectorAll(".cmsChSocial").forEach(function(cb){cb.checked=false});
  setTimeout(function(){cmsInitQuill("")},100);
}

function cmsEditPost(id){
  var p=null;
  for(var i=0;i<cmsPosts.length;i++){if(cmsPosts[i].id===id){p=cmsPosts[i];break}}
  if(!p){showToast("Not found","error");return}
  document.getElementById("cmsFormTitle").textContent="Edit Article #"+p.id;
  document.getElementById("cmsPEid").value=p.id;
  document.getElementById("cmsPTitle").value=p.title||"";
  document.getElementById("cmsPAuthor").value=p.author||"";
  document.getElementById("cmsPCat").value=p.category||(cmsCategories.length?cmsCategories[0].name:"");
  document.getElementById("cmsPSummary").value=p.excerpt||"";
  document.getElementById("cmsPostForm").style.display="block";
  document.getElementById("cmsPTitle")._previewSlug=p.slug||'';
  var pbtn=document.getElementById("cmsPreviewBtn");
  if(pbtn){pbtn.style.display=p.slug?"inline-flex":"none"}
  // Restore channel selections
  var saved=p.publish_channels||[];
  setTimeout(function(){
    document.querySelectorAll(".cmsChLocal").forEach(function(cb){
      cb.checked=saved.indexOf(cb.value)>=0;
    });
    document.querySelectorAll(".cmsChSocial").forEach(function(cb){
      cb.checked=saved.indexOf(cb.value)>=0;
    });
    cmsInitQuill(p.content||"")
  },100);
}

function cmsCloseForm(){
  document.getElementById("cmsPostForm").style.display="none";
}

function cmsPreviewPost(){
  var slug=document.getElementById("cmsPTitle")._previewSlug||'';
  if(!slug){
    showToast("Save draft first before preview","");
    cmsSaveDraftWithPreview();
    return;
  }
  window.open('//easykai.cn/preview/'+slug,'_blank');
}

function cmsSaveDraftWithPreview(){
  var data=cmsGetFormData();
  if(!data.title||!data.content||data.content==="<p><br></p>"){showToast("Title and body are required","error");return}
  data.is_published=0;
  data.publish_channels=[];
  var eid=document.getElementById("cmsPEid").value;
  if(eid)data.id=parseInt(eid);
  showToast("Saving...","");
  var url=eid?"/admin/cms/posts/"+eid:"/admin/cms/posts";
  var method=eid?"PUT":"POST";
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var slug=d.data&&d.data.slug;
      if(slug){document.getElementById("cmsPTitle")._previewSlug=slug;window.open('//easykai.cn/preview/'+slug,'_blank')}
      else showToast("Saved but slug not generated","success");
    }
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

// ── Save Draft & Publish ──

function cmsGetFormData(){
  var body=cmsQuill?cmsQuill.root.innerHTML:"";
  return {
    title: document.getElementById("cmsPTitle").value.trim(),
    author: document.getElementById("cmsPAuthor").value.trim(),
    content: body,
    excerpt: document.getElementById("cmsPSummary").value.trim(),
    category: document.getElementById("cmsPCat").value,
    slug: ""  // Auto-generated by Backend
  };
}

function cmsGetSelectedChannels(){
  var channels=[];
  document.querySelectorAll(".cmsChLocal:checked").forEach(function(cb){channels.push(cb.value)});
  document.querySelectorAll(".cmsChSocial:checked").forEach(function(cb){channels.push(cb.value)});
  return channels;
}

function cmsSaveDraft(){
  var data=cmsGetFormData();
  if(!data.title||!data.content||data.content==="<p><br></p>"){showToast("Title and body are required","error");return}
  data.is_published=0;
  data.publish_channels=[];
  var eid=document.getElementById("cmsPEid").value;
  if(eid)data.id=parseInt(eid);
  showToast("Saving...","");
  var url=eid?"/admin/cms/posts/"+eid:"/admin/cms/posts";
  var method=eid?"PUT":"POST";
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var slug=d.data&&d.data.slug;
      if(slug){document.getElementById("cmsPTitle")._previewSlug=slug}
      var pbtn=document.getElementById("cmsPreviewBtn");
      if(pbtn&&slug){pbtn.style.display="inline-flex"}
      showToast("Draft saved","success");cmsCloseForm();cmsLoadPosts()
    }
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cmsPublishPost(){
  var data=cmsGetFormData();
  if(!data.title||!data.content||data.content==="<p><br></p>"){showToast("Title and body are required","error");return}
  var channels=cmsGetSelectedChannels();
  if(!channels.length){showToast("Select at least one channel","error");return}
  data.is_published=1;
  data.publish_channels=channels;
  var eid=document.getElementById("cmsPEid").value;
  if(eid)data.id=parseInt(eid);
  showToast("Publishing...","");
  // Step 1: save post
  var url=eid?"/admin/cms/posts/"+eid:"/admin/cms/posts";
  var method=eid?"PUT":"POST";
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){showToast(d.error||"Save failed","error");return}
    var savedId=eid||d.data.id;
    // Check if any social platforms are selected
    var socialChannels=channels.filter(function(ch){return ch!=='local'&&!ch.startsWith('local:')});
    if(!socialChannels.length){
      showToast("Published to local category","success");
      cmsCloseForm();
      cmsLoadPosts();
      return;
    }
    // Step 2: publish to social
    fetch("/admin/cms/posts/"+savedId+"/publish",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({channels:socialChannels,auto_publish:true})}).then(function(r2){return r2.json()}).then(function(d2){
      if(d2.success){
        var msgs=(d2.data.results.social||[]).map(function(r){return r.platform+": "+(r.message||r.status)});
        showToast("Published: "+msgs.join(" | "),"success");
      }else{showToast(d2.error||"Social Media Publish Failed","error")}
      cmsCloseForm();
      cmsLoadPosts();
    }).catch(function(){showToast("Social media publish request failed","error");cmsCloseForm();cmsLoadPosts()});
  }).catch(function(){showToast("Save failed","error")});
}

function cmsGenerateStatic(){
  var eid=document.getElementById("cmsPEid").value;
  var title=document.getElementById("cmsPTitle").value||"";
  var data={action:"post"};
  if(eid){
    // Find slug from cached posts
    for(var i=0;i<cmsPosts.length;i++){
      if(cmsPosts[i].id===parseInt(eid)){data.slug=cmsPosts[i].slug;break}
    }
  }
  if(!data.slug){showToast("Save article first before generating static page","error");return}
  showToast("Generating...","");
  fetch("/admin/content-factory/generate-static",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(data)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      showToast("Static Page Generated: "+d.ok+" Success", "success");
    }else{
      showToast(d.error||"Generation Failed","error");
    }
  }).catch(function(){showToast("Request Failed","error")});
}

function cmsGenerateAllStatic(){
  if(!confirm("Generate static pages for all public articles? May take a few seconds."))return;
  showToast("Generating entire site...","");
  fetch("/admin/content-factory/generate-static",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({action:"all"})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      showToast("Static Pages Generated: "+d.ok+" Success, "+d.fail+" Failed", d.fail?"error":"success");
    }else{
      showToast(d.error||"Generation Failed","error");
    }
  }).catch(function(){showToast("Request Failed","error")});
}

function cmsDelPost(id){
  if(!confirm("Confirm Delete Article #"+id+"？"))return;
  fetch("/admin/cms/posts/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Deleted","success");cmsLoadPosts()}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cmsAiformat(){
  var body=cmsQuill?cmsQuill.root.innerHTML:"";
  var title=document.getElementById("cmsPTitle").value.trim();
  if(!body||body==="<p><br></p>"){showToast("Body cannot be empty","error");return}
  showToast("AI Formatting (~10s)...","");
  fetch("/admin/content-factory/ai-format",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({content:body,title:title})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){cmsQuill.root.innerHTML=d.formatted;showToast("Layout complete","success")}
    else{showToast(d.error||"Layout Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cmsAicover(){
  var title=document.getElementById("cmsPTitle").value.trim()||"Article Image";
  var p=prompt("Image Description（Auto Generate if Empty）:",title+" Fintech Dark Sci-Fi");
  if(p===null)return;
  showToast("AI Generating Image (~30s)...","");
  fetch("/admin/content-factory/ai-cover",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({title:title,prompt:p||""})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var img='<p><img src="'+d.image_url+'" alt="Add Image" style="max-width:100%;border-radius:8px"></p>';
      cmsQuill.clipboard.dangerouslyPasteHTML(cmsQuill.getLength(),img);
      showToast("Image inserted","success")
    }else{showToast(d.error||"Image Attach Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

// ── Publish History ──

var cmsHistoryVisible=false;
function cmsToggleSocialHistory(){
  cmsHistoryVisible=!cmsHistoryVisible;
  var wrap=document.getElementById("cmsSocialHistoryWrap");
  if(!cmsHistoryVisible){wrap.style.display="none";return}
  wrap.style.display="block";
  wrap.innerHTML='<div class="cd"><div class="s"></div>Loading......</div>';
  fetch("/admin/social/history?limit=50",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){wrap.innerHTML='<div class="cd"><div class="em">No Publication Records</div></div>';return}
    var items=d.data.items||[];
    if(!items.length){wrap.innerHTML='<div class="cd"><div class="em">No Publication Records</div></div>';return}
    var h='<div class="cd"><div class="st">Publish History（Social Media）</div><table><tr><th>Platform</th><th>Title</th><th>Type</th><th>Status</th><th>Time</th></tr>';
    items.forEach(function(r){
      var stHtml={published:'<span class="bdg on">Published</span>',draft:'<span class="bdg pd">Draft</span>',publishing:'<span class="bdg pd">Publishing</span>',failed:'<span class="bdg off">Failed</span>'}[r.status]||'<span class="bdg pd">'+r.status+'</span>';
      h+='<tr><td>'+r.platform+'</td><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;font-weight:600">'+esc(r.title||"-")+'</td><td style="font-size:10px">'+r.content_type+'</td><td>'+stHtml+'</td><td style="font-size:10px">'+(r.created_at||"").slice(0,16)+'</td></tr>';
    });
    h+='</table></div>';
    wrap.innerHTML=h;
  }).catch(function(){wrap.innerHTML='<div class="cd"><div class="em">Request Failed</div></div>'});
}

// ── Category Management Modal ──

function cmsManageCategories(){
  var h='<div class="modal-overlay" onclick="if(event.target===this)cmsCloseModal()">';
  h+='<div class="modal-box" style="width:500px">';
  h+='<h3>Column Management <span style="font-size:11px;font-weight:400;color:var(--dim)">CMS Local Publish Column</span></h3>';
  h+='<div style="margin-bottom:10px;display:flex;gap:6px">';
  h+='<input class="in" id="catInput" placeholder="Column Name" style="flex:1">';
  h+='<input class="in" id="catIcon" placeholder="Icon(emoji)" style="width:50px" value="📄">';
  h+='<button class="btn bp" onclick="cmsAddCategory()">+ Add</button></div>';
  h+='<div id="catList"><div class="lo"><div class="s"></div></div></div>';
  h+='<div style="margin-top:10px"><button class="btn bo" onclick="cmsCloseModal()">Close</button></div>';
  h+='</div></div>';
  var m=document.createElement("div");
  m.id="cmsCatModal";
  m.innerHTML=h;
  document.body.appendChild(m);
  cmsReloadCategoryList();
}

function cmsReloadCategoryList(){
  var el=document.getElementById("catList");
  if(!el)return;
  fetch("/admin/cms/categories",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){el.innerHTML='<div class="em">Load failed</div>';return}
    var cats=d.data;
    if(!cats.length){el.innerHTML='<div class="em">No Columns，Add</div>';return}
    var h='&lt;table&gt;&lt;tr&gt;&lt;th&gt;Order&lt;/th&gt;&lt;th&gt;Icon&lt;/th&gt;&lt;th&gt;Name&lt;/th&gt;&lt;th&gt;Status&lt;/th&gt;&lt;th&gt;Action&lt;/th&gt;&lt;/tr&gt;';
    cats.forEach(function(c,i){
      var st=c.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Deactivate</span>';
      h+='<tr>';
      h+='<td style="font-size:10px">'+(i+1)+'</td>';
      h+='<td style="font-size:16px">'+esc(c.icon||'📄')+'</td>';
      h+='<td>'+esc(c.name)+'</td>';
      h+='<td>'+st+'</td>';
      h+='<td>';
      h+='<button class="btn bo bs" onclick="cmsEditCategory('+c.id+','+c.is_active+')">'+(c.is_active?'Deactivate':'Enabled')+'</button> ';
      h+='<button class="btn bo bs" onclick="cmsDelCategory('+c.id+',\''+esc(c.name)+'\')">Delete</button>';
      h+='</td></tr>';
    });
    h+='</table>';
    el.innerHTML=h;
  }).catch(function(){var el=document.getElementById("catList");if(el)el.innerHTML='<div class="em">Request Failed</div>'});
}

function cmsAddCategory(){
  var name=document.getElementById("catInput").value.trim();
  if(!name){showToast("Enter category name","error");return}
  var icon=document.getElementById("catIcon").value.trim()||"📄";
  fetch("/admin/cms/categories",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({name:name,icon:icon})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Added","success");document.getElementById("catInput").value="";cmsReloadCategoryList()}
    else{showToast(d.error||"Add Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cmsEditCategory(id,wasActive){
  fetch("/admin/cms/categories/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({is_active:wasActive?0:1})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Updated","success");cmsReloadCategoryList()}
    else{showToast(d.error||"Update Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cmsDelCategory(id,name){
  if(!confirm("Confirm Delete Column「"+name+"」？"))return;
  fetch("/admin/cms/categories/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Deleted","success");cmsReloadCategoryList()}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cmsCloseModal(){
  var m=document.getElementById("cmsCatModal");
  if(m)m.remove();
}

// ============================
// Social Push
// ============================

window.l_social=function(){
  go("cms");return;
  var h='';
  h+='<div style="margin-bottom:12px;display:flex;gap:4px;flex-wrap:wrap">';
  h+='<button class="btn bp" onclick="socialTab(0)" id="soc-t0">Article Edit</button>';
  h+='<button class="btn bo" onclick="socialTab(1)" id="soc-t1">🎨 Add Image</button>';
  h+='<button class="btn bo" onclick="socialTab(2)" id="soc-t2">📤 Publish</button>';
  h+='<span style="flex:1"></span>';
  h+='<span id="socConfigStatus" style="font-size:10px;color:var(--dim);align-self:center"></span>';
  h+='</div><div id="socContent"></div>';
  document.getElementById("mc").innerHTML=h;
  // Show config status
  fetch("/admin/social/check-config",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var st=[];
    d.data.platforms.forEach(function(p){
      if(p.configured)st.push(p.icon+" "+p.name+"✅");
      else st.push(p.icon+" "+p.name+"❌");
    });
    document.getElementById("socConfigStatus").textContent=st.join(" | ");
  }).catch(function(){});
  socialTab(0);
};

var socArticle={title:"",summary:"",body_html:""};
var socCoverUrl="";

function socialTab(n){
  document.querySelectorAll('[id^="soc-t"]').forEach(function(e){e.className="btn bo"});
  var el=document.getElementById("soc-t"+n);
  if(el)el.className="btn bp";
  if(n===0)socialEditor();
  else if(n===1)socialImageGen();
  else if(n===2)socialPublish();
}

// ── Tab 0: Article Edit ──
function socialEditor(){
  var h='<div class="cd"><div class="st">Edit Content</div>';
  h+='<div class="fl"><div style="font-size:11px;color:var(--dim);width:60px">Platform</div>';
  h+='<select class="sl" id="socPlatform" style="flex:1" onchange="socialUpdateContentTypes()"><option value="wechat">WeChat OA Articles</option><option value="weibo">Weibo</option></select></div>';
  h+='<div class="fl"><div style="font-size:11px;color:var(--dim);width:60px">Type</div>';
  h+='<select class="sl" id="socType" style="flex:1"><option value="article">Article</option><option value="announcement">Notification</option><option value="promotion">Promote</option></select></div>';
  h+='<div class="fl"><div style="font-size:11px;color:var(--dim);width:60px">Theme</div><input class="in" id="socTopic" placeholder="Enter Topic，如：AI Transform Finance" style="flex:1"></div>';
  h+='<div style="margin-top:8px;display:flex;gap:8px">';
  h+='<button class="btn bp" onclick="socialGen()">🤖 AI Generate</button>';
  h+='<button class="btn bo" onclick="socialClearEditor()">Clear</button></div></div>';
  h+='<button class="btn bo" onclick="socialImportFromCMS()">📥 从CMSImport</button>';

  h+='<div class="cd" style="margin-top:12px"><div class="st">Content</div>';
  h+='<div class="fl"><div style="font-size:11px;color:var(--dim);width:60px">Title</div><input class="in" id="socTitle" placeholder="Title" style="flex:1" value="'+esc(socArticle.title)+'"></div>';
  h+='<div class="fl" id="socSummaryRow"><div style="font-size:11px;color:var(--dim);width:60px">Summary</div><input class="in" id="socSummary" placeholder="Summary（Optional）" style="flex:1" value="'+esc(socArticle.summary)+'"></div>';
  h+='<div style="font-size:11px;color:var(--dim);margin:8px 0 4px">Body</div>';
  h+='<textarea class="ta" id="socBody" style="min-height:200px;width:100%" placeholder="Body Content...">'+esc(socArticle.body_html)+'</textarea>';
  h+='<div style="margin-top:6px;display:flex;gap:6px"><button class="btn bo bs" onclick="socAiformat()">🤖 AILayout</button><button class="btn bo bs" onclick="socAicover()">🎨 AIAdd Image</button></div>';
  h+='<div id="socCmsImportList" style="margin-top:8px;display:none"></div>';
  h+='</div>';

  document.getElementById("socContent").innerHTML=h;
}



function socialImportFromCMS(){
  var el=document.getElementById("socCmsImportList");
  if(!el){showToast("Use this feature in the editor first","error");return}
  if(el.style.display!="none"&&el.innerHTML){el.style.display="none";return}
  el.style.display="block";
  el.innerHTML='<div class="lo"><div class="s"></div>LoadingCMSArticle...</div>';
  fetch("/admin/social/import-from-cms",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){el.innerHTML='<div class="em">Load failed</div>';return}
    var posts=d.data;
    if(!posts.length){el.innerHTML='<div class="em">No PublishedCMSArticle</div>';return}
    var h='<div class="st" style="font-size:12px">SelectCMSArticle Import</div><table><tr><th>Title</th><th>Categories</th><th>Time</th><th>Actions</th></tr>';
    posts.forEach(function(p){
      h+='<tr><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;font-weight:600">'+esc(p.title)+'</td>';
      h+='<td>'+esc(p.category)+'</td>';
      h+='<td style="font-size:10px;color:var(--dim)">'+(p.published_at||p.created_at||'').slice(0,10)+'</td>';
      h+='<td><button class="btn bo bs" onclick="socialImportCMSArticle('+p.id+')">Import</button></td></tr>';
    });
    h+='</table><div style="margin-top:8px"><button class="btn bo bs" onclick="document.getElementById(&#39;socCmsImportList&#39;).style.display=&#39;none&#39;">Close</button></div>';
    el.innerHTML=h;
  }).catch(function(){el.innerHTML='<div class="em">Request Failed</div>'});
}

function socialImportCMSArticle(id){
  fetch("/admin/social/import-from-cms",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){showToast("Load failed","error");return}
    var post=null;
    for(var i=0;i<d.data.length;i++){if(d.data[i].id===id){post=d.data[i];break}}
    if(!post){showToast("Article not found","error");return}
    socArticle.title=post.title||"";
    socArticle.summary=post.excerpt||"";
    socArticle.body_html=post.content||"";
    socCoverUrl=post.cover_image||"";
    socialEditor();
    showToast("Imported: "+post.title,"success");
    var el=document.getElementById("socCmsImportList");
    if(el)el.style.display="none";
  }).catch(function(){showToast("Request Failed","error")});
}

function socAiformat(){
  var body=document.getElementById("socBody").value;
  var title=document.getElementById("socTitle").value.trim();
  if(!body){showToast("Body cannot be empty","error");return}
  showToast("AI Formatting (~10s)...","");
  fetch("/admin/content-factory/ai-format",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({content:body,title:title})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){document.getElementById("socBody").value=d.formatted;showToast("Layout complete","success")}
    else{showToast(d.error||"Layout Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function socAicover(){
  var title=document.getElementById("socTitle").value.trim()||"Article Image";
  var p=prompt("Image Description（Auto Generate if Empty）:",title+" Fintech Dark Sci-Fi");
  if(p===null)return;
  showToast("AI Generating Image (~30s)...","");
  fetch("/admin/content-factory/ai-cover",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({title:title,prompt:p||""})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var img='<img src="'+d.image_url+'" style="max-width:100%;border-radius:8px">';
      document.getElementById("socBody").value+="\n\n[Add Image] "+d.image_url;
      showToast("Image generated, URL inserted at bottom","success")
    }else{showToast(d.error||"Image Attach Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function socialUpdateContentTypes(){
  var platform=document.getElementById("socPlatform").value;
  var typeSel=document.getElementById("socType");
  var summaryRow=document.getElementById("socSummaryRow");
  if(platform==="weibo"){
    typeSel.innerHTML='<option value="weibo">Weibo</option>';
    if(summaryRow)summaryRow.style.display="none";
  }else{
    typeSel.innerHTML='<option value="article">Article</option><option value="announcement">Notification</option><option value="promotion">Promote</option>';
    if(summaryRow)summaryRow.style.display="flex";
  }
}

function socialClearEditor(){
  document.getElementById("socTitle").value="";
  document.getElementById("socSummary").value="";
  document.getElementById("socBody").value="";
}

function socialGen(){
  var topic=document.getElementById("socTopic").value.trim();
  var type=document.getElementById("socType").value;
  if(!topic){showToast("Enter a topic","error");return}
  document.getElementById("socContent").innerHTML='<div class="lo"><div class="s"></div>AI Generating...</div>';
  fetch("/admin/social/generate",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({topic:topic,content_type:type})})
    .then(function(r){return r.json()}).then(function(d){
      if(!d.success){document.getElementById("socContent").innerHTML='<div class="em">'+esc(d.error||"Generation Failed")+'</div>';return}
      var a=d.data;
      socArticle={title:a.title||"",summary:a.summary||"",body_html:a.body_html||""};
      socialEditor();
      showToast("Generation complete","success");
    }).catch(function(){document.getElementById("socContent").innerHTML='<div class="em">Request Failed</div>'});
}

// ── Tab 1: Add Image ──
function socialImageGen(){
  var h='<div class="cd"><div class="st">AI Image Generation（Tongyi Wanxiang）</div>';
  h+='<div class="fl"><div style="font-size:11px;color:var(--dim);width:60px">Description</div><input class="in" id="socImgPrompt" placeholder="Describe Image Effect，如：Ink Landscape" style="flex:1"></div>';
  h+='<div style="margin:8px 0;display:flex;gap:12px">';
  h+='<label style="font-size:11px;display:flex;align-items:center;gap:4px"><input type="checkbox" id="socIsCover" checked> As Cover Image</label></div>';
  h+='<button class="btn bp" onclick="socialGenImage()">🎨 Generate Picture</button>';
  h+='</div>';
  h+='<div id="socImgResult" style="margin-top:12px"></div>';
  if(socCoverUrl){
    h+='<div class="cd"><div class="st">Current Cover</div><img src="'+esc(socCoverUrl)+'" style="max-width:100%;max-height:300px;border-radius:8px">';
    h+='<div style="margin-top:8px"><button class="btn bo" onclick="socCoverUrl=\'\';showToast(\'Cleared\',\'success\')">Clear Cover</button></div></div>';
  }
  document.getElementById("socContent").innerHTML=h;
}

function socialGenImage(){
  var prompt=document.getElementById("socImgPrompt").value.trim();
  var isCover=document.getElementById("socIsCover").checked;
  var title=socArticle.title;
  if(!prompt&&!title){showToast("Enter image description","error");return}
  document.getElementById("socImgResult").innerHTML='<div class="lo"><div class="s"></div>Tongyi Wanxiang Generating...</div>';
  fetch("/admin/social/generate-image",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({prompt:prompt,title:title,cover:isCover})})
    .then(function(r){return r.json()}).then(function(d){
      if(!d.success){document.getElementById("socImgResult").innerHTML='<div class="em">'+esc(d.error||"Generation Failed")+'</div>';return}
      var url=d.data.image_url;
      socCoverUrl=url;
      var h='<div class="cd"><div class="st">Generation Result</div>';
      h+='<img src="'+esc(url)+'" style="max-width:100%;max-height:350px;border-radius:8px">';
      h+='<div style="margin-top:8px;display:flex;gap:8px">';
      h+='<button class="btn bp" onclick="socCoverUrl=\''+esc(url)+'\';showToast(\'Set as Cover\',\'success\')">Set as Cover</button>';
      h+='<button class="btn bo" onclick="window.open(\''+esc(url)+'\',\'_blank\')">View Original</button></div></div>';
      document.getElementById("socImgResult").innerHTML=h;
      showToast("Image generated","success");
    }).catch(function(){document.getElementById("socImgResult").innerHTML='<div class="em">Request Failed</div>'});
}

// ── Tab 2: Publish ──
function socialPublish(){
  fetch("/admin/social/check-config",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(cfg){
    var platforms=cfg.success?cfg.data.platforms:[];
    var h='';

    // Platform selection
    h+='<div class="cd"><div class="st">Push To</div>';
    h+='<div style="display:flex;gap:12px;flex-wrap:wrap">';
    platforms.forEach(function(p){
      var checked=p.configured?"checked":"";
      var disabled=p.configured?"":"disabled";
      h+='<label style="font-size:12px;display:flex;align-items:center;gap:4px;opacity:'+(p.configured?1:0.4)+'">';
      h+='<input type="checkbox" class="socPlatformCheck" value="'+p.id+'" '+checked+' '+disabled+'>';
      h+=p.icon+' '+p.name;
      if(!p.configured)h+=' <span style="font-size:9px;color:var(--dim)">(Not Configured)</span>';
      h+='</label>';
    });
    h+='</div></div>';

    // Any platform configured?
    var hasAny=platforms.some(function(p){return p.configured});
    if(!hasAny){
      h+='<div class="cd"><div class="st">⚠️ No Configured Platform</div>';
      h+='<p style="font-size:12px;color:var(--dim)">First「System Settings」Configure WeChat OA、Weibo or Tongyi Wanxiang API Key</p>';
      h+='<button class="btn bp" onclick="go(\'config\')">Go to Config</button></div>';
      document.getElementById("socContent").innerHTML=h;
      return;
    }

    // Preview
    h+='<div class="cd"><div class="st">Preview</div>';
    h+='<div style="font-size:13px;font-weight:600;margin-bottom:8px">'+esc(socArticle.title||"（No Title）")+'</div>';
    h+='<div style="font-size:11px;color:var(--dim);margin-bottom:8px">'+esc(socArticle.summary||"")+'</div>';
    if(socCoverUrl){
      h+='<img src="'+esc(socCoverUrl)+'" style="max-width:100%;max-height:200px;border-radius:8px;margin-bottom:8px">';
    }
    h+='<div style="font-size:12px;max-height:250px;overflow-y:auto;border:1px solid var(--border);padding:12px;border-radius:8px;background:var(--bg2)">'+(socArticle.body_html||"（No Body）")+'</div>';
    h+='</div>';

    // Publish
    h+='<div class="cd" style="margin-top:12px"><div class="st">Publish</div>';
    h+='<label style="font-size:12px;display:flex;align-items:center;gap:6px;margin-bottom:8px"><input type="checkbox" id="socAutoPub"> Direct WeChat Publish（Unchecked=Draft Only；Always Direct Publish to Weibo）</label>';
    h+='<button class="btn bp" onclick="socialDoPublish()">📤 Send to Selected Platform</button>';
    h+='</div>';

    // History
    h+='<div class="cd" style="margin-top:12px"><div class="st">Push History</div><div id="socHistory"><div class="lo"><div class="s"></div></div></div></div>';

    document.getElementById("socContent").innerHTML=h;
    loadSocialHistory();
  }).catch(function(){document.getElementById("socContent").innerHTML='<div class="em">Check Configuration Failed</div>'});
}

function socialDoPublish(){
  var te=document.getElementById("socTitle");
  var se=document.getElementById("socSummary");
  var be=document.getElementById("socBody");
  if(te&&te.value) socArticle.title=te.value;
  if(se&&se.value) socArticle.summary=se.value;
  if(be&&be.value) socArticle.body_html=be.value;

  if(!socArticle.title||!socArticle.body_html){showToast("Title and body are required","error");return}

  // Get selected platforms
  var platforms=[];
  document.querySelectorAll(".socPlatformCheck:checked").forEach(function(cb){platforms.push(cb.value)});
  if(!platforms.length){showToast("Select at least one platform","error");return}

  var autoPub=document.getElementById("socAutoPub")&&document.getElementById("socAutoPub").checked;

  fetch("/admin/social/publish",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({
    title:socArticle.title,
    body:socArticle.body_html,
    body_html:socArticle.body_html,
    summary:socArticle.summary,
    author:"admin",
    cover_image_url:socCoverUrl||"",
    platforms:platforms,
    auto_publish:autoPub,
  })}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var msgs=d.data.results.map(function(r){return r.platform+": "+(r.message||r.error||r.status)});
      showToast(msgs.join(" | "),d.data.results.some(function(r){return r.status=="failed"})?"error":"success");
      loadSocialHistory();
    }else{
      showToast(d.error||"Failed to send","error");
    }
  }).catch(function(){showToast("Request Failed","error")});
}

function loadSocialHistory(){
  var el=document.getElementById("socHistory");
  if(!el)return;
  fetch("/admin/social/history?limit=20",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){el.innerHTML='<div class="em">Load failed</div>';return}
    var items=d.data.items;
    if(!items||!items.length){el.innerHTML='<div class="em">No Push Records</div>';return}
    var h='&lt;table&gt;&lt;tr&gt;&lt;th&gt;Platform&lt;/th&gt;&lt;th&gt;Title&lt;/th&gt;&lt;th&gt;Status&lt;/th&gt;&lt;th&gt;ID&lt;/th&gt;&lt;th&gt;Time&lt;/th&gt;&lt;th&gt;Action&lt;/th&gt;&lt;/tr&gt;';
    var statusMap={draft:"Draft",publishing:"Publishing",published:"Published",failed:"Failed"};
    var platformIcon={wechat:"💬",weibo:"📢",toutiao:"📰"};
    items.forEach(function(r){
      var st=statusMap[r.status]||r.status;
      var stCls=r.status==="published"?"on":(r.status==="failed"?"off":"pd");
      var icon=platformIcon[r.platform]||"📤";
      h+='<tr><td>'+icon+'</td>';
      h+='<td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">'+esc(r.title)+'</td>';
      h+='<td><span class="bdg '+stCls+'">'+st+'</span></td>';
      h+='<td style="font-size:10px;font-family:monospace">'+(r.publish_id||r.media_id?"#"+esc(r.publish_id||r.media_id):"-")+'</td>';
      h+='<td style="font-size:11px;color:var(--dim)">'+(r.created_at||"")+'</td>';
      h+='<td><button class="btn bo bs" onclick="socialDeleteHistory('+r.id+')">Delete</button></td></tr>';
    });
    h+='</table><div style="font-size:10px;color:var(--dim);margin-top:8px">Total: '+d.data.total+' entries</div>';
    el.innerHTML=h;
  }).catch(function(){el.innerHTML='<div class="em">Load failed</div>'});
}

function socialDeleteHistory(id){
  if(!confirm("Delete?"))return;
  fetch("/admin/social/history/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){loadSocialHistory();showToast("Deleted","success")}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}


// ============================
// 🏭 Content Factory
// ============================
var cfTab=0, cfSources=[], cfRawContents=[], cfProcessed=[];

// ── Multimedia Generation ──

// ── PPT Generate ──
window.l_ppt_gen=function(){
  document.getElementById("pt").textContent="PPT Generation";
  var h='<div class="cd" style="margin-bottom:12px"><div class="st">📊 AI Presentation Generation</div>';
  h+='<div style="font-size:12px;color:var(--muted);margin-bottom:12px">Enter Topic，AI Auto-generate Structured Presentation（.pptx），Dark Tech Style，16:9 Widescreen。</div>';
  h+='<div class="g2">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Demo Theme *</div><input class="in" id="pptTopic" placeholder="如：AI in Financial Risk Control" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Pages</div><select class="sl" id="pptSlides" style="width:100%">';
  [5,8,10,12,15,20].forEach(function(n){h+='<option value="'+n+'"'+(n==8?' selected':'')+'>'+n+' pages</option>'});
  h+='</select></div>';
  h+='</div>';
  h+='<div style="margin-top:12px"><button class="btn bp" id="pptGenBtn" onclick="pptGenerate()">🚀 Generate PPT</button></div>';
  h+='</div><div id="pptResult"></div>';
  document.getElementById("mc").innerHTML=h;
};
function pptGenerate(){
  var topic=document.getElementById("pptTopic").value.trim();
  if(!topic){showToast("Enter demo topic","error");return}
  var slides=parseInt((document.getElementById("pptPages")||{}).value)||10;
  var style=document.getElementById("pptStyle").value.trim()||'DarkTech Style，16:9';
  var btn=document.getElementById("pptGenBtn");
  btn.disabled=true;btn.textContent="Generating...";
  var el=document.getElementById("pptResult");
  el.innerHTML='<div class="lo"><div class="s"></div>AI Creating，约15-30秒...</div>';
  fetch("/admin/generate-ppt",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({topic:topic,slides:slides,style:style})})
  .then(function(r){return r.json()})
  .then(function(d){
    btn.disabled=false;btn.textContent="🤖 AI Generate PPT";
    if(!d.success){el.innerHTML='<div class="em">'+esc(d.error||"Generation Failed")+'</div>';return}
    el.innerHTML='<div class="cd" style="border-color:var(--accent)"><div class="st">✅ Generated Successfully — '+d.slides+' 页</div>'
      +'<div style="font-size:11px;color:var(--dim);margin:4px 0">'+esc(d.filename)+'</div>'
      +'<a class="btn bp" href="'+d.url+'" download style="margin-top:8px;text-decoration:none">⬇ Download PPTX</a></div>';
  }).catch(function(e){
    btn.disabled=false;btn.textContent="🤖 AI Generate PPT";
    el.innerHTML='<div class="em">Request Failed — Please Refresh &amp; Retry</div>';
  });
}

function imgGenerate(){
  var prompt=(document.getElementById("imgPrompt")||{}).value;
  if(!prompt||!prompt.trim()){showToast("Enter a prompt","error");return}
  var style=document.getElementById("imgStyle").value||'realistic';
  var count=parseInt(document.getElementById("imgCount").value)||1;
  var btn=document.getElementById("imgGenBtn");
  btn.disabled=true;btn.textContent="Generating...";
  var el=document.getElementById("imgResult");
  el.innerHTML='<div class="lo"><div class="s"></div>Image Generation In Progress，约10-30秒...</div>';
  fetch("/admin/generate-image",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({prompt:prompt.trim(),style:style,count:count})})
  .then(function(r){return r.json()})
  .then(function(d){
    btn.disabled=false;btn.textContent="🎨 Generate Image";
    if(!d.success){el.innerHTML='<div class="em">'+esc(d.error||"Generation Failed")+'</div>';return}
    var h='';
    (d.images||[]).forEach(function(img){
      h+='<div style="text-align:center"><img src="'+img.url+'" style="max-width:300px;max-height:300px;border-radius:8px;border:1px solid var(--border)" onerror="this.style.display=\'none\'"><br><a href="'+img.url+'" download class="btn bo bs" style="font-size:10px;margin-top:4px">⬇ Download</a></div>';
    });
    if(!h)h='<div class="em">No Results</div>';
    el.innerHTML=h;
  }).catch(function(e){
    btn.disabled=false;btn.textContent="🎨 Generate Image";
    el.innerHTML='<div class="em">Request Failed</div>';
  });
}
// ── Multimedia Generation ──
var mvTab=0;
window.l_media_video=function(){
  mvSwitchTab(mvTab||0);
};
function mvSwitchTab(t){
  mvTab=t;
  var parent=document.getElementById("cmsContent")||document.getElementById("mc");
  var h='<div style="margin-bottom:10px;display:flex;gap:4px">';
  h+='<button class="btn '+(t===0?'bp':'bo')+'" onclick="mvSwitchTab(0)">🎙️ Audio Source Management</button>';
  h+='<button class="btn '+(t===1?'bp':'bo')+'" onclick="mvSwitchTab(1)">🎬 Video Creation</button>';
  h+='<button class="btn '+(t===2?'bp':'bo')+'" onclick="mvSwitchTab(2)">📋 Publish Management</button>';
  h+='</div><div id="mvContent"></div>';
  parent.innerHTML=h;
  if(t===0)mvTabVoice();
  else if(t===1)mvTabCreate();
  else mvTabList();
}

// ── Tab 1: Voice Management ──
function mvTabVoice(){
  var el=document.getElementById("mvContent");
  el.innerHTML='<div class="lo"><div class="s"></div>Loading Voice List...</div>';
  fetch("/admin/media/voice/list",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success){el.innerHTML='<div class="em">Load failed</div>';return}
    var h='<div class="cd" style="margin-bottom:12px"><div class="st">+ Clone New Voice</div>';
    h+='<div class="g2">';
    h+='<div><div style="font-size:11px;color:var(--dim)">Voice Name *</div><input class="in" id="mvVoiceName" placeholder="如：My Voices" style="width:100%"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Audio Sample URL *</div><input class="in" id="mvVoiceUrl" placeholder="https://... Publicly Accessible wav/mp3" style="width:100%"></div>';
    h+='</div>';
    h+='<div style="font-size:10px;color:var(--muted);margin:4px 0">Format: wav/mp3, 16kHz Mono, 10-30秒。Upload Audio to Public URL First。</div>';
    h+='<button class="btn bp" onclick="mvCloneVoice()">Submit Clone</button></div>';

    // Voice List
    h+='<div class="cd"><div class="st">Cloned Voices</div>';
    if(!d.data||!d.data.length){
      h+='<div class="em">No Voices，Please Clone First</div>';
    }else{
      h+='<table><tr><th>Name</th><th>Voice ID</th><th>Status</th><th>Created</th><th>Actions</th></tr>';
      d.data.forEach(function(v){
        var st=v.status==="ready"?'<span class="bdg on">Ready</span>':v.status==="pending"?'<span class="bdg" style="background:var(--accent2)">Cloning</span>':'<span class="bdg off">Failed</span>';
        h+='<tr><td>'+esc(v.name)+'</td><td style="font-size:10px">'+esc(v.external_voice_id||"—")+'</td><td>'+st+'</td><td style="font-size:10px;color:var(--dim)">'+esc(v.created_at||"")+'</td>';
        h+='<td><button class="btn bo bs" style="color:#f85149" onclick="mvDelVoice('+v.id+')">Delete</button></td></tr>';
      });
      h+='</table>';
    }
    h+='</div>';
    el.innerHTML=h;
  }).catch(function(){el.innerHTML='<div class="em">Request Failed</div>'});
}

function mvCloneVoice(){
  var name=document.getElementById("mvVoiceName").value.trim();
  var url=document.getElementById("mvVoiceUrl").value.trim();
  if(!name||!url){showToast("Name and URL are required","error");return}
  var btn=event.target;btn.disabled=true;btn.textContent="Submitting...";
  fetch("/admin/media/voice/clone",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({name:name,audio_url:url})})
  .then(function(r){return r.json()})
  .then(function(d){
    btn.disabled=false;btn.textContent="Submit Clone";
    if(d.success){showToast("Voice clone task submitted");mvTabVoice()}
    else showToast(d.error||"Clone Failed","error");
  }).catch(function(e){btn.disabled=false;btn.textContent="Submit Clone";showToast("Request Failed","error")});
}

function mvDelVoice(id){
  if(!confirm("Delete this voice?"))return;
  fetch("/admin/media/voice/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){if(d.success)mvTabVoice();else showToast(d.error,"error")});
}

// ── Tab 2: Video Creation ──
function mvTabCreate(){
  var el=document.getElementById("mvContent");
  el.innerHTML='<div class="lo"><div class="s"></div>Loading Voice List...</div>';
  fetch("/admin/media/voice/list",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    var voices=d.data||[];
    var readyVoices=voices.filter(function(v){return v.status==="ready"});
    var h='<div class="cd"><div class="st">🎬 Create Video</div>';
    h+='<div class="g2">';
    h+='<div><div style="font-size:11px;color:var(--dim)">Video Title *</div><input class="in" id="mvTitle" placeholder="如：Feature Release" style="width:100%"></div>';
    h+='<div><div style="font-size:11px;color:var(--dim)">Select Voice *</div><select class="sl" id="mvVoiceId" style="width:100%">';
    if(!readyVoices.length)h+='<option value="">— No Ready Voices，Please Clone First —</option>';
    else readyVoices.forEach(function(v){h+='<option value="'+v.id+'">'+esc(v.name)+' ('+esc(v.external_voice_id||"")+')</option>'});
    h+='</select></div>';
    h+='</div>';
    h+='<div style="margin-top:8px"><div style="font-size:11px;color:var(--dim)">Script *（Suggestion50-500字）</div>';
    h+='<textarea class="in" id="mvText" placeholder="Enter Digital Human Script..." style="width:100%;min-height:120px;font-size:13px;line-height:1.5"></textarea></div>';
    h+='<div style="margin-top:8px"><div style="font-size:11px;color:var(--dim)">Digital Human Avatar URL</div>';
    h+='<input class="in" id="mvAvatar" placeholder="https://... PhotoURL（Leave Empty for Default Avatar）" style="width:100%"></div>';
    h+='<div style="margin-top:12px"><button class="btn bp" onclick="mvCreateVideo()">🎬 Generate Video</button></div>';
    h+='</div>';
    el.innerHTML=h;
  }).catch(function(){el.innerHTML='<div class="em">Request Failed</div>'});
}

function mvCreateVideo(){
  var title=document.getElementById("mvTitle").value.trim();
  var text=document.getElementById("mvText").value.trim();
  var voiceId=document.getElementById("mvVoiceId").value;
  var avatar=document.getElementById("mvAvatar").value.trim();
  if(!title||!text){showToast("Title and copy are required","error");return}
  if(!voiceId){showToast("Please select a cloned voice first","error");return}
  var btn=event.target;btn.disabled=true;btn.textContent="Submitting...";
  fetch("/admin/media/video/create",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({title:title,text:text,voice_id:voiceId,image_url:avatar})})
  .then(function(r){return r.json()})
  .then(function(d){
    btn.disabled=false;btn.textContent="Generate Video";
    if(d.success){showToast("Video generation task submitted");mvTab=2;l_media_video()}
    else showToast(d.error||"Creation Failed","error");
  }).catch(function(e){btn.disabled=false;btn.textContent="Generate Video";showToast("Request Failed","error")});
}

// ── Tab 3: Publish Management ──
var mvPolling=null, mvPubChannel=0;  // 0=Internal Channels, 1=External Channels
function mvTabList(){
  if(mvPolling){clearInterval(mvPolling);mvPolling=null}
  var el=document.getElementById("mvContent");
  el.innerHTML='<div class="lo"><div class="s"></div>Load Video List...</div>';
  fetch("/admin/media/video/list?limit=50",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success||!d.data){el.innerHTML='<div class="em">Load failed</div>';return}
    var items=d.data.items||[];
    var h='';

    // Channel Switch
    var channels=[["🏠 Internal Channels","在 EasyKai / tm.easykai.cn Homepage Video Window"],["🌐 External Channels","Publish to Douyin、Kuaishou &amp; Other Social Media"]];
    h+='<div style="display:flex;gap:6px;margin-bottom:12px">';
    channels.forEach(function(c,i){
      var sel=i===mvPubChannel;
      h+='<div class="cd" onclick="mvPubChannel='+i+';mvTabList()" style="flex:1;cursor:pointer;padding:12px;border-color:'+(sel?'var(--accent)':'var(--border)')+';background:'+(sel?'rgba(47,107,255,0.06)':'')+'">';
      h+='<div style="font-size:13px;font-weight:600;color:'+(sel?'var(--accent)':'var(--text)')+'">'+c[0]+'</div>';
      h+='<div style="font-size:10px;color:var(--dim);margin-top:2px">'+c[1]+'</div>';
      h+='</div>';
    });
    h+='</div>';

    // Video List
    var doneItems=items.filter(function(t){return t.status==="done"});
    h+='<div class="cd"><div class="st">📋 Publishable Videos ('+doneItems.length+'/'+items.length+')</div>';

    if(!doneItems.length){
      h+='<div class="em">No Completed Videos，First「Video Creation」Generate In</div>';
    }else if(mvPubChannel===0){
      // Internal Channels：Homepage Display + Download
      h+='<table><tr><th>Title</th><th>Sound</th><th>Home</th><th>Actions</th></tr>';
      doneItems.forEach(function(t){
        var hp=t.is_homepage?'<span class="bdg on">Showing</span>':'<span class="bdg off">Not Shown</span>';
        h+='<tr><td>'+esc(t.title)+'</td><td style="font-size:11px">'+esc(t.voice_name||"—")+'</td><td>'+hp+'</td>';
        h+='<td><a class="btn bo bs" href="/admin/media/video/'+t.id+'/download" target="_blank">Download</a> ';
        h+='<button class="btn bo bs" onclick="mvToggleHomepage('+t.id+')">'+(t.is_homepage?'Unset Home':'Homepage Display')+'</button>';
        h+='<button class="btn bo bs" style="color:#f85149" onclick="mvDelVideo('+t.id+')">Delete</button></td></tr>';
      });
      h+='</table>';
    }else{
      // External Channels：Douyin、Kuaishou
      h+='<table><tr><th>Title</th><th>Sound</th><th>Douyin</th><th>Kuaishou</th><th>Actions</th></tr>';
      doneItems.forEach(function(t){
        var dy=t.published_douyin?'<span class="bdg on">Published</span>':'<span class="bdg off">Unpublished</span>';
        h+='<tr><td>'+esc(t.title)+'</td><td style="font-size:11px">'+esc(t.voice_name||"—")+'</td>';
        h+='<td>'+dy+'</td><td><span class="bdg off" style="font-size:10px">In Development</span></td>';
        h+='<td><a class="btn bo bs" href="/admin/media/video/'+t.id+'/download" target="_blank">Download</a> ';
        if(!t.published_douyin)h+='<button class="btn bo bs" onclick="mvPublishDouyin('+t.id+')">Post to Douyin</button> ';
        h+='<button class="btn bo bs" style="color:#f85149" onclick="mvDelVideo('+t.id+')">Delete</button></td></tr>';
      });
      h+='</table>';
    }
    h+='</div>';

    // Processing/Failed Task List
    var otherItems=items.filter(function(t){return t.status!=="done"});
    if(otherItems.length>0){
      h+='<div class="cd" style="margin-top:4px"><div class="st">⏳ Processing / Failed ('+otherItems.length+')</div>';
      h+='<table style="font-size:11px"><tr><th>Title</th><th>Status</th><th>Actions</th></tr>';
      otherItems.forEach(function(t){
        var st=t.status==="processing"?'<span class="bdg" style="background:var(--accent2)">Generating</span>':t.status==="pending"?'<span class="bdg" style="background:var(--warn)">Waiting</span>':'<span class="bdg off">Failed</span>';
        h+='<tr><td>'+esc(t.title)+'</td><td>'+st+'</td>';
        h+='<td>'+(t.status==="processing"?'<span style="font-size:10px;color:var(--accent)">Polling...</span>':t.status==="failed"?'<button class="btn bo bs" onclick="mvRetry('+t.id+')">Retry</button>':'')
        +'<button class="btn bo bs" style="color:#f85149;margin-left:4px" onclick="mvDelVideo('+t.id+')">Delete</button></td></tr>';
      });
      h+='</table></div>';
    }

    el.innerHTML=h;
    // Auto Poll
    var processingIds=[];
    items.forEach(function(t){if(t.status==="processing")processingIds.push(t.id)});
    if(processingIds.length>0){
      mvPolling=setInterval(function(){processingIds.forEach(function(id){mvPollStatus(id)})},5000);
    }
  }).catch(function(){el.innerHTML='<div class="em">Request Failed</div>'});
}

function mvPollStatus(tid){
  fetch("/admin/media/video/"+tid+"/status",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success)return;
    if(d.data.status==="done"||d.data.status==="failed")mvTabList();
  }).catch(function(){});
}

function mvToggleHomepage(tid){
  fetch("/admin/media/video/"+tid+"/toggle-homepage",{method:"POST",headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){if(d.success)mvTabList();else showToast(d.error,"error")});
}

function mvPublishDouyin(tid){
  if(!confirm("Publish to Douyin?"))return;
  showToast("Douyin publish under development, download video and publish manually","warn");
}

function mvRetry(tid){
  var btn=event.target;btn.disabled=true;btn.textContent="Retrying...";
  fetch("/admin/media/video/"+tid+"/retry",{method:"POST",headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    btn.disabled=false;btn.textContent="Retry";
    if(d.success){showToast("Re-submitted");mvTabList()}
    else showToast(d.error,"error");
  }).catch(function(e){btn.disabled=false;btn.textContent="Retry";showToast("Request Failed","error")});
}

function mvDelVideo(tid){
  if(!confirm("Delete this video? File will be permanently removed."))return;
  fetch("/admin/media/video/"+tid,{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){if(d.success)mvTabList();else showToast(d.error,"error")});
}


window.l_contentfactory=function(){
  document.getElementById("pt").textContent="Content Factory";
  var h='<div style="margin-bottom:12px">';
  h+='<button class="btn '+(cfTab===0?'bp':'bo')+'" onclick="cfSwitchTab(0)">📡 Source Management</button> ';
  h+='<button class="btn '+(cfTab===1?'bp':'bo')+'" onclick="cfSwitchTab(1)">📥 Raw Content</button> ';
  h+='<button class="btn '+(cfTab===2?'bp':'bo')+'" onclick="cfSwitchTab(2)">✏️ Process Content</button> ';
  h+='</div><div id="cfTabContent"><div class="lo"><div class="s"></div></div></div>';
  document.getElementById("mc").innerHTML=h;
  cfRenderTab();
};

function cfSwitchTab(t){
  cfTab=t;
  var btns=document.getElementById("mc").querySelectorAll("button");
  btns.forEach(function(b,i){b.className=b.className.replace(/btn bp/g,"btn bo");if(i===t)b.className="btn bp"});
  cfRenderTab();
}

function cfRenderTab(){
  if(cfTab===0)cfRenderSources();
  else if(cfTab===1)cfRenderRaw();
  else if(cfTab===2)cfRenderProcessed();
}

// ── Tab 0: Source Management ──
function cfRenderSources(){
  var h='<div style="margin-bottom:10px"><button class="btn bp" onclick="cfShowSourceForm()">+ Add Source</button></div>';
  h+='<div id="cfSourceForm" style="display:none;margin-bottom:14px" class="cd">';
  h+='<div class="st" id="cfSfTitle">Add Source</div><div class="g2">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Name</div><input class="in" id="cfSn" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Type</div><select class="sl" id="cfSt" style="width:100%"><option value="rss">RSS</option><option value="api">API</option><option value="web">Web Page</option></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">URL</div><input class="in" id="cfSu" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Collection Interval(秒,0=Manual)</div><input class="in" id="cfSi" value="0" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Max Per Round</div><input class="in" id="cfSm" value="10" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Keywords Filter</div><input class="in" id="cfSk" style="width:100%"></div>';
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Platform ID(Optional)</div><input class="in" id="cfSp" placeholder="rss/xueqiu/sec" style="width:100%"></div>';
  h+='</div><div style="margin-top:8px"><button class="btn bp" onclick="cfSaveSource()">Save</button> <button class="btn bo" onclick="cfHideSourceForm()">Cancel</button><input type="hidden" id="cfSeid"></div></div>';
  h+='<div class="cd"><div class="st">Collection Source <span id="cfScnt">0</span></div>';
  h+='<table><tr><th>Name</th><th>Type</th><th>URL</th><th>Interval</th><th>Last Collected</th><th>Status</th><th>Actions</th></tr><tbody id="cfStbody"></tbody></table></div>';
  document.getElementById("cfTabContent").innerHTML=h;
  cfLoadSources();
}

function cfLoadSources(){
  fetch("/admin/content-factory/sources",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("cfStbody").innerHTML='<tr><td colspan="7"><div class="em">Load failed</div></td></tr>';return}
    cfSources=d.data||[];
    document.getElementById("cfScnt").textContent=cfSources.length;
    var h='';
    if(!cfSources.length){h='<tr><td colspan="7"><div class="em">No Source</div></td></tr>'}
    else{cfSources.forEach(function(s){
      h+='<tr><td style="font-weight:600">'+esc(s.name)+'</td><td><span class="bdg '+(s.source_type==='rss'?'on':'pd')+'">'+s.source_type+'</span></td>';
      h+='<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;font-family:monospace;font-size:10px">'+esc(s.url)+'</td>';
      h+='<td>'+(s.crawl_interval?s.crawl_interval+'s':'Manual')+'</td>';
      h+='<td style="font-size:10px;color:var(--dim)">'+(s.last_crawled_at||'-')+'</td>';
      h+='<td>'+(s.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Disable</span>')+'</td>';
      h+='<td><button class="btn bo bs" onclick="cfRunCrawl('+s.id+')">Crawl</button> ';
      h+='<button class="btn bo bs" onclick="cfEditSource('+s.id+')">Edit</button> ';
      h+='<button class="btn bo bs" onclick="cfDelSource('+s.id+')">Delete</button></td></tr>';
    })}
    document.getElementById("cfStbody").innerHTML=h;
  }).catch(function(){document.getElementById("cfStbody").innerHTML='<tr><td colspan="7"><div class="em">Request Failed</div></td></tr>'});
}

function cfShowSourceForm(){
  document.getElementById("cfSourceForm").style.display="block";
  document.getElementById("cfSfTitle").textContent="Add Source";
  document.getElementById("cfSeid").value="";
  var fid=["cfSn","cfSt","cfSu","cfSi","cfSm","cfSk","cfSp"];
  for(var i=0;i<fid.length;i++){document.getElementById(fid[i]).value=""};
}

function cfHideSourceForm(){document.getElementById("cfSourceForm").style.display="none"}

function cfSaveSource(){
  var eid=document.getElementById("cfSeid").value;
  var name=document.getElementById("cfSn").value.trim();
  var st=document.getElementById("cfSt").value;
  var url=document.getElementById("cfSu").value.trim();
  if(!name||!url){showToast("Name and URL are required","error");return}
  var body={name:name,source_type:st,url:url,
    crawl_interval:parseInt(document.getElementById("cfSi").value)||0,
    max_per_run:parseInt(document.getElementById("cfSm").value)||10,
    keywords:document.getElementById("cfSk").value.trim(),
    platform:document.getElementById("cfSp").value.trim(),config:{}};
  var method=eid?"PUT":"POST";
  var apiUrl="/admin/content-factory/sources"+(eid?"/"+eid:"");
  fetch(apiUrl,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){cfHideSourceForm();cfLoadSources();showToast("Saved","success")}
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfEditSource(id){
  var s=null;
  for(var i=0;i<cfSources.length;i++){if(cfSources[i].id===id){s=cfSources[i];break}}
  if(!s){showToast("Not found","error");return}
  document.getElementById("cfSourceForm").style.display="block";
  document.getElementById("cfSfTitle").textContent="Edit Source";
  document.getElementById("cfSeid").value=s.id;
  document.getElementById("cfSn").value=s.name;
  document.getElementById("cfSt").value=s.source_type;
  document.getElementById("cfSu").value=s.url;
  document.getElementById("cfSi").value=s.crawl_interval||0;
  document.getElementById("cfSm").value=s.max_per_run||10;
  document.getElementById("cfSk").value=s.keywords||"";
  document.getElementById("cfSp").value=s.platform||"";
}

function cfDelSource(id){
  if(!confirm("Delete this source?"))return;
  fetch("/admin/content-factory/sources/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){cfLoadSources();showToast("Deleted","success")}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfRunCrawl(id){
  showToast("Collecting...","");
  fetch("/admin/content-factory/crawl",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({source_id:id})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){cfLoadSources();showToast("Collection Complete: Add"+d.inserted+" Skip"+d.skipped,"success")}
    else{showToast("Collect Failed: "+d.error,"error")}
  }).catch(function(){showToast("Request Failed","error")});
}

// ── Tab 1: Raw Content List ──
function cfRenderRaw(){
  var h='<div class="cd"><div class="st">Raw Content <span id="cfRawCnt">0</span></div>';
  h+='<div class="sbar"><input id="cfRawSearch" placeholder="Search Title..." onkeyup="cfLoadRaw()"> ';
  h+='<select class="sl" id="cfRawStatus" onchange="cfLoadRaw()"><option value="">All</option><option value="pending">Pending Process</option><option value="processed">Processed</option><option value="failed">Failed</option></select>';
  h+='<button class="btn bp bs" onclick="cfBatchProcess()">⚡ BatchAIProcess</button> ';
  h+='<button class="btn bo bs" onclick="cfBatchDelete()">🗑 Batch Delete</button></div>';
  h+='<table><tr><th style="width:24px"><input type="checkbox" id="cfRawAll" onchange="cfToggleRawAll()"></th><th>Source</th><th>Title</th><th>Summary</th><th>Status</th><th>Time</th><th>Actions</th></tr><tbody id="cfRawBody"></tbody></table></div>';
  document.getElementById("cfTabContent").innerHTML=h;
  cfLoadRaw();
}

function cfLoadRaw(){
  var s=document.getElementById("cfRawStatus")?document.getElementById("cfRawStatus").value:"";
  var url="/admin/content-factory/contents?limit=30";
  if(s)url+="&status="+s;
  fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("cfRawBody").innerHTML='<tr><td colspan="7"><div class="em">Load failed</div></td></tr>';return}
    cfRawContents=d.data||[];
    var q=document.getElementById("cfRawSearch")?document.getElementById("cfRawSearch").value.trim():"";
    var filtered=cfRawContents;
    if(q){filtered=filtered.filter(function(r){return(r.title||"").indexOf(q)>=0})}
    document.getElementById("cfRawCnt").textContent=filtered.length;
    var h='';
    if(!filtered.length){h='<tr><td colspan="7"><div class="em">No Content</div></td></tr>'}
    else{filtered.forEach(function(r){
      var sc={pending:'pd',processed:'on',failed:'off'}[r.status]||'';
      h+='<tr><td><input type="checkbox" class="cfRawCb" value="'+r.id+'"></td>';
      h+='<td style="font-size:10px">'+esc(r.source_name||'')+'</td>';
      h+='<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;font-weight:600">'+esc(r.title||'No Title')+'</td>';
      h+='<td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;font-size:11px;color:var(--dim)">'+esc((r.summary||r.content_text||'').slice(0,60))+'</td>';
      h+='<td><span class="bdg '+sc+'">'+r.status+'</span></td>';
      h+='<td style="font-size:10px">'+(r.created_at||'').slice(0,16)+'</td>';
      h+='<td>'+(r.status==='pending'?'<button class="btn bo bs" onclick="cfProcessOne('+r.id+')">Process</button>':'')+'</td></tr>';
    })}
    document.getElementById("cfRawBody").innerHTML=h;
  }).catch(function(){document.getElementById("cfRawBody").innerHTML='<tr><td colspan="7"><div class="em">Request Failed</div></td></tr>'});
}

function cfToggleRawAll(){
  var chk=document.getElementById("cfRawAll").checked;
  var cbs=document.querySelectorAll(".cfRawCb");
  for(var i=0;i<cbs.length;i++){cbs[i].checked=chk};
}

function cfBatchProcess(){
  var ids=[];
  var cbs=document.querySelectorAll(".cfRawCb:checked");
  for(var i=0;i<cbs.length;i++){ids.push(parseInt(cbs[i].value))};
  if(!ids.length){showToast("Please select content first","error");return}
  showToast("AIProcessing ("+ids.length+"条)...","");
  fetch("/admin/content-factory/process",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({raw_ids:ids})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Complete: OK="+d.ok+" FAIL="+d.fail,"success");cfLoadRaw()}
    else{showToast("Failed: "+d.error,"error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfBatchDelete(){
  var ids=[];
  var cbs=document.querySelectorAll(".cfRawCb:checked");
  for(var i=0;i<cbs.length;i++){ids.push(parseInt(cbs[i].value))};
  if(!ids.length){showToast("Please select content first","error");return}
  if(!confirm("Confirm Delete "+ids.length+" Items？Cannot Be Recovered！"))return;
  showToast("Deleting...","");
  // Delete One by One (No Batch DeleteAPI, 用DELETEOne by One)
  var done=0,fail=0;
  function delNext(){
    if(!ids.length){showToast("Deleted: OK="+done+" FAIL="+fail,"success");cfLoadRaw();return}
    var id=ids.shift();
    fetch("/admin/content-factory/contents/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
      if(d.success){done++}else{fail++}
      delNext();
    }).catch(function(){fail++;delNext()});
  }
  delNext();
}

function cfProcessOne(id){
  showToast("AI Processing...","");
  fetch("/admin/content-factory/process",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({raw_ids:[id]})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Processing complete","success");cfLoadRaw()}
    else{showToast("Process Failed: "+d.error,"error")}
  }).catch(function(){showToast("Request Failed","error")});
}

// ── Tab 2: Process Content List ──
function cfRenderProcessed(){
  var h='<div class="cd"><div class="st">Process Content <span id="cfPcCnt">0</span></div>';
  h+='<div class="sbar"><select class="sl" id="cfPcStatus" onchange="cfLoadProcessed()">';
  h+='<option value="">All</option><option value="draft">Draft</option><option value="review">Reviewing</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="published">Published</option>';
  h+='</select>';
  h+='<button class="btn bo bs" onclick="cfBatchDeleteProcessed()">🗑 Batch Delete</button></div>';
  h+='<table><tr><th style="width:24px"><input type="checkbox" id="cfPcAll" onchange="cfTogglePcAll()"></th><th>Title</th><th>Type</th><th>Risk</th><th>Status</th><th>Time</th><th>Actions</th></tr><tbody id="cfPcBody"></tbody></table></div>';
  h+='<div id="cfPcDetail" style="display:none"></div>';
  document.getElementById("cfTabContent").innerHTML=h;
  cfLoadProcessed();
}

function cfLoadProcessed(){
  var s=document.getElementById("cfPcStatus")?document.getElementById("cfPcStatus").value:"";
  var url="/admin/content-factory/processed?limit=30";
  if(s)url+="&status="+s;
  fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("cfPcBody").innerHTML='<tr><td colspan="6"><div class="em">Load failed</div></td></tr>';return}
    cfProcessed=d.data||[];
    document.getElementById("cfPcCnt").textContent=cfProcessed.length;
    var h='';
    if(!cfProcessed.length){h='<tr><td colspan="6"><div class="em">No Process Content</div></td></tr>'}
    else{cfProcessed.forEach(function(p){
      var rl={low:'<span class="bdg on">低</span>',normal:'<span class="bdg pd">中</span>',high:'<span class="bdg off">高</span>',critical:'<span class="bdg off" style="background:rgba(248,81,73,.2)">Danger</span>'};
      var st_bdg={draft:'pd',review:'pd',approved:'on',rejected:'off',published:'on'}[p.status]||'pd';
      var st_label={draft:'Draft',review:'Reviewing',approved:'✅Approved',rejected:'❌Reject',published:'Published'}[p.status]||p.status;
      var st='<span class="bdg '+st_bdg+'">'+st_label+'</span>';
      h+='<tr><td><input type="checkbox" class="cfPcCb" value="'+p.id+'"></td>';
      h+='<td style="font-weight:600;max-width:200px;overflow:hidden;text-overflow:ellipsis">'+esc(p.title||'No Title')+'</td>';
      h+='<td style="font-size:10px">'+p.content_type+'</td>';
      h+='<td>'+(rl[p.risk_level]||'<span class="bdg pd">Medium</span>')+'</td>';
      h+='<td>'+st+'</td>';
      h+='<td style="font-size:10px">'+(p.created_at||'').slice(0,16)+'</td>';
      h+='<td><button class="btn bo bs" onclick="cfViewProcessed('+p.id+')">View</button> ';
      if(p.status==='draft'){h+='<button class="btn bo bs" onclick="cfReview('+p.id+',\'submit_review\')">Submit for Review</button>'}
      if(p.status==='review'){h+='<button class="btn bp bs" onclick="cfReview('+p.id+',\'approve\')">Approve</button> <button class="btn bo bs" onclick="cfReview('+p.id+',\'reject\')">Reject</button>'}
      if(p.status==='approved'){h+='<button class="btn bp bs" onclick="cfPublishOne('+p.id+')">📄Publish</button> <button class="btn bo bs" onclick="cfPublishToSocial('+p.id+')">📢Social Media</button>'}
      if(p.status==='rejected'){h+='<button class="btn bo bs" onclick="cfReview('+p.id+',\'back_to_draft\')">Revert to Draft</button>'}
      h+='</td></tr>';
    })}
    document.getElementById("cfPcBody").innerHTML=h;
  }).catch(function(){document.getElementById("cfPcBody").innerHTML='<tr><td colspan="6"><div class="em">Request Failed</div></td></tr>'});
}

function cfViewProcessed(id){
  var p=null;
  for(var i=0;i<cfProcessed.length;i++){if(cfProcessed[i].id===id){p=cfProcessed[i];break}}
  if(!p){showToast("Not found","error");return}
  var h='<div class="cd" style="margin-top:10px">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
  h+='<div class="st">'+esc(p.title||'No Title')+'</div>';
  h+='<button class="btn bo bs" onclick="document.getElementById(\'cfPcDetail\').style.display=\'none\'">× Close</button></div>';
  h+='<div style="font-size:11px;color:var(--dim);margin-bottom:8px">Keywords: '+esc(p.keywords||'')+' | Risk: '+p.risk_level+'</div>';
  h+='<div style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:12px;font-size:12px;line-height:1.6;white-space:pre-wrap;max-height:400px;overflow-y:auto">'+esc(p.body||'No Body')+'</div>';
  h+='<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">';
  h+='<div style="font-size:11px;color:var(--dim);padding:4px 0;margin-right:12px">Status: <span class="bdg '+
    ({draft:'pd',review:'pd',approved:'on',rejected:'off',published:'on'}[p.status]||'pd')+'">'+
    ({draft:'Draft',review:'Reviewing',approved:'Approved',rejected:'Rejected',published:'Published'}[p.status]||p.status)+'</span></div>';
  if(p.status==='draft'){h+='<button class="btn bo bs" onclick="cfReview('+p.id+',\'submit_review\')">📋 Submit for Review</button>'}
  if(p.status==='review'){h+='<button class="btn bp bs" onclick="cfReview('+p.id+',\'approve\')">✅ Approve</button> <button class="btn bo bs" onclick="cfReview('+p.id+',\'reject\')">❌ Reject</button>'}
  if(p.status==='approved'){h+='<button class="btn bp bs" onclick="cfPublishOne('+p.id+')">📄 Publish to This Site</button> <button class="btn bo bs" onclick="cfPublishToSocial('+p.id+')">📢 Push to Social Media</button> <button class="btn bo bs" onclick="cfPublishBoth('+p.id+')">📄+📢 Multi-Publish</button>'}
  h+='<button class="btn bo bs" onclick="cfPushToKnowledge('+p.id+')">📚 Push to Knowledge Base</button> '
  if(p.status==='rejected'){h+='<button class="btn bo bs" onclick="cfReview('+p.id+',\'back_to_draft\')">↩ Revert to Draft</button>'}
  h+='<button class="btn bo bs" onclick="cfEditProcessed('+p.id+')">✏️ Edit Content</button> ';
  h+='<button class="btn bo bs" onclick="cfPushToSkill('+p.id+')">🧠 SkillPush</button></div></div>';
  document.getElementById("cfPcDetail").innerHTML=h;
  document.getElementById("cfPcDetail").style.display="block";
}

function cfPushToKnowledge(pid){
  if(!confirm('Push this content to knowledge base?'))return;
  showToast('Pushing to knowledge base...','');
  fetch("/admin/content-factory/push-to-knowledge",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({processed_id:pid})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast('✅ Pushed to Knowledge Base (ID: '+(d.kb_id||'')+')',"success");cfLoadProcessed()}
    else{showToast(d.error||'Push Failed',"error")}
  }).catch(function(){showToast("Request Failed","error")});
}
function cfReview(id,action){
  var labels={'submit_review':'Submit for Review','approve':'Approve','reject':'Reject','back_to_draft':'Revert to Draft'};
  if(!confirm('Go'+labels[action]+'？'))return;
  showToast(labels[action]+' In Progress...','');
  fetch("/admin/content-factory/review",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({processed_id:id,action:action})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast(labels[action]+'Success',"success");cfLoadProcessed();document.getElementById('cfPcDetail').style.display='none'}
    else{showToast(d.error||'Operation Failed',"error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfTogglePcAll(){
  var chk=document.getElementById("cfPcAll").checked;
  var cbs=document.querySelectorAll(".cfPcCb");
  for(var i=0;i<cbs.length;i++){cbs[i].checked=chk};
}

function cfBatchDeleteProcessed(){
  var ids=[];
  var cbs=document.querySelectorAll(".cfPcCb:checked");
  for(var i=0;i<cbs.length;i++){ids.push(parseInt(cbs[i].value))};
  if(!ids.length){showToast("Please select content first","error");return}
  if(!confirm("Confirm Delete "+ids.length+" Process Content Items(Including PushedSkill)？Cannot Be Recovered！"))return;
  showToast("Deleting...","");
  fetch("/admin/content-factory/processed/batch-delete",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({ids:ids})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Deleted "+d.deleted+" 条","success");cfLoadProcessed();document.getElementById('cfPcDetail').style.display='none'}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfEditProcessed(id){
  for(var i=0;i<cfProcessed.length;i++){if(cfProcessed[i].id===id){var p=cfProcessed[i];break}}
  if(!p){showToast("Not found","error");return}
  var h='<div class="cd" style="margin-top:10px">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
  h+='<div class="st">Edit: '+esc(p.title||'No Title')+'</div>';
  h+='<button class="btn bo bs" onclick="cfCloseEditor('+id+')">× Close</button></div>';
  h+='<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--dim);margin-bottom:3px">Title</div>';
  h+='<input class="in" id="cfEditTitle" value="'+esc(p.title||'')+'" style="width:100%"></div>';
  h+='<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--dim);margin-bottom:3px">Summary</div>';
  h+='<input class="in" id="cfEditSummary" value="'+esc(p.summary||'')+'" style="width:100%"></div>';
  h+='<div style="margin-bottom:8px"><div style="font-size:11px;color:var(--dim);margin-bottom:3px">Body (Markdown)</div>';
  h+='<textarea class="ta" id="cfEditBody" rows="15" style="font-family:monospace;font-size:12px;line-height:1.6">'+esc(p.body||'')+'</textarea></div>';
  h+='<div style="margin-top:8px"><button class="btn bp bs" onclick="cfSaveEdit('+id+')">Save</button></div></div>';
  document.getElementById("cfPcDetail").innerHTML=h;
  document.getElementById("cfPcDetail").style.display="block";
}

function cfSaveEdit(id){
  var title=document.getElementById("cfEditTitle").value.trim();
  var summary=document.getElementById("cfEditSummary").value.trim();
  var body=document.getElementById("cfEditBody").value.trim();
  if(!body){showToast("Body cannot be empty","error");return}
  fetch("/admin/content-factory/processed/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({title:title,summary:summary,body:body})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Saved","success");cfLoadProcessed();document.getElementById('cfPcDetail').style.display='none'}
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfCloseEditor(id){
  if(document.getElementById("cfEditBody")){
    if(!confirm("Discard changes?"))return;
  }
  document.getElementById("cfPcDetail").style.display="none";
}

function cfPublishOne(id){
  if(!confirm("Publish to local CMS?"))return;
  fetch("/admin/content-factory/publish",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({processed_id:id,platform:"internal"})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Published Successfully post_id="+d.post_id,"success");cfLoadProcessed()}
    else{showToast(d.error||"Publish Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfPublishToSocial(id){
  var platforms=prompt("Push Platform: wechat / weibo / toutiao（Comma Separated）","wechat");
  if(!platforms)return;
  var list=platforms.split(",").map(function(p){return p.trim()}).filter(function(p){return p});
  if(!list.length)return;
  var autoPub=confirm("Direct Publish to WeChat？\nGo=Publish Directly，Cancel=Draft Only");
  fetch("/admin/content-factory/publish",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({processed_id:id,platform:"social",social_platforms:list,auto_publish:autoPub})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var msgs=d.social_results.map(function(r){return r.platform+": "+(r.message||r.error||r.status)});
      showToast("Social Media Publish: "+msgs.join(" | "),d.social_results.some(function(r){return r.status=="failed"})?"error":"success");
      cfLoadProcessed()
    }else{showToast(d.error||"Publish Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfPublishBoth(id){
  var platforms=prompt("Push Platform: wechat / weibo / toutiao（Comma Separated）","wechat");
  if(!platforms)return;
  var list=platforms.split(",").map(function(p){return p.trim()}).filter(function(p){return p});
  if(!list.length)return;
  if(!confirm("Publish to CMS + Social Media?"))return;
  var autoPub=confirm("Direct Publish to WeChat？\nGo=Publish Directly，Cancel=Draft Only");
  fetch("/admin/content-factory/publish",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({processed_id:id,platform:"both",social_platforms:list,auto_publish:autoPub})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var msgs=["CMS post_id="+d.post_id];
      if(d.social_results)msgs.push(d.social_results.map(function(r){return r.platform+": "+(r.message||r.error||r.status)}).join(" | "));
      showToast("Published: "+msgs.join(" ; "),d.social_results&&d.social_results.some(function(r){return r.status=="failed"})?"error":"success");
      cfLoadProcessed()
    }else{showToast(d.error||"Publish Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function cfPushToSkill(id){
  var target=prompt("Push Target: hermes / openclaw","hermes");
  if(!target)return;
  showToast("Pushing...","");
  fetch("/admin/content-factory/push-skill",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({processed_id:id,target_agent:target})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var preview=d.skill_content.slice(0,200)+"...";
      var html='<div class="cd" style="margin-top:10px">';
      html+='<div class="st">Push Success 🎉</div>';
      html+='<div style="font-size:12px;margin-bottom:8px;color:var(--accent)">Skill: '+esc(d.skill_name)+' → '+esc(d.target_agent)+'</div>';
      html+='<div style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:12px;font-size:11px;font-family:monospace;white-space:pre-wrap;max-height:300px;overflow-y:auto">'+esc(preview)+'</div>';
      html+='<div style="margin-top:8px"><button class="btn bo bs" onclick="document.getElementById(\'cfPcDetail\').innerHTML=\'\'">Close</button></div></div>';
      document.getElementById("cfPcDetail").innerHTML+=html;
      showToast("Push Success: "+d.skill_name,"success")
    }
    else{showToast(d.error||"Push Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

// ============================================================
// ⚡ Auto Schedule (Cron + Workflow)
// ============================================================

window.l_automation=function(){
  document.getElementById("pt").textContent="Auto Schedule";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  aLStats();
}

// 📊 Analytics — iframe srcdoc Inject（Same Origin、Cookie Natural Sharing、No Auth Issues）
// ============================================================

window.l_analytics=function(){
  document.getElementById("pt").textContent="Analytics";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  var xhr=new XMLHttpRequest();
  xhr.open('GET','/admin/analytics/',true);
  xhr.setRequestHeader('Authorization','Bearer '+T);
  xhr.onload=function(){
    if(xhr.status===200){
      var html=xhr.responseText;
      var ifr=document.createElement('iframe');
      ifr.style.cssText='width:100%;height:calc(100vh - 70px);border:none;background:#050508';
      ifr.srcdoc=html;
      document.getElementById("mc").innerHTML='';
      document.getElementById("mc").appendChild(ifr);
    }else{
      document.getElementById("mc").innerHTML='<div class="em">⚠️ Load failed HTTP '+xhr.status+'</div>';
    }
  };
  xhr.onerror=function(){
    document.getElementById("mc").innerHTML='<div class="em">⚠️ Network Request Failed</div>';
  };
  xhr.send();
}

// 🏥 Health Check (Health Check)

window.l_health=function(){
  document.getElementById("pt").textContent="Health Check";
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/admin/health/', true);
  xhr.setRequestHeader('Authorization', 'Bearer ' + T);
  xhr.onload = function() {
    if (xhr.status === 200) {
      var html = xhr.responseText;
      var headMatch = html.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
      var headHtml = headMatch ? headMatch[1] : '';
      var headResources = '';
      headHtml.replace(/<(style|link|script)[^>]*>[\s\S]*?<\/\1>/gi, function(m){ headResources += m; return m; });
      headHtml.replace(/<(style|link|script)[^>]*\/>/gi, function(m){ headResources += m; return m; });
      var bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
      var bodyContent = bodyMatch ? bodyMatch[1] : html;
      document.getElementById("mc").innerHTML = '<div id="health-root">' + headResources + bodyContent + '</div>';
      document.getElementById("health-root").querySelectorAll("script").forEach(function(oldScript){
        var ns = document.createElement("script");
        if (oldScript.src) { ns.src = oldScript.src; }
        else { ns.textContent = oldScript.textContent; }
        oldScript.parentNode.replaceChild(ns, oldScript);
      });
    } else {
      document.getElementById("mc").innerHTML = '<div class="em">Load failed: HTTP ' + xhr.status + '</div>';
    }
  };
  xhr.onerror = function() {
    document.getElementById("mc").innerHTML = '<div class="em">Network Request Failed</div>';
  };
  xhr.send();
}

// 🌐 i18n Translations
// ============================

window.l_i18n_translations=function(){
  document.getElementById("pt").textContent="Translations";
  var mc=document.getElementById("mc");
  var page=1,search='',locale='en';
  function load(){
    mc.innerHTML='<div class="lo"><div class="s"></div>Loading...</div>';
    var url='/admin/i18n/translations?page='+page+'&limit=50&locale='+locale;
    if(search)url+='&search='+encodeURIComponent(search);
    fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
      if(!d.success){mc.innerHTML='<div class="em">'+d.error+'</div>';return}
      var ds=d.data;
      var h='<div style="margin-bottom:12px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">';
      h+='<select id="i18nLocale" onchange="locale=this.value;load()" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:13px">';
      h+='<option value="zh-CN" '+(locale==='zh-CN'?'selected':'')+'>Chinese</option>';
      h+='<option value="en" '+(locale==='en'?'selected':'')+'>English</option>';
      h+='</select>';
      h+='<input type="text" id="i18nSearch" placeholder="Search..." value="'+escAttr(search)+'" ';
      h+='onkeydown="if(event.key===\'Enter\'){search=this.value;page=1;load()}" style="background:var(--bg2);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:4px 8px;font-size:13px;width:200px">';
      h+='<span class="btn bo" onclick="search=document.getElementById(\'i18nSearch\').value;page=1;load()">Search</span>';
      h+='<span class="btn" onclick="showAddDialog()">+ Add</span>';
      h+='<span class="btn" onclick="seedFromYaml()">Sync from YAML</span>';
      h+='</div>';
      h+='<div style="margin-bottom:8px;font-size:12px;color:var(--text-dim)">Total: '+ds.total+' translations</div>';
      h+='<table><tr><th>ID</th><th>Source</th><th>Translation</th><th>Auto</th><th>Updated</th><th>Actions</th></tr>';
      (ds.items||[]).forEach(function(t){
        var autoBadge=t.is_auto?'<span class="bdg">Auto</span>':'<span class="bdg on">Manual</span>';
        h+='<tr><td>'+t.id+'</td><td style="max-width:300px;word-break:break-all">'+esc(t.source)+'</td>';
        h+='<td style="max-width:300px;word-break:break-all">'+esc(t.translation)+'</td>';
        h+='<td>'+autoBadge+'</td><td style="font-size:11px">'+(t.updated_at||'')+'</td>';
        h+='<td><span class="btn bo" onclick="editTranslation('+t.id+',\''+escAttr(t.source)+'\',\''+escAttr(t.translation)+'\')">Edit</span> ';
        h+='<span class="btn bo" style="color:var(--red)" onclick="deleteTranslation('+t.id+')">Delete</span></td></tr>';
      });
      h+='</table>';
      // Pagination
      var totalPages=Math.ceil(ds.total/50);
      if(totalPages>1){
        h+='<div style="margin-top:12px;display:flex;gap:4px;align-items:center;justify-content:center">';
        for(var p=1;p<=Math.min(totalPages,10);p++){
          var act=p===page?'background:var(--accent);color:#fff':'';
          h+='<span class="btn bo" style="'+act+'" onclick="page='+p+';load()">'+p+'</span>';
        }
        if(totalPages>10)h+='<span>...</span>';
        h+='</div>';
      }
      mc.innerHTML=h;
    }).catch(function(){mc.innerHTML='<div class="em">Request Failed</div>'});
  }
  function showAddDialog(){
    var src=prompt('Enter source text (Chinese)');
    if(!src)return;
    var trans=prompt('Enter translation text');
    if(trans===null)return;
    fetch('/admin/i18n/translations',{method:'POST',headers:{"Authorization":"Bearer "+T,'Content-Type':'application/json'},
      body:JSON.stringify({locale:locale,source:src,translation:trans||''})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success)load();
      else alert(d.error);
    });
  }
  window.showAddDialog=showAddDialog;
  function editTranslation(id,src,trans){
    var newTrans=prompt('Edit Translation: '+(src.length>60?src.substring(0,60)+'...':src),trans);
    if(newTrans===null)return;
    fetch('/admin/i18n/translations/'+id,{method:'PUT',headers:{"Authorization":"Bearer "+T,'Content-Type':'application/json'},
      body:JSON.stringify({translation:newTrans,is_auto:0})})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success)load();
      else alert(d.error);
    });
  }
  window.editTranslation=editTranslation;
  function deleteTranslation(id){
    if(!confirm('Delete this translation?'))return;
    fetch('/admin/i18n/translations/'+id,{method:'DELETE',headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success)load();
      else alert(d.error);
    });
  }
  window.deleteTranslation=deleteTranslation;
  function seedFromYaml(){
    fetch('/admin/i18n/seed?locale='+locale,{method:'POST',headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()}).then(function(d){
      if(d.success)load();
      else alert(d.error);
    });
  }
  window.seedFromYaml=seedFromYaml;
  load();
}

// 💬 Comment Management
// ============================

window.l_comments=function(){
  document.getElementById("pt").textContent="Comment Management";
  var h='<div style="margin-bottom:12px;display:flex;gap:4px">';
  h+='<button class="btn bp" onclick="comLoad(\x27\x27)" id="com-t0">All</button>';
  h+='<button class="btn bo" onclick="comLoad(\x27pending\x27)" id="com-t1">⏳ Pending Review</button>';
  h+='<button class="btn bo" onclick="comLoad(\x27approved\x27)" id="com-t2">✅ Approved</button>';
  h+='<button class="btn bo" onclick="comLoad(\x27rejected\x27)" id="com-t3">❌ Rejected</button>';
  h+='</div><div id="comList"><div class="lo"><div class="s"></div></div></div>';
  document.getElementById("mc").innerHTML=h;
  comLoad("");
};

var comFilter="";
function comLoad(filter){
  comFilter=filter||"";
  document.querySelectorAll('[id^="com-t"]').forEach(function(e){e.className="btn bo"});
  var el=document.getElementById("com-t"+(comFilter==="pending"?1:comFilter==="approved"?2:comFilter==="rejected"?3:0));
  if(el)el.className="btn bp";
  var url="/admin/comments?status="+comFilter+"&limit=50";
  fetch(url,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("comList").innerHTML='<div class="em">Load failed</div>';return}
    var items=d.data&&d.data.items?d.data.items:[];
    if(!items.length){document.getElementById("comList").innerHTML='<div class="em">No Comments</div>';return}
    var h='<div class="cd"><div class="st">Comments ('+items.length+')</div><table><tr><th>Article</th><th>Nickname</th><th>Content</th><th>AIRating</th><th>Status</th><th>Time</th><th>Actions</th></tr>';
    items.forEach(function(c){
      var st=c.status;
      var stHtml={pending:'<span class="bdg pd">Pending Review</span>',approved:'<span class="bdg on">Approved</span>',rejected:'<span class="bdg off">Rejected</span>'}[st]||'<span class="bdg pd">'+st+'</span>';
      var score=c.ai_score!==null&&c.ai_score!==undefined?'<span style="font-size:10px;color:'+(c.ai_score<0.3?'var(--green)':c.ai_score<0.7?'var(--dim)':'var(--red)')+'">'+c.ai_score.toFixed(2)+'</span>':'<span style="font-size:10px;color:var(--dim)">-</span>';
      h+='<tr><td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;font-size:11px">'+esc(c.post_title||"-")+'</td>';
      h+='<td>'+esc(c.nickname||"-")+'</td>';
      h+='<td style="max-width:250px;overflow:hidden;text-overflow:ellipsis">'+esc(c.content||"").slice(0,80)+'</td>';
      h+='<td>'+score+'</td><td>'+stHtml+'</td>';
      h+='<td style="font-size:10px">'+(c.created_at||"").slice(0,16)+'</td>';
      h+='<td style="white-space:nowrap">';
      if(c.status==="pending"){h+='<button class="btn bp bs" onclick="comApprove('+c.id+')">Approve</button> <button class="btn bo bs" onclick="comReject('+c.id+')">Reject</button>'}
      else{h+='<button class="btn bo bs" onclick="comDelete('+c.id+')">Delete</button>'}
      h+='</td></tr>';
    });
    h+='</table></div>';
    document.getElementById("comList").innerHTML=h;
  }).catch(function(){document.getElementById("comList").innerHTML='<div class="em">Request Failed</div>'});
}

function comApprove(id){
  fetch("/admin/comments/"+id+"/review",{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({action:"approve"})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Approved","success");comLoad(comFilter)}
    else{showToast(d.error||"Operation Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function comReject(id){
  fetch("/admin/comments/"+id+"/review",{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({action:"reject"})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Rejected","success");comLoad(comFilter)}
    else{showToast(d.error||"Operation Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function comDelete(id){
  if(!confirm("Delete this comment?"))return;
  fetch("/admin/comments/"+id+"/review",{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({action:"delete"})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Deleted","success");comLoad(comFilter)}
    else{showToast(d.error||"Operation Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

var aS={}; // Currently Selected sub tab
function aLStats(){
  fetch("/admin/automation/stats",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("mc").innerHTML='<div class="em">Load failed，Confirm Installed APScheduler</div>';return}
    var s=d.data;
    var h='<div class="gr">';
    h+=hka('Cron Tasks',s.total_jobs,'g');
    h+=hka('Active Tasks',s.active_jobs,'b');
    h+=hka('Workflow',s.total_workflows,'g');
    h+=hka('Running',s.running_instances,'b');
    h+=hka('Today Completed',s.completed_today,'g');
    h+=hka('Today Failures',s.failed_today,'r');
    h+='</div>';
    // Scheduler Status
    if(s.scheduler){
      h+='<div class="cd" style="margin-bottom:12px"><div class="st">🟢 Scheduler Status</div>';
      h+='<div style="font-size:12px;color:var(--muted)">Instance: '+esc(s.scheduler.scheduler_id)+'</div>';
      h+='<div style="font-size:12px;color:var(--muted)">Scheduled Tasks: '+s.scheduler.scheduled_jobs+'</div>';
      h+='</div>';
    }
    // Action Button
    h+='<div style="display:flex;gap:8px;margin-bottom:12px">';
    h+='<button class="btn bp" onclick="aLTab(\'jobs\')">📋 Task Management</button>';
    h+='<button class="btn bp" onclick="aLTab(\'workflows\')">🔧 Workflow</button>';
    h+='<button class="btn bp" onclick="aLTab(\'instances\')">📊 Execution History</button>';
    h+='<button class="btn bo" onclick="aLTab(\'logs\')">📄 Log</button>';
    h+='</div>';
    // Content Area
    h+='<div id="aLContent"><div class="em">Select Function to Start Settings</div></div>';
    document.getElementById("mc").innerHTML=h;
  }).catch(function(){
    document.getElementById("mc").innerHTML='<div class="em">Load failed，Please Confirm Scheduler is Running</div>';
  });
}

function hka(l,v,c){return '<div class="cd"><div class="l">'+l+'</div><div class="v '+(c||'')+'">'+(v!=null?v:'-')+'</div></div>'}

// ---- 子 Tab Switch ----
function aLTab(tab){
  aS.current=tab;
  if(tab=='jobs')aLJobs();
  else if(tab=='workflows')aLWorkflows();
  else if(tab=='instances')aLInstances();
  else if(tab=='logs')aLLogs();
}

// ===== Task Management =====
var aJobs=[];
function aLJobs(){
  document.getElementById("aLContent").innerHTML='<div class="lo"><div class="s"></div>Load Tasks...</div>';
  fetch("/admin/automation/jobs?limit=100",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    aJobs=d.data.jobs||[];
    var h='<div class="cd"><div class="st">📋 Cron Tasks ('+d.data.total+')';
    h+=' <button class="btn bp bs" onclick="aJNew()" style="float:right">+ New</button></div>';
    h+='<table><tr><th>Name</th><th>Type</th><th>Expression</th><th>Priority</th><th>Agent</th><th>Last</th><th>Status</th><th>Actions</th></tr>';
    if(!aJobs.length)h+='<tr><td colspan="8"><div class="em">No Tasks</div></td></tr>';
    else aJobs.forEach(function(j){
      var st=j.is_active?'<span class="bdg on">Active</span>':'<span class="bdg off">Pause</span>';
      var ls=j.last_status?('<span class="bdg '+(j.last_status=='success'?'on':j.last_status=='failed'?'off':'pd')+'">'+j.last_status+'</span>'):'-';
      h+='<tr><td style="font-weight:600">'+esc(j.name)+'</td>';
      h+='<td>'+j.job_type+'</td>';
      h+='<td style="font-family:monospace;font-size:11px">'+esc(j.cron_expr||j.natural_expr||j.interval_seconds+'s')+'</td>';
      h+='<td>'+j.priority+'</td>';
      h+='<td>'+j.agent_type+'</td>';
      h+='<td style="font-size:11px">'+(j.last_run_at||'-')+'</td>';
      h+='<td>'+st+'</td>';
      h+='<td>'+
        '<button class="btn bo bs" onclick="aJRun('+j.id+')">▶</button> '+
        '<button class="btn bo bs" onclick="aJToggle('+j.id+','+j.is_active+')">'+(j.is_active?'⏸':'▶')+'</button> '+
        '<button class="btn bo bs" onclick="aJEdit('+j.id+')">✏️</button> '+
        '<button class="btn bo bs" onclick="aJDel('+j.id+')">🗑️</button></td></tr>';
    });
    h+='</table></div>';
    document.getElementById("aLContent").innerHTML=h;
  }).catch(function(){});
}

function aJForm(editJob){
  var j=editJob||{};
  var h='<div class="cd" id="aJForm" style="margin-bottom:12px">';
  h+='<div class="st">'+(j.id?'Edit Task':'New Task')+'</div>';
  h+='<div class="g2">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Name *</div><input class="in" id="aJName" value="'+esc(j.name||'')+'" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Type</div><select class="sl" id="aJType" style="width:100%"><option value="cron" '+(j.job_type=='cron'?'selected':'')+'>Cron</option><option value="interval" '+(j.job_type=='interval'?'selected':'')+'>Interval</option><option value="once" '+(j.job_type=='once'?'selected':'')+'>One-Time</option></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Cron Expression <span style="color:var(--dim)">Or Natural Language</span></div><input class="in" id="aJCron" value="'+esc(j.cron_expr||j.natural_expr||'')+'" placeholder="0 30 9 * * 1-5 或 Per Trading Day9:30" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Interval Seconds</div><input class="in" id="aJInterval" value="'+esc(j.interval_seconds||'')+'" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Priority</div><select class="sl" id="aJPriority" style="width:100%"><option value="critical" '+(j.priority=='critical'?'selected':'')+'>高(Critical)</option><option value="high" '+(j.priority=='high'?'selected':'')+'>高</option><option value="normal" '+(j.priority=='normal'?'selected':'')+'>中</option><option value="low" '+(j.priority=='low'?'selected':'')+'>低</option></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Agent Type</div><select class="sl" id="aJAgent" style="width:100%"><option value="system" '+(j.agent_type=='system'?'selected':'')+'>System Agent</option><option value="user" '+(j.agent_type=='user'?'selected':'')+'>User Agent</option></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Target Type</div><select class="sl" id="aJTarget" style="width:100%"><option value="workflow" '+(j.target_type=='workflow'?'selected':'')+'>Workflow</option><option value="api" '+(j.target_type=='api'?'selected':'')+'>API</option><option value="script" '+(j.target_type=='script'?'selected':'')+'>Script</option></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Timeout(秒)</div><input class="in" id="aJTimeout" value="'+esc(j.timeout_seconds||'300')+'" style="width:100%"></div>';
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Description</div><input class="in" id="aJDesc" value="'+esc(j.description||'')+'" style="width:100%"></div>';
  h+='</div><div style="margin-top:8px"><button class="btn bp" onclick="aJSave('+(j.id||'')+')">Save</button> <button class="btn bo" onclick="document.getElementById(\'aJForm\').remove();aLJobs()">Cancel</button></div></div>';
  return h;
}

function aJSave(id){
  var name=document.getElementById("aJName").value.trim();
  if(!name){showToast("Name is required","error");return}
  var cron=document.getElementById("aJCron").value.trim();
  var data={
    name:name,
    job_type:document.getElementById("aJType").value,
    cron_expr:cron,
    natural_expr:cron,
    interval_seconds:parseInt(document.getElementById("aJInterval").value)||0,
    priority:document.getElementById("aJPriority").value,
    agent_type:document.getElementById("aJAgent").value,
    target_type:document.getElementById("aJTarget").value,
    timeout_seconds:parseInt(document.getElementById("aJTimeout").value)||300,
    description:document.getElementById("aJDesc").value.trim()
  };
  var url="/admin/automation/jobs"+(id?"/"+id:"");
  var method=id?"PUT":"POST";
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Saved","success");aLJobs()}
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function aJToggle(id,active){
  fetch("/admin/automation/jobs/"+id+"/toggle",{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast(d.message||"Switched","success");aLJobs()}
    else{showToast(d.error||"Operation Failed","error")}
  }).catch(function(){});
}

function aJRun(id){
  fetch("/admin/automation/jobs/"+id+"/run",{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success)showToast("Task triggered","success");
    else showToast(d.error||"Trigger Failed","error");
  }).catch(function(){});
}

function aJEdit(id){
  console.log("aJEdit called with id:", id, typeof id);
  var j=null;
  for(var i=0;i<aJobs.length;i++){console.log("  aJobs["+i+"].id:", aJobs[i].id, typeof aJobs[i].id);if(aJobs[i].id===id){j=aJobs[i];break}}
  console.log("  found j:", j ? j.name : null);
  if(!j){showToast("Task not found","error");return}
  // Insert Form Above Table
  var h=aJForm(j);
  console.log("  form HTML length:", h.length);
  var el=document.getElementById("aLContent");
  console.log("  aLContent element:", el);
  if(el)el.insertAdjacentHTML("afterbegin",h);
  window.scrollTo(0,0);
}

function aJNew(){var h=aJForm();var el=document.getElementById("aLContent");if(el){el.insertAdjacentHTML("afterbegin",h);window.scrollTo(0,0)}}

function aJDel(id){
  if(!confirm("Delete this task?"))return;
  fetch("/admin/automation/jobs/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Deleted","success");aLJobs()}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){});
}

// ===== Workflow Management =====
var aWfs=[];
function aLWorkflows(){
  document.getElementById("aLContent").innerHTML='<div class="lo"><div class="s"></div>Loading Workflow...</div>';
  fetch("/admin/automation/workflows?limit=100",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    aWfs=d.data.workflows||[];
    var h='<div class="cd"><div class="st">🔧 Workflow Definition ('+d.data.total+')';
    h+=' <button class="btn bp bs" onclick="aWNew()" style="float:right">+ New</button></div>';
    h+='<table><tr><th>Name</th><th>Version</th><th>Agent</th><th>Nodes</th><th>Trigger</th><th>Status</th><th>Actions</th></tr>';
    if(!aWfs.length)h+='<tr><td colspan="7"><div class="em">No Workflow</div></td></tr>';
    else aWfs.forEach(function(w){
      var def=(typeof w.definition=='string')?JSON.parse(w.definition||'{}'):(w.definition||{});
      var nodes=def.nodes||[];
      var st=w.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Disable</span>';
      h+='<tr><td style="font-weight:600">'+esc(w.name)+'</td>';
      h+='<td>v'+w.version+'</td>';
      h+='<td>'+w.agent_type+'</td>';
      h+='<td>'+nodes.length+'</td>';
      h+='<td>'+(w.triggers&&w.triggers.length?w.triggers.map(function(t){return t.type}).join(","):'Manual')+'</td>';
      h+='<td>'+st+'</td>';
      h+='<td>'+
        '<button class="btn bp bs" onclick="aWRun('+w.id+')">▶ Run</button> '+
        '<button class="btn bo bs" onclick="aWEdit('+w.id+')">✏️</button> '+
        '<button class="btn bo bs" onclick="aWDel('+w.id+')">🗑️</button></td></tr>';
    });
    h+='</table></div>';
    document.getElementById("aLContent").innerHTML=h;
  }).catch(function(){});
}

function aWForm(editWf){
  var w=editWf||{};
  var def=(typeof w.definition=='string')?JSON.parse(w.definition||'{"nodes":[],"edges":[]}'):(w.definition||{nodes:[],edges:[]});
  var nodesTxt=JSON.stringify(def,null,2);
  var h='<div class="cd" id="aWForm" style="margin-bottom:12px">';
  h+='<div class="st">'+(w.id?'Edit Workflow':'New Workflow')+'</div>';
  h+='<div class="g2">';
  h+='<div><div style="font-size:11px;color:var(--dim)">Name *</div><input class="in" id="aWName" value="'+esc(w.name||'')+'" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Agent Type</div><select class="sl" id="aWAgent" style="width:100%"><option value="system" '+(w.agent_type=='system'?'selected':'')+'>System Agent</option><option value="user" '+(w.agent_type=='user'?'selected':'')+'>User Agent</option></select></div>';
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">Description</div><input class="in" id="aWDesc" value="'+esc(w.description||'')+'" style="width:100%"></div>';
  h+='<div style="grid-column:1/3"><div style="font-size:11px;color:var(--dim)">DAG Define (JSON) <span style="color:var(--dim)">Node+边</span></div>';
  h+='<textarea class="ta" id="aWDef" rows="15" style="font-family:monospace;font-size:11px;line-height:1.5">'+esc(nodesTxt)+'</textarea></div>';
  h+='<div style="grid-column:1/3;font-size:11px;color:var(--dim)">Node Type: ai_agent, data_collect, ai_process, condition, approve, publish, notify, wait, sub_workflow, market_check, http_request, script</div>';
  h+='</div><div style="margin-top:8px"><button class="btn bp" onclick="aWSave('+(w.id||'')+')">Save</button> <button class="btn bo" onclick="aWCloseForm()">Cancel</button></div></div>';
  return h;
}
function aWCloseForm(){document.getElementById("aWForm").remove();aLWorkflows()}
function aWNew(){var h=aWForm();document.getElementById("aLContent").insertAdjacentHTML("afterbegin",h);window.scrollTo(0,0);}

function aWSave(id){
  var name=document.getElementById("aWName").value.trim();
  if(!name){showToast("Name is required","error");return}
  var defText=document.getElementById("aWDef").value.trim();
  try{JSON.parse(defText)}catch(e){showToast("JSON Invalid Format: "+e.message,"error");return}
  var data={name:name,description:document.getElementById("aWDesc").value.trim(),agent_type:document.getElementById("aWAgent").value,definition:defText};
  var url="/admin/automation/workflows"+(id?"/"+id:"");
  var method=id?"PUT":"POST";
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Saved","success");aWCloseForm()}
    else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

function aWRun(id){
  fetch("/admin/automation/workflows/"+id+"/run",{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast(d.message||"Workflow Started","success");aLInstances()}
    else{showToast(d.error||"Start Failed","error")}
  }).catch(function(){});
}

function aWEdit(id){
  var w=null;
  for(var i=0;i<aWfs.length;i++){if(aWfs[i].id===id){w=aWfs[i];break}}
  if(!w){showToast("Workflow not found","error");return}
  var h=aWForm(w);
  document.getElementById("aLContent").insertAdjacentHTML("afterbegin",h);
  window.scrollTo(0,0);
}

function aWDel(id){
  if(!confirm("Delete this workflow?"))return;
  fetch("/admin/automation/workflows/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Deleted","success");aLWorkflows()}
    else{showToast(d.error||"Delete failed","error")}
  }).catch(function(){});
}

// ===== Execution History =====
var aInsts=[];
function aLInstances(){
  document.getElementById("aLContent").innerHTML='<div class="lo"><div class="s"></div>Loading Execution History...</div>';
  fetch("/admin/automation/instances?limit=50",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    aInsts=d.data.instances||[];
    var h='<div class="cd"><div class="st">📊 WorkflowExecution History ('+d.data.total+')</div>';
    h+='<table><tr><th>ID</th><th>Workflow</th><th>Trigger</th><th>Status</th><th>Duration</th><th>Start Time</th><th>Actions</th></tr>';
    if(!aInsts.length)h+='<tr><td colspan="7"><div class="em">No Execution Records</div></td></tr>';
    else aInsts.forEach(function(i){
      var stMap={'running':'<span class="bdg pd">Running</span>','completed':'<span class="bdg on">Complete</span>','failed':'<span class="bdg off">Failed</span>','cancelled':'<span class="bdg off">Cancelled</span>','timeout':'<span class="bdg off">Timeout</span>','paused':'<span class="bdg pd">Paused</span>'};
      var st=stMap[i.status]||i.status;
      h+='<tr><td>#'+i.id+'</td><td>'+(i.workflow_id||'')+'</td><td>'+i.trigger_type+'</td><td>'+st+'</td><td>'+(i.duration_ms?Math.round(i.duration_ms/1000)+'s':'-')+'</td><td style="font-size:11px">'+(i.created_at||'')+'</td>';
      h+='<td>';
      if(i.status=='running'||i.status=='paused'){
        h+='<button class="btn bo bs" onclick="aIPause('+i.id+',\''+i.status+'\')">'+(i.status=='paused'?'▶':'⏸')+'</button> ';
        h+='<button class="btn bo bs" onclick="aICancel('+i.id+')">🛑</button> ';
      }
      h+='<button class="btn bo bs" onclick="aIDetail('+i.id+')">📋</button></td></tr>';
    });
    h+='</table></div>';
    document.getElementById("aLContent").innerHTML=h;
  }).catch(function(){});
}

function aIPause(id,status){
  var action=status=='paused'?'resume':'pause';
  fetch("/admin/automation/instances/"+id+"/"+action,{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast(d.message,"success");aLInstances()}
    else showToast(d.error||"Operation Failed","error");
  }).catch(function(){});
}

function aICancel(id){
  if(!confirm("Cancel this workflow?"))return;
  fetch("/admin/automation/instances/"+id+"/cancel",{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Cancelled","success");aLInstances()}
    else showToast(d.error||"Cancel Failed","error");
  }).catch(function(){});
}

function aIDetail(id){
  fetch("/admin/automation/instances/"+id,{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var inst=d.data.instance;
    var nodes=d.data.nodes||[];
    var wfName=d.data.workflow_name||'Unknown';
    var h='<div class="modal-overlay" onclick="if(event.target==this)this.remove()"><div class="modal-box">';
    h+='<h3>📋 Workflow Execution #'+inst.id+' - '+esc(wfName)+'</h3>';
    h+='<div class="modal-meta"><span>Status: '+(inst.status||'-')+'</span><span>Trigger: '+inst.trigger_type+'</span><span>Duration: '+(inst.duration_ms?Math.round(inst.duration_ms/1000)+'s':'-')+'</span></div>';
    h+='<div class="modal-meta"><span>Start: '+(inst.started_at||'-')+'</span><span>End: '+(inst.finished_at||'-')+'</span></div>';
    if(inst.error_message)h+='<div class="modal-body" style="color:#f85149;margin-bottom:12px">❌ '+esc(inst.error_message)+'</div>';
    // Node List
    h+='<div class="st">Node Execution Details</div><table><tr><th>Node</th><th>Type</th><th>Status</th><th>Duration</th><th>Error</th></tr>';
    nodes.forEach(function(n){
      var s=n.status=='completed'?'<span class="bdg on">Complete</span>':n.status=='running'?'<span class="bdg pd">Running</span>':n.status=='failed'?'<span class="bdg off">Failed</span>':n.status=='waiting_approval'?'<span class="bdg pd">Pending Approval</span>':'<span class="bdg off">'+n.status+'</span>';
      h+='<tr><td>'+esc(n.node_name||n.node_id)+'</td><td>'+n.node_type+'</td><td>'+s+'</td><td>'+(n.duration_ms?Math.round(n.duration_ms/1000)+'s':'-')+'</td><td style="color:#f85149;font-size:11px">'+(n.error_message?esc(n.error_message).slice(0,50):'')+'</td></tr>';
    });
    h+='</table>';
    h+='<div style="margin-top:12px"><button class="btn bo" onclick="this.closest(\'.modal-overlay\').remove()">Close</button></div>';
    h+='</div></div>';
    document.body.insertAdjacentHTML("beforeend",h);
  }).catch(function(){});
}

// ===== Log =====
function aLLogs(){
  document.getElementById("aLContent").innerHTML='<div class="lo"><div class="s"></div>Load Logs...</div>';
  fetch("/admin/automation/logs?limit=100",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data)return;
    var logs=d.data.logs||[];
    var h='<div class="cd"><div class="st">📄 Execution Log ('+d.data.total+')</div>';
    h+='<table><tr><th>Type</th><th>Level</th><th>Message</th><th>Time</th></tr>';
    if(!logs.length)h+='<tr><td colspan="4"><div class="em">No Logs Yet</div></td></tr>';
    else logs.forEach(function(l){
      var lvlMap={info:'<span class="bdg on">info</span>',warn:'<span class="bdg pd">warn</span>',error:'<span class="bdg off">error</span>',fatal:'<span class="bdg off" style="background:rgba(248,81,73,.2)">fatal</span>'};
      h+='<tr><td>'+l.source_type+'</td><td>'+(lvlMap[l.level]||l.level)+'</td><td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(l.message)+'</td><td style="font-size:11px">'+l.created_at+'</td></tr>';
    });
    h+='</table></div>';
    document.getElementById("aLContent").innerHTML=h;
  }).catch(function(){});
}

// ============================================================
// Admin Management — l_admins (2026-05-10 v2 - inline expand)
// ============================================================
var adminsData = [];
var admMe = null;  // current admin's own data


window.l_admins = function() {
  document.getElementById("pt").textContent="Admin Management";
  var h = '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">';
  h += '<div style="font-size:13px;color:var(--muted)"><strong id="admStats">-</strong> Admin(s)</div>';
  h += '<div style="display:flex;gap:8px">';
  h += '<button class="btn bp" id="admAddBtn" onclick="admToggleAdd()" style="display:none">+ Add Admin</button>';
  h += '<button class="btn bo" onclick="admFocusSelf()">👤 My Settings</button>';
  h += '</div></div>';
  // Add admin form (hidden by default)
  h += '<div id="admAddForm" style="display:none" class="cd" style="margin-bottom:12px">';
  h += '<div class="st">Add Admin</div>';
  h += '<div class="g2">';
  h += '<div><div style="font-size:11px;color:var(--dim);margin-bottom:4px">Phone No.</div><input class="in" id="admAddPhone" placeholder="Enter phone number" style="width:100%"></div>';
  h += '<div><div style="font-size:11px;color:var(--dim);margin-bottom:4px">Role</div><select class="sl" id="admAddRole" style="width:100%"><option value="admin">Admin</option><option value="operator">Operations</option></select></div>';
  h += '<div style="grid-column:1/3;display:flex;flex-wrap:wrap;gap:8px;margin-top:4px" id="admAddPermsBody">';
  [['users','User Management'],['content','Content Management'],['finance','Financial Management'],['system','System Settings'],['matrix','AgentMatrix']].forEach(function(p){
    h += '<label style="font-size:12px;cursor:pointer;display:flex;align-items:center;gap:4px"><input type="checkbox" id="admAddPerm_'+p[0]+'" checked> '+p[1]+'</label>';
  });
  h += '</div>';
  h += '<div><div style="font-size:11px;color:var(--dim);margin-bottom:4px">Real Name</div><input class="in" id="admAddName" placeholder="Optional" style="width:100%"></div>';
  h += '<div><div style="font-size:11px;color:var(--dim);margin-bottom:4px">Notes</div><input class="in" id="admAddNotes" placeholder="Optional" style="width:100%"></div>';
  h += '</div>';
  h += '<div style="margin-top:8px"><button class="btn bp" onclick="admDoAdd()">Confirm Addition</button> <button class="btn bo" onclick="admToggleAdd()">Cancel</button></div>';
  h += '</div>';
  // Card list
  h += '<div id="admList"><div class="lo"><div class="s"></div></div></div>';
  document.getElementById("mc").innerHTML = h;
  admLoad();
};

function admLoad() {
  fetch("/admin/admins/me", {headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success)return;
      admMe = d.data;
      if(admMe.role === "super_admin") {
        var btn = document.getElementById("admAddBtn");
        if(btn) btn.style.display = "inline-block";
      }
    }).catch(function(){});
  
  fetch("/admin/admins", {headers:{"Authorization":"Bearer "+T}})
    .then(function(r){
      if(r.status === 403) return null;
      return r.json();
    })
    .then(function(d){
      if(d && d.success) {
        adminsData = d.data || [];
        admRender();
      } else {
        if(admMe) {
          adminsData = [admMe];
          admRender();
        }
      }
    }).catch(function(){});
}

function admRender() {
  document.getElementById("admStats").textContent = adminsData.length;
  var h = '';
  adminsData.forEach(function(a){
    var expanded = (a._expanded) ? true : false;
    // ── Card container ──
    h += '<div class="cd" style="margin-bottom:12px" id="admCard_'+a.id+'">';
    // ── Summary row ──
    h += '<div style="display:flex;align-items:center;gap:14px">';
    // Avatar
    var avatarHtml = '';
    if(a.avatar_url) {
      avatarHtml = '<img src="'+esc(a.avatar_url)+'" style="width:46px;height:46px;border-radius:50%;object-fit:cover;flex-shrink:0;cursor:pointer" onclick="admUploadAvatar('+a.id+')" title="Click to Change Avatar">';
    } else {
      avatarHtml = '<div style="width:46px;height:46px;flex-shrink:0;cursor:pointer" onclick="admUploadAvatar('+a.id+')" title="Click to Upload Avatar">'+dicebearAvatar(a.real_name||a.nickname||a.phone||'A','initials',46)+'</div>';
    }
    h += avatarHtml;
    // Hidden file input for avatar upload (must exist even when row is collapsed)
    h += '<input type="file" id="admFile_'+a.id+'" accept="image/*" style="display:none" onchange="admUploadAvatarFile('+a.id+',this)">';
    // Name + role + info
    h += '<div style="flex:1;min-width:0">';
    h += '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">';
    h += '<strong style="font-size:14px">'+esc(a.real_name||a.nickname||'Admin')+'</strong>';
    if(a.role === 'super_admin') h += '<span class="bdg" style="background:#d4a000;color:#000;font-size:10px">Super Admin</span>';
    else if(a.role === 'admin') h += '<span class="bdg on" style="font-size:10px">Admin</span>';
    else h += '<span class="bdg pd" style="font-size:10px">Operations</span>';
    h += '</div>';
    h += '<div style="font-size:12px;color:var(--muted);margin-top:2px">'+esc(a.phone||'')+' · '+(a.email||'-')+' · Create '+(a.admin_since||a.registered_at||'').slice(0,10)+'</div>';
    // Permission badges
    var perms = a.permissions||[];
    if(perms.length) {
      var permMap = {users:'User',content:'Content',finance:'Finance',system:'System',matrix:'Matrix',admins:'Management'};
      h += '<div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">';
      perms.forEach(function(p){
        var label = permMap[p]||p;
        h += '<span style="font-size:10px;background:rgba(0,212,170,.1);color:var(--accent);padding:1px 6px;border-radius:3px">'+label+'</span>';
      });
      h += '</div>';
    }
    h += '</div>';
    // Right side: last login + buttons
    h += '<div style="text-align:right;flex-shrink:0">';
    if(a.last_login) h += '<div style="font-size:10px;color:var(--dim)">Last Login<br>'+(a.last_login||'').slice(0,10)+'</div>';
    h += '<div style="margin-top:6px;display:flex;gap:4px;justify-content:flex-end">';
    h += '<button class="btn bo bs" onclick="admToggleExpand('+a.id+')">'+(expanded?'Collapse':'Edit')+'</button>';
    if(a.role !== 'super_admin') {
      h += '<button class="btn bo bs" onclick="admConfirmRemove('+a.id+')" style="color:#f85149">Remove</button>';
    }
    h += '</div></div></div>';
    // ── Expanded edit area ──
    if(expanded) {
      h += '<div style="border-top:1px solid var(--border);margin-top:12px;padding-top:12px">';
      // Avatar upload hint
      h += '<div style="font-size:11px;color:var(--dim);margin-bottom:10px">Click Avatar to Upload New Avatar（≤800×800，≤1MB）</div>';
      // Two-column form
      var isSelf = (admMe && admMe.id === a.id);
      h += '<div class="g2">';
      // Left column - basic info
      h += '<div>';
      h += '<div style="font-size:11px;color:var(--dim);margin-bottom:4px">Real Name</div>';
      h += '<input class="in" id="admEdit_'+a.id+'_realName" value="'+esc(a.real_name||'')+'" style="width:100%">';
      h += '</div>';
      h += '<div>';
      h += '<div style="font-size:11px;color:var(--dim);margin-bottom:4px">Internal Contact Phone</div>';
      h += '<input class="in" id="admEdit_'+a.id+'_intPhone" value="'+esc(a.internal_phone||'')+'" style="width:100%">';
      h += '</div>';
      h += '<div>';
      h += '<div style="font-size:11px;color:var(--dim);margin-bottom:4px">Internal Contact Email</div>';
      h += '<input class="in" id="admEdit_'+a.id+'_intEmail" value="'+esc(a.internal_email||'')+'" style="width:100%">';
      h += '</div>';
      h += '<div>';
      h += '<div style="font-size:11px;color:var(--dim);margin-bottom:4px">Notes</div>';
      h += '<input class="in" id="admEdit_'+a.id+'_notes" value="'+esc(a.notes||'')+'" style="width:100%">';
      h += '</div>';
      // Role (only for super_admin editing others)
      if(!isSelf) {
        h += '<div>';
        h += '<div style="font-size:11px;color:var(--dim);margin-bottom:4px">Role</div>';
        h += '<select class="sl" id="admEdit_'+a.id+'_role" style="width:100%">';
        h += '<option value="super_admin" '+(a.role==='super_admin'?'selected':'')+'>Super Admin</option>';
        h += '<option value="admin" '+(a.role==='admin'?'selected':'')+'>Admin</option>';
        h += '<option value="operator" '+(a.role==='operator'?'selected':'')+'>Operations</option>';
        h += '</select></div>';
      }
      // Permissions (not for super_admin)
      if(!isSelf && a.role !== 'super_admin') {
        h += '<div style="grid-column:1/3">';
        h += '<div style="font-size:11px;color:var(--dim);margin-bottom:4px">Permissions</div>';
        h += '<div style="display:flex;flex-wrap:wrap;gap:8px">';
        var curPerms = a.permissions||[];
        [['users','User Management'],['content','Content Management'],['finance','Financial Management'],['system','System Settings'],['matrix','AgentMatrix']].forEach(function(p){
          var checked = curPerms.indexOf(p[0])>=0?'checked':'';
          h += '<label style="font-size:12px;cursor:pointer;display:flex;align-items:center;gap:4px">';
          h += '<input type="checkbox" id="admEdit_'+a.id+'_perm_'+p[0]+'" '+checked+'> '+p[1]+'</label>';
        });
        h += '</div></div>';
      }
      h += '</div>'; // end g2
      
      // Password change — SMS CAPTCHA Method（Two Rows：New Password+Confirm，Verification Code）
      h += '<div style="margin-top:12px;padding:10px;background:var(--bg);border-radius:6px">';
      h += '<div style="font-size:12px;font-weight:600;margin-bottom:6px">Change Password</div>';
      h += '<div style="font-size:11px;color:var(--rose);margin-bottom:6px">Password Rules：At Least10位，Must Include Uppercase、Lowercase、Digital、At Least One Special Character3种</div>';
      h += '<div style="display:flex;gap:8px">';
      h += '<div style="display:flex;flex:1;gap:0;align-items:stretch">';
      h += '<input class="in" id="admEdit_'+a.id+'_pwd" type="password" placeholder="New Password" style="flex:1;border-top-right-radius:0;border-bottom-right-radius:0">';
      h += '<button class="btn bs" id="admEdit_'+a.id+'_pwdBtn" onclick="admTogglePwd('+a.id+',\'pwd\')" style="border-radius:0 8px 8px 0;border-left:none;white-space:nowrap;font-size:12px" title="Show/Hide Password">👁</button>';
      h += '</div>';
      h += '<div style="display:flex;flex:1;gap:0;align-items:stretch">';
      h += '<input class="in" id="admEdit_'+a.id+'_pwdConfirm" type="password" placeholder="Confirm New Password" style="flex:1;border-top-right-radius:0;border-bottom-right-radius:0">';
      h += '<button class="btn bs" id="admEdit_'+a.id+'_pwdConfirmBtn" onclick="admTogglePwd('+a.id+',\'pwdConfirm\')" style="border-radius:0 8px 8px 0;border-left:none;white-space:nowrap;font-size:12px" title="Show/Hide Password">👁</button>';
      h += '</div>';
      h += '</div>';
      h += '<div style="margin-top:6px;display:flex;gap:8px;align-items:center">';
      h += '<span style="font-size:11px;color:var(--dim);flex-shrink:0">Phone Verification</span>';
      h += '<span style="font-size:12px;font-weight:500">'+esc(a.phone)+'</span>';
      h += '<button class="btn bo bs" id="admCodeBtn_'+a.id+'" onclick="admSendCode('+a.id+')">Send Captcha</button>';
      h += '<input class="in" id="admEdit_'+a.id+'_code" placeholder="6-digit Captcha" maxlength="6" style="flex:1">';
      h += '</div>';
      h += '</div>';
      
      // Action buttons
      h += '<div style="margin-top:12px;display:flex;gap:8px">';
      h += '<button class="btn bp" onclick="admSaveEdit('+a.id+')">Save</button>';
      h += '<button class="btn bo" onclick="admToggleExpand('+a.id+')">Cancel</button>';
      if(isSelf) {
        h += '<button class="btn bo" style="margin-left:auto" onclick="admChangePhone('+a.id+')">📱 Change Phone No.</button>';
      }
      h += '</div>';
      
      // Audit log
      if(a.recent_logs && a.recent_logs.length) {
        h += '<div style="margin-top:12px">';
        h += '<div style="font-size:11px;color:var(--dim);margin-bottom:4px">Recent Actions</div>';
        h += '<div style="max-height:100px;overflow-y:auto;font-size:11px;color:var(--muted);border:1px solid var(--border);border-radius:4px;padding:4px">';
        a.recent_logs.slice(0,10).forEach(function(l){
          h += '<div style="padding:2px 4px">';
          h += '<span style="color:var(--dim)">'+(l.created_at||'').slice(0,16)+'</span> ';
          h += esc(l.action)+' '+(l.detail?esc(l.detail):'');
          h += '</div>';
        });
        h += '</div></div>';
      }
      
      h += '</div>'; // end expanded area
    }
    h += '</div>'; // end cd
  });
  document.getElementById("admList").innerHTML = h;
}

// ── Toggle card expand/collapse ──
function admToggleExpand(uid) {
  for(var i=0;i<adminsData.length;i++) {
    if(adminsData[i].id === uid) {
      adminsData[i]._expanded = !adminsData[i]._expanded;
      // Fetch detail data if expanding and not already loaded
      if(adminsData[i]._expanded && !adminsData[i].recent_logs) {
        fetch("/admin/admins/"+uid, {headers:{"Authorization":"Bearer "+T}})
          .then(function(r){return r.json()})
          .then(function(d){
            if(d && d.success) {
              var detail = d.data;
              for(var j=0;j<adminsData.length;j++) {
                if(adminsData[j].id === detail.id) {
                  adminsData[j].recent_logs = detail.recent_logs;
                  adminsData[j].internal_email = detail.internal_email;
                  adminsData[j].internal_phone = detail.internal_phone;
                  adminsData[j].real_name = detail.real_name;
                  adminsData[j].notes = detail.notes;
                  adminsData[j].permissions = detail.permissions;
                  break;
                }
              }
              admRender();
            }
          }).catch(function(){});
      } else {
        admRender();
      }
      break;
    }
  }
}

// ── Avatar upload ──
function admUploadAvatar(uid) {
  // For self or others? For now only self can upload their own
  if(!admMe || admMe.id !== uid) {
    showToast("Can only edit your own avatar","error");
    return;
  }
  var fileInput = document.getElementById("admFile_"+uid);
  if(fileInput) fileInput.click();
}

function admUploadAvatarFile(uid, input) {
  if(!input.files || !input.files[0]) return;
  var file = input.files[0];
  // Validate size
  if(file.size > 1024 * 1024) {
    showToast("Image Must Not Exceed 1MB（Approx. "+(file.size/1024).toFixed(0)+"KB）","error");
    return;
  }
  // Validate dimensions
  var img = new Image();
  img.onload = function() {
    if(img.width > 800 || img.height > 800) {
      showToast("Image Size Must Not Exceed 800×800（Current "+img.width+"×"+img.height+"）","error");
      return;
    }
    // Upload
    var formData = new FormData();
    formData.append("avatar", file);
    fetch("/admin/admins/me/avatar", {
      method:"POST",
      headers:{"Authorization":"Bearer "+T},
      body:formData
    }).then(function(r){return r.json()}).then(function(d){
      if(d.success) {
        showToast("Avatar updated","success");
        // Update local data and re-render
        for(var i=0;i<adminsData.length;i++) {
          if(adminsData[i].id === uid) {
            adminsData[i].avatar_url = d.data.avatar_url;
            break;
          }
        }
        admRender();
      } else {
        showToast(d.error||"Upload failed","error");
      }
    }).catch(function(){showToast("Upload request failed","error")});
  };
  img.onerror = function() { showToast("Cannot load image","error"); };
  img.src = URL.createObjectURL(file);
}

// ── Add admin (super_admin only) ──
function admToggleAdd() {
  var el = document.getElementById("admAddForm");
  if(el) el.style.display = el.style.display==="none"?"block":"none";
}

function admDoAdd() {
  var phone = document.getElementById("admAddPhone").value.trim();
  if(!phone) { showToast("Enter phone number","error"); return; }
  var perms = [];
  ['users','content','finance','system','matrix'].forEach(function(k){
    var el = document.getElementById("admAddPerm_"+k);
    if(el && el.checked) perms.push(k);
  });
  var data = {
    phone: phone,
    role: document.getElementById("admAddRole").value,
    permissions: perms,
    real_name: document.getElementById("admAddName").value.trim(),
    notes: document.getElementById("admAddNotes").value.trim()
  };
  fetch("/admin/admins", {method:"POST", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify(data)})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success) { showToast(d.message,"success"); admToggleAdd(); admLoad(); }
      else { showToast(d.error||"Add Failed","error"); }
    }).catch(function(){showToast("Request Failed","error")});
}

// ── Save edit ──
function admSaveEdit(uid) {
  var data = {};
  var el, val;
  
  el = document.getElementById("admEdit_"+uid+"_realName");
  if(el) data.real_name = el.value.trim();
  el = document.getElementById("admEdit_"+uid+"_intPhone");
  if(el) data.internal_phone = el.value.trim();
  el = document.getElementById("admEdit_"+uid+"_intEmail");
  if(el) data.internal_email = el.value.trim();
  el = document.getElementById("admEdit_"+uid+"_notes");
  if(el) data.notes = el.value.trim();
  
  // Role
  var isSelf = (admMe && admMe.id === uid);
  if(!isSelf) {
    el = document.getElementById("admEdit_"+uid+"_role");
    if(el) data.role = el.value;
    
    // Permissions
    var perms = [];
    ['users','content','finance','system','matrix'].forEach(function(k){
      var cb = document.getElementById("admEdit_"+uid+"_perm_"+k);
      if(cb && cb.checked) perms.push(k);
    });
    if(perms.length) data.permissions = perms;
  }
  
  // Password — New Password+Confirm+SMS Code
  var pwdEl = document.getElementById("admEdit_"+uid+"_pwd");
  var confirmEl = document.getElementById("admEdit_"+uid+"_pwdConfirm");
  var codeEl = document.getElementById("admEdit_"+uid+"_code");
  if(pwdEl && pwdEl.value.trim()) {
    if(confirmEl && pwdEl.value.trim() !== confirmEl.value.trim()) {
      showToast("Passwords do not match","error"); return;
    }
    data.password = pwdEl.value.trim();
    if(codeEl && codeEl.value.trim()) data.code = codeEl.value.trim();
    else { showToast("Enter SMS code","error"); return; }
  }
  
  // Send to When Password Data Exists /admin/admins/<uid>，纯 profile Customize /admin/admins/me
  var hasPwd = data.password !== undefined;
  var url = (isSelf && !hasPwd) ? "/admin/admins/me" : "/admin/admins/"+uid;
  fetch(url, {method:"PUT", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify(data)})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success) { showToast(d.message||"Updated","success"); admLoad(); }
      else { showToast(d.error||"Save failed","error"); }
    }).catch(function(){showToast("Request Failed","error")});
}

// ── Send SMS code for password change ──
function admSendCode(uid) {
  // Get Phone from Loaded Data（Avoid Call /admin/admins/<uid> 需 super_admin Permissions）
  var phone = '';
  for(var i=0;i<adminsData.length;i++) {
    if(adminsData[i].id === uid) { phone = adminsData[i].phone; break; }
  }
  if(admMe && admMe.id === uid && !phone) phone = admMe.phone;
  if(!phone){showToast("This admin has no phone bound","error");return}
  // Must Include Authorization header，Otherwise Backend Requires CAPTCHA
  fetch("/auth/sms/send", {method:"POST", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify({phone:phone, purpose:"modify_password"})})
        .then(function(r){return r.json()})
        .then(function(d2){
          if(d2.success) showToast("Captcha Sent To "+phone,"success");
          else showToast(d2.error||"Failed to send","error");
        }).catch(function(){showToast("Request Failed","error")});
}

// ── Toggle password visibility in admin edit ──
function admTogglePwd(uid, suffix) {
  var el = document.getElementById("admEdit_"+uid+"_"+suffix);
  var btn = document.getElementById("admEdit_"+uid+"_"+suffix+"Btn");
  if (!el || !btn) return;
  if (el.type === "password") { el.type = "text"; btn.textContent = "🙈"; }
  else { el.type = "password"; btn.textContent = "👁"; }
}

// ── Remove admin ──
function admConfirmRemove(uid) {
  fetch("/admin/admins/"+uid, {headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success){showToast("Failed to get info","error");return}
      var name = d.data.real_name||d.data.nickname||d.data.phone||"This Admin";
      if(!confirm("Confirm "+name+" Downgrade to Regular User？")) return;
      fetch("/admin/admins/"+uid, {method:"DELETE", headers:{"Authorization":"Bearer "+T}})
        .then(function(r2){return r2.json()})
        .then(function(d2){
          if(d2.success) { showToast(d2.message,"success"); admLoad(); }
          else { showToast(d2.error||"Operation Failed","error"); }
        }).catch(function(){showToast("Request Failed","error")});
    }).catch(function(){showToast("Request Failed","error")});
}

// ── Focus own card ──
function admFocusSelf() {
  if(!admMe) { showToast("Loading...",""); return; }
  var found = false;
  for(var i=0;i<adminsData.length;i++) {
    if(adminsData[i].id === admMe.id) {
      if(!adminsData[i]._expanded) {
        adminsData[i]._expanded = true;
        // Fetch detail
        fetch("/admin/admins/"+admMe.id, {headers:{"Authorization":"Bearer "+T}})
          .then(function(r){return r.json()})
          .then(function(d){
            if(d && d.success) {
              var detail = d.data;
              for(var j=0;j<adminsData.length;j++) {
                if(adminsData[j].id === detail.id) {
                  adminsData[j].recent_logs = detail.recent_logs;
                  adminsData[j].internal_email = detail.internal_email;
                  adminsData[j].internal_phone = detail.internal_phone;
                  adminsData[j].real_name = detail.real_name;
                  adminsData[j].notes = detail.notes;
                  adminsData[j].permissions = detail.permissions;
                  break;
                }
              }
              admRender();
            }
          }).catch(function(){});
      }
      admRender();
      found = true;
      break;
    }
  }
  if(!found) {
    adminsData = [admMe];
    adminsData[0]._expanded = true;
    admRender();
  }
  // Scroll to top
  window.scrollTo(0, 0);
}

// ── Change phone (self-service) ──
function admChangePhone(uid) {
  if(!confirm("Changing phone will send SMS to new number. Continue?")) return;
  var newPhone = prompt("Enter New Phone No.：");
  if(!newPhone || !/^1\\d{10}$/.test(newPhone.replace(/\\D/g,''))) {
    showToast("Enter a valid phone number","error");
    return;
  }
  newPhone = newPhone.replace(/\\D/g,'');
  // Send code to new phone
  fetch("/auth/sms/send", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({phone:newPhone, purpose:"change_phone"})})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success) {
        var code = prompt("Captcha Sent To "+newPhone+"，Please enter：");
        if(!code) return;
        fetch("/admin/admins/me/phone", {method:"PUT", headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"}, body:JSON.stringify({phone:newPhone, code:code})})
          .then(function(r2){return r2.json()})
          .then(function(d2){
            if(d2.success) { showToast("Phone updated, please login again","success"); setTimeout(function(){logout()},1500); }
            else { showToast(d2.error||"Modification Failed","error"); }
          }).catch(function(){showToast("Request Failed","error")});
      } else {
        showToast(d.error||"Send Captcha Failed","error");
      }
    }).catch(function(){showToast("Request Failed","error")});
}



window.l_themes=function(){
  document.getElementById("pt").textContent="Template Management";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Load Theme List...</div>';

  Promise.all([
    fetch("/admin/themes",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}),
    fetch("/admin/themes/sites",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()})
  ]).then(function(results){
    var themes=results[0],sites=results[1];
    if(!themes.success||!sites.success){mc.innerHTML='<div class="empty-state">Load failed</div>';return}
    renderThemeGrid(mc,themes.data,sites.data);
  }).catch(function(e){
    mc.innerHTML='<div class="empty-state">Load failed: '+esc(e.message)+'</div>';
  });
};

function themeInstall(){
  var fi=document.getElementById("themeFileInput");
  if(fi)fi.click();
}
function themeDoInstall(el){
  var f=el.files[0];
  if(!f)return;
  var fd=new FormData();
  fd.append("file",f);
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Installing...</div>';
  fetch("/admin/themes/install",{method:"POST",headers:{"Authorization":"Bearer "+T},body:fd})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Install Success: "+d.theme.name,"success");l_themes()}
      else{showToast(d.error||"Install Failed","error");l_themes()}
    }).catch(function(){showToast("Network error","error");l_themes()});
}
function themeActivate(themeId,themeName){
  var siteKey=prompt("Select Target Site:\n\nmain = Main Site\nplatform = User Dashboard\nadmin = Admin Panel","admin");
  if(!siteKey)return;
  var keys=["main","platform","admin"];
  if(keys.indexOf(siteKey)===-1){showToast("Invalid site","error");return}
  fetch("/admin/themes/sites",{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({site_key:siteKey,theme_id:themeId})
  }).then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast(themeName+" → "+siteKey+" Enabled","success");l_themes()}
      else{showToast(d.error||"Switch Failed","error")}
    }).catch(function(){showToast("Network error","error")});
}
function themeActivateDefault(siteKey){
  if(!siteKey)return;
  fetch("/admin/themes/sites",{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({site_key:siteKey,theme_id:null})
  }).then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Site "+siteKey+" Restored Default Theme","success");l_themes()}
      else{showToast(d.error||"Switch Failed","error")}
    }).catch(function(){showToast("Network error","error")});
}
function themeDelete(themeId,themeName,themeSlug){
  if(themeSlug==="default"){showToast("Cannot delete default theme","error");return}
  if(!confirm("Confirm Theme Uninstall\""+themeName+"\"吗？\n\nSites using this theme will auto-restore Default Theme。"))return;
  fetch("/admin/themes/"+themeId,{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Uninstalled","success");l_themes()}
      else{showToast(d.error||"Delete failed","error")}
    }).catch(function(){showToast("Network error","error")});
}
function themePreview(thumbnailUrl){
  if(!thumbnailUrl)return;
  window.open(thumbnailUrl,"_blank");
}
function renderThemeGrid(mc,themes,sites){
  var siteMap={};
  sites.forEach(function(s){siteMap[s.site_key]=s});
  var h='';
  h+='<div class="cfg-section">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">';
  h+='<h3 class="cfg-section-title" style="margin:0">Theme Installed ('+themes.length+')</h3>';
  h+='<button class="btn bp" onclick="themeInstall()">+ Install Theme</button>';
  h+='</div>';
  h+='<input type="file" id="themeFileInput" accept=".zip" style="display:none" onchange="themeDoInstall(this)">';
  h+='<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px">';
  themes.forEach(function(t){
    var activeSites=[];
    for(var k in siteMap){if(siteMap[k].theme_id===t.id)activeSites.push(siteMap[k].label)}
    var isDefault=t.slug==="default";
    h+='<div class="glass-card" style="padding:16px;display:flex;flex-direction:column;gap:12px">';
    h+='<div style="background:var(--bg-card);border-radius:8px;height:140px;overflow:hidden;display:flex;align-items:center;justify-content:center;cursor:pointer" onclick="themePreview(\''+escAttr(t.thumbnail||'')+'\')">';
    h+='<img src="'+escAttr(t.thumbnail||'')+'" alt="'+escAttr(t.name)+'" style="width:100%;height:100%;object-fit:cover" onerror="this.style.display=\'none\';this.parentElement.innerHTML=\'<div style=color:var(--text-muted);font-size:13px>No Preview</div>\'">';
    h+='</div>';
    h+='<div>'
    h+='<div style="font-weight:600;font-size:14px;color:var(--text)">'+esc(t.name)+'</div>';
    h+='<div style="font-size:11px;color:var(--text-muted);margin-top:2px">v'+esc(t.version)+(t.author?' · '+esc(t.author):'')+(isDefault?' · Built-in':'')+'</div>';
    if(t.industry)h+='<span style="display:inline-block;margin-top:6px;padding:2px 8px;border-radius:4px;font-size:10px;background:var(--bg-glass);color:var(--blue);border:1px solid var(--border)">'+esc(t.industry)+'</span>';
    h+='</div>';
    if(activeSites.length>0){
      h+='<div style="font-size:11px;color:var(--text-dim)">Enabled: '+activeSites.join(" · ")+'</div>';
    }
    h+='<div style="display:flex;gap:8px;margin-top:auto">';
    if(!isDefault){
      h+='<select style="flex:1;padding:6px 8px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:6px;font-size:12px" onchange="var v=this.value;this.value=\'\';if(v===\'default\')themeActivateDefault(\''+siteMap[Object.keys(siteMap)[0]]?siteMap[Object.keys(siteMap)[0]].site_key:''+'\');else themeActivate('+t.id+',\''+escAttr(t.name)+'\',v)">';
      h+='<option value="">Enabled ▼</option>';
      h+='<option value="default">Restore Default</option>';
      sites.forEach(function(s){
        var sel=siteMap[s.site_key]&&siteMap[s.site_key].theme_id===t.id?' ✓':'';
        h+='<option value="'+escAttr(s.site_key)+'">'+esc(s.label)+sel+'</option>';
      });
      h+='</select>';
    }
    h+='<button class="btn" style="padding:6px 10px;font-size:11px" onclick="themePreview(\''+escAttr(t.thumbnail||'')+'\')">Preview</button>';
    if(!isDefault)h+='<button class="btn" style="padding:6px 10px;font-size:11px;color:var(--rose)" onclick="themeDelete('+t.id+',\''+escAttr(t.name)+'\',\''+escAttr(t.slug)+'\')">Delete</button>';
    h+='</div></div>';
  });
  h+='</div>';
  if(themes.length===0)h+='<div class="empty-state">No Installed Theme<br><br><button class="btn bp" onclick="themeInstall()">Install First Theme</button></div>';
  h+='</div>';
  mc.innerHTML=h;
}

// ════════════════════════════════════════════════════════
// Sub-site Nav Management (header_nav)
// ════════════════════════════════════════════════════════

window.l_headernav=function(){
  document.getElementById("pt").textContent="Sub-site Navigation";
  var mc=document.getElementById("mc");
  var currentSite='platform';
  renderHeaderNav(mc,currentSite);
};

function renderHeaderNav(mc,site){
  fetch("/admin/header-nav?site="+site,{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success){mc.innerHTML='<div class="em">Load failed: '+esc(d.error||'')+'</div>';return}
      var items=d.data||[];
      var h='';
      // Switch Site
      h+='<div style="display:flex;gap:8px;margin-bottom:20px">';
      h+='<button class="btn '+(site==='platform'?'bp':'')+'" onclick="headerNavSwitch(\'platform\')">🌐 Portal</button>';
      // 🏘 Community Offline
      h+='<button class="btn '+(site==='trademind'?'bp':'')+'" onclick="headerNavSwitch(\'trademind\')">📈 TradeMind</button>';
      h+='</div>';
      // Add Button
      h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">';
      h+='<span style="font-size:13px;color:var(--text-muted)">共 '+items.length+' Links</span>';
      h+='<button class="btn bp" onclick="headerNavAdd(\''+site+'\')">+ Add Link</button>';
      h+='</div>';
      // List
      if(items.length===0){
        h+='<div class="empty-state">No Nav Links<br><br><button class="btn bp" onclick="headerNavAdd(\''+site+'\')">Add First Links</button></div>';
      } else {
        h+='<table style="width:100%;font-size:13px">';
        h+='<tr><th style="text-align:left;padding:8px 12px;color:var(--text-muted);border-bottom:1px solid var(--border)">Title</th><th style="text-align:left;padding:8px 12px;color:var(--text-muted);border-bottom:1px solid var(--border)">URL</th><th style="text-align:center;padding:8px 12px;color:var(--text-muted);border-bottom:1px solid var(--border)">Sort</th><th style="text-align:center;padding:8px 12px;color:var(--text-muted);border-bottom:1px solid var(--border)">Status</th><th style="text-align:center;padding:8px 12px;color:var(--text-muted);border-bottom:1px solid var(--border)">Actions</th></tr>';
        items.forEach(function(item,i){
          var statusBg=item.is_enabled?'var(--green)':'var(--rose)';
          var statusText=item.is_enabled?'Enabled':'Disable';
          h+='<tr>';
          h+='<td style="padding:10px 12px;border-bottom:1px solid var(--border)">'+esc(item.title)+'</td>';
          h+='<td style="padding:10px 12px;border-bottom:1px solid var(--border);color:var(--text-dim);max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(item.url)+'</td>';
          h+='<td style="padding:10px 12px;border-bottom:1px solid var(--border);text-align:center;color:var(--text-muted);font-size:11px">'+(item.sort_order||0)+'</td>';
          h+='<td style="padding:10px 12px;border-bottom:1px solid var(--border);text-align:center"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:'+statusBg+'" title="'+statusText+'"></span></td>';
          h+='<td style="padding:10px 12px;border-bottom:1px solid var(--border);text-align:center">';
          h+='<button class="btn" style="padding:4px 10px;font-size:11px;margin-right:4px" onclick="headerNavEdit('+item.id+',\''+escAttr(item.title)+'\',\''+escAttr(item.url)+'\','+item.is_enabled+',\''+site+'\')">Edit</button>';
          h+='<button class="btn" style="padding:4px 10px;font-size:11px;color:var(--rose)" onclick="headerNavDelete('+item.id+',\''+escAttr(item.title)+'\',\''+site+'\')">Delete</button>';
          h+='</td></tr>';
        });
        h+='</table>';
        // Sort Button
        h+='<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">';
        items.forEach(function(item,i){
          if(i>0)h+='<button class="btn" style="padding:4px 8px;font-size:11px" onclick="headerNavMoveUp('+item.id+','+(item.sort_order||0)+',\''+site+'\')">↑ '+esc(item.title)+'</button>';
        });
        h+='</div>';
      }
      h+='<div id="headerNavForm" style="margin-top:20px"></div>';
      mc.innerHTML=h;
    }).catch(function(){mc.innerHTML='<div class="em">Load failed</div>'});
}

function headerNavSwitch(site){
  var mc=document.getElementById("mc");
  renderHeaderNav(mc,site);
}

function headerNavAdd(site){
  var f=document.getElementById("headerNavForm");
  f.innerHTML='<div class="cd"><div class="st">Add Nav Link — '+esc(site)+'</div>'+
    '<div style="display:flex;flex-direction:column;gap:8px;margin-top:12px">'+
    '<input class="in" id="hnTitle" placeholder="Link Title（如：Plaza）">'+
    '<input class="in" id="hnUrl" placeholder="Link URL（如：/plaza）">'+
    '</div>'+
    '<div style="margin-top:12px;display:flex;gap:8px">'+
    '<button class="btn bp" onclick="headerNavDoAdd(\''+site+'\')">Save</button>'+
    '<button class="btn bo" onclick="document.getElementById(\"headerNavForm\").innerHTML=\'\'">Cancel</button>'+
    '</div></div>';
}

function headerNavDoAdd(site){
  var title=document.getElementById("hnTitle").value.trim();
  var url=document.getElementById("hnUrl").value.trim();
  if(!title||!url){showToast("Title and URL are required","error");return}
  fetch("/admin/header-nav",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({site:site,title:title,url:url,is_enabled:true})
  }).then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Added","success");document.getElementById("headerNavForm").innerHTML='';renderHeaderNav(document.getElementById("mc"),site)}
      else{showToast(d.error||"Add Failed","error")}
    }).catch(function(){showToast("Network error","error")});
}

function headerNavEdit(id,title,url,enabled,site){
  var f=document.getElementById("headerNavForm");
  f.innerHTML='<div class="cd"><div class="st">Edit Nav Link</div>'+
    '<div style="display:flex;flex-direction:column;gap:8px;margin-top:12px">'+
    '<input class="in" id="hnTitle" value="'+escAttr(title)+'" placeholder="Link Title">'+
    '<input class="in" id="hnUrl" value="'+escAttr(url)+'" placeholder="Link URL">'+
    '<label><input type="checkbox" id="hnEnabled"'+(enabled?' checked':'')+'> Enabled</label>'+
    '</div>'+
    '<div style="margin-top:12px;display:flex;gap:8px">'+
    '<button class="btn bp" onclick="headerNavDoSave('+id+',\''+site+'\')">Save</button>'+
    '<button class="btn bo" onclick="document.getElementById(\"headerNavForm\").innerHTML=\'\'">Cancel</button>'+
    '</div></div>';
}

function headerNavDoSave(id,site){
  var title=document.getElementById("hnTitle").value.trim();
  var url=document.getElementById("hnUrl").value.trim();
  var enabled=document.getElementById("hnEnabled").checked;
  if(!title||!url){showToast("Title and URL are required","error");return}
  fetch("/admin/header-nav/"+id,{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({title:title,url:url,is_enabled:enabled})
  }).then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Updated","success");document.getElementById("headerNavForm").innerHTML='';renderHeaderNav(document.getElementById("mc"),site)}
      else{showToast(d.error||"Update Failed","error")}
    }).catch(function(){showToast("Network error","error")});
}

function headerNavDelete(id,title,site){
  if(!confirm("Confirm Delete「"+title+"」？"))return;
  fetch("/admin/header-nav/"+id,{
    method:"DELETE",
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Deleted","success");renderHeaderNav(document.getElementById("mc"),site)}
      else{showToast(d.error||"Delete failed","error")}
    }).catch(function(){showToast("Network error","error")});
}

function headerNavMoveUp(id,sortOrder,site){
  fetch("/admin/header-nav",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success)return;
      var items=d.data||[];
      items.sort(function(a,b){return (a.sort_order||0)-(b.sort_order||0)});
      var idx=-1;
      for(var i=0;i<items.length;i++){if(items[i].id===id){idx=i;break}}
      if(idx<=0)return;
      var prev=items[idx-1];
      fetch("/admin/header-nav/reorder",{
        method:"POST",
        headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
        body:JSON.stringify({items:[
          {id:id,sort_order:prev.sort_order||0},
          {id:prev.id,sort_order:items[idx].sort_order||0}
        ].concat(items.filter(function(x){return x.id!==id&&x.id!==prev.id}).map(function(x,i){return {id:x.id,sort_order:i+2}}))})
      }).then(function(r){return r.json()})
        .then(function(dd){
          if(dd.success){renderHeaderNav(document.getElementById("mc"),site)}
          else{showToast(dd.error||"Sort failed","error")}
        });
    });
}

function escAttr(s){if(!s)return'';return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;').replace(/'/g,'&#39;').replace(/\\/g,'\\\\')}

// =============================================
// Brand Settings — Entire Site Logo / Name / Slogan / SEO
// =============================================

window.l_brand=function(){
  document.getElementById("pt").textContent="Brand Settings";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/admin/brand-settings",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data){mc.innerHTML='<div class="em">Load failed</div>';return;}
      renderBrand(d.data);
    }).catch(function(){mc.innerHTML='<div class="em">Connection Failed</div>';});

  function renderBrand(b){
    var h='';
    h+='<div>';
    h+='<div class="cd" style="margin-bottom:16px"><div class="st">Site Logo</div>';
    h+='<div style="display:flex;gap:20px;align-items:center;margin-top:8px">';
    h+='<div style="width:100px;height:50px;background:var(--card);border:1px solid var(--border);border-radius:8px;display:flex;align-items:center;justify-content:center">';
    h+=b.logo_url?'<img src="'+escAttr(b.logo_url)+'" style="max-width:90px;max-height:44px;object-fit:contain">':'<span style="font-size:24px;font-weight:900;color:var(--dim)">E</span>';
    h+='</div>';
    h+='<div style="flex:1">';
    h+='<label class="btn btn-sm bp" style="cursor:pointer;margin-right:8px">Upload Logo<input type="file" accept="image/png,image/jpeg,image/svg+xml" style="display:none" onchange="brandUploadLogo(this)"></label>';
    if(b.logo_url){h+='<button class="btn btn-sm" style="color:var(--rose);border-color:var(--rose)" onclick="brandDeleteLogo()">Reset to Default</button>';}
    h+='<div style="font-size:11px;color:var(--dim);margin-top:6px">Suggestion 200×50px PNG/SVG，Max 500KB</div>';
    h+='</div></div></div>';
    // Icon Only Logo
    h+='<div class="cd" style="margin-bottom:16px"><div class="st">Icon Only Logo（Favicon / Sidebar）</div>';
    h+='<div style="display:flex;gap:20px;align-items:center;margin-top:8px">';
    h+='<div style="width:56px;height:56px;background:var(--card);border:1px solid var(--border);border-radius:8px;display:flex;align-items:center;justify-content:center">';
    h+=b.logo_icon_url?'<img src="'+escAttr(b.logo_icon_url)+'" style="max-width:48px;max-height:48px;object-fit:contain">':'<span style="font-size:20px;font-weight:900;color:var(--dim)">EK</span>';
    h+='</div>';
    h+='<div style="flex:1">';
    h+='<label class="btn btn-sm bp" style="cursor:pointer;margin-right:8px">Upload Icon<input type="file" accept="image/png,image/jpeg,image/svg+xml" style="display:none" onchange="brandUploadLogoIcon(this)"></label>';
    if(b.logo_icon_url){h+='<button class="btn btn-sm" style="color:var(--rose);border-color:var(--rose)" onclick="brandDeleteLogoIcon()">Reset to Default</button>';}
    h+='<div style="font-size:11px;color:var(--dim);margin-top:6px">Suggestion 64×64px PNG/SVG，Used For Favicon &amp; Small Size Scenarios</div>';
    h+='</div></div></div>';
    var fields=[
      {k:'company_name',label:'Company Name',ph:'EasyKai Network'},
      {k:'site_name_cn',label:'Chinese Site Name',ph:'EasyKai Network'},
      {k:'software_name',label:'Software Name（Footer Display）',ph:'EasyKaiAI'},
      {k:'site_name_en',label:'English Site Name',ph:'EasyKai'},
      {k:'slogan',label:'Slogan / Slogan',ph:'Agent Smart Finance Platform'},
      {k:'tagline',label:'Tagline / Subtitle',ph:'Agent Applied Tech'},
      {k:'description',label:'Brief Description（Footer Left Text）',ph:'为 Agent Build Financial Analysis...',ta:true},
      {k:'copyright',label:'Copyright',ph:'© 2026 EasyKaiAI | Multi-Agent AI Operating System'},
    ];
    h+='<div class="cd" style="margin-bottom:16px"><div class="st">Brand Info <span style="font-size:11px;color:var(--dim)">Current Version v'+esc(b.version||'0.9.5')+'</span></div>';
    fields.forEach(function(f){
      h+='<div style="margin-bottom:12px">';
      h+='<label style="display:block;font-size:12px;color:var(--text);margin-bottom:4px">'+esc(f.label)+'</label>';
      if(f.ta){
        h+='<textarea class="in" id="brand_'+f.k+'" style="width:100%;min-height:50px;resize:vertical">'+esc(b[f.k]||'')+'</textarea>';
      }else{
        h+='<input class="in" id="brand_'+f.k+'" value="'+escAttr(b[f.k]||'')+'" placeholder="'+esc(f.ph)+'" style="width:100%">';
      }
      h+='</div>';
    });
    h+='</div>';
    h+='<div class="cd" style="margin-bottom:16px"><div class="st">SEO Settings</div>';
    var seoFields=[
      {k:'seo_title',label:'SEO Title',ph:''},
      {k:'seo_desc',label:'SEO Description',ph:''},
    ];
    seoFields.forEach(function(f){
      h+='<div style="margin-bottom:12px">';
      h+='<label style="display:block;font-size:12px;color:var(--text);margin-bottom:4px">'+esc(f.label)+'</label>';
      h+='<textarea class="in" id="brand_'+f.k+'" style="width:100%;min-height:40px;resize:vertical">'+esc(b[f.k]||'')+'</textarea>';
      h+='</div>';
    });
    h+='</div>';
    h+='<div class="cd" style="margin-bottom:16px"><div class="st">Enterprise &amp; Compliance</div>';
    var complianceFields=[
      {k:'icp_number',label:'ICP ICP No.（Support HTML）',ph:'<a href="https://beian.miit.gov.cn/" target="_blank">苏ICP备2026017510号-1</a>',ta:true},
      {k:'security_number',label:'ICP No.（Support HTML，Leave Empty to Hide）',ph:'<a href="https://beian.mps.gov.cn/#/query/webSearch?code=32031102020288" rel="noreferrer" target="_blank">Jiangsu Public Security32031102020288号</a>',ta:true},
      {k:'contact_email',label:'Contact Email',ph:'hi@easykai.cn'},
    ];
    complianceFields.forEach(function(f){
      h+='<div style="margin-bottom:12px">';
      h+='<label style="display:block;font-size:12px;color:var(--text);margin-bottom:4px">'+esc(f.label)+'</label>';
      if(f.ta){
        h+='<textarea class="in" id="brand_'+f.k+'" style="width:100%;min-height:36px;resize:vertical;font-family:monospace;font-size:12px" placeholder="'+esc(f.ph)+'">'+esc(b[f.k]||'')+'</textarea>';
      }else{
        h+='<input class="in" id="brand_'+f.k+'" value="'+escAttr(b[f.k]||'')+'" placeholder="'+esc(f.ph)+'" style="width:100%">';
      }
      h+='</div>';
    });
    h+='</div>';
    // Sub-brand Management（TradeMind）- Expandable
    h+='<div class="cd" style="margin-bottom:16px;border-left:3px solid var(--accent)">';
    h+='<div class="st" style="cursor:pointer;margin:0;padding:12px 16px;user-select:none" id="subbrand_hdr" onclick="toggleSubBrand()">▶ Sub-brand Management</div>';
    h+='<div id="subbrand_body" style="display:none;padding:0 16px 12px">';
    h+='<div id="subbrand_content" style="min-height:40px"></div>';
    h+='</div></div>';
    h+='<div class="cd" style="margin-bottom:16px"><div class="st">Favicon（Optional）</div>';
    h+='<div style="display:flex;gap:12px;align-items:center;margin-top:8px">';
    if(b.favicon_url){h+='<img src="'+escAttr(b.favicon_url)+'" style="width:32px;height:32px;border-radius:4px">';}
    h+='<label class="btn btn-sm bp" style="cursor:pointer">Upload Favicon<input type="file" accept="image/png,image/x-icon,.ico" style="display:none" onchange="brandUploadFavicon(this)"></label>';
    if(b.favicon_url){h+='<button class="btn btn-sm" style="color:var(--rose);border-color:var(--rose)" onclick="brandDeleteFavicon()">Reset to Default</button>';}
    h+='<span style="font-size:11px;color:var(--dim)">Suggestion 32×32px PNG/ICO</span>';
    h+='</div></div>';
    h+='<div style="text-align:center;margin-top:20px">';
    h+='<button class="btn bp" style="padding:10px 40px;font-size:15px" onclick="brandSave()">Save Settings</button>';
    h+='</div>';
    h+='</div>';
    mc.innerHTML=h;
  }
};

function brandSave(){
  var fields=['company_name','site_name_cn','site_name_en','slogan','tagline','description','copyright','seo_title','seo_desc','icp_number','security_number','contact_email','logo_full_url','logo_icon_url','software_name','software_slogan'];
  var swFields=['software_name','software_slogan'];
  var data={};
  fields.forEach(function(k){
    var el=document.getElementById("brand_"+k);
    if(el){data[k]=el.value;}
  });
  fetch("/admin/brand-settings",{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(data)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Brand settings saved","success")}else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Save failed","error")});
}

function brandUploadLogo(input){
  if(!input.files||!input.files[0])return;
  var fd=new FormData();fd.append("logo",input.files[0]);
  fetch("/admin/brand-settings/logo",{method:"POST",headers:{"Authorization":"Bearer "+T},body:fd})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Logo updated","success");go("brand")}
      else{showToast(d.error||"Upload failed","error")}
    }).catch(function(){showToast("Upload failed","error")});
}

function brandDeleteLogo(){
  if(!confirm("Restore default logo?"))return;
  fetch("/admin/brand-settings/logo",{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Default logo restored","success");go("brand")}
      else{showToast(d.error||"Operation Failed","error")}
    }).catch(function(){showToast("Operation Failed","error")});
}

function brandUploadFavicon(input){
  if(!input.files||!input.files[0])return;
  var fd=new FormData();fd.append("favicon",input.files[0]);
  fetch("/admin/brand-settings/favicon",{method:"POST",headers:{"Authorization":"Bearer "+T},body:fd})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Favicon updated","success");go("brand")}
      else{showToast(d.error||"Upload failed","error")}
    }).catch(function(){showToast("Upload failed","error")});
}

function brandDeleteFavicon(){
  if(!confirm("Restore default favicon?"))return;
  fetch("/admin/brand-settings/favicon",{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Default favicon restored","success");go("brand")}
      else{showToast(d.error||"Operation Failed","error")}
    }).catch(function(){showToast("Operation Failed","error")});
}

function brandUploadLogoIcon(input){
  if(!input.files||!input.files[0])return;
  var fd=new FormData();fd.append("logo_icon",input.files[0]);
  fetch("/admin/brand-settings/logo-icon",{method:"POST",headers:{"Authorization":"Bearer "+T},body:fd})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Icon updated","success");go("brand")}
      else{showToast(d.error||"Upload failed","error")}
    }).catch(function(){showToast("Upload failed","error")});
}

function brandDeleteLogoIcon(){
  if(!confirm("Restore default icon?"))return;
  fetch("/admin/brand-settings/logo-icon",{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Default icon restored","success");go("brand")}
      else{showToast(d.error||"Operation Failed","error")}
    }).catch(function(){showToast("Operation Failed","error")});
}

// =============================================
// Sub-brand Management — Inlined in Brand Settings Page
// =============================================
var subBrandLoaded=false;
function toggleSubBrand(){
  var body=document.getElementById("subbrand_body");
  var hdr=document.getElementById("subbrand_hdr");
  if(!subBrandLoaded){
    hdr.textContent='▼ Sub-brand Management';
    body.style.display="block";
    loadTmBrand();
    subBrandLoaded=true;
  }else{
    var vis=body.style.display==="none";
    body.style.display=vis?"block":"none";
    hdr.textContent=(vis?"▼":"▶")+" Sub-brand Management";
  }
}

function loadTmBrand(){
  var el=document.getElementById("subbrand_content");
  el.innerHTML='<div class="lo" style="margin:12px 0"><div class="s"></div>Loading......</div>';
  fetch("/admin/tm-brand-settings",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data){el.innerHTML='<div class="em">Load failed — <a href="javascript:loadTmBrand()">Retry</a></div>';return;}
      renderTmBrandInline(d.data);
    }).catch(function(){el.innerHTML='<div class="em">Connection Failed — <a href="javascript:loadTmBrand()">Retry</a></div>';});
}

function renderTmBrandInline(b){
  var h='';
  // Logo
  h+='<div style="margin-top:8px"><div style="font-size:12px;color:var(--dim);margin-bottom:6px">TradeMind Logo</div>';
  h+='<div style="display:flex;gap:16px;align-items:center">';
  h+='<div style="width:80px;height:40px;background:var(--card);border:1px solid var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center">';
  h+=b.logo_url?'<img src="'+escAttr(b.logo_url)+'" style="max-width:72px;max-height:36px;object-fit:contain">':'<span style="font-size:20px;font-weight:900;color:var(--dim)">TM</span>';
  h+='</div>';
  h+='<div><label class="btn btn-sm bp" style="cursor:pointer;margin-right:8px">Upload Logo<input type="file" accept="image/png,image/jpeg,image/svg+xml" style="display:none" onchange="tmBrandUploadLogo(this)"></label>';
  if(b.logo_url){h+='<button class="btn btn-sm" style="color:var(--rose);border-color:var(--rose)" onclick="tmBrandDeleteLogo()">Reset to Default</button>';}
  h+='<div style="font-size:11px;color:var(--dim);margin-top:4px">Suggestion 200×50px PNG/SVG，Max 500KB</div>';
  h+='</div></div></div>';

  var tmFields=[
    {k:'site_name_cn',label:'Chinese Name',ph:'TradeMind'},
    {k:'site_name_en',label:'English Name',ph:'TradeMind'},
    {k:'slogan',label:'Slogan / Slogan',ph:'AIDrivenAStock Analysis Platform'},
    {k:'tagline',label:'Tagline / Subtitle',ph:''},
    {k:'description',label:'Product Description',ph:'ForAData Analysis for Retail &amp; Professional InvestorsAPIPlatform。',ta:true},
    {k:'copyright',label:'Copyright',ph:''},
  ];
  h+='<div style="margin-top:12px"><div style="font-size:12px;color:var(--dim);margin-bottom:6px">Brand Info</div>';
  tmFields.forEach(function(f){
    h+='<div style="margin-bottom:10px">';
    h+='<label style="display:block;font-size:12px;color:var(--text);margin-bottom:3px">'+esc(f.label)+'</label>';
    if(f.ta){
      h+='<textarea class="in" id="tmb_'+f.k+'" style="width:100%;min-height:40px;resize:vertical">'+esc(b[f.k]||'')+'</textarea>';
    }else{
      h+='<input class="in" id="tmb_'+f.k+'" value="'+escAttr(b[f.k]||'')+'" placeholder="'+esc(f.ph)+'" style="width:100%">';
    }
    h+='</div>';
  });
  h+='</div>';

  var tmSeo=[
    {k:'seo_title',label:'SEO Title',ph:'TradeMind — AIDrivenAStock Analysis Platform'},
    {k:'seo_desc',label:'SEO Description',ph:'ForAData Analysis for Retail &amp; Professional InvestorsAPIPlatform。'},
  ];
  h+='<div style="margin-top:12px"><div style="font-size:12px;color:var(--dim);margin-bottom:6px">SEO Settings</div>';
  tmSeo.forEach(function(f){
    h+='<div style="margin-bottom:10px">';
    h+='<label style="display:block;font-size:12px;color:var(--text);margin-bottom:3px">'+esc(f.label)+'</label>';
    h+='<textarea class="in" id="tmb_'+f.k+'" style="width:100%;min-height:36px;resize:vertical">'+esc(b[f.k]||'')+'</textarea>';
    h+='</div>';
  });
  h+='</div>';
  h+='<div style="text-align:center;margin-top:16px">';
  h+='<button class="btn bp" style="padding:8px 32px;font-size:14px" onclick="tmBrandSave()">Save Sub-brand Settings</button>';
  h+='</div>';
  document.getElementById("subbrand_content").innerHTML=h;
}

// 原 TradeMind Standalone Page Render（Kept for Backward Compatibility，But No Longer Called from Sidebar）
// =============================================
// TradeMind Sub Brand Settings
// =============================================

window.l_tm_brand=function(){
  document.getElementById("pt").textContent="TradeMind Brand Settings";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/admin/tm-brand-settings",{headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(!d.success||!d.data){mc.innerHTML='<div class="em">Load failed</div>';return}
      renderTmBrand(d.data);
    }).catch(function(){mc.innerHTML='<div class="em">Connection Failed</div>';});

  function renderTmBrand(b){
    var h='';
    h+='<div>';
    h+='<div class="cd" style="margin-bottom:16px"><div class="st">TradeMind Logo</div>';
    h+='<div style="display:flex;gap:20px;align-items:center;margin-top:8px">';
    h+='<div style="width:100px;height:50px;background:var(--card);border:1px solid var(--border);border-radius:8px;display:flex;align-items:center;justify-content:center">';
    h+=b.logo_url?'<img src="'+escAttr(b.logo_url)+'" style="max-width:90px;max-height:44px;object-fit:contain">':'<span style="font-size:24px;font-weight:900;color:var(--dim)">TM</span>';
    h+='</div><div style="flex:1">';
    h+='<label class="btn btn-sm bp" style="cursor:pointer;margin-right:8px">Upload Logo<input type="file" accept="image/png,image/jpeg,image/svg+xml" style="display:none" onchange="tmBrandUploadLogo(this)"></label>';
    if(b.logo_url){h+='<button class="btn btn-sm" style="color:var(--rose);border-color:var(--rose)" onclick="tmBrandDeleteLogo()">Reset to Default</button>';}
    h+='<div style="font-size:11px;color:var(--dim);margin-top:6px">Suggestion 200×50px PNG/SVG，Max 500KB</div>';
    h+='</div></div></div>';
    var tmFields=[
      {k:'site_name_cn',label:'Chinese Name',ph:'TradeMind'},
      {k:'site_name_en',label:'English Name',ph:'TradeMind'},
      {k:'slogan',label:'Slogan / Slogan',ph:'AIDrivenAStock Analysis Platform'},
      {k:'tagline',label:'Tagline / Subtitle',ph:''},
      {k:'description',label:'Product Description',ph:'ForAData Analysis for Retail &amp; Professional InvestorsAPIPlatform。',ta:true},
      {k:'copyright',label:'Copyright',ph:''},
    ];
    h+='<div class="cd" style=\"margin-bottom:16px\"><div class=\"st\">Brand Info</div>';
    tmFields.forEach(function(f){
      h+='<div style="margin-bottom:12px">';
      h+='<label style="display:block;font-size:12px;color:var(--text);margin-bottom:4px">'+esc(f.label)+'</label>';
      if(f.ta){
        h+='<textarea class="in" id="tmb_'+f.k+'" style="width:100%;min-height:50px;resize:vertical">'+esc(b[f.k]||'')+'</textarea>';
      }else{
        h+='<input class="in" id="tmb_'+f.k+'" value="'+escAttr(b[f.k]||'')+'" placeholder="'+esc(f.ph)+'" style="width:100%">';
      }
      h+='</div>';
    });
    h+='</div>';
    h+='<div class="cd" style=\"margin-bottom:16px\"><div class=\"st\">SEO Settings</div>';
    var tmSeo=[
      {k:'seo_title',label:'SEO Title',ph:'TradeMind — AIDrivenAStock Analysis Platform'},
      {k:'seo_desc',label:'SEO Description',ph:'ForAData Analysis for Retail &amp; Professional InvestorsAPIPlatform。'},
    ];
    tmSeo.forEach(function(f){
      h+='<div style="margin-bottom:12px">';
      h+='<label style="display:block;font-size:12px;color:var(--text);margin-bottom:4px">'+esc(f.label)+'</label>';
      h+='<textarea class="in" id="tmb_'+f.k+'" style="width:100%;min-height:40px;resize:vertical">'+esc(b[f.k]||'')+'</textarea>';
      h+='</div>';
    });
    h+='</div>';
    h+='<div style="text-align:center;margin-top:20px">';
    h+='<button class="btn bp" style="padding:10px 40px;font-size:15px" onclick="tmBrandSave()">Save Settings</button>';
    h+='</div>';
    h+='</div>';
    mc.innerHTML=h;
  }
};

function tmBrandSave(){
  var fields=['site_name_cn','site_name_en','slogan','tagline','description','copyright','seo_title','seo_desc'];
  var data={};
  fields.forEach(function(k){
    var el=document.getElementById("tmb_"+k);
    if(el){data[k]=el.value;}
  });
  fetch("/admin/tm-brand-settings",{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(data)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("TradeMind brand settings saved","success")}else{showToast(d.error||"Save failed","error")}
  }).catch(function(){showToast("Save failed","error")});
}

function tmBrandUploadLogo(input){
  if(!input.files||!input.files[0])return;
  var fd=new FormData();fd.append("tm_logo",input.files[0]);
  fetch("/admin/tm-brand-settings/logo",{method:"POST",headers:{"Authorization":"Bearer "+T},body:fd})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Logo updated","success");loadTmBrand()}
      else{showToast(d.error||"Upload failed","error")}
    }).catch(function(){showToast("Upload failed","error")});
}
function tmBrandDeleteLogo(){
  if(!confirm("Restore default TradeMind logo?"))return;
  fetch("/admin/tm-brand-settings/logo",{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
    .then(function(r){return r.json()})
    .then(function(d){
      if(d.success){showToast("Restored to default","success");loadTmBrand()}
      else{showToast(d.error||"Operation Failed","error")}
    }).catch(function(){showToast("Operation Failed","error")});
}


window.l_token_monitoring=function(){
  document.getElementById("pt").textContent="Token Usage";
  var mc=document.getElementById("mc");
  mc.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';

  var period="today", dimension="", tab="agents";  // tab: agents|models|users

  function loadStats(){
    var url="/admin/agent-matrix/token-stats?period="+period;
    if(dimension)url+="&dimension="+dimension;
    fetch(url,{headers:{"Authorization":"Bearer "+T}})
      .then(function(r){return r.json()})
      .then(function(d){
        if(!d.success||!d.data){mc.innerHTML='<div class="em">Load failed</div>';return}
        render(d.data);
      }).catch(function(){mc.innerHTML='<div class="em">Load failed — <a href="javascript:l_token_monitoring()">Retry</a></div>'});
  }

  function tf(n){if(n>=1e6)return (n/1e6).toFixed(1)+'M';if(n>=1e3)return (n/1e3).toFixed(1)+'K';return n.toString()}

  function render(ds){
    var thr=ds.thresholds||{},mt=ds.today_matrix_total||0;
    var pricing=ds.pricing||{},cost=ds.cost_estimate||0;
    var byDim=ds.by_dimension||[];
    var tot=ds.total||{};

    // Dimension Stats
    var dimStats={};
    byDim.forEach(function(d){dimStats[d.dimension]=d;});
    var voiceCalls=(dimStats.voice||{}).calls||0;
    var videoCalls=(dimStats.video||{}).calls||0;
    var imageCalls=(dimStats.image||{}).calls||0;

    var h='';

    // Alert Bar
    if(mt>=thr.matrix_red){
      h+='<div class="cd" style="background:rgba(255,59,48,0.12);border-color:var(--rose);margin-bottom:8px"><div style="font-size:13px;color:var(--rose);font-weight:600">\u26A0 Site Alert：Today Total Token '+tf(mt)+'，Threshold Exceeded '+tf(thr.matrix_red)+'</div></div>';
    }

    // Time Tags
    var tabs=[["today","Today"],["week","This Week"],["month","This Month"],["all","Cumulative"]];
    h+='<div class="cd"><div class="st" style="display:flex;align-items:center;gap:4px;margin-bottom:8px">';
    tabs.forEach(function(t){
      var sel=t[0]===period;
      h+='<span class="btn '+(sel?'bp':'bo')+'" style="padding:3px 10px;font-size:11px;cursor:pointer" onclick="document.getElementById(\'mc\').dispatchEvent(new CustomEvent(\'token-period\',{detail:\''+t[0]+'\'}))">'+t[1]+'</span>';
    });
    h+='<span style="flex:1"></span>';
    h+='<span style="font-size:11px;color:var(--dim)">\u9EC4:&gt;'+tf(thr.agent_yellow)+' \u7EA2:&gt;'+tf(thr.agent_red)+'</span>';
    h+='</div>';

    // Dimension Filter Tags
    var dims=[["","All"],["text","LLM Text"],["voice","Voice"],["video","Video"],["image","Image"]];
    h+='<div style="display:flex;gap:4px;margin-bottom:12px">';
    dims.forEach(function(d){
      var sel=d[0]===dimension;
      h+='<span class="btn '+(sel?'bp':'bo')+'" style="padding:2px 8px;font-size:10px;cursor:pointer" onclick="document.getElementById(\'mc\').dispatchEvent(new CustomEvent(\'token-dim\',{detail:\''+d[0]+'\'}))">'+d[1]+'</span>';
    });
    h+='</div>';

    // Global Summary Card
    h+='<div class="gr" style="margin-bottom:8px">';
    h+=hk("Total Token",tf(tot.total||0),"b");
    h+=hk("Call Count",tot.calls||0,"g");
    h+=hk("Estimated Fee","\u00A5"+cost.toFixed(2),"");
    h+=hk("Input Token",tf(tot.prompt||0),"");
    h+=hk("Output Token",tf(tot.completion||0),"g");
    h+=hk("Voice Call",voiceCalls,"");
    h+=hk("Video Generate",videoCalls,"");
    h+=hk("Image Gen",imageCalls,"");
    h+='</div></div>';

    // ── Chart ──
    h+='<div style="display:flex;gap:8px;margin-bottom:8px" id="token-charts">';
    h+='<div class="cd" style="flex:1;min-width:0"><div class="st">Dimension Distribution</div><div style="height:180px;position:relative"><canvas id="chartDim"></canvas></div></div>';
    h+='<div class="cd" style="flex:2;min-width:0"><div class="st">Agent Token Spend</div><div style="height:180px;position:relative"><canvas id="chartAgent"></canvas></div></div>';
    h+='</div>';

    // ── Tab Switch ──
    var tabs2=[["agents","Agent\u00D7\u6A21\u578B"],["models","Summary by Model"]];
    if((ds.users||[]).length>0)tabs2.push(["users","User Consumption"]);
    h+='<div class="cd" style="margin-top:4px"><div style="display:flex;gap:2px;margin-bottom:12px">';
    tabs2.forEach(function(t){
      var sel=t[0]===tab;
      h+='<span class="btn '+(sel?'bp':'bo')+'" style="padding:3px 10px;font-size:11px;cursor:pointer" onclick="document.getElementById(\'mc\').dispatchEvent(new CustomEvent(\'token-tab\',{detail:\''+t[0]+'\'}))">'+t[1]+'</span>';
    });
    h+='</div>';

    // Render Chart（Each render After Call）
    setTimeout(function(){
      var byDim=ds.by_dimension||[],pricing=ds.pricing||{};
      var dimColors={text:'#2F6BFF',voice:'#00D68F',video:'#FF3D71',image:'#FFAA00'};
      var dimLabels={text:'LLMText',voice:'Voice',video:'Video',image:'Image'};

      // Pie Chart: Dimension Distribution（By Fee）
      var dimData=[],dimBg=[];
      byDim.forEach(function(d){
        var cost=0;
        if(d.dimension==='voice')cost=d.calls*(pricing.voice_per_call||0.02);
        else if(d.dimension==='video')cost=d.calls*(pricing.video_per_call||0.10);
        else if(d.dimension==='image')cost=d.calls*(pricing.image_per_call||0.05);
        else cost=d.total/1000*(pricing.text_per_1k||0.003);
        if(cost>0){dimData.push(cost);dimBg.push(dimColors[d.dimension]||'#888');}
      });
      if(dimData.length&&document.getElementById('chartDim')){
        if(window._chartDim)window._chartDim.destroy();
        window._chartDim=new Chart(document.getElementById('chartDim'),{
          type:'doughnut',
          data:{labels:byDim.filter(function(d){return d.calls||d.total}).map(function(d){return dimLabels[d.dimension]||d.dimension}),datasets:[{data:dimData,backgroundColor:dimBg,borderColor:'rgba(6,11,24,0.8)',borderWidth:2}]},
          options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#8894B0',font:{size:10},padding:8}}}}
        });
      }

      // Bar Chart: Agent×Models Top 8
      var ams=(ds.agent_models||[]).filter(function(a){return (a.total||0)>0}).slice(0,8);
      if(ams.length&&document.getElementById('chartAgent')){
        var labels=ams.map(function(a){return a.agent_name||'#'+a.agent_id}),vals=ams.map(function(a){return a.total||0});
        if(window._chartAgent)window._chartAgent.destroy();
        window._chartAgent=new Chart(document.getElementById('chartAgent'),{
          type:'bar',
          data:{labels:labels,datasets:[{data:vals,backgroundColor:'rgba(47,107,255,0.6)',borderColor:'#2F6BFF',borderWidth:1,borderRadius:4}]},
          options:{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(136,148,176,0.1)'},ticks:{color:'#8894B0',font:{size:9}}},y:{grid:{display:false},ticks:{color:'#8894B0',font:{size:10}}}}}
        });
      }
    },50);

    // Tab Content
    if(tab==="agents"){
      h+=renderAgentModels(ds);
    }else if(tab==="models"){
      h+=renderModelSummary(ds);
    }else if(tab==="users"){
      h+=renderUsers(ds);
    }

    h+='</div>';

    // Recent Call Log Card
    h+='<div class="cd" style="margin-top:4px" id="token-log-card"><div class="st">Recent Call Logs</div><div id="token-log-body" style="font-size:11px;color:var(--dim);padding:8px 0">Click Agent View Logs by Name</div></div>';

    mc.innerHTML=h;
  }

  // Agent×Model Cross Table (Collapsible)
  function renderAgentModels(ds){
    var ams=ds.agent_models||[],thr=ds.thresholds||{},pricing=ds.pricing||{};
    if(ams.length===0)return'<div style="color:var(--dim);font-size:12px;padding:16px 0">No data</div>';

    // 按 agent_id Group
    var groups={};
    ams.forEach(function(r){
      var k=r.agent_id;
      if(!groups[k])groups[k]={name:r.agent_name||'Agent#'+r.agent_id,total:0,calls:0,models:[]};
      groups[k].models.push(r);
      groups[k].total+=r.total||0;
      groups[k].calls+=r.calls||0;
    });

    var h='<div class="st">Agent \u00D7 Model Usage</div>';
    h+='<table style="font-size:12px;margin-top:8px"><tr><th>#</th><th>Agent / Models</th><th>Dimension</th><th>Provider</th><th>Count</th><th>Spend</th><th>Fee</th><th>Input</th><th>Output</th></tr>';

    var idx=0;
    Object.keys(groups).sort(function(a,b){return groups[b].total-groups[a].total}).forEach(function(aid){
      var g=groups[aid]; idx++;
      var rowClr=g.total>=thr.agent_red?'rgba(255,59,48,0.08)':g.total>=thr.agent_yellow?'rgba(255,204,0,0.08)':'';
      // Agent summary row
      var estCost=dimension==='voice'||dimension==='video'?g.calls*(pricing.voice_per_call||0.02):g.total/1000*(pricing.text_per_1k||0.003);
      h+='<tr style="background:'+rowClr+';cursor:pointer" onclick="var t=this.nextElementSibling;while(t&&t.dataset.agent==\''+aid+'\'){t.style.display=t.style.display==\'none\'?\'\':\'none\';t=t.nextElementSibling}">';
      h+='<td>'+idx+'</td><td style="font-weight:600">\u25B6 '+esc(g.name)+'</td><td></td><td></td><td>'+g.calls+'</td>';
      h+='<td style="font-weight:600;color:'+(g.total>=thr.agent_red?'var(--rose)':g.total>=thr.agent_yellow?'var(--amber)':'var(--text)')+'">'+tf(g.total)+(dimension?'':'')+'</td>';
      h+='<td>\u00A5'+estCost.toFixed(2)+'</td><td></td><td></td></tr>';

      // Model sub-rows
      g.models.sort(function(a,b){return (b.total||0)-(a.total||0)}).forEach(function(m){
        var mc=m.dimension==='voice'?m.calls*(pricing.voice_per_call||0.02):(m.dimension==='video'?m.calls*(pricing.video_per_call||0.10):(m.dimension==='image'?m.calls*(pricing.image_per_call||0.05):m.total/1000*(pricing.text_per_1k||0.003)));
        h+='<tr data-agent="'+aid+'" style="display:none;font-size:11px;color:var(--dim)">';
        h+='<td></td><td style="padding-left:20px">\u2514 '+esc(m.model_name||'-')+'</td>';
        h+='<td>'+esc(m.dimension||'text')+'</td><td>'+esc(m.provider||'-')+'</td><td>'+m.calls+'</td>';
        h+='<td>'+tf(m.total||0)+(m.dimension==='voice'||m.dimension==='video'?' \u6B21':'')+'</td>';
        h+='<td>\u00A5'+mc.toFixed(2)+'</td>';
        h+='<td>'+tf(m.prompt||0)+'</td><td>'+tf(m.completion||0)+'</td></tr>';
      });
    });
    h+='</table>';
    return h;
  }

  // Summary by Model
  function renderModelSummary(ds){
    var ams=ds.agent_models||[],pricing=ds.pricing||{};
    if(ams.length===0)return'<div style="color:var(--dim);font-size:12px;padding:16px 0">No data</div>';

    // 按 model+provider+dimension Summary
    var map={};
    ams.forEach(function(r){
      var k=r.model_name+'|||'+r.provider+'|||'+r.dimension;
      if(!map[k])map[k]={model_name:r.model_name,provider:r.provider,dimension:r.dimension,total:0,calls:0,prompt:0,completion:0};
      map[k].total+=r.total||0;
      map[k].calls+=r.calls||0;
      map[k].prompt+=r.prompt||0;
      map[k].completion+=r.completion||0;
    });
    var vals=Object.values(map).sort(function(a,b){return b.total-a.total});

    var h='<div class="st">Model Usage Summary</div>';
    h+='<table style="font-size:12px;margin-top:8px"><tr><th>#</th><th>Models</th><th>Dimension</th><th>Provider</th><th>Count</th><th>Spend</th><th>Fee</th><th>Percentage</th></tr>';

    var grandTotal=vals.reduce(function(s,v){return s+v.total},0);
    vals.forEach(function(v,i){
      var ec=0;
      if(v.dimension==='voice')ec=v.calls*(pricing.voice_per_call||0.02);
      else if(v.dimension==='video')ec=v.calls*(pricing.video_per_call||0.10);
      else if(v.dimension==='image')ec=v.calls*(pricing.image_per_call||0.05);
      else ec=v.total/1000*(pricing.text_per_1k||0.003);
      var pct=grandTotal>0?(v.total/grandTotal*100).toFixed(1):'0';
      h+='<tr><td>'+(i+1)+'</td><td style="font-weight:600">'+esc(v.model_name||'-')+'</td>';
      h+='<td>'+esc(v.dimension||'text')+'</td><td>'+esc(v.provider||'-')+'</td><td>'+v.calls+'</td>';
      h+='<td>'+tf(v.total)+(v.dimension==='voice'||v.dimension==='video'?' \u6B21':'')+'</td>';
      h+='<td>\u00A5'+ec.toFixed(2)+'</td><td>'+pct+'%</td></tr>';
    });
    h+='</table>';
    return h;
  }

  // User Consumption
  function renderUsers(ds){
    var users=ds.users||[],pricing=ds.pricing||{};
    if(users.length===0)return'<div style="color:var(--dim);font-size:12px;padding:16px 0">No User Consumption Data</div>';

    var h='<div class="st">User Token Consumption Ranking</div>';
    h+='<table style="font-size:12px;margin-top:8px"><tr><th>#</th><th>User</th><th>Agent</th><th>Models</th><th>Dimension</th><th>Count</th><th>Spend</th></tr>';
    users.forEach(function(u,i){
      var ec=0;
      if(u.dimension==='voice')ec=u.calls*(pricing.voice_per_call||0.02);
      else if(u.dimension==='video')ec=u.calls*(pricing.video_per_call||0.10);
      else if(u.dimension==='image')ec=u.calls*(pricing.image_per_call||0.05);
      else ec=u.total/1000*(pricing.text_per_1k||0.003);
      h+='<tr><td>'+(i+1)+'</td><td>'+esc(u.username||'User#'+u.user_id)+'</td>';
      h+='<td>'+esc(u.agent_name||'-')+'</td><td>'+esc(u.model_name||'-')+'</td>';
      h+='<td>'+esc(u.dimension||'text')+'</td><td>'+u.calls+'</td>';
      h+='<td>'+tf(u.total)+(u.dimension==='voice'||u.dimension==='video'?' \u6B21':'')+'</td></tr>';
    });
    h+='</table>';
    return h;
  }

  // Event: Switch Time
  mc.addEventListener('token-period',function(ev){
    period=ev.detail;
    mc.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
    loadStats();
    mc.addEventListener('token-period',arguments.callee);
  });
  // Event: Switch Dimension
  mc.addEventListener('token-dim',function(ev){
    dimension=ev.detail;
    mc.innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
    loadStats();
    mc.addEventListener('token-dim',arguments.callee);
  });
  // Event: SwitchTab
  mc.addEventListener('token-tab',function(ev){
    tab=ev.detail;
    loadStats();
    mc.addEventListener('token-tab',arguments.callee);
  });

  // View Specific Agent Log
  window.loadLogs=function(aid,aname){
    fetch("/admin/agent-matrix/token-logs?agent_id="+aid+"&limit=30",{headers:{"Authorization":"Bearer "+T}})
      .then(function(r){return r.json()})
      .then(function(d){
        var body=document.getElementById("token-log-body");
        if(!body)return;
        if(!d.success||!d.data||!d.data.logs||d.data.logs.length===0){
          body.innerHTML='<div style="color:var(--dim);padding:8px 0">\u6682\u65E0\u8C03\u7528\u8BB0\u5F55</div>';
          return;
        }
        var h='<div style="font-size:12px;margin-bottom:6px">'+esc(aname||'Agent#'+aid)+' \u6700\u8FD1 30 \u6761\u8BB0\u5F55</div>';
        h+='<table style="font-size:11px"><tr><th>\u65F6\u95F4</th><th>\u6A21\u578B</th><th>Provider</th><th>\u7C7B\u578B</th><th>\u7EF4\u5EA6</th><th>Prompt</th><th>Compl</th><th>Total</th></tr>';
        d.data.logs.forEach(function(l){
          h+='<tr><td style="white-space:nowrap">'+esc(l.created_at||'')+'</td><td>'+esc(l.model_name||'-')+'</td><td>'+esc(l.provider||'-')+'</td><td>'+esc(l.call_type||'')+'</td><td>'+esc(l.dimension||'text')+'</td><td>'+l.prompt_tokens+'</td><td>'+l.completion_tokens+'</td><td style="font-weight:600">'+l.total_tokens+'</td></tr>';
        });
        h+='</table>';
        body.innerHTML=h;
      }).catch(function(){});
  };

  loadStats();
};
// ══════════════════════════════════════════════

window.l_notifications=function(){
  document.getElementById("pt").textContent="Notifications";
  var h='<div style="display:flex;gap:12px;margin-bottom:16px">';
  h+='<button class="btn bp" onclick="notifShowTab(\'push\')" id="ntabPush">Manual Push</button>';
  h+='<button class="btn" onclick="notifShowTab(\'templates\')" id="ntabTemplates">Push Template</button>';
  h+='<button class="btn" onclick="notifTest(\'templates\')" id="ntabTest">📨 Send Test</button>';
  h+='</div><div id="notifContent"><div class="lo">Loading......</div></div>';
  document.getElementById("mc").innerHTML=h;
  notifShowTab("push");
};

var _notifTab="";

function notifShowTab(tab){
  _notifTab=tab;
  document.querySelectorAll("#ntabPush,#ntabTemplates,#ntabTest").forEach(function(e){e.classList.remove("bp")});
  var el=document.getElementById("ntab"+tab.charAt(0).toUpperCase()+tab.slice(1));
  if(el)el.classList.add("bp");
  if(tab==="push")notifShowPush();
  else if(tab==="templates")notifShowTemplates();
}

function notifShowPush(){
  var ct=document.getElementById("notifContent");
  ct.innerHTML='<div class="ca"><div class="ct">Manual Push Notification</div><div class="cb">'
    +'<div class="f"><label>Target Users</label><select id="notifTarget" style="flex:1" onchange="notifToggleUserIds()">'
    +'<option value="all">All Users（active=1）</option>'
    +'<option value="self">Myself Only（Admin Test）</option>'
    +'<option value="user_ids">Specific UserID（Comma Separated）</option>'
    +'</select></div>'
    +'<div id="notifUserIdsWrap" style="display:none" class="f"><label>UserID</label><input id="notifUserIds" placeholder="e.g.: 1,2,3" style="flex:1"></div>'
    +'<div class="f"><label>Type</label><select id="notifType" style="flex:1">'
    +'<option value="system">System Notification</option><option value="reward">Reward Notification</option><option value="promo">Campaign Notice</option><option value="event">Event Notification</option>'
    +'</select></div>'
    +'<div class="f"><label>Title</label><input id="notifTitle" placeholder="Notification Title" style="flex:1"></div>'
    +'<div class="f"><label>Content</label><textarea id="notifContent_" rows="4" placeholder="Notification Content，SupportHTML" style="flex:1;min-height:80px"></textarea></div>'
    +'<div class="f"><label>Redirect Link</label><input id="notifLink" placeholder="Optional，如 /user/coupons" style="flex:1"></div>'
    +'<div class="f"><label></label><button class="btn bp" onclick="notifSend()">📤 Send Notification</button> '
    +'<span id="notifSendResult" style="font-size:12px;color:var(--dim)"></span></div>'
    +'</div></div>';
}

function notifToggleUserIds(){
  var v=document.getElementById("notifTarget").value;
  document.getElementById("notifUserIdsWrap").style.display=v==="user_ids"?"flex":"none";
}

function notifSend(){
  var resultEl=document.getElementById("notifSendResult");
  resultEl.textContent="Sending...";
  var targetType=document.getElementById("notifTarget").value;
  var userIds=[];
  if(targetType==="user_ids"){
    var raw=document.getElementById("notifUserIds").value;
    userIds=raw.split(",").map(function(s){return parseInt(s.trim())}).filter(function(n){return!isNaN(n)});
    if(userIds.length===0){resultEl.textContent="Enter a valid user ID";return}
  }
  var data={
    target_type: targetType,
    user_ids: userIds,
    title: document.getElementById("notifTitle").value,
    content: document.getElementById("notifContent_").value,
    link_url: document.getElementById("notifLink").value,
    type: document.getElementById("notifType").value
  };
  if(!data.title||!data.content){resultEl.textContent="Title and content are required";return}
  fetch("/admin/notifications/send", {
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(data)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success)resultEl.textContent="Sent "+d.sent+"/"+d.total+" 条";
    else resultEl.textContent="Send failed: "+(d.error||"Unknown Error");
  }).catch(function(){resultEl.textContent="Request Failed"});
}

function notifTest(){
  fetch("/admin/notifications/test", {
    method:"POST",
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success)showToast("Test Notification Sent!");
    else showToast("Failed to send: "+(d.error||""),"error");
  }).catch(function(){showToast("Request Failed","error")});
}

function notifShowTemplates(){
  var ct=document.getElementById("notifContent");
  ct.innerHTML='<div class="lo">Loading......</div>';
  fetch("/admin/notifications/templates", {
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){ct.innerHTML='<div class="em">Load failed</div>';return}
    var h='<div class="ca"><div class="ct">Push Template Management</div><div class="cb">';
    h+='<table><tr><th>Event Type</th><th>Title Template</th><th>Content Template</th><th>Type</th><th>Status</th><th>Actions</th></tr>';
    if(d.data.length===0)h+='<tr><td colspan="6" class="em">No Templates</td></tr>';
    d.data.forEach(function(t){
      h+='<tr>';
      h+='<td style="font-family:mono;font-size:11px">'+esc(t.event_type)+'</td>';
      h+='<td>'+esc(t.title_template)+'</td>';
      h+='<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">'+esc(t.content_template)+'</td>';
      h+='<td>'+esc(t.type)+'</td>';
      h+='<td>'+(t.is_active?'<span class="g">Enabled</span>':'<span class="r">Disable</span>')+'</td>';
      h+='<td><button class="btn btn-sm" onclick="notifToggleTemplate('+t.id+','+(t.is_active?0:1)+')">'+(t.is_active?"Disable":"Enabled")+'</button> ';
      h+='<button class="btn btn-sm" onclick="notifEditTemplate('+t.id+',\'"+esc(t.event_type)+"\',\'"+esc(t.title_template)+"\',\'"+esc(t.content_template)+"\',\'"+esc(t.link_url_template||"")+"\',\'"+t.type+"\')">Edit</button></td>';
      h+='</tr>';
    });
    h+='</table>';
    h+='<div style="margin-top:12px"><button class="btn bp" onclick="notifNewTemplate()">+ New Template</button></div>';
    h+='</div></div>';
    ct.innerHTML=h;
  }).catch(function(){ct.innerHTML='<div class="em">Load failed</div>'});
}

function notifToggleTemplate(tid,newState){
  fetch("/admin/notifications/templates/"+tid,{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({is_active:newState})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success)notifShowTemplates();
    else showToast("Operation Failed","error");
  }).catch(function(){showToast("Request Failed","error")});
}

function notifNewTemplate(){
  var eventType=prompt("Event Type（如 user.realname_verified）:");
  if(!eventType)return;
  var titleTmpl=prompt("Title Template（Support {variable} Variables）:");
  if(!titleTmpl)return;
  var contentTmpl=prompt("Content Template（Support {variable} Variables）:");
  if(!contentTmpl)return;
  var linkTmpl=prompt("Redirect Link Template（Optional）:")||"";
  fetch("/admin/notifications/templates",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({event_type:eventType,title_template:titleTmpl,content_template:contentTmpl,link_url_template:linkTmpl})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success)notifShowTemplates();
    else showToast("Creation Failed: "+(d.error||""),"error");
  }).catch(function(){showToast("Request Failed","error")});
}

function notifEditTemplate(){
  // Use modal overlay for editing
  var args=Array.prototype.slice.call(arguments);
  var tid=args[0],eventType=args[1],titleTmpl=args[2],contentTmpl=args[3],linkTmpl=args[4]||"",ntype=args[5]||"system";
  var overlay=document.createElement("div");
  overlay.style.cssText="position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:200;display:flex;align-items:center;justify-content:center";
  overlay.innerHTML='<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;width:560px;max-height:80vh;overflow-y:auto">'
    +'<div style="font-size:16px;font-weight:700;margin-bottom:16px">Edit Template #'+tid+'</div>'
    +'<div class="f"><label>Event Type</label><input id="nt_evt" value="'+escAttr(eventType)+'" style="flex:1"></div>'
    +'<div class="f"><label>Title Template</label><input id="nt_title" value="'+escAttr(titleTmpl)+'" style="flex:1"></div>'
    +'<div class="f"><label>Content Template</label><textarea id="nt_content" rows="4" style="flex:1;min-height:80px">'+escAttr(contentTmpl)+'</textarea></div>'
    +'<div class="f"><label>Redirect Template</label><input id="nt_link" value="'+escAttr(linkTmpl)+'" style="flex:1"></div>'
    +'<div class="f"><label>Type</label><select id="nt_type" style="flex:1">'
    +'<option value="system"'+(ntype==="system"?" selected":"")+'>System</option>'
    +'<option value="reward"'+(ntype==="reward"?" selected":"")+'>Reward</option>'
    +'<option value="promo"'+(ntype==="promo"?" selected":"")+'>Campaign</option>'
    +'<option value="event"'+(ntype==="event"?" selected":"")+'>Event</option></select></div>'
    +'<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">'
    +'<button class="btn" onclick="this.closest(\'[style*=\"fixed\"]\').remove()">Cancel</button>'
    +'<button class="btn bp" onclick="notifSaveTemplate('+tid+')">Save</button></div></div>';
  document.body.appendChild(overlay);
}

function notifSaveTemplate(tid){
  var data={
    event_type: document.getElementById("nt_evt").value,
    title_template: document.getElementById("nt_title").value,
    content_template: document.getElementById("nt_content").value,
    link_url_template: document.getElementById("nt_link").value,
    type: document.getElementById("nt_type").value
  };
  if(!data.event_type||!data.title_template||!data.content_template){showToast("Required fields cannot be empty","error");return}
  fetch("/admin/notifications/templates/"+tid,{
    method:"PUT",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify(data)
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      document.querySelector("[style*=\"fixed\"]")?.remove();
      notifShowTemplates();
    }else showToast("Save failed: "+(d.error||""),"error");
  }).catch(function(){showToast("Request Failed","error")});
}

// ══════════════════════════════════════════════
// Completion Reward Rule Management
// ══════════════════════════════════════════════

window.l_reward_rules=function(){
  document.getElementById("pt").textContent="Completion Reward Rules";
  var h='<div style="margin-bottom:12px"><button class="btn bp" onclick="rrShowForm()">+ New Rule</button></div>';
  h+='<div id="rrForm" style="display:none;margin-bottom:16px" class="cd"><div class="st" id="rrFormTitle">New Rule</div>';
  h+='<div class="field"><label>Rule Name</label><input type="text" id="rrName" placeholder="e.g.：Verification Reward" style="flex:1;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px"></div>';
  h+='<div class="field"><label>Trigger Condition</label><select id="rrCondition" style="flex:1;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px">';
  h+='<option value="completion_percentage|100">Progress 100%</option>';
  h+='<option value="completion_percentage|50">Progress ≥ 50%</option>';
  h+='<option value="phone_verified|1">Phone Verified</option>';
  h+='<option value="email_verified|1">Email Verified</option>';
  h+='<option value="has_profile|1">Fill in Details</option>';
  h+='<option value="avatar_set|1">Set Avatar</option>';
  h+='</select></div>';
  h+='<div class="field"><label>Reward Type</label><select id="rrRewardType" style="flex:1;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px" onchange="rrLoadCoupons()">';
  h+='<option value="coupon">Coupon</option>';
  h+='</select></div>';
  h+='<div class="field"><label>Select Coupon</label><select id="rrCoupon" style="flex:1;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px"><option value="">Select Coupons</option></select></div>';
  h+='<div class="field"><label>Reward Name</label><input type="text" id="rrRewardName" placeholder="User-visible Name" style="flex:1;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px"></div>';
  h+='<div class="field"><label>Sort</label><input type="number" id="rrSort" value="0" style="width:80px;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:4px;padding:6px 8px"></div>';
  h+='<div class="field"><label>Enabled</label><label class="sw"><input type="checkbox" id="rrActive" checked><span class="sl"></span></label></div>';
  h+='<div style="display:flex;gap:8px;margin-top:12px"><button class="btn bp" id="rrSaveBtn" onclick="rrSave()">Save</button><button class="btn" onclick="rrHideForm()">Cancel</button></div>';
  h+='</div>';
  h+='<div id="rrList"><div class="lo"><div class="s"></div>Loading......</div></div>';
  document.getElementById("mc").innerHTML=h;
  rrLoadList();
  rrLoadCoupons();
};

var rrEditingId=null;

function rrShowForm(data){
  rrEditingId=data?data.id:null;
  document.getElementById("rrFormTitle").textContent=data?'Edit Rule':'New Rule';
  document.getElementById("rrForm").style.display='block';
  document.getElementById("rrName").value=data?data.name:'';
  document.getElementById("rrRewardName").value=data?data.reward_name||'':'';
  document.getElementById("rrSort").value=data?data.sort_order||0:0;
  document.getElementById("rrActive").checked=data?data.is_active==1:true;
  if(data){
    document.getElementById("rrCondition").value=data.condition_key+'|'+data.condition_value;
    document.getElementById("rrRewardType").value=data.reward_type||'coupon';
  }
  rrLoadCoupons(data?data.reward_id:null);
}

function rrHideForm(){document.getElementById("rrForm").style.display='none';rrEditingId=null}

function rrLoadList(){
  fetch("/admin/reward-rules",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success||!d.data){document.getElementById("rrList").innerHTML='<div class="em">Load failed</div>';return}
    var rules=d.data;
    if(rules.length===0){document.getElementById("rrList").innerHTML='<div class="em" style="padding:40px;text-align:center;color:var(--muted)">No Reward Rules — Click"New Rule"Add</div>';return}
    var h='<table class="t"><thead><tr><th>Name</th><th>Trigger Condition</th><th>Reward</th><th>Sort</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
    var condNames={'completion_percentage|100':'Progress100%','completion_percentage|50':'Progress≥50%','phone_verified|1':'Phone Verification','email_verified|1':'Email Verification','has_profile|1':'Fill in Details','avatar_set|1':'Set Avatar'};
    rules.forEach(function(r){
      var cv=r.condition_key+'|'+r.condition_value;
      var cn=condNames[cv]||r.condition_key;
      h+='<tr><td>'+esc(r.name)+'</td><td>'+esc(cn)+'</td><td>'+esc(r.reward_name||'')+'</td><td>'+r.sort_order+'</td><td>'+(r.is_active?'<span class="tag tag-green">Enabled</span>':'<span class="tag">Disable</span>')+'</td>';
      h+='<td><button class="btn btn-sm" onclick="rrShowForm('+JSON.stringify(r).replace(/"/g,"'")+')">Edit</button> <button class="btn btn-sm btn-danger" onclick="rrDelete('+r.id+',\''+esc(r.name)+'\')">Delete</button></td></tr>';
    });
    h+='</tbody></table>';
    document.getElementById("rrList").innerHTML=h;
  }).catch(function(){document.getElementById("rrList").innerHTML='<div class="em">Load failed</div>'});
}

function rrLoadCoupons(selectedId){
  fetch("/subscription/admin/coupons",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    var sel=document.getElementById("rrCoupon");
    if(!sel)return;
    sel.innerHTML='<option value="">Select Coupons</option>';
    if(d.success&&d.coupons){
      d.coupons.forEach(function(c){
        sel.innerHTML+='<option value="'+c.id+'"'+(selectedId&&c.id==selectedId?' selected':'')+'>'+esc(c.code)+(c.type?(' ('+c.type+')'):'')+'</option>';
      });
    }
  }).catch(function(){});
}

function rrSave(){
  var name=document.getElementById("rrName").value.trim();
  if(!name){showToast("Enter rule name","error");return}
  var cond=document.getElementById("rrCondition").value.split('|');
  var key=cond[0],val=cond[1];
  var rid=document.getElementById("rrCoupon").value;
  var data={
    name:name, condition_key:key, condition_value:val,
    reward_type:document.getElementById("rrRewardType").value,
    reward_id:rid?parseInt(rid):null,
    reward_name:document.getElementById("rrRewardName").value.trim(),
    sort_order:parseInt(document.getElementById("rrSort").value)||0,
    is_active:document.getElementById("rrActive").checked
  };
  var url="/admin/reward-rules";
  var method="POST";
  if(rrEditingId){url+="/"+rrEditingId;method="PUT"}
  fetch(url,{method:method,headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("Saved");rrHideForm();rrLoadList()}
    else showToast("Save failed: "+(d.error||""),"error");
  }).catch(function(){showToast("Request Failed","error")});
}

function rrDelete(id,name){
  if(!confirm('Confirm Deletion Rule "'+name+'"? Related Claim Records Will Also Be Cleared。'))return;
  fetch("/admin/reward-rules/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("Deleted");rrLoadList()}
    else showToast("Delete failed","error");
  }).catch(function(){showToast("Request Failed","error")});
}

// ═══════════ Model Management（Provider → Models Two Levels） ═══════════

window.l_model_providers=function(){
  document.getElementById("pt").textContent="Model Management";
  mpRefresh();
};

function mpRefresh(){
  fetch("/admin/providers",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success){document.getElementById("mc").innerHTML='<div class="em">Load failed</div>';return}
    var h='<div class="cd" style="margin-bottom:12px">';
    h+='<div class="st">Model Management</div>';
    h+='<div id="mpAddForm" style="display:none"></div>';
    if(!d.data||!d.data.length){
      h+='<div class="em">No Models Settings</div>';
    }else{
      var caps={'text':'Text','image':'Image','voice':'Voice','video':'Video','tts':'TTS'};
      d.data.forEach(function(p){
        h+='<div style="margin-bottom:16px;border:1px solid var(--border);border-radius:8px;overflow:hidden">';
        h+='<div style="background:var(--bg2);padding:8px 12px;display:flex;justify-content:space-between;align-items:center">';
        h+='<div><b>'+esc(p.name)+'</b> <span style="font-size:10px;color:var(--dim)">('+esc(p.slug)+')</span>'+(p.description?' — '+esc(p.description):'')+'</div>';
        h+='<button class="btn bp bs" onclick="mpShowAddModel('+p.id+',\''+escJs(p.name)+'\')">+ Add Model</button>';
        h+='</div>';
        if(!p.models||!p.models.length){
          h+='<div class="em" style="margin:8px">No Models</div>';
        }else{
          h+='<table style="margin:0"><tr><th>Name</th><th>Model Name</th><th>Endpoint</th><th>Key</th><th>Ability</th><th>Status</th><th>Actions</th></tr>';
          p.models.forEach(function(m){
            h+='<tr>';
            h+='<td>'+esc(m.name)+'</td>';
            h+='<td><code style="font-size:10px;color:var(--accent)">'+esc(m.model_name)+'</code></td>';
            h+='<td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px;color:var(--dim)">'+esc(m.endpoint_url||'—')+'</td>';
            h+='<td><code style="font-size:10px">'+esc(m.api_key_ref||'—')+'</code></td>';
            h+='<td>'+esc(caps[m.capabilities]||m.capabilities)+'</td>';
            h+='<td>'+(m.is_active?'<span class="bdg on">Enabled</span>':'<span class="bdg off">Disable</span>')+'</td>';
            h+='<td><button class="btn bo bs" onclick="mpShowEditModel('+m.id+')">Edit</button> ';
            h+='<button class="btn bo bs" style="color:#f85149" onclick="mpDeleteModel('+m.id+',\''+escJs(m.name)+'\')">Delete</button></td>';
            h+='</tr>';
          });
          h+='</table>';
        }
        h+='</div>';
      });
    }
    h+='</div>';
    document.getElementById("mc").innerHTML=h;
  }).catch(function(e){
    document.getElementById("mc").innerHTML='<div class="em">Request Failed — Check Network or<a href="javascript:go(\'model_providers\')">Refresh &amp; Retry</a><br><span style="font-size:10px;color:var(--dim)">'+esc(String(e))+'</span></div>';
  });
}

function mpShowAddModel(providerId, providerName){
  var f=document.getElementById("mpAddForm");
  f.style.display="block";
  f.innerHTML='<div class="cd" style="margin-bottom:12px">'+
    '<div class="st">Add Model — '+esc(providerName)+'</div>'+
    '<input type="hidden" id="mpEditId" value="">'+
    '<input type="hidden" id="mpProvId" value="'+providerId+'">'+
    '<div class="g2">'+
    '<div><div style="font-size:11px;color:var(--dim)">Display Name *</div><input class="in" id="mpName" placeholder="如：Voice Cloning v2" style="width:100%"></div>'+
    '<div><div style="font-size:11px;color:var(--dim)">Model Name</div><input class="in" id="mpModelName" placeholder="如：volc-voice-clone-v2" style="width:100%"></div>'+
    '<div><div style="font-size:11px;color:var(--dim)">Ability Type</div><select class="sl" id="mpCaps" style="width:100%"><option value="text">Text</option><option value="image">Image</option><option value="voice">Voice</option><option value="tts">TTS</option><option value="video">Video</option></select></div>'+
    '<div><div style="font-size:11px;color:var(--dim)">API Key Reference</div><input class="in" id="mpKeyRef" placeholder="如：volcengine_credentials" style="width:100%"></div>'+
    '</div>'+
    '<div style="margin-top:8px"><div style="font-size:11px;color:var(--dim)">API Endpoint</div><input class="in" id="mpUrl" placeholder="https://openspeech.bytedance.com/api/v1/tts" style="width:100%"></div>'+
    '<div style="margin-top:10px"><button class="btn bp" onclick="mpCreateModel()">Save</button> <button class="btn bo" onclick="document.getElementById(\'mpAddForm\').style.display=\'none\'">Cancel</button></div>'+
    '</div>';
}

function mpShowEditModel(id){
  fetch("/admin/provider-models",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    var m=null;
    if(d.data) d.data.forEach(function(x){if(x.id==id)m=x});
    if(!m){showToast("Model not found","error");return}
    var f=document.getElementById("mpAddForm");
    f.style.display="block";
    f.innerHTML='<div class="cd" style="margin-bottom:12px">'+
      '<div class="st">Edit Model</div>'+
      '<input type="hidden" id="mpEditId" value="'+m.id+'">'+
      '<input type="hidden" id="mpProvId" value="'+m.provider_id+'">'+
      '<div class="g2">'+
      '<div><div style="font-size:11px;color:var(--dim)">Display Name *</div><input class="in" id="mpName" value="'+escAttr(m.name)+'" style="width:100%"></div>'+
      '<div><div style="font-size:11px;color:var(--dim)">Model Name</div><input class="in" id="mpModelName" value="'+escAttr(m.model_name)+'" style="width:100%"></div>'+
      '<div><div style="font-size:11px;color:var(--dim)">Ability Type</div><select class="sl" id="mpCaps" style="width:100%">'+
        '<option value="text"'+(m.capabilities=='text'?' selected':'')+'>Text</option>'+
        '<option value="image"'+(m.capabilities=='image'?' selected':'')+'>Image</option>'+
        '<option value="voice"'+(m.capabilities=='voice'?' selected':'')+'>Voice</option>'+
        '<option value="tts"'+(m.capabilities=='tts'?' selected':'')+'>TTS</option>'+
        '<option value="video"'+(m.capabilities=='video'?' selected':'')+'>Video</option>'+
      '</select></div>'+
      '<div><div style="font-size:11px;color:var(--dim)">API Key Reference</div><input class="in" id="mpKeyRef" value="'+escAttr(m.api_key_ref||'')+'" style="width:100%"></div>'+
      '</div>'+
      '<div style="margin-top:8px"><div style="font-size:11px;color:var(--dim)">API Endpoint</div><input class="in" id="mpUrl" value="'+escAttr(m.endpoint_url||'')+'" style="width:100%"></div>'+
      '<div style="margin-top:8px"><label style="font-size:11px"><input type="checkbox" id="mpActive"'+(m.is_active?' checked':'')+'> Enabled</label></div>'+
      '<div style="margin-top:10px"><button class="btn bp" onclick="mpUpdateModel()">Save</button> <button class="btn bo" onclick="document.getElementById(\'mpAddForm\').style.display=\'none\'">Cancel</button></div>'+
      '</div>';
  }).catch(function(){showToast("Request Failed","error")});
}

function mpCreateModel(){
  var name=document.getElementById("mpName").value.trim();
  if(!name){showToast("Name is required","error");return}
  var data={
    name:name,
    provider_id:parseInt(document.getElementById("mpProvId").value),
    model_name:document.getElementById("mpModelName").value.trim(),
    endpoint_url:document.getElementById("mpUrl").value.trim(),
    api_key_ref:document.getElementById("mpKeyRef").value.trim(),
    capabilities:document.getElementById("mpCaps").value
  };
  fetch("/admin/provider-models",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("Added");mpRefresh()}
    else showToast("Add Failed: "+(d.error||""),"error");
  }).catch(function(){showToast("Request Failed","error")});
}

function mpUpdateModel(){
  var id=document.getElementById("mpEditId").value;
  var name=document.getElementById("mpName").value.trim();
  if(!name){showToast("Name is required","error");return}
  var data={
    name:name,
    provider_id:parseInt(document.getElementById("mpProvId").value),
    model_name:document.getElementById("mpModelName").value.trim(),
    endpoint_url:document.getElementById("mpUrl").value.trim(),
    api_key_ref:document.getElementById("mpKeyRef").value.trim(),
    capabilities:document.getElementById("mpCaps").value,
    is_active:document.getElementById("mpActive")?document.getElementById("mpActive").checked?1:0:1
  };
  fetch("/admin/provider-models/"+id,{method:"PUT",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify(data)})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("Updated");mpRefresh()}
    else showToast("Update Failed: "+(d.error||""),"error");
  }).catch(function(){showToast("Request Failed","error")});
}

function mpDeleteModel(id,name){
  if(!confirm('Confirm Deletion of Model "'+name+'"?'))return;
  fetch("/admin/provider-models/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.success){showToast("Deleted");mpRefresh()}
    else showToast("Delete failed","error");
  }).catch(function(){showToast("Request Failed","error")});
}

// ═══════════════════════════════════════════════════════════
//  Media Library — l_media_library
// ═══════════════════════════════════════════════════════════

window.l_media_library=function(){
  document.getElementById("pt").textContent="Media Library";
  loadMediaLibrary();
};

function loadMediaLibrary(){
  document.getElementById("mc").innerHTML='<div class="lo"><div class="s"></div>Loading......</div>';
  fetch("/admin/media-library/list",{headers:{"Authorization":"Bearer "+T}})
  .then(function(r){return r.json()})
  .then(function(d){
    if(!d.success){document.getElementById("mc").innerHTML='<div class="em">Load failed: '+esc(d.error)+'</div>';return}
    renderMediaLibrary(d.data);
  }).catch(function(){document.getElementById("mc").innerHTML='<div class="em">Request Failed</div>'});
}

var _mlAllItems=[];
function mlApplyFilter(){
  var txt=document.getElementById("mlFilterText").value.toLowerCase().trim();
  var tp=document.getElementById("mlFilterType").value;
  var grid=document.getElementById("mlGrid");
  if(!grid)return;
  var filtered=_mlAllItems.filter(function(f){
    if(tp&&!f.mime_type.startsWith(tp+'/'))return false;
    if(txt&&f.original_name.toLowerCase().indexOf(txt)===-1)return false;
    return true;
  });
  renderMediaGrid(grid,filtered);
  document.getElementById("mlFilterCount").textContent='Filter: '+filtered.length+'/'+_mlAllItems.length;
}
function renderMediaGrid(grid,items){
  var h='';
  items.forEach(function(f){
    var isV=f.mime_type&&f.mime_type.startsWith('video/'),isA=f.mime_type&&f.mime_type.startsWith('audio/'),isI=f.mime_type&&f.mime_type.startsWith('image/');
    var icon=isV?'🎬':isA?'🎵':isI?'🖼️':'📄',thumb='';
    if(isI)thumb='<img src="/static/'+esc(f.file_path)+'" style="width:100%;height:100px;object-fit:cover;border-radius:6px 6px 0 0">';
    else if(f.thumb_path)thumb='<img src="/static/'+esc(f.thumb_path)+'" style="width:100%;height:100px;object-fit:cover;border-radius:6px 6px 0 0">';
    else thumb='<div style="width:100%;height:100px;display:flex;align-items:center;justify-content:center;font-size:36px;background:var(--bg);border-radius:6px 6px 0 0">'+icon+'</div>';
    h+='<div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden">'+thumb;
    h+='<div style="padding:8px">';
    h+='<div style="font-size:12px;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="'+esc(f.original_name)+'">'+esc(f.original_name)+(f.push_status==='done'?' ✅':'')+'</div>';
    h+='<div style="font-size:11px;color:var(--dim);margin:4px 0">'+formatSize(f.file_size)+'</div>';
    h+='<div style="display:flex;gap:4px">';
    h+='<button class="btn bo bs" style="font-size:10px;padding:2px 6px" onclick="mlPreview('+f.id+')">👁</button>';
    h+='<button class="btn bo bs" style="font-size:10px;padding:2px 6px" onclick="mlDownload('+f.id+')">⬇</button>';
    h+='<button class="btn bo bs" style="font-size:10px;padding:2px 6px" onclick="mlShowPush('+f.id+',\''+esc(f.original_name)+'\')">📤</button>';
    h+='<button class="btn bo bs" style="font-size:10px;padding:2px 6px;color:#f85149" onclick="mlDelete('+f.id+',\''+esc(f.original_name)+'\')">🗑</button>';
    h+='</div></div></div>';
  });
  grid.innerHTML=h||'<div style="text-align:center;padding:40px;color:var(--dim);grid-column:1/-1">No Matching Files</div>';
}
function formatSize(b){
  if(b<1024)return b+" B";
  if(b<1048576)return (b/1024).toFixed(1)+" KB";
  if(b<1073741824)return (b/1048576).toFixed(1)+" MB";
  return (b/1073741824).toFixed(2)+" GB";
}

function renderMediaLibrary(items){
  var h='';
  h+='<div class="cd" style="margin-bottom:16px"><div class="st">Upload Media</div>';
  h+='<div id="mlUploadZone" style="border:2px dashed var(--border);border-radius:var(--radius);padding:32px 24px;text-align:center;cursor:pointer;background:var(--card)"';
  h+=' onclick="document.getElementById(\'mlFileInput\').click()"';
  h+=' ondragover="event.preventDefault();this.style.borderColor=\'var(--accent)\'"';
  h+=' ondragleave="this.style.borderColor=\'var(--border)\'" ondrop="mlHandleDrop(event)">';
  h+='<div style="font-size:32px;margin-bottom:8px">📁</div>';
  h+='<div style="color:var(--text);margin-bottom:4px">Drag &amp; Drop Files Here，Or Click to Select</div>';
  h+='<div style="font-size:11px;color:var(--dim)">Video/Audio/Image，Max 500MB。FFmpeg Local Run，Server Only Stores &amp; Distributes</div>';
  h+='<input type="file" id="mlFileInput" style="display:none" onchange="mlUploadFile(event)" accept="video/*,audio/*,image/*,.mp4,.mp3,.wav,.ogg,.mov,.avi,.webm,.mkv,.flv,.m4v">';
  h+='</div><div id="mlUploadStatus" style="margin-top:8px;font-size:12px"></div></div>';
  _mlAllItems=items||[];
  setTimeout(function(){mlApplyFilter()},50);

  h+='<div class="cd"><div class="st">Media Library <span style="font-weight:400;font-size:11px;color:var(--dim)">共 '+items.length+' Files</span></div>';
  h+='<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">';
  h+='<input class="in" id="mlFilterText" placeholder="Search File Name..." style="flex:1;min-width:120px;font-size:12px;padding:6px 10px" onkeyup="mlApplyFilter()">';
  h+='<select class="sl" id="mlFilterType" onchange="mlApplyFilter()" style="font-size:12px;padding:6px 10px"><option value="">All Types</option><option value="image">🖼 Image</option><option value="video">🎬 Video</option><option value="audio">🎵 Audio</option></select>';
  h+='<span style="font-size:11px;color:var(--dim);align-self:center" id="mlFilterCount"></span></div>';
  h+='<div id="mlGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px">';
  h+='</div>';
  h+='</div>';
  document.getElementById("mc").innerHTML=h;
}

function mlHandleDrop(e){e.preventDefault();e.target.style.borderColor='var(--border)';if(e.dataTransfer.files[0])mlDoUpload(e.dataTransfer.files[0])}
function mlUploadFile(e){var f=e.target.files[0];if(!f)return;mlDoUpload(f);e.target.value=''}
function mlDoUpload(file){
  if(file.size>524288000){showToast("File exceeds 500MB","error");return}
  var st=document.getElementById("mlUploadStatus");st.innerHTML='<span style="color:var(--accent)">Uploading...</span>';
  var fd=new FormData();fd.append('file',file);
  fetch("/admin/media-library/upload",{method:"POST",headers:{"Authorization":"Bearer "+T},body:fd})
  .then(function(r){return r.json()})
  .then(function(d){if(d.success){st.innerHTML='<span style="color:var(--green)">✅ Upload Successful</span>';loadMediaLibrary()}else st.innerHTML='<span style="color:var(--rose)">❌ '+(d.error||'')+'</span>'})
  .catch(function(){st.innerHTML='<span style="color:var(--rose)">❌ Upload failed</span>'});
  setTimeout(function(){st.innerHTML=''},5000);
}
function mlPreview(id){mlGetItem(id,function(f){
  var u="/admin/media-library/"+id+"/download",h='<div style="max-width:800px;margin:0 auto">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><div class="st" style="margin:0">'+esc(f.original_name)+'</div><button class="btn bo" onclick="loadMediaLibrary()">✕</button></div>';
  if(f.mime_type&&f.mime_type.startsWith('video/'))h+='<video src="'+u+'" controls style="width:100%;max-height:500px;border-radius:var(--radius);background:#000" autoplay></video>';
  else if(f.mime_type&&f.mime_type.startsWith('audio/'))h+='<audio src="'+u+'" controls style="width:100%"></audio>';
  else if(f.mime_type&&f.mime_type.startsWith('image/'))h+='<img src="'+u+'" style="max-width:100%;max-height:500px;border-radius:var(--radius)">';
  else h+='<div class="cd"><a href="'+u+'" target="_blank">Download File</a></div>';
  h+='</div>';document.getElementById("mc").innerHTML=h;
})}
function mlDownload(id){window.open("/admin/media-library/"+id+"/download","_blank")}
function mlShowPush(id,name){mlGetItem(id,function(f){
  var h='<div class="cd" style="max-width:420px;margin:0 auto">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px"><div class="st" style="margin:0">Push: '+esc(name)+'</div><button class="btn bo" onclick="loadMediaLibrary()">✕</button></div>';
  h+='<div style="display:flex;gap:8px"><button class="btn bo" style="flex:1;padding:12px" onclick="mlDoPush('+id+',\'feishu\')">📱 Feishu Group</button><button class="btn bo" style="flex:1;padding:12px" onclick="mlDoPush('+id+',\'wecom\')">💬 WeCom</button></div>';
  h+='<div id="mlPushStatus" style="margin-top:12px;font-size:12px"></div></div>';
  document.getElementById("mc").innerHTML=h;
})}
function mlGetItem(id,cb){fetch("/admin/media-library/list",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(d.success){var f=d.data.find(function(x){return x.id===id});if(f)cb(f)}})}
function mlDoPush(id,target){var st=document.getElementById("mlPushStatus");if(!st)return;st.innerHTML='Pushing...';fetch("/admin/media-library/"+id+"/push",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({target:target})}).then(function(r){return r.json()}).then(function(d){if(d.success){setTimeout(loadMediaLibrary,1500)}else st.innerHTML='❌ '+esc(d.error||'Push Failed')}).catch(function(){st.innerHTML='❌ Push failed'})}
function mlDelete(id,name){if(!confirm('Confirm Delete "'+name+'" 吗？'))return;fetch("/admin/media-library/"+id,{method:"DELETE",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){if(d.success){showToast("Deleted");loadMediaLibrary()}else showToast(d.error||"Delete failed","error")})}

// 🧹 Data Cleaning Agent

window.l_cleaner=function(){
  var c=document.getElementById("mc"),h='';
  h+='<div style="max-width:960px;margin:0 auto;padding:20px">';
  h+='<h2 style="margin-bottom:20px">🧹 Data Cleaning Agent</h2>';
  h+='<p style="color:var(--dim);margin-bottom:20px">Paste Raw Content（Article、Whitepaper、Industry Background etc.），AIAuto-clean into Structured KB Entries。Cleaned Knowledge Auto-synced to Mini ProgramAICS &amp; This SiteAICS Agent。</p>';

  // Submit Area
  h+='<div class="card" style="padding:20px;margin-bottom:20px">';
  h+='<h3 style="margin-bottom:12px">📝 Submit Raw Content</h3>';
  h+='<textarea id="cleanerInput" style="width:100%;min-height:200px;padding:12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--fg);font-size:14px;resize:vertical" placeholder="Paste Article、Whitepaper、Industry Analysis etc...."></textarea>';
  h+='<div style="display:flex;gap:10px;margin-top:12px">';
  h+='<button onclick="cleanerSubmit()" style="padding:10px 24px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer">📤 Submit for Cleaning</button>';
  h+='<button onclick="cleanerRunAll()" style="padding:10px 24px;background:var(--bg2);color:var(--fg);border:1px solid var(--border);border-radius:6px;cursor:pointer">▶ Batch Clean All</button>';
  h+='</div></div>';

  // Queue List
  h+='<div class="card" style="padding:20px">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">';
  h+='<h3>📋 Cleaning Queue</h3>';
  h+='<div style="display:flex;gap:6px">';
  h+='<button class="tb" onclick="cleanerLoad()">🔄 Refresh</button>';
  h+='<select id="cleanerFilter" onchange="cleanerLoad()" style="padding:6px 10px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--fg)">';
  h+='<option value="">All</option><option value="pending">Pending</option><option value="cleaning">Cleaning</option><option value="done">Completed</option><option value="failed">Failed</option>';
  h+='</select></div></div>';
  h+='<div id="cleanerList"><div class="em">Loading......</div></div></div>';
  h+='</div>';
  c.innerHTML=h;
  cleanerLoad();
};

function cleanerSubmit(){
  var input=document.getElementById("cleanerInput");
  var txt=(input.value||'').trim();
  if(!txt){showToast("Content cannot be empty","error");return}
  fetch("/shop/cleaner/submit",{method:"POST",headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},body:JSON.stringify({content:txt})}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ Added to Cleaning Queue (#"+d.data.id+")","success");input.value='';cleanerLoad()}
    else showToast(d.error||"Submit Failed","error")
  }).catch(function(){showToast("Submit Failed","error")})
}

function cleanerRunAll(){
  if(!confirm("Batch clean all pending items?"))return;
  fetch("/shop/cleaner/run-all",{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ "+d.message,"success");cleanerLoad()}
    else showToast(d.error||"Batch cleanup failed","error")
  }).catch(function(){showToast("Batch cleanup failed","error")})
}

function cleanerRun(id){
  fetch("/shop/cleaner/run/"+id,{method:"POST",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("✅ "+d.message,"success");cleanerLoad()}
    else showToast(d.error||"Cleanup failed","error")
  }).catch(function(){showToast("Cleanup failed","error")})
}

function cleanerViewResult(id){
  fetch("/shop/cleaner/list?status=",{method:"GET",headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success)return;
    var item=d.data.find(function(x){return x.id===id});
    if(!item){showToast("Record not found","error");return}
    alert("Raw Content:\n"+(item.raw_content||'').substring(0,500)+"...\n\nStatus: "+item.status+"\nKnowledge BaseID: "+(item.cleaned_id||'-')+"\nError: "+(item.error_msg||'无'))
  })
}

function cleanerLoad(){
  var list=document.getElementById("cleanerList");
  if(!list)return;
  var filter=document.getElementById("cleanerFilter");
  var statusParam=filter?filter.value:'';
  list.innerHTML='<div class="em">Loading......</div>';
  fetch("/shop/cleaner/list"+(statusParam?'?status='+statusParam:''),{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success||!d.data){list.innerHTML='<div class="em">No data</div>';return}
    var items=d.data;
    if(!items.length){list.innerHTML='<div class="em">No data</div>';return}
    var h='<table class="dt"><thead><tr><th>ID</th><th>Status</th><th>Source</th><th>Content Preview</th><th>Knowledge BaseID</th><th>Time</th><th>Actions</th></tr></thead><tbody>';
    items.forEach(function(r){
      var statusClass=r.status==='done'?'sc-done':(r.status==='failed'?'sc-failed':(r.status==='cleaning'?'sc-pending':'sc-pending'));
      var statusLabel=r.status==='done'?'✅ Completed':(r.status==='failed'?'❌ Failed':(r.status==='cleaning'?'⏳ Cleaning':'⏸ Pending'));
      h+='<tr><td>'+r.id+'</td><td><span class="status-badge '+statusClass+'">'+statusLabel+'</span></td>';
      h+='<td>'+(r.source||'manual')+'</td>';
      h+='<td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc((r.raw_content||'').substring(0,80))+'</td>';
      h+='<td>'+(r.cleaned_id||'-')+'</td>';
      h+='<td>'+(r.created_at||'')+'</td>';
      h+='<td>';
      if(r.status==='pending') h+='<button onclick="cleanerRun('+r.id+')" class="tb">▶ Execute</button> ';
      h+='<button onclick="cleanerViewResult('+r.id+')" class="tb">👁 View</button>';
      h+='</td></tr>'
    });
    h+='</tbody></table>';
    list.innerHTML=h;
  }).catch(function(){list.innerHTML='<div class="em">Load failed</div>'})
}

// ============================
// Deploy Code Management — l_deploy
// ============================

window.l_deploy=function(){
  document.getElementById("pt").textContent="Deploy Code Management";
  var h='<div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap">';
  h+='<button class="btn bp" onclick="showDeployForm()">+ Generate Code</button>';
  h+='<button class="btn bo" onclick="refreshDeployList()">🔄 Refresh</button></div>';
  h+='<div id="deployForm" style="display:none;margin-bottom:16px" class="cd"><div class="st">Generate Code</div>';
  h+='<div class="g2">';
  h+='<div><div style="font-size:11px;color:var(--dim)">User ID</div><input class="in" id="dpUserId" type="number" min="1" value="1" style="width:100%"></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Plan</div><select class="in" id="dpPlanKey" style="width:100%"></select></div>';
  h+='<div><div style="font-size:11px;color:var(--dim)">Valid Period (天)</div><select class="in" id="dpDuration" style="width:100%"><option value="365">1 年</option><option value="730">2 年</option><option value="1095">3 年</option><option value="30">1 Months</option><option value="90">3 Months</option></select></div>';
  h+='<div style="display:flex;align-items:end;gap:8px"><button class="btn bp" onclick="doGenerateCode()">Confirm Generate</button> <button class="btn bo" onclick="hideDeployForm()">Cancel</button></div>';
  h+='</div></div>';
  h+='<div id="deployResult" style="display:none;margin-bottom:16px" class="cd"><div class="st">Deploy Code</div>';
  h+='<div style="font-size:24px;font-weight:700;text-align:center;padding:20px;letter-spacing:4px;font-family:monospace" id="deployCodeText"></div>';
  h+='<div style="text-align:center;margin-top:8px"><button class="btn bp" onclick="copyDeployCode()">📋 Copy</button></div></div>';
  h+='<div id="deployList"><div class="lo"><div class="s"></div></div></div>';
  document.getElementById("mc").innerHTML=h;
  fetch("/subscription/admin/plans",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    var sel=document.getElementById("dpPlanKey");
    if(d.success&&d.data&&d.data.plans){
      d.data.plans.forEach(function(p){
        var opt=document.createElement("option");
        opt.value=p.plan_key;
        opt.textContent=p.name+' ('+p.plan_key+')';
        sel.appendChild(opt);
      });
    }
  });
  refreshDeployList();
};

function refreshDeployList(){
  document.getElementById("deployList").innerHTML='<div class="lo"><div class="s"></div></div>';
  fetch("/api/subscription/admin/codes",{headers:{"Authorization":"Bearer "+T}}).then(function(r){return r.json()}).then(function(d){
    if(!d.success){document.getElementById("deployList").innerHTML='<div class="em">Load failed</div>';return}
    var rows=d.data||[];
    var h='<div class="cd"><div class="st">Deploy Codes ('+rows.length+')</div>';
    h+='<div style="overflow-x:auto"><table><tr><th>ID</th><th>Deploy Code</th><th>User</th><th>Plan</th><th>Status</th><th>Expires</th><th>Last Heartbeat</th><th>Hostname</th><th>Actions</th></tr>';
    if(!rows.length){h+='<tr><td colspan="9"><div class="em">No Deploy Code</div></td></tr>'}
    else{
      rows.forEach(function(r){
        var st='';
        if(r.status==='active') st='<span class="bdg on">Active</span>';
        else if(r.status==='used') st='<span class="bdg pd">Used</span>';
        else if(r.status==='expired') st='<span class="bdg off">Expired</span>';
        else if(r.status==='revoked') st='<span class="bdg off">Voided</span>';
        else st='<span class="bdg">'+esc(r.status)+'</span>';
        var revokeBtn=r.status==='active'?'<button class="btn bo bs" onclick="doRevokeCode('+r.id+')">Revoke</button>':'';
        h+='<tr><td>'+r.id+'</td><td style="font-family:monospace;font-size:12px">'+esc(r.code)+'</td>'+
          '<td>'+r.user_id+'</td><td style="font-family:monospace;font-size:11px">'+esc(r.plan_key)+'</td>'+
          '<td>'+st+'</td><td style="font-size:12px">'+(r.expires_at||'-')+'</td>'+
          '<td style="font-size:12px">'+(r.last_heartbeat||'-')+'</td><td style="font-size:11px;max-width:120px;overflow:hidden;text-overflow:ellipsis">'+(r.last_hostname||'')+'</td>'+
          '<td>'+revokeBtn+'</td></tr>';
      });
    }
    h+='</table></div></div>';
    document.getElementById("deployList").innerHTML=h;
  }).catch(function(){document.getElementById("deployList").innerHTML='<div class="em">Load failed</div>'});
}

function showDeployForm(){
  document.getElementById("deployForm").style.display="block";
  document.getElementById("deployResult").style.display="none";
}

function hideDeployForm(){
  document.getElementById("deployForm").style.display="none";
}

function doGenerateCode(){
  var userId=parseInt(document.getElementById("dpUserId").value)||1;
  var planKey=document.getElementById("dpPlanKey").value;
  var duration=parseInt(document.getElementById("dpDuration").value)||365;
  if(!planKey){showToast("Select a plan","error");return}
  fetch("/api/subscription/admin/codes/generate",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T,"Content-Type":"application/json"},
    body:JSON.stringify({user_id:userId,plan_key:planKey,duration_days:duration})
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){
      var code=d.data.code;
      document.getElementById("deployCodeText").textContent=code;
      document.getElementById("deployResult").style.display="block";
      document.getElementById("deployForm").style.display="none";
      showToast("Deploy code generated","success");
      refreshDeployList();
    }else{
      showToast(d.error||"Generation Failed","error");
    }
  }).catch(function(){showToast("Request Failed","error")});
}

function copyDeployCode(){
  var code=document.getElementById("deployCodeText").textContent;
  if(!code)return;
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(code).then(function(){showToast("Copied to clipboard","success")});
  }else{
    var ta=document.createElement("textarea");
    ta.value=code;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    showToast("Copied to clipboard","success");
  }
}

function doRevokeCode(id){
  if(!confirm("Void this deploy code? This cannot be undone!"))return;
  fetch("/api/subscription/admin/codes/"+id+"/revoke",{
    method:"POST",
    headers:{"Authorization":"Bearer "+T}
  }).then(function(r){return r.json()}).then(function(d){
    if(d.success){showToast("Voided","success");refreshDeployList()}
    else{showToast(d.error||"Revoke Failed","error")}
  }).catch(function(){showToast("Request Failed","error")});
}

// 函数别名：修复 PPT/图像生成/多媒体 的 loading 问题

window.l_ppt=window.l_ppt_gen;
window.l_image=window.l_media_video;
window.l_media_tools=window.l_media_video;


