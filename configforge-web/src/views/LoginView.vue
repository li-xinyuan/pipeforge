<template>
  <div class="login">
    <!-- Atmosphere -->
    <div class="login__bg">
      <div class="login__orb login__orb--1"></div>
      <div class="login__orb login__orb--2"></div>
    </div>

    <div class="login__card">
      <div class="login__brand">
        <span class="login__logo">⚡</span>
        <span class="login__logo-text">ConfigForge</span>
        <p class="login__tagline">AI 驱动的数据流水线配置工具</p>
      </div>

      <p class="login__intro">
        用自然语言描述需求，AI 自动生成完整的数据处理流程配置。无需编写代码，5 步向导即可从数据接入到结果输出。
      </p>

      <!-- Demo -->
      <div class="login__demo">
        <PipelineAnimation />
      </div>

      <!-- Capabilities -->
      <div class="login__caps">
        <div class="login__cap"><span>📥</span> 7 种输入：Excel · CSV · 数据库 · JSON · XML · Parquet · API</div>
        <div class="login__cap"><span>⚡</span> 2 种处理：SQL 查询 · Python 脚本</div>
        <div class="login__cap"><span>📤</span> 3 种输出：Excel · CSV · 数据库</div>
      </div>

      <!-- Form -->
      <form class="login__form" @submit.prevent="onLogin">
        <div class="login__field">
          <span class="login__label">用户名</span>
          <div class="login__input" :class="{ 'is-error': loginError }">
            <span class="login__input-icon">👤</span>
            <input v-model="loginForm.username" type="text" placeholder="admin" autocomplete="username" required />
          </div>
        </div>

        <div class="login__field">
          <span class="login__label">密码</span>
          <div class="login__input" :class="{ 'is-error': loginError }">
            <span class="login__input-icon">🔑</span>
            <input v-model="loginForm.password" :type="showPassword ? 'text' : 'password'" placeholder="······" autocomplete="current-password" required />
            <button type="button" class="login__eye" @click="showPassword = !showPassword">{{ showPassword ? '🙈' : '👁' }}</button>
          </div>
        </div>

        <Transition name="shake">
          <p v-if="loginError" class="login__error">{{ loginError }}</p>
        </Transition>

        <button type="submit" class="login__btn" :disabled="loginLoading">
          <span v-if="loginLoading" class="login__spinner"></span>
          <span v-else>登 录</span>
        </button>
      </form>

      <p class="login__hint">默认账号 admin / admin123</p>
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
  background: linear-gradient(160deg, #1a0533 0%, #2d1654 25%, #4c3d6e 50%, #78716c 80%, #d6d3d1 100%);
  position: relative; overflow: hidden;
  padding: 40px 24px;
}
.login__bg { position: absolute; inset: 0; pointer-events: none; }
.login__orb {
  position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.3;
  animation: drift 18s ease-in-out infinite;
}
.login__orb--1 { width: 500px; height: 500px; background: #7c3aed; top: -150px; right: -100px; animation-delay: 0s; }
.login__orb--2 { width: 400px; height: 400px; background: #14b8a6; bottom: -100px; left: -80px; animation-delay: -6s; }
@keyframes drift { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(40px,-30px) scale(1.05)} 66%{transform:translate(-30px,20px) scale(0.95)} }

.login__card {
  position: relative; z-index: 2;
  width: 100%; max-width: 560px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 20px;
  padding: 24px 36px 20px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.08), 0 1px 3px rgba(0,0,0,0.04);
}
.login__brand { text-align: center; margin-bottom: 8px; }
.login__logo { font-size: 28px; display: block; margin-bottom: 4px; }
.login__logo-text {
  font-family: var(--font-display);
  font-size: 22px; font-weight: 800;
  background: linear-gradient(135deg, #7c3aed, #0f766e);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.login__tagline { font-size: 12px; color: var(--color-text-muted); margin: 2px 0 0; }

.login__intro {
  text-align: center; font-size: 13px; color: var(--color-text-secondary);
  line-height: 1.6; margin: 0 auto 12px; max-width: 440px;
}

.login__demo { max-width: 480px; margin: 0 auto 10px; }

.login__caps {
  display: flex; gap: 8px; justify-content: center;
  margin-bottom: 16px; flex-wrap: wrap;
}
.login__cap {
  font-size: 10px; color: var(--color-text-secondary);
  background: rgba(255,255,255,0.4); backdrop-filter: blur(4px);
  border: 1px solid var(--color-border-light);
  border-radius: 8px; padding: 6px 10px;
  white-space: nowrap;
}
.login__cap span { margin-right: 2px; }

.login__form { display: flex; flex-direction: column; gap: 14px; }
.login__field { display: flex; flex-direction: column; gap: 4px; }
.login__label {
  font-family: var(--font-display);
  font-size: 13px; font-weight: 600; color: var(--color-text-secondary);
}
.login__input {
  display: flex; align-items: center;
  background: rgba(255,255,255,0.6);
  border: 1.5px solid var(--color-border);
  border-radius: 10px; overflow: hidden;
  transition: all 0.2s;
}
.login__input:focus-within { border-color: #7c3aed; box-shadow: 0 0 0 3px rgba(124,58,237,0.06); background: #fff; }
.login__input.is-error { border-color: #ef4444 !important; }
.login__input-icon { width: 42px; text-align: center; font-size: 15px; opacity: 0.4; flex-shrink: 0; }
.login__input input {
  flex: 1; padding: 11px 12px 11px 0;
  font-family: var(--font-body); font-size: 14px; color: var(--color-text);
  background: transparent; border: none; outline: none;
}
.login__input input::placeholder { color: var(--color-text-muted); }
.login__eye {
  width: 38px; height: 38px; font-size: 15px;
  background: none; border: none; cursor: pointer;
  opacity: 0.4; flex-shrink: 0;
}
.login__eye:hover { opacity: 0.7; }

.login__btn {
  width: 100%; padding: 13px 24px;
  font-family: var(--font-display); font-size: 15px; font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  border: none; border-radius: 10px; cursor: pointer;
  box-shadow: 0 0 0 0 rgba(124,58,237,0.35);
  animation: pulse 2.5s ease-in-out infinite;
  transition: all 0.3s;
  letter-spacing: 0.06em;
}
.login__btn:hover:not(:disabled) { animation: none; transform: translateY(-2px); box-shadow: 0 4px 20px rgba(124,58,237,0.3); }
.login__btn:active:not(:disabled) { transform: scale(0.97); }
.login__btn:disabled { opacity: 0.5; cursor: not-allowed; animation: none; }
@keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(124,58,237,0.3)} 50%{box-shadow:0 0 0 6px rgba(124,58,237,0)} }

.login__spinner { display: inline-block; width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.login__error { font-size: 13px; color: #dc2626; background: rgba(220,38,38,0.05); border: 1px solid rgba(220,38,38,0.12); border-radius: 8px; padding: 10px 14px; margin: 0; }
.shake-enter-active { animation: shake 0.35s ease; }
@keyframes shake { 0%,100%{transform:translateX(0)} 20%{transform:translateX(-6px)} 40%{transform:translateX(6px)} 60%{transform:translateX(-4px)} 80%{transform:translateX(4px)} }

.login__hint { text-align: center; font-size: 12px; color: var(--color-text-muted); margin: 14px 0 0; }

[data-theme="dark"] .login { background: linear-gradient(160deg, #0a0015 0%, #1a0a2e 40%, #2d1060 70%, #44403c 100%); }
[data-theme="dark"] .login__card { background: rgba(41,37,36,0.6); border-color: rgba(255,255,255,0.06); }
[data-theme="dark"] .login__input { background: rgba(41,37,36,0.5); border-color: var(--color-border); }
[data-theme="dark"] .login__input input { color: var(--color-text); }
[data-theme="dark"] .login__label { color: var(--color-text-secondary); }

@media (max-width: 600px) {
  .login__card { padding: 28px 24px; }
  .login__demo { max-width: 100%; }
}
</style>
