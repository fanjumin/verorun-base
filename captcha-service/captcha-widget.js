/**
 * Captcha Widget — Vue3 slider puzzle CAPTCHA
 * Usage: <div id="captcha-widget" data-api="https://your-domain.com"></div>
 *         <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
 *         <script src="/captcha-widget.js"></script>
 */
(function() {
  const API_BASE = document.getElementById('captcha-widget')?.dataset?.api
    || window.location.origin;

  // Track state
  let app = null;
  let widgetEl = null;

  // Create widget container
  function createWidget() {
    const el = document.getElementById('captcha-widget');
    if (!el) return;

    widgetEl = el;

    const { createApp, ref, reactive, computed, onMounted, nextTick } = Vue;

    app = createApp({
      template: `
        <div class="captcha-root" :class="{ dark: isDark }">
          <!-- Captcha area -->
          <div class="captcha-box" @dragstart.prevent>
            <div class="captcha-image-area" ref="imageArea">
              <!-- Background -->
              <img v-if="bgSrc" :src="bgSrc" class="captcha-bg" ref="bgImg" />
              <div v-else class="captcha-bg captcha-loading">
                <div class="spinner"></div>
              </div>

              <!-- Puzzle piece -->
              <img v-if="puzzleSrc && !solved"
                   :src="puzzleSrc"
                   class="captcha-piece"
                   :style="pieceStyle"
                   ref="pieceImg" />

              <!-- Success overlay -->
              <div v-if="solved" class="captcha-success-overlay">
                <svg viewBox="0 0 24 24" class="success-icon">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" fill="currentColor"/>
                </svg>
              </div>

              <!-- Error shake -->
              <div v-if="errorShake" class="captcha-error-overlay">
                <svg viewBox="0 0 24 24" class="error-icon">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" fill="currentColor"/>
                </svg>
              </div>
            </div>

            <!-- Slider track -->
            <div class="slider-track" ref="sliderTrack"
                 @mousedown="startDrag" @touchstart.prevent="startTouchDrag">
              <div class="slider-fill" :style="{ width: sliderPercent + '%' }"></div>
              <div class="slider-thumb" :class="{ dragging: isDragging }"
                   :style="{ left: sliderPercent + '%' }"
                   @mousedown.prevent="startDrag"
                   @touchstart.prevent="startTouchDrag">
                <svg viewBox="0 0 24 24" class="thumb-icon">
                  <path d="M14 17l-5-5 5-5v10z" fill="currentColor"/>
                  <path d="M10 17l5-5-5-5v10z" fill="currentColor"/>
                </svg>
              </div>
              <span class="slider-label" v-if="!solved && !isDragging">
                {{ trackLabel }}
              </span>
            </div>
          </div>

          <!-- Controls: refresh + status -->
          <div class="captcha-controls">
            <span class="captcha-status" :class="statusClass">{{ statusMsg }}</span>
            <button class="captcha-refresh" @click="refresh" :disabled="loading"
                    title="刷新验证码">
              <svg viewBox="0 0 24 24" class="refresh-icon" :class="{ spinning: loading }">
                <path d="M17.65 6.35A7.958 7.958 0 0012 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0112 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" fill="currentColor"/>
              </svg>
            </button>
          </div>
        </div>
      `,

      setup() {
        const loading = ref(true);
        const solved = ref(false);
        const errorShake = ref(false);
        const isDragging = ref(false);
        const isDark = ref(false);

        const bgSrc = ref('');
        const puzzleSrc = ref('');
        const sliderPercent = ref(0);
        const statusMsg = ref('加载中...');
        const statusClass = ref('');
        const trackLabel = ref('拖动滑块完成拼图');
        const token = ref('');
        const targetX = ref(0);
        const pieceW = ref(56);
        const pieceH = ref(170);
        const yPos = ref(0);
        const maxOffset = ref(224); // 280 - 56

        const dragTrace = ref([]);
        const dragStartTime = ref(0);
        const dragStartX = ref(0);

        const sliderTrack = ref(null);
        const pieceImg = ref(null);
        const bgImg = ref(null);

        const pieceStyle = computed(() => ({
          left: Math.round(sliderPercent.value * maxOffset.value / 100) + 'px',
          top: yPos.value + 'px',
          width: pieceW.value + 'px',
          height: pieceH.value + 'px',
        }));

        // Dark mode detection
        function detectDarkMode() {
          isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches;
        }

        // Fetch new challenge
        async function loadChallenge() {
          loading.value = true;
          solved.value = false;
          errorShake.value = false;
          sliderPercent.value = 0;
          statusMsg.value = '加载中...';
          statusClass.value = '';
          trackLabel.value = '拖动滑块完成拼图';
          dragTrace.value = [];
          token.value = '';

          try {
            const res = await fetch(API_BASE + '/api/captcha/generate');
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const data = await res.json();

            token.value = data.token;
            bgSrc.value = 'data:image/png;base64,' + data.background;
            puzzleSrc.value = 'data:image/png;base64,' + data.puzzle;
            pieceW.value = data.piece_width;
            pieceH.value = data.piece_height;
            yPos.value = data.y_position;
            maxOffset.value = 280 - data.piece_width;

            loading.value = false;
            statusMsg.value = '';
          } catch (e) {
            loading.value = false;
            statusMsg.value = '加载失败，点击刷新';
            statusClass.value = 'error';
            console.error('Captcha load failed:', e);
          }
        }

        // Start drag
        function startDrag(e) {
          if (solved.value || loading.value) return;
          isDragging.value = true;
          dragStartTime.value = Date.now();
          dragStartX.value = e.clientX;
          dragTrace.value = [{
            t: 0,
            x: 0,
            y: 0
          }];
          trackLabel.value = '';

          document.addEventListener('mousemove', onMouseDrag);
          document.addEventListener('mouseup', endDrag);
        }

        function startTouchDrag(e) {
          if (solved.value || loading.value) return;
          const touch = e.touches[0];
          isDragging.value = true;
          dragStartTime.value = Date.now();
          dragStartX.value = touch.clientX;
          dragTrace.value = [{ t: 0, x: 0, y: 0 }];
          trackLabel.value = '';

          document.addEventListener('touchmove', onTouchDrag, { passive: false });
          document.addEventListener('touchend', endTouchDrag);
        }

        function onMouseDrag(e) {
          if (!isDragging.value) return;
          const track = sliderTrack.value;
          if (!track) return;
          const rect = track.getBoundingClientRect();
          const dx = e.clientX - dragStartX.value;
          const percent = Math.max(0, Math.min(100, (dx / (rect.width - 36)) * 100));
          sliderPercent.value = percent;

          // Record trajectory (throttled)
          const now = Date.now();
          const last = dragTrace.value[dragTrace.value.length - 1];
          if (!last || now - last.t > 16) {
            dragTrace.value.push({
              t: now - dragStartTime.value,
              x: Math.round(percent * maxOffset.value / 100),
              y: 0
            });
          }
        }

        function onTouchDrag(e) {
          e.preventDefault();
          if (!isDragging.value) return;
          const track = sliderTrack.value;
          if (!track) return;
          const touch = e.touches[0];
          const rect = track.getBoundingClientRect();
          const dx = touch.clientX - dragStartX.value;
          const percent = Math.max(0, Math.min(100, (dx / (rect.width - 36)) * 100));
          sliderPercent.value = percent;

          const now = Date.now();
          const last = dragTrace.value[dragTrace.value.length - 1];
          if (!last || now - last.t > 16) {
            dragTrace.value.push({
              t: now - dragStartTime.value,
              x: Math.round(percent * maxOffset.value / 100),
              y: 0
            });
          }
        }

        async function endDrag() {
          document.removeEventListener('mousemove', onMouseDrag);
          document.removeEventListener('mouseup', endDrag);
          if (!isDragging.value) return;
          isDragging.value = false;

          const finalX = Math.round(sliderPercent.value * maxOffset.value / 100);
          dragTrace.value.push({
            t: Date.now() - dragStartTime.value,
            x: finalX,
            y: 0
          });

          await verify(finalX);
        }

        async function endTouchDrag() {
          document.removeEventListener('touchmove', onTouchDrag);
          document.removeEventListener('touchend', endTouchDrag);
          if (!isDragging.value) return;
          isDragging.value = false;

          const finalX = Math.round(sliderPercent.value * maxOffset.value / 100);
          dragTrace.value.push({
            t: Date.now() - dragStartTime.value,
            x: finalX,
            y: 0
          });

          await verify(finalX);
        }

        async function verify(dragDistance) {
          statusMsg.value = '验证中...';
          statusClass.value = '';

          try {
            const res = await fetch(API_BASE + '/api/captcha/verify', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                token: token.value,
                drag_distance: dragDistance,
                drag_trace: dragTrace.value,
              }),
            });
            const data = await res.json();

            if (data.success) {
              solved.value = true;
              sliderPercent.value = (dragDistance / maxOffset.value) * 100;
              statusMsg.value = '✓ 验证通过';
              statusClass.value = 'success';
              trackLabel.value = '验证通过';

              // Emit event for parent page
              widgetEl.dispatchEvent(new CustomEvent('captcha-success', {
                detail: { token: token.value, risk_score: data.risk_score }
              }));
            } else {
              sliderPercent.value = 0;
              errorShake.value = true;
              statusMsg.value = '✗ 验证失败，请重试';
              statusClass.value = 'error';
              trackLabel.value = '拖动滑块完成拼图';

              setTimeout(() => { errorShake.value = false; }, 600);

              if (data.next_action === 'refresh') {
                setTimeout(() => loadChallenge(), 800);
              }
            }
          } catch (e) {
            sliderPercent.value = 0;
            statusMsg.value = '网络错误';
            statusClass.value = 'error';
          }
        }

        function refresh() {
          loadChallenge();
        }

        onMounted(() => {
          detectDarkMode();
          window.matchMedia('(prefers-color-scheme: dark)')
            .addEventListener('change', detectDarkMode);
          loadChallenge();
        });

        return {
          loading, solved, errorShake, isDragging, isDark,
          bgSrc, puzzleSrc, sliderPercent, statusMsg, statusClass,
          trackLabel, pieceW, pieceH, yPos, maxOffset, pieceStyle,
          sliderTrack, pieceImg, bgImg,
          startDrag, startTouchDrag, refresh,
        };
      }
    });

    app.mount(el);
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createWidget);
  } else {
    createWidget();
  }
})();
