<template>
  <div class="login">
    <!-- Background atmosphere -->
    <div class="login__bg">
      <div class="login__orb login__orb--1"></div>
      <div class="login__orb login__orb--2"></div>
      <div class="login__orb login__orb--3"></div>
    </div>

    <!-- Centered card -->
    <div class="login__card">
      <!-- Top: Logo + tagline -->
      <div class="login__brand">
        <span class="login__logo">⚡</span>
        <h1 class="login__title">ConfigForge</h1>
        <p class="login__tagline">AI 驱动的数据流水线配置工具</p>
      </div>

      <!-- Demo preview (collapsed by default on mobile) -->
      <div class="login__demo">
        <PipelineAnimation />
      </div>
      <p class="login__demo-label">5 步向导，零代码创建数据处理流程</p>

      <!-- Form -->
      <form class="login__form" @submit.prevent="onLogin">
        <label class="login__field">
          <span class="login__label">用户名</span>
          <div class="login__input" :class="{ 'is-error': loginError }">
            <span class="login__input-icon">👤</span>
            <input v-model="loginForm.username" type="text" placeholder="输入用户名" autocomplete="username" required />
          </div>
        </label>

        <label class="login__field">
          <span class="login__label">密码</span>
          <div class="login__input" :class="{ 'is-error': loginError }">
            <span class="login__input-icon">🔑</span>
            <input v-model="loginForm.password" :type="showPassword ? 'text' : 'password'" placeholder="输入密码" autocomplete="current-password" required />
            <button type="button" class="login__eye" @click="showPassword = !showPassword">{{ showPassword ? '🙈' : '👁' }}</button>
          </div>
        </label>

        <Transition name="shake">
          <p v-if="loginError" class="login__error">{{ loginError }}</p>
        </Transition>

        <button type="submit" class="login__btn" :disabled="loginLoading">
          <span v-if="loginLoading" class="login__spinner"></span>
          <span v-else>登录</span>
        </button>
      </form>

      <p class="login__hint">默认账户 admin / admin123</p>
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
.login {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: #0a0012;
  position: relative; overflow: hidden;
  padding: 32px 24px;
}

/* ───── Background ───── */
.login__bg { position: absolute; inset: 0; pointer-events: none; }
.login__orb {
  position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.35;
  animation: orb-drift 16s ease-in-out infinite;
}
.login__orb--1 { width: 400px; height: 400px; background: #7c3aed; top: -120px; right: -80px; animation-delay: 0s; }
.login__orb--2 { width: 300px; height: 300px; background: #0f766e; bottom: -80px; left: -60px; animation-delay: -5s; }
.login__orb--3 { width: 250px; height: 250px; background: #6366f1; top: 50%; left: 50%; transform: translate(-50%,-50%); animation-delay: -10s; }
@keyframes orb-drift {
  0%,100% { transform: translate(0,0) scale(1); }
  33% { transform: translate(30px,-20px) scale(1.08); }
  66% { transform: translate(-20px,25px) scale(0.92); }
}

/* ───── Card ───── */
.login__card {
  position: relative; z-index: 2;
  width: 100%; max-width: 440px;
  background: rgba(255,255,255,0.07);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 24px;
  padding: 48px 40px 40px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

/* ───── Brand ───── */
.login__brand { text-align: center; margin-bottom: 24px; }
.login__logo {
  font-size: 44px;
  filter: drop-shadow(0 4px 16px rgba(124,58,237,0.5));
  display: block; margin-bottom: 8px;
}
.login__title {
  font-family: var(--font-display);
  font-size: 28px; font-weight: 800; color: #fff;
  margin: 0; letter-spacing: -0.02em;
}
.login__tagline { font-size: 13px; color: rgba(255,255,255,0.4); margin: 4px 0 0; }

/* ───── Demo ───── */
.login__demo {
  transform: scale(0.72);
  transform-origin: top center;
  margin: -12px 0 -8px;
  opacity: 0.8;
}
.login__demo-label {
  text-align: center; font-size: 11px; color: rgba(255,255,255,0.3);
  margin: -4px 0 24px; letter-spacing: 0.05em;
}

/* ───── Form ───── */
.login__form { display: flex; flex-direction: column; gap: 16px; }
.login__field { display: flex; flex-direction: column; gap: 4px; }
.login__label {
  font-family: var(--font-display);
  font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.4);
}
.login__input {
  display: flex; align-items: center;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px; overflow: hidden;
  transition: all 0.2s;
}
.login__input:focus-within {
  border-color: rgba(124,58,237,0.5);
  background: rgba(255,255,255,0.1);
  box-shadow: 0 0 0 3px rgba(124,58,237,0.08);
}
.login__input.is-error { border-color: rgba(239,68,68,0.5) !important; }
.login__input-icon { width: 40px; text-align: center; font-size: 14px; opacity: 0.4; flex-shrink: 0; }
.login__input input {
  flex: 1; padding: 11px 12px 11px 0;
  font-family: var(--font-body); font-size: 14px; color: #fff;
  background: transparent; border: none; outline: none;
}
.login__input input::placeholder { color: rgba(255,255,255,0.2); }
.login__eye {
  width: 36px; height: 36px; font-size: 14px;
  background: none; border: none; cursor: pointer;
  opacity: 0.3; flex-shrink: 0; margin-right: 2px;
}
.login__eye:hover { opacity: 0.6; }

/* ───── Button ───── */
.login__btn {
  width: 100%; padding: 13px 24px; margin-top: 4px;
  font-family: var(--font-display); font-size: 15px; font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  border: none; border-radius: 10px; cursor: pointer;
  box-shadow: 0 0 0 0 rgba(124,58,237,0.4);
  animation: btn-pulse 2.5s ease-in-out infinite;
  transition: all 0.3s;
  letter-spacing: 0.06em;
}
.login__btn:hover:not(:disabled) {
  animation: none;
  transform: translateY(-2px);
  box-shadow: 0 4px 24px rgba(124,58,237,0.4);
}
.login__btn:active:not(:disabled) { transform: scale(0.97); }
.login__btn:disabled { opacity: 0.5; cursor: not-allowed; animation: none; }
@keyframes btn-pulse {
  0%,100% { box-shadow: 0 0 0 0 rgba(124,58,237,0.35); }
  50% { box-shadow: 0 0 0 6px rgba(124,58,237,0); }
}

.login__spinner {
  display: inline-block; width: 18px; height: 18px;
  border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
  border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ───── Error ───── */
.login__error {
  font-size: 13px; color: #fca5a5;
  background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.15);
  border-radius: 8px; padding: 10px 14px; margin: 0;
}
.shake-enter-active { animation: shake 0.35s ease; }
@keyframes shake { 0%,100%{transform:translateX(0)} 20%{transform:translateX(-6px)} 40%{transform:translateX(6px)} 60%{transform:translateX(-4px)} 80%{transform:translateX(4px)} }

/* ───── Hint ───── */
.login__hint {
  text-align: center; font-size: 12px; color: rgba(255,255,255,0.2);
  margin: 20px 0 0;
}

@media (max-width: 480px) {
  .login__card { padding: 32px 24px 28px; }
  .login__demo { display: none; }
  .login__demo-label { display: none; }
}
</style>
