<template>
  <nav class="app-nav-bar">
    <div class="app-nav-bar__left">
      <router-link to="/" class="app-nav-bar__brand">
        <span class="app-nav-bar__logo">⚡</span>
        <span class="app-nav-bar__name">ConfigForge</span>
      </router-link>
      <span v-if="badge" class="app-nav-bar__badge">{{ badge }}</span>
    </div>
    <div class="app-nav-bar__right">
      <router-link to="/" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'home' }" :aria-current="currentRoute === 'home' ? 'page' : undefined">我的配置</router-link>
      <router-link to="/templates" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'templates' }" :aria-current="currentRoute === 'templates' ? 'page' : undefined">模板市场</router-link>
      <router-link to="/history" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'history' }" :aria-current="currentRoute === 'history' ? 'page' : undefined">执行历史</router-link>
      <router-link to="/schedules" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'schedules' }" :aria-current="currentRoute === 'schedules' ? 'page' : undefined">定时任务</router-link>
      <router-link to="/settings" class="app-nav-bar__link" :class="{ 'app-nav-bar__link--active': currentRoute === 'settings' }" :aria-current="currentRoute === 'settings' ? 'page' : undefined">设置</router-link>
      <button class="app-nav-bar__theme-btn" @click="toggleTheme" :title="isDark ? '切换亮色模式' : '切换暗色模式'" :aria-label="isDark ? '切换亮色模式' : '切换暗色模式'">
        {{ isDark ? '☀' : '☾' }}
      </button>
      <!-- User menu (only when JWT auth is enabled) -->
      <div v-if="auth.isAuthenticated" class="app-nav-bar__user">
        <button class="app-nav-bar__user-btn" @click="showUserMenu = !showUserMenu" :aria-label="'用户菜单'">
          <span class="app-nav-bar__user-avatar">{{ auth.user?.username?.charAt(0).toUpperCase() }}</span>
          <span class="app-nav-bar__user-name">{{ auth.user?.username }}</span>
        </button>
        <Transition name="nav-menu">
          <div v-if="showUserMenu" class="app-nav-bar__user-menu">
            <div class="app-nav-bar__user-info">
              <span class="app-nav-bar__user-role">{{ roleLabel }}</span>
            </div>
            <button v-if="auth.isAdmin" class="app-nav-bar__user-menu-item" @click="onOpenRegister">注册新用户</button>
            <button class="app-nav-bar__user-menu-item app-nav-bar__user-menu-item--danger" @click="onLogout">退出登录</button>
          </div>
        </Transition>
      </div>
    </div>
    <!-- Mobile hamburger button (visible ≤767px) -->
    <button class="app-nav-bar__hamburger" @click="showMobileDrawer = true" aria-label="打开导航菜单">
      <span class="app-nav-bar__hamburger-icon" :class="{ 'app-nav-bar__hamburger-icon--open': showMobileDrawer }"></span>
    </button>
    <!-- Mobile drawer -->
    <NDrawer v-model:show="showMobileDrawer" placement="left" :width="260" class="app-nav-bar__drawer">
      <NDrawerContent :title="'ConfigForge'" closable>
        <div class="app-nav-bar__drawer-links">
          <router-link to="/" class="app-nav-bar__drawer-link" :class="{ 'app-nav-bar__drawer-link--active': currentRoute === 'home' }" @click="showMobileDrawer = false">我的配置</router-link>
          <router-link to="/templates" class="app-nav-bar__drawer-link" :class="{ 'app-nav-bar__drawer-link--active': currentRoute === 'templates' }" @click="showMobileDrawer = false">模板市场</router-link>
          <router-link to="/history" class="app-nav-bar__drawer-link" :class="{ 'app-nav-bar__drawer-link--active': currentRoute === 'history' }" @click="showMobileDrawer = false">执行历史</router-link>
          <router-link to="/schedules" class="app-nav-bar__drawer-link" :class="{ 'app-nav-bar__drawer-link--active': currentRoute === 'schedules' }" @click="showMobileDrawer = false">定时任务</router-link>
          <router-link to="/settings" class="app-nav-bar__drawer-link" :class="{ 'app-nav-bar__drawer-link--active': currentRoute === 'settings' }" @click="showMobileDrawer = false">设置</router-link>
        </div>
        <div class="app-nav-bar__drawer-footer">
          <button class="app-nav-bar__drawer-theme-btn" @click="toggleTheme">
            {{ isDark ? '☀ 亮色模式' : '☾ 暗色模式' }}
          </button>
          <template v-if="auth.isAuthenticated">
            <div class="app-nav-bar__drawer-user">
              <span class="app-nav-bar__user-avatar">{{ auth.user?.username?.charAt(0).toUpperCase() }}</span>
              <span class="app-nav-bar__drawer-user-name">{{ auth.user?.username }}</span>
              <span class="app-nav-bar__user-role">{{ roleLabel }}</span>
            </div>
            <button v-if="auth.isAdmin" class="app-nav-bar__drawer-action" @click="showMobileDrawer = false; onOpenRegister()">注册新用户</button>
            <button class="app-nav-bar__drawer-action app-nav-bar__drawer-action--danger" @click="showMobileDrawer = false; onLogout()">退出登录</button>
          </template>
        </div>
      </NDrawerContent>
    </NDrawer>
    <!-- Click-outside backdrop for user menu -->
    <Teleport to="body">
      <div v-if="showUserMenu" class="app-nav-bar__backdrop" @click="showUserMenu = false"></div>
    </Teleport>

    <!-- Register user modal (admin only) -->
    <Teleport to="body">
      <div v-if="showRegisterModal" class="app-nav-bar__modal-backdrop" @click.self="showRegisterModal = false">
        <div class="app-nav-bar__modal">
          <h3 class="app-nav-bar__modal-title">注册新用户</h3>
          <form @submit.prevent="onRegister">
            <div class="app-nav-bar__modal-field">
              <label class="cf-label">用户名</label>
              <input v-model="registerForm.username" type="text" class="app-nav-bar__modal-input" placeholder="输入用户名" required />
            </div>
            <div class="app-nav-bar__modal-field">
              <label class="cf-label">密码</label>
              <input v-model="registerForm.password" type="password" class="app-nav-bar__modal-input" placeholder="输入密码" required />
            </div>
            <div class="app-nav-bar__modal-field">
              <label class="cf-label">角色</label>
              <div class="app-nav-bar__role-select">
                <button type="button" class="app-nav-bar__role-btn" :class="{ 'app-nav-bar__role-btn--active': registerForm.role === 'editor' }" @click="registerForm.role = 'editor'">✏️ 编辑者</button>
                <button type="button" class="app-nav-bar__role-btn" :class="{ 'app-nav-bar__role-btn--active': registerForm.role === 'viewer' }" @click="registerForm.role = 'viewer'">👁 查看者</button>
              </div>
            </div>
            <p v-if="registerError" class="app-nav-bar__modal-error">{{ registerError }}</p>
            <p v-if="registerSuccess" class="app-nav-bar__modal-success">{{ registerSuccess }}</p>
            <div class="app-nav-bar__modal-actions">
              <button type="button" class="app-nav-bar__modal-cancel" @click="showRegisterModal = false">取消</button>
              <button type="submit" class="app-nav-bar__modal-submit" :disabled="registerLoading">
                <span v-if="registerLoading" class="login__spinner"></span>
                <span v-else>创建用户</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import { NDrawer, NDrawerContent } from 'naive-ui'
import { useTheme } from '../../composables/useTheme'
import { useAuthStore } from '../../stores/auth'

defineProps<{
  currentRoute: 'home' | 'wizard' | 'settings' | 'history' | 'schedules' | 'guide' | 'templates' | 'login'
  badge?: string
}>()

const { isDark, toggleTheme } = useTheme()
const auth = useAuthStore()
const showUserMenu = ref(false)
const showMobileDrawer = ref(false)
const showRegisterModal = ref(false)
const registerLoading = ref(false)
const registerError = ref('')
const registerSuccess = ref('')
const registerForm = reactive({ username: '', password: '', role: 'editor' })

const roleLabel = computed(() => {
  const role = auth.user?.role
  if (role === 'admin') return '管理员'
  if (role === 'editor') return '编辑者'
  if (role === 'viewer') return '查看者'
  return role || ''
})

function onLogout() {
  showUserMenu.value = false
  // Check if there's unsaved changes in the wizard
  const confirmed = window.confirm('确定要退出登录吗？未保存的修改将会丢失。')
  if (!confirmed) return
  auth.logout()
}

function onOpenRegister() {
  showUserMenu.value = false
  registerError.value = ''
  registerSuccess.value = ''
  registerForm.username = ''
  registerForm.password = ''
  registerForm.role = 'editor'
  showRegisterModal.value = true
}

async function onRegister() {
  registerError.value = ''
  registerSuccess.value = ''
  if (!registerForm.username.trim() || !registerForm.password) {
    registerError.value = '请输入用户名和密码'
    return
  }
  registerLoading.value = true
  try {
    const resp = await fetch('/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${auth.token}`,
      },
      body: JSON.stringify({
        username: registerForm.username.trim(),
        password: registerForm.password,
        role: registerForm.role,
      }),
    })
    const data = await resp.json()
    if (!resp.ok) {
      if (data.code === 'USERNAME_EXISTS') registerError.value = '用户名已存在'
      else if (data.code === 'FORBIDDEN') registerError.value = '仅管理员可注册新用户'
      else registerError.value = data.error || '注册失败'
    } else {
      registerSuccess.value = `用户 "${data.username}" 创建成功`
      registerForm.username = ''
      registerForm.password = ''
    }
  } catch {
    registerError.value = '网络连接失败'
  } finally {
    registerLoading.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (showRegisterModal.value) showRegisterModal.value = false
    else if (showUserMenu.value) showUserMenu.value = false
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.app-nav-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--color-surface-glass);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--color-border-light);
  transition: background var(--transition-normal);
}
.app-nav-bar__left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.app-nav-bar__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--color-text);
}
.app-nav-bar__logo {
  font-size: 20px;
}
.app-nav-bar__name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}
.app-nav-bar__badge {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
  border: 1px solid var(--color-primary-border);
}
.app-nav-bar__right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.app-nav-bar__link {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color var(--transition-fast);
  padding: 4px 0;
}
.app-nav-bar__link:hover {
  color: var(--color-primary);
}
.app-nav-bar__link--active {
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}
.app-nav-bar__theme-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  color: var(--color-text);
}
.app-nav-bar__theme-btn:hover {
  border-color: var(--color-primary-lighter);
  background: var(--color-primary-bg);
}

/* ───── User menu ───── */
.app-nav-bar__user {
  position: relative;
}

.app-nav-bar__user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 4px;
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 999px;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: var(--font-family);
}

.app-nav-bar__user-btn:hover {
  border-color: var(--color-primary-border);
  background: var(--color-primary-bg);
}

.app-nav-bar__user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  color: #fff;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.app-nav-bar__user-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.app-nav-bar__user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  min-width: 180px;
  padding-top: 6px;
}

.app-nav-bar__user-menu::after {
  content: '';
  position: absolute;
  top: 6px;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  z-index: -1;
}

.app-nav-bar__user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border-light);
  margin-bottom: 4px;
  position: relative;
  z-index: 1;
}

.app-nav-bar__user-role {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
  border: 1px solid var(--color-primary-border);
}

.app-nav-bar__user-menu-item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
  position: relative;
  z-index: 1;
}

.app-nav-bar__user-menu-item--danger:hover {
  background: var(--color-surface-hover);
  color: var(--color-error);
}

/* ───── Register modal ───── */
.app-nav-bar__modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.app-nav-bar__modal {
  width: 380px;
  max-width: 90vw;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 24px;
  animation: cf-slide-up 0.25s ease;
}

.app-nav-bar__modal-title {
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  margin: 0 0 20px;
}

.app-nav-bar__modal-field {
  margin-bottom: 16px;
}

.app-nav-bar__modal-input {
  width: 100%;
  padding: 10px 12px;
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  color: var(--color-text);
  background: var(--color-bg);
  border: 1.5px solid var(--color-border-light);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color var(--transition-fast);
  box-sizing: border-box;
}

.app-nav-bar__modal-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.app-nav-bar__role-select {
  display: flex;
  gap: 8px;
}

.app-nav-bar__role-btn {
  flex: 1;
  padding: 8px 12px;
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border: 1.5px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.app-nav-bar__role-btn:hover {
  border-color: var(--color-primary-border);
}

.app-nav-bar__role-btn--active {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.app-nav-bar__modal-error {
  font-size: var(--font-size-sm);
  color: var(--color-error);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin: 0 0 12px;
}

.app-nav-bar__modal-success {
  font-size: var(--font-size-sm);
  color: var(--color-success);
  background: var(--color-success-bg);
  border: 1px solid var(--color-success-border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin: 0 0 12px;
}

.app-nav-bar__modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.app-nav-bar__modal-cancel {
  padding: 8px 16px;
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.app-nav-bar__modal-cancel:hover {
  background: var(--color-surface-hover);
}

.app-nav-bar__modal-submit {
  padding: 8px 20px;
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-button);
}

.app-nav-bar__modal-submit:hover:not(:disabled) {
  transform: translateY(-1px);
}

.app-nav-bar__modal-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.app-nav-bar__backdrop {
  position: fixed;
  inset: 0;
  z-index: 99;
}

/* ───── Menu transition ───── */
.nav-menu-enter-active,
.nav-menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.nav-menu-enter-from,
.nav-menu-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.97);
}

/* ───── Hamburger button (mobile only) ───── */
.app-nav-bar__hamburger {
  display: none;
  width: 44px;
  height: 44px;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  padding: 0;
  transition: all var(--transition-fast);
  color: var(--color-text);
}

.app-nav-bar__hamburger:hover {
  border-color: var(--color-primary-lighter);
  background: var(--color-primary-bg);
}

.app-nav-bar__hamburger-icon {
  display: block;
  width: 20px;
  height: 2px;
  background: var(--color-text);
  position: relative;
  transition: background var(--transition-fast);
}

.app-nav-bar__hamburger-icon::before,
.app-nav-bar__hamburger-icon::after {
  content: '';
  position: absolute;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--color-text);
  transition: transform var(--transition-fast);
}

.app-nav-bar__hamburger-icon::before {
  top: -6px;
}

.app-nav-bar__hamburger-icon::after {
  top: 6px;
}

.app-nav-bar__hamburger-icon--open {
  background: transparent;
}

.app-nav-bar__hamburger-icon--open::before {
  top: 0;
  transform: rotate(45deg);
}

.app-nav-bar__hamburger-icon--open::after {
  top: 0;
  transform: rotate(-45deg);
}

/* ───── Mobile drawer ───── */
.app-nav-bar__drawer-links {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.app-nav-bar__drawer-link {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 10px 12px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.app-nav-bar__drawer-link:hover {
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

.app-nav-bar__drawer-link--active {
  color: var(--color-primary);
  background: var(--color-primary-bg);
  font-weight: var(--font-weight-semibold);
}

.app-nav-bar__drawer-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
  margin-top: 16px;
}

.app-nav-bar__drawer-theme-btn {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 10px 12px;
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: none;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.app-nav-bar__drawer-theme-btn:hover {
  color: var(--color-primary);
  border-color: var(--color-primary-border);
  background: var(--color-primary-bg);
}

.app-nav-bar__drawer-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  min-height: 44px;
}

.app-nav-bar__drawer-user-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.app-nav-bar__drawer-action {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 10px 12px;
  font-family: var(--font-family);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: none;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition-fast);
}

.app-nav-bar__drawer-action:hover {
  background: var(--color-surface-hover);
}

.app-nav-bar__drawer-action--danger:hover {
  color: var(--color-error);
}

/* Mobile */
@media (max-width: 767px) {
  .app-nav-bar {
    padding: 0 12px;
  }
  .app-nav-bar__name {
    display: none;
  }
  .app-nav-bar__right {
    display: none;
  }
  .app-nav-bar__hamburger {
    display: flex;
  }
}
</style>
