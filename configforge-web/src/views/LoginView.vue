<template>
  <div class="login">
    <!-- Left: brand panel -->
    <div class="login__brand">
      <div class="login__brand-inner">
        <div class="login__brand-logo">⚡</div>
        <h1 class="login__brand-title">ConfigForge</h1>
        <p class="login__brand-desc">AI 驱动的数据流水线配置工具</p>
        <div class="login__brand-features">
          <div class="login__brand-feature">
            <span class="login__brand-feature-icon">🎯</span>
            <span>5 步向导，快速构建数据管道</span>
          </div>
          <div class="login__brand-feature">
            <span class="login__brand-feature-icon">🤖</span>
            <span>AI 辅助 SQL 生成与列映射</span>
          </div>
          <div class="login__brand-feature">
            <span class="login__brand-feature-icon">🔒</span>
            <span>所有数据本地处理，安全可控</span>
          </div>
        </div>
        <div class="login__brand-decoration">
          <div class="login__orb login__orb--1"></div>
          <div class="login__orb login__orb--2"></div>
          <div class="login__orb login__orb--3"></div>
        </div>
      </div>
    </div>

    <!-- Right: login form -->
    <div class="login__form-panel">
      <div class="login__form-inner">
        <div class="login__form-section">
          <h2 class="login__form-title">欢迎回来</h2>
          <p class="login__form-subtitle">登录你的 ConfigForge 账号</p>

          <form class="login__form" @submit.prevent="onLogin">
            <div class="login__field">
              <label class="cf-label">用户名</label>
              <div class="login__input-wrap" :class="{ 'login__input-wrap--error': loginError }">
                <span class="login__input-icon">👤</span>
                <input
                  v-model="loginForm.username"
                  type="text"
                  class="login__input"
                  placeholder="输入用户名"
                  autocomplete="username"
                  required
                />
              </div>
            </div>

            <div class="login__field">
              <label class="cf-label">密码</label>
              <div class="login__input-wrap" :class="{ 'login__input-wrap--error': loginError }">
                <span class="login__input-icon">🔑</span>
                <input
                  v-model="loginForm.password"
                  :type="showPassword ? 'text' : 'password'"
                  class="login__input"
                  placeholder="输入密码"
                  autocomplete="current-password"
                  required
                />
                <button type="button" class="login__toggle-pw" @click="showPassword = !showPassword" :aria-label="showPassword ? '隐藏密码' : '显示密码'">
                  {{ showPassword ? '🙈' : '👁' }}
                </button>
              </div>
            </div>

            <Transition name="login-shake">
              <p v-if="loginError" class="login__error">{{ loginError }}</p>
            </Transition>

            <button type="submit" class="login__submit" :disabled="loginLoading">
              <span v-if="loginLoading" class="login__spinner"></span>
              <span v-else>登 录</span>
            </button>
          </form>
        </div>

        <p class="login__hint">默认管理员账号：admin / admin123</p>
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
    const redirect = (router.currentRoute.value.query.redirect as string) || '/'
    router.push(redirect)
  } else {
    loginError.value = result.error || '登录失败'
  }
}
</script>

<style scoped>
.login {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg);
}

/* ───── Left brand panel ───── */
.login__brand {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #0a2e1f 0%, #0d4a35 40%, #0d9488 100%);
  position: relative;
  overflow: hidden;
  padding: 48px;
}

.login__brand-inner {
  position: relative;
  z-index: 2;
  max-width: 420px;
}

.login__brand-logo {
  font-size: 56px;
  margin-bottom: 16px;
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.3));
}

.login__brand-title {
  font-size: 40px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.03em;
  margin: 0 0 12px;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.login__brand-desc {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.75);
  line-height: 1.6;
  margin: 0 0 40px;
}

.login__brand-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.login__brand-feature {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.85);
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-md);
  backdrop-filter: blur(8px);
  transition: background 0.2s, border-color 0.2s;
}

.login__brand-feature:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.2);
}

.login__brand-feature-icon {
  font-size: 20px;
  flex-shrink: 0;
}

/* ───── Decorative orbs ───── */
.login__brand-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login__orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: orb-float 12s ease-in-out infinite;
}

.login__orb--1 {
  width: 300px;
  height: 300px;
  background: #14b8a6;
  top: -80px;
  right: -60px;
  animation-delay: 0s;
}

.login__orb--2 {
  width: 200px;
  height: 200px;
  background: #5eead4;
  bottom: -40px;
  left: -40px;
  animation-delay: -4s;
}

.login__orb--3 {
  width: 160px;
  height: 160px;
  background: #0d9488;
  top: 50%;
  left: 60%;
  animation-delay: -8s;
}

@keyframes orb-float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(20px, -30px) scale(1.05); }
  66% { transform: translate(-15px, 20px) scale(0.95); }
}

/* ───── Right form panel ───── */
.login__form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
  background: var(--color-surface);
}

.login__form-inner {
  width: 100%;
  max-width: 400px;
}

.login__form-section {
  animation: cf-slide-up 0.35s ease;
}

.login__form-title {
  font-size: 28px;
  font-weight: 800;
  color: var(--color-text);
  margin: 0 0 8px;
  letter-spacing: -0.02em;
}

.login__form-subtitle {
  font-size: 15px;
  color: var(--color-text-secondary);
  margin: 0 0 32px;
}

/* ───── Form fields ───── */
.login__form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.login__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.login__input-wrap {
  display: flex;
  align-items: center;
  gap: 0;
  background: var(--color-bg);
  border: 1.5px solid var(--color-border-light);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  overflow: hidden;
}

.login__input-wrap:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.login__input-wrap--error {
  border-color: var(--color-error) !important;
  box-shadow: 0 0 0 3px var(--color-error-bg) !important;
}

.login__input-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  font-size: 16px;
  flex-shrink: 0;
  opacity: 0.5;
}

.login__input-wrap:focus-within .login__input-icon {
  opacity: 0.8;
}

.login__input {
  flex: 1;
  padding: 12px 14px 12px 0;
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  color: var(--color-text);
  background: transparent;
  border: none;
  outline: none;
}

.login__input::placeholder {
  color: var(--color-text-muted);
}

.login__toggle-pw {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 100%;
  font-size: 16px;
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity var(--transition-fast);
  flex-shrink: 0;
}

.login__toggle-pw:hover {
  opacity: 0.8;
}

/* ───── Submit button ───── */
.login__submit {
  width: 100%;
  padding: 13px 24px;
  font-family: var(--font-family);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: #ffffff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-button);
  margin-top: 4px;
  letter-spacing: 0.08em;
}

.login__submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(13, 148, 136, 0.35);
}

.login__submit:active:not(:disabled) {
  transform: translateY(0);
}

.login__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ───── Spinner ───── */
.login__spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: login-spin 0.6s linear infinite;
}

@keyframes login-spin {
  to { transform: rotate(360deg); }
}

/* ───── Error message ───── */
.login__error {
  font-size: var(--font-size-sm);
  color: var(--color-error);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin: 0;
}

/* ───── Hint ───── */
.login__hint {
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin: 16px 0 0;
  opacity: 0.7;
}

/* ───── Transitions ───── */
.login-shake-enter-active {
  animation: login-shake 0.35s ease;
}

@keyframes login-shake {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-6px); }
  40% { transform: translateX(6px); }
  60% { transform: translateX(-4px); }
  80% { transform: translateX(4px); }
}

/* ───── Responsive ───── */
@media (max-width: 900px) {
  .login__brand {
    display: none;
  }
  .login__form-panel {
    padding: 32px 24px;
  }
}

@media (max-width: 480px) {
  .login__form-panel {
    padding: 24px 16px;
  }
  .login__form-title {
    font-size: 24px;
  }
}
</style>
