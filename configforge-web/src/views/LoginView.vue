<template>
  <div class="login">
    <!-- Left: Product Demo -->
    <div class="login__demo">
      <div class="login__demo-bg"></div>
      <div class="login__demo-inner">
        <div class="login__logo-row">
          <span class="login__logo-icon">⚡</span>
          <span class="login__logo-name">ConfigForge</span>
        </div>
        <p class="login__demo-tagline">5 步向导，AI 驱动，零代码创建数据管道</p>
        <div class="login__anim-wrap">
          <PipelineAnimation />
        </div>
      </div>
    </div>

    <!-- Right: Login Form -->
    <div class="login__form">
      <div class="login__form-card">
        <h1 class="login__form-title">欢迎回来</h1>
        <p class="login__form-subtitle">登录以继续</p>

        <form class="login__form-fields" @submit.prevent="onLogin">
          <label class="login__field">
            <span class="login__field-label">用户名</span>
            <div class="login__field-wrap" :class="{ 'is-error': loginError }">
              <span class="login__field-ico">👤</span>
              <input v-model="loginForm.username" type="text" class="login__field-inp" placeholder="admin" autocomplete="username" required />
            </div>
          </label>

          <label class="login__field">
            <span class="login__field-label">密码</span>
            <div class="login__field-wrap" :class="{ 'is-error': loginError }">
              <span class="login__field-ico">🔑</span>
              <input v-model="loginForm.password" :type="showPassword ? 'text' : 'password'" class="login__field-inp" placeholder="······" autocomplete="current-password" required />
              <button type="button" class="login__field-eye" @click="showPassword = !showPassword">{{ showPassword ? '🙈' : '👁' }}</button>
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

        <p class="login__hint">默认账户 admin / admin123</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import PipelineAnimation from '../components/PipelineAnimation.vue'

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
   LEFT — PRODUCT DEMO (50%)
   ============================================================ */
.login__demo {
  flex: 1;
  position: relative;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  background: #080012;
}
.login__demo-bg {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 70% 50% at 30% 80%, rgba(124,58,237,0.25) 0%, transparent 50%),
    radial-gradient(ellipse 50% 30% at 70% 20%, rgba(20,184,166,0.2) 0%, transparent 40%),
    linear-gradient(160deg, #080012 0%, #12082e 40%, #0f766e 100%);
}
.login__demo-inner {
  position: relative; z-index: 2;
  display: flex; flex-direction: column; align-items: center;
  padding: 40px 20px;
}
.login__logo-row {
  display: flex; align-items: center; gap: 10px;
}
.login__logo-icon {
  font-size: 32px;
  filter: drop-shadow(0 2px 12px rgba(124,58,237,0.5));
}
.login__logo-name {
  font-family: var(--font-display);
  font-size: 24px; font-weight: 800;
  background: linear-gradient(135deg, #fff, #c4b5fd);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.login__demo-tagline {
  font-family: var(--font-display);
  font-size: 13px; color: rgba(255,255,255,0.45);
  margin: 6px 0 24px; letter-spacing: 0.05em;
}
.login__anim-wrap {
  transform: scale(0.85);
  filter: drop-shadow(0 8px 32px rgba(0,0,0,0.4));
}

/* ============================================================
   RIGHT — LOGIN FORM (50%)
   ============================================================ */
.login__form {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  padding: 48px;
  background: linear-gradient(135deg, rgba(250,250,249,0.85), rgba(250,250,249,0.5));
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.login__form-card { width: 100%; max-width: 360px; }
.login__form-title {
  font-family: var(--font-display);
  font-size: 28px; font-weight: 800; color: var(--color-text);
  margin: 0 0 4px; letter-spacing: -0.02em;
}
.login__form-subtitle {
  font-size: 14px; color: var(--color-text-secondary);
  margin: 0 0 32px;
}
.login__form-fields { display: flex; flex-direction: column; gap: 18px; }

/* Fields */
.login__field { display: flex; flex-direction: column; gap: 5px; }
.login__field-label {
  font-family: var(--font-display);
  font-size: 12px; font-weight: 600; color: var(--color-text-secondary);
}
.login__field-wrap {
  display: flex; align-items: center;
  background: rgba(255,255,255,0.5);
  border: 1.5px solid var(--color-border);
  border-radius: 10px; overflow: hidden;
  transition: all 0.2s;
}
.login__field-wrap:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(15,118,110,0.08);
  background: rgba(255,255,255,0.8);
}
.login__field-wrap.is-error {
  border-color: var(--color-error) !important;
  box-shadow: 0 0 0 3px rgba(220,38,38,0.06) !important;
}
.login__field-ico { width: 40px; text-align: center; font-size: 15px; opacity: 0.4; flex-shrink: 0; }
.login__field-inp {
  flex: 1; padding: 11px 12px 11px 0;
  font-family: var(--font-body); font-size: 14px; color: var(--color-text);
  background: transparent; border: none; outline: none;
}
.login__field-inp::placeholder { color: var(--color-text-muted); }
.login__field-eye {
  width: 36px; height: 36px; font-size: 15px;
  background: none; border: none; cursor: pointer;
  opacity: 0.4; flex-shrink: 0; margin-right: 4px;
}
.login__field-eye:hover { opacity: 0.7; }

/* Submit */
.login__submit {
  width: 100%; padding: 13px 24px; margin-top: 6px;
  font-family: var(--font-display); font-size: 15px; font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, rgba(15,118,110,0.9), rgba(20,184,166,0.85));
  border: 1px solid rgba(15,118,110,0.12); border-radius: 10px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(15,118,110,0.12), 0 4px 12px rgba(15,118,110,0.08);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  transition: all 0.3s;
  letter-spacing: 0.06em;
}
.login__submit:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(15,118,110,0.18), 0 8px 24px rgba(15,118,110,0.12);
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
  background: rgba(220,38,38,0.05); border: 1px solid rgba(220,38,38,0.12);
  border-radius: 8px; padding: 10px 14px; margin: 0;
}
.shake-enter-active { animation: shake 0.35s ease; }
@keyframes shake {
  0%,100%{transform:translateX(0)} 20%{transform:translateX(-6px)} 40%{transform:translateX(6px)} 60%{transform:translateX(-4px)} 80%{transform:translateX(4px)}
}

/* Hint */
.login__hint {
  text-align: center; font-size: 12px; color: var(--color-text-muted);
  margin: 18px 0 0; opacity: 0.55;
}

/* Dark mode */
[data-theme="dark"] .login__form {
  background: linear-gradient(135deg, rgba(28,25,23,0.85), rgba(28,25,23,0.5));
}
[data-theme="dark"] .login__field-wrap {
  background: rgba(41,37,36,0.5);
}
[data-theme="dark"] .login__field-wrap:focus-within {
  background: rgba(41,37,36,0.75);
}

/* Responsive */
@media (max-width: 900px) {
  .login__demo { display: none; }
  .login__form { flex: 1; padding: 32px 24px; }
}
</style>
