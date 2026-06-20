<template>
  <div class="login">
    <!-- Left: Brand -->
    <div class="login__brand">
      <!-- Gradient mesh background -->
      <div class="login__brand-bg"></div>

      <!-- Content -->
      <div class="login__brand-body">
        <div class="login__brand-top">
          <div class="login__logo">
            <span class="login__logo-mark">⚡</span>
            <span class="login__logo-text">ConfigForge</span>
          </div>
          <p class="login__tagline">数据管道配置向导</p>
        </div>

        <div class="login__features">
          <div class="login__feature">
            <span class="login__feature-icon">🎯</span>
            <div>
              <div class="login__feature-title">5 步向导</div>
              <div class="login__feature-desc">场景 → 输入 → 处理 → 输出 → 导出</div>
            </div>
          </div>
          <div class="login__feature">
            <span class="login__feature-icon">🤖</span>
            <div>
              <div class="login__feature-title">AI 智能辅助</div>
              <div class="login__feature-desc">自动生成 SQL、列映射与诊断修复</div>
            </div>
          </div>
          <div class="login__feature">
            <span class="login__feature-icon">🔒</span>
            <div>
              <div class="login__feature-title">安全可控</div>
              <div class="login__feature-desc">数据本地处理，支持加密与认证</div>
            </div>
          </div>
        </div>

        <p class="login__brand-footer">7 种数据源 · 3 种输出 · 一键部署</p>
      </div>
    </div>

    <!-- Right: Form -->
    <div class="login__form">
      <div class="login__form-card">
        <div class="login__form-header">
          <h1 class="login__form-title">欢迎回来</h1>
          <p class="login__form-subtitle">登录以继续你的数据之旅</p>
        </div>

        <form @submit.prevent="onLogin" class="login__form-fields">
          <label class="login__field">
            <span class="login__field-label">用户名</span>
            <div class="login__field-wrap" :class="{ 'login__field-wrap--error': loginError }">
              <span class="login__field-icon">👤</span>
              <input v-model="loginForm.username" type="text" class="login__field-input" placeholder="输入用户名" autocomplete="username" required />
            </div>
          </label>

          <label class="login__field">
            <span class="login__field-label">密码</span>
            <div class="login__field-wrap" :class="{ 'login__field-wrap--error': loginError }">
              <span class="login__field-icon">🔑</span>
              <input v-model="loginForm.password" :type="showPassword ? 'text' : 'password'" class="login__field-input" placeholder="输入密码" autocomplete="current-password" required />
              <button type="button" class="login__field-toggle" @click="showPassword = !showPassword">
                {{ showPassword ? '🙈' : '👁' }}
              </button>
            </div>
          </label>

          <Transition name="shake">
            <p v-if="loginError" class="login__error">{{ loginError }}</p>
          </Transition>

          <button type="submit" class="login__submit" :disabled="loginLoading">
            <span v-if="loginLoading" class="login__spinner"></span>
            <span v-else>登 录</span>
          </button>
        </form>

        <p class="login__hint">默认账号 admin / admin123</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const showPassword = ref(false)
const loginLoading = ref(false)
const loginError = ref('')
const loginForm = reactive({ username: '', password: '' })

async function onLogin() {
  loginError.value = ''
  if (!loginForm.username.trim() || !loginForm.password) {
    loginError.value = '请输入用户名和密码'
    return
  }
  loginLoading.value = true
  const result = await auth.login(loginForm.username.trim(), loginForm.password)
  loginLoading.value = false
  if (result.success) {
    router.push((router.currentRoute.value.query.redirect as string) || '/')
  } else {
    loginError.value = result.error || '登录失败'
  }
}
</script>

<style scoped>
.login { display: flex; min-height: 100vh; }

/* ============================================================
   LEFT — BRAND PANEL (55%)
   ============================================================ */
.login__brand {
  flex: 5.5;
  position: relative;
  display: flex;
  align-items: center;
  overflow: hidden;
  background: #0a0015;
}
.login__brand-bg {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 20% 80%, rgba(124,58,237,0.4) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 80% 20%, rgba(15,118,110,0.3) 0%, transparent 50%),
    radial-gradient(ellipse 50% 30% at 50% 50%, rgba(99,102,241,0.2) 0%, transparent 40%),
    linear-gradient(160deg, #0a0015 0%, #1a0a2e 30%, #3b1f6e 55%, #0f766e 100%);
  animation: brand-breathe 8s ease-in-out infinite;
}
@keyframes brand-breathe {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.9; }
}

.login__brand-body {
  position: relative; z-index: 2;
  display: flex; flex-direction: column; justify-content: space-between;
  height: 100%; padding: 64px 72px; max-width: 480px;
  margin: 0 auto;
}

/* Logo */
.login__logo { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
.login__logo-mark {
  font-size: 48px;
  filter: drop-shadow(0 4px 20px rgba(124,58,237,0.6));
  animation: logo-glow 3s ease-in-out infinite;
}
@keyframes logo-glow {
  0%, 100% { filter: drop-shadow(0 4px 20px rgba(124,58,237,0.6)); }
  50% { filter: drop-shadow(0 4px 40px rgba(124,58,237,0.9)); }
}
.login__logo-text {
  font-family: var(--font-display);
  font-size: 36px; font-weight: 800;
  background: linear-gradient(135deg, #fff 0%, #c4b5fd 50%, #5eead4 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.03em;
}
.login__tagline {
  font-family: var(--font-display);
  font-size: 16px; color: rgba(255,255,255,0.5);
  letter-spacing: 0.15em; text-transform: uppercase;
  margin: 0;
}

/* Features */
.login__features { display: flex; flex-direction: column; gap: 20px; margin: auto 0; }
.login__feature {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 20px 24px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: all 0.4s cubic-bezier(0.16,1,0.3,1);
  opacity: 0;
  animation: feature-in 0.6s ease forwards;
}
.login__feature:nth-child(1) { animation-delay: 0.2s; }
.login__feature:nth-child(2) { animation-delay: 0.35s; }
.login__feature:nth-child(3) { animation-delay: 0.5s; }
@keyframes feature-in {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}
.login__feature:hover {
  background: rgba(255,255,255,0.12);
  border-color: rgba(255,255,255,0.2);
  transform: translateX(6px);
}
.login__feature-icon { font-size: 28px; flex-shrink: 0; line-height: 1.2; }
.login__feature-title {
  font-family: var(--font-display);
  font-size: 15px; font-weight: 600; color: #fff;
  margin-bottom: 4px;
}
.login__feature-desc { font-size: 13px; color: rgba(255,255,255,0.5); line-height: 1.5; }

.login__brand-footer {
  font-family: var(--font-display);
  font-size: 13px; color: rgba(255,255,255,0.3);
  letter-spacing: 0.08em;
}

/* ============================================================
   RIGHT — FORM PANEL (45%)
   ============================================================ */
.login__form {
  flex: 4.5;
  display: flex; align-items: center; justify-content: center;
  padding: 48px;
  background: linear-gradient(135deg, rgba(250,250,249,0.85), rgba(250,250,249,0.5));
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.login__form-card { width: 100%; max-width: 380px; }
.login__form-header { margin-bottom: 36px; }
.login__form-title {
  font-family: var(--font-display);
  font-size: 32px; font-weight: 800;
  color: var(--color-text);
  margin: 0 0 8px;
  letter-spacing: -0.03em;
}
.login__form-subtitle {
  font-size: 15px; color: var(--color-text-secondary);
  margin: 0;
}
.login__form-fields { display: flex; flex-direction: column; gap: 20px; }

/* Fields */
.login__field { display: flex; flex-direction: column; gap: 6px; }
.login__field-label {
  font-family: var(--font-display);
  font-size: 13px; font-weight: 600;
  color: var(--color-text-secondary);
}
.login__field-wrap {
  display: flex; align-items: center;
  background: rgba(255,255,255,0.6);
  border: 1.5px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.2s;
}
.login__field-wrap:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(15,118,110,0.08);
  background: rgba(255,255,255,0.9);
}
.login__field-wrap--error {
  border-color: var(--color-error) !important;
  box-shadow: 0 0 0 3px rgba(220,38,38,0.08) !important;
}
.login__field-icon {
  width: 44px; text-align: center; font-size: 16px;
  opacity: 0.4; flex-shrink: 0;
}
.login__field-wrap:focus-within .login__field-icon { opacity: 0.7; }
.login__field-input {
  flex: 1; padding: 12px 14px 12px 0;
  font-family: var(--font-body); font-size: 15px; color: var(--color-text);
  background: transparent; border: none; outline: none;
}
.login__field-input::placeholder { color: var(--color-text-muted); }
.login__field-toggle {
  width: 40px; height: 44px; font-size: 16px;
  background: none; border: none; cursor: pointer;
  opacity: 0.4; flex-shrink: 0;
}
.login__field-toggle:hover { opacity: 0.7; }

/* Submit */
.login__submit {
  width: 100%; padding: 14px 24px; margin-top: 8px;
  font-family: var(--font-display); font-size: 15px; font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, rgba(15,118,110,0.9), rgba(20,184,166,0.85));
  border: 1px solid rgba(15,118,110,0.15);
  border-radius: 10px; cursor: pointer;
  box-shadow: 0 2px 4px rgba(15,118,110,0.15), 0 4px 16px rgba(15,118,110,0.1);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transition: all 0.3s;
  letter-spacing: 0.08em;
}
.login__submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(15,118,110,0.2), 0 8px 28px rgba(15,118,110,0.15);
}
.login__submit:active:not(:disabled) { transform: scale(0.97); }
.login__submit:disabled { opacity: 0.5; cursor: not-allowed; }

/* Spinner */
.login__spinner {
  display: inline-block; width: 18px; height: 18px;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Error */
.login__error {
  font-size: 13px; color: var(--color-error);
  background: rgba(220,38,38,0.06); border: 1px solid rgba(220,38,38,0.15);
  border-radius: 8px; padding: 10px 14px; margin: 0;
}
.shake-enter-active { animation: shake 0.35s ease; }
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-6px); }
  40% { transform: translateX(6px); }
  60% { transform: translateX(-4px); }
  80% { transform: translateX(4px); }
}

/* Hint */
.login__hint {
  text-align: center; font-size: 12px; color: var(--color-text-muted);
  margin: 20px 0 0; opacity: 0.6;
}

/* ============================================================
   DARK MODE
   ============================================================ */
[data-theme="dark"] .login__form {
  background: linear-gradient(135deg, rgba(28,25,23,0.85), rgba(28,25,23,0.5));
}
[data-theme="dark"] .login__field-wrap {
  background: rgba(41,37,36,0.5);
}
[data-theme="dark"] .login__field-wrap:focus-within {
  background: rgba(41,37,36,0.75);
}

/* ============================================================
   RESPONSIVE
   ============================================================ */
@media (max-width: 900px) {
  .login__brand { display: none; }
  .login__form { flex: 1; padding: 32px 24px; }
  .login__form-card { max-width: 100%; }
}
@media (max-width: 480px) {
  .login__form { padding: 24px 16px; }
  .login__form-title { font-size: 26px; }
}
</style>
