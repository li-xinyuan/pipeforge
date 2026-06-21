<template>
  <div class="change-password">
    <div class="change-password__bg">
      <div class="change-password__orb change-password__orb--1"></div>
      <div class="change-password__orb change-password__orb--2"></div>
    </div>

    <div class="change-password__card">
      <div class="change-password__brand">
        <span class="change-password__logo">⚡</span>
        <span class="change-password__logo-text">ConfigForge</span>
        <p class="change-password__tagline">修改密码</p>
      </div>

      <div class="change-password__alert">
        首次登录需要修改默认密码后才能继续使用系统
      </div>

      <form class="change-password__form" @submit.prevent="onSubmit">
        <div class="change-password__field">
          <span class="change-password__label">旧密码</span>
          <div class="change-password__input" :class="{ 'is-error': errorMsg }">
            <span class="change-password__input-icon">🔑</span>
            <input v-model="form.old_password" type="password" placeholder="请输入旧密码" autocomplete="current-password" required />
          </div>
        </div>

        <div class="change-password__field">
          <span class="change-password__label">新密码</span>
          <div class="change-password__input" :class="{ 'is-error': errorMsg }">
            <span class="change-password__input-icon">🔒</span>
            <input v-model="form.new_password" type="password" placeholder="至少 6 个字符" autocomplete="new-password" required />
          </div>
        </div>

        <div class="change-password__field">
          <span class="change-password__label">确认新密码</span>
          <div class="change-password__input" :class="{ 'is-error': errorMsg }">
            <span class="change-password__input-icon">🔒</span>
            <input v-model="form.confirm_password" type="password" placeholder="再次输入新密码" autocomplete="new-password" required />
          </div>
        </div>

        <Transition name="shake">
          <p v-if="errorMsg" class="change-password__error">{{ errorMsg }}</p>
        </Transition>

        <button type="submit" class="change-password__btn" :disabled="loading">
          <span v-if="loading" class="change-password__spinner"></span>
          <span v-else>确认修改</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const errorMsg = ref('')
const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

async function onSubmit() {
  errorMsg.value = ''

  if (!form.old_password) {
    errorMsg.value = '请输入旧密码'
    return
  }
  if (form.new_password.length < 6) {
    errorMsg.value = '新密码长度不能少于 6 个字符'
    return
  }
  if (form.new_password !== form.confirm_password) {
    errorMsg.value = '两次输入的新密码不一致'
    return
  }

  loading.value = true
  try {
    const resp = await fetch('/api/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${auth.token}`,
      },
      body: JSON.stringify({
        old_password: form.old_password,
        new_password: form.new_password,
      }),
    })

    if (!resp.ok) {
      const data = await resp.json()
      if (data.code === 'INVALID_PASSWORD') {
        errorMsg.value = '旧密码错误'
      } else {
        errorMsg.value = data.error || '修改密码失败'
      }
      return
    }

    auth.mustChangePassword = false
    router.push('/')
  } catch {
    errorMsg.value = '网络连接失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(160deg, #f0fdfa 0%, #fafaf9 40%, #f0fdfa 100%);
  position: relative; overflow: hidden;
  padding: 40px 24px;
}
.change-password__bg { position: absolute; inset: 0; pointer-events: none; }
.change-password__orb {
  position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.25;
  animation: drift 20s ease-in-out infinite;
}
.change-password__orb--1 { width: 500px; height: 500px; background: #5eead4; top: -150px; right: -120px; animation-delay: 0s; }
.change-password__orb--2 { width: 400px; height: 400px; background: #99f6e4; bottom: -120px; left: -100px; animation-delay: -7s; }
@keyframes drift { 0%,100%{transform:translate(0,0) scale(1)} 33%{transform:translate(30px,-20px) scale(1.05)} 66%{transform:translate(-20px,25px) scale(0.95)} }

.change-password__card {
  position: relative; z-index: 2;
  width: 100%; max-width: 440px;
  background: var(--color-surface-glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(153,246,228,0.3);
  border-radius: 20px;
  padding: 24px 36px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 8px 32px rgba(13,148,136,0.06);
}
.change-password__brand { text-align: center; margin-bottom: 8px; }
.change-password__logo { font-size: 28px; display: block; margin-bottom: 4px; }
.change-password__logo-text {
  font-family: var(--font-display);
  font-size: 22px; font-weight: 800;
  color: var(--color-primary);
}
.change-password__tagline { font-size: 14px; color: var(--color-text-secondary); margin: 2px 0 0; }

.change-password__alert {
  text-align: center; font-size: 13px; color: var(--color-warning);
  background: var(--color-warning-bg); border: 1px solid var(--color-warning-border);
  border-radius: 8px; padding: 10px 14px; margin: 0 0 16px;
}

.change-password__form { display: flex; flex-direction: column; gap: 14px; }
.change-password__field { display: flex; flex-direction: column; gap: 4px; }
.change-password__label {
  font-family: var(--font-display);
  font-size: 13px; font-weight: 600; color: var(--color-text-secondary);
}
.change-password__input {
  display: flex; align-items: center;
  background: var(--color-surface-input);
  border: 1.5px solid var(--color-border);
  border-radius: 10px; overflow: hidden;
  transition: all 0.2s;
}
.change-password__input:focus-within { border-color: var(--color-primary); box-shadow: 0 0 0 3px rgba(15,118,110,0.06); background: var(--color-surface-input-focus); }
.change-password__input.is-error { border-color: var(--color-error) !important; }
.change-password__input-icon { width: 42px; text-align: center; font-size: 15px; opacity: 0.4; flex-shrink: 0; }
.change-password__input input {
  flex: 1; padding: 11px 12px 11px 0;
  font-family: var(--font-body); font-size: 14px; color: var(--color-text);
  background: transparent; border: none; outline: none;
}
.change-password__input input::placeholder { color: var(--color-text-muted); }

.change-password__btn {
  width: 100%; padding: 13px 24px;
  font-family: var(--font-display); font-size: 15px; font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  border: none; border-radius: 10px; cursor: pointer;
  box-shadow: 0 0 0 0 rgba(15,118,110,0.3);
  transition: all 0.3s;
  letter-spacing: 0.06em;
}
.change-password__btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(15,118,110,0.25); }
.change-password__btn:active:not(:disabled) { transform: scale(0.97); }
.change-password__btn:disabled { opacity: 0.5; cursor: not-allowed; }

.change-password__spinner { display: inline-block; width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.change-password__error { font-size: 13px; color: var(--color-error); background: var(--color-error-bg); border: 1px solid var(--color-error-border); border-radius: 8px; padding: 10px 14px; margin: 0; }
.shake-enter-active { animation: shake 0.35s ease; }
@keyframes shake { 0%,100%{transform:translateX(0)} 20%{transform:translateX(-6px)} 40%{transform:translateX(6px)} 60%{transform:translateX(-4px)} 80%{transform:translateX(4px)} }

[data-theme="dark"] .change-password { background: linear-gradient(160deg, #0d241a 0%, #1c1917 50%, #0d241a 100%); }
[data-theme="dark"] .change-password__orb--1 { background: #0f766e; opacity: 0.15; }
[data-theme="dark"] .change-password__orb--2 { background: #14b8a6; opacity: 0.1; }
[data-theme="dark"] .change-password__card { border-color: rgba(20,184,166,0.1); }
[data-theme="dark"] .change-password__input input { color: var(--color-text); }
[data-theme="dark"] .change-password__label { color: var(--color-text-secondary); }
[data-theme="dark"] .change-password__logo-text { color: var(--color-primary-light); }

@media (max-width: 600px) {
  .change-password__card { padding: 28px 24px; }
}
</style>
