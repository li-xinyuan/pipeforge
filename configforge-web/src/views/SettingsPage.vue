<template>
  <div class="settings">
    <AppNavBar current-route="settings" />

    <!-- Page content -->
    <div class="settings__body">
      <h1 class="settings__title">{{ t('settings.title') }}</h1>

      <!-- Desktop: NTabs -->
      <NTabs v-if="!isMobile" type="segment" animated>
        <NTabPane v-if="authStore.canAdmin" name="ai" :tab="t('settings.tabs.ai')">
          <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; padding: 12px; background: var(--color-primary-bg); border-radius: var(--radius-md); border: 1px solid var(--color-primary-border);">
            {{ t('settings.ai.hint') }}
          </p>
          <div class="settings__card">
            <!-- Enable switch -->
            <div class="settings__row">
              <span class="settings__label">{{ t('settings.ai.enable') }}</span>
              <NSwitch :value="form.enabled" @update:value="form.enabled = $event" />
            </div>

            <div class="settings__divider" />

            <!-- Provider -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.provider') }}</label>
              <NSelect v-model:value="form.provider" :options="providerOptions" />
            </div>

            <!-- Model -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.model') }}</label>
              <NInput v-model:value="form.model" :placeholder="defaultModel" />
              <p class="settings__hint">{{ t('settings.ai.modelHint', { default: defaultModel }) }}</p>
            </div>

            <!-- API Key -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.apiKey') }}</label>
              <NInput v-model:value="form.api_key" type="password" placeholder="sk-..." show-password-toggle />
              <p v-if="maskedKey" class="settings__hint">{{ t('settings.ai.currentKey', { key: maskedKey }) }}</p>
            </div>

            <!-- Base URL -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.baseUrl') }}</label>
              <NInput v-model:value="form.base_url" :placeholder="baseUrlPlaceholder" />
            </div>

            <!-- Temperature -->
            <div class="settings__field">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <label class="settings__field-label" style="margin-bottom: 0;">Temperature</label>
                <span style="font-size: var(--font-size-sm); font-weight: 600; color: var(--color-primary);">{{ form.temperature }}</span>
              </div>
              <NSlider v-model:value="form.temperature" :min="0" :max="2" :step="0.1" />
            </div>

            <!-- Max Tokens -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.maxTokens') }}</label>
              <NInputNumber v-model:value="form.max_tokens" :min="256" :max="65536" class="w-full" :placeholder="t('settings.ai.maxTokensPlaceholder')" />
            </div>

            <div class="settings__divider" />

            <!-- Actions -->
            <div class="settings__actions">
              <NButton :loading="testing" @click="testConnection">{{ t('settings.ai.testConnection') }}</NButton>
              <span style="font-size: var(--font-size-xs); color: var(--color-text-muted); margin-left: 8px;">{{ t('settings.ai.testHint') }}</span>
              <NButton type="primary" class="btn-primary" :loading="saving" @click="saveSettings">{{ t('settings.ai.saveSettings') }}</NButton>
            </div>
            <p v-if="testResult" class="settings__result" :class="testResult.ok ? 'settings__result--ok' : 'settings__result--error'">
              {{ testResult.msg }}
            </p>
            <p v-if="saveMsg" class="settings__result settings__result--ok">{{ saveMsg }}</p>
          </div>
        </NTabPane>

        <NTabPane v-if="authStore.canAdmin" name="database" :tab="t('settings.tabs.database')">
          <div class="settings__card">
            <ConnectionManager />
          </div>
        </NTabPane>

        <NTabPane name="smtp" :tab="t('settings.tabs.smtp')">
          <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; padding: 12px; background: var(--color-primary-bg); border-radius: var(--radius-md); border: 1px solid var(--color-primary-border);">
            {{ t('settings.smtp.hint') }}
          </p>
          <div class="settings__card">
            <!-- Host -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.host') }}</label>
              <NInput v-model:value="smtpForm.host" placeholder="smtp.gmail.com" />
            </div>

            <!-- Port -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.port') }}</label>
              <NInputNumber v-model:value="smtpForm.port" :min="1" :max="65535" class="w-full" placeholder="587" />
            </div>

            <!-- User -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.user') }}</label>
              <NInput v-model:value="smtpForm.user" placeholder="your@gmail.com" />
            </div>

            <!-- Password -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.password') }}</label>
              <NInput v-model:value="smtpForm.password" type="password" :placeholder="t('settings.smtp.passwordPlaceholder')" show-password-toggle />
              <p v-if="smtpMaskedPwd" class="settings__hint">{{ t('settings.smtp.currentKey', { key: smtpMaskedPwd }) }}</p>
            </div>

            <!-- Sender -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.sender') }}</label>
              <NInput v-model:value="smtpForm.sender" :placeholder="t('settings.smtp.senderPlaceholder')" />
            </div>

            <!-- TLS -->
            <div class="settings__row">
              <span class="settings__label">{{ t('settings.smtp.useTls') }}</span>
              <NSwitch :value="smtpForm.use_tls" @update:value="smtpForm.use_tls = $event" />
            </div>

            <div class="settings__divider" />

            <!-- Actions -->
            <div class="settings__actions">
              <NButton :loading="smtpTesting" @click="testSmtpConnection">{{ t('settings.smtp.testConnection') }}</NButton>
              <span style="font-size: var(--font-size-xs); color: var(--color-text-muted); margin-left: 8px;">{{ t('settings.smtp.testHint') }}</span>
              <NButton type="primary" class="btn-primary" :loading="smtpSaving" @click="saveSmtpSettings">{{ t('settings.smtp.saveSettings') }}</NButton>
            </div>
            <p v-if="smtpTestResult" class="settings__result" :class="smtpTestResult.ok ? 'settings__result--ok' : 'settings__result--error'">
              {{ smtpTestResult.msg }}
            </p>
            <p v-if="smtpSaveMsg" class="settings__result settings__result--ok">{{ smtpSaveMsg }}</p>
          </div>
        </NTabPane>

        <NTabPane v-if="authStore.canAdmin" name="storage" :tab="t('settings.tabs.storage')">
          <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; padding: 12px; background: var(--color-primary-bg); border-radius: var(--radius-md); border: 1px solid var(--color-primary-border);">
            {{ t('settings.storage.hint') }}
          </p>
          <div class="settings__card">
            <!-- Current backend -->
            <div class="settings__row">
              <span class="settings__label">{{ t('settings.storage.currentBackend') }}</span>
              <span style="font-weight: 600; color: var(--color-primary);">{{ storageInfo.backend }}</span>
            </div>
            <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin: 4px 0 0 0;">{{ storageInfo.description }}</p>

            <template v-if="storageInfo.dialect">
              <div class="settings__divider" />
              <div class="settings__row">
                <span class="settings__label">{{ t('settings.storage.dialect') }}</span>
                <span>{{ storageInfo.dialect }}</span>
              </div>
              <div v-if="storageInfo.table_count !== null" class="settings__row">
                <span class="settings__label">{{ t('settings.storage.tableCount') }}</span>
                <span>{{ storageInfo.table_count }}</span>
              </div>
            </template>

            <div class="settings__divider" />

            <!-- Config summary -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.storage.configSummary') }}</label>
              <div v-for="(value, key) in storageInfo.config" :key="key" class="settings__row">
                <span class="settings__label" style="font-family: monospace; min-width: 140px;">{{ key }}</span>
                <span style="font-family: monospace; word-break: break-all; text-align: right;">{{ value }}</span>
              </div>
            </div>

            <div class="settings__divider" />

            <!-- Switch hint -->
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.storage.switchHint') }}</label>
              <p style="font-size: var(--font-size-sm); color: var(--color-text-muted);">{{ t('settings.storage.switchHintText') }}</p>
              <p style="font-size: var(--font-size-xs); color: #e6a23c; margin-top: 8px;">⚠ {{ t('settings.storage.needRestart') }}</p>
            </div>

            <!-- Available backends with pros/cons -->
            <div class="settings__divider" />
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.storage.availableBackends') }}</label>
              <div v-for="opt in backendOptions" :key="opt.key"
                :style="{
                  border: '1px solid ' + (opt.key === storageInfo.backend ? 'var(--color-primary, #4f46e5)' : 'var(--color-border, #e0e0e0)'),
                  borderRadius: 'var(--radius-md, 8px)',
                  padding: '12px',
                  marginBottom: '8px',
                  backgroundColor: opt.key === storageInfo.backend ? 'var(--color-primary-bg, #eef2ff)' : 'transparent',
                }">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span style="font-weight: 600;">{{ opt.name }}</span>
                  <span v-if="opt.key === storageInfo.backend" style="font-size: var(--font-size-xs); color: var(--color-primary, #4f46e5); font-weight: 600;">✓ {{ t('settings.storage.currentBackend') }}</span>
                </div>
                <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin: 0 0 8px 0;">{{ opt.scenario }}</p>
                <code style="display: block; font-size: var(--font-size-xs); background: var(--color-bg-secondary, #f5f5f5); padding: 4px 8px; border-radius: 4px; margin-bottom: 8px; word-break: break-all;">{{ opt.envValue }}</code>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: var(--font-size-sm);">
                  <div>
                    <p style="font-weight: 600; margin: 0 0 4px 0; color: #22c55e;">✅ {{ t('settings.storage.pros') }}</p>
                    <ul style="margin: 0; padding-left: 16px; color: var(--color-text-muted);">
                      <li v-for="(pro, i) in opt.pros" :key="i">{{ pro }}</li>
                    </ul>
                  </div>
                  <div>
                    <p style="font-weight: 600; margin: 0 0 4px 0; color: #ef4444;">❌ {{ t('settings.storage.cons') }}</p>
                    <ul style="margin: 0; padding-left: 16px; color: var(--color-text-muted);">
                      <li v-for="(con, i) in opt.cons" :key="i">{{ con }}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </NTabPane>

        <NTabPane name="language" :tab="t('settings.tabs.language')">
          <div class="settings__card">
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.language.label') }}</label>
              <NSelect v-model:value="currentLocale" :options="localeOptions" @update:value="onLocaleChange" />
              <p class="settings__hint">{{ t('settings.language.hint') }}</p>
            </div>
          </div>
        </NTabPane>
      </NTabs>

      <!-- Mobile: NCollapse -->
      <NCollapse v-else :default-expanded-names="['ai', 'database', 'smtp', 'storage', 'language']">
        <NCollapseItem v-if="authStore.canAdmin" name="ai" :title="t('settings.tabs.ai')">
          <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; padding: 12px; background: var(--color-primary-bg); border-radius: var(--radius-md); border: 1px solid var(--color-primary-border);">
            {{ t('settings.ai.hint') }}
          </p>
          <div class="settings__card">
            <div class="settings__row">
              <span class="settings__label">{{ t('settings.ai.enable') }}</span>
              <NSwitch :value="form.enabled" @update:value="form.enabled = $event" />
            </div>
            <div class="settings__divider" />
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.provider') }}</label>
              <NSelect v-model:value="form.provider" :options="providerOptions" />
            </div>
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.model') }}</label>
              <NInput v-model:value="form.model" :placeholder="defaultModel" />
              <p class="settings__hint">{{ t('settings.ai.modelHint', { default: defaultModel }) }}</p>
            </div>
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.apiKey') }}</label>
              <NInput v-model:value="form.api_key" type="password" placeholder="sk-..." show-password-toggle />
              <p v-if="maskedKey" class="settings__hint">{{ t('settings.ai.currentKey', { key: maskedKey }) }}</p>
            </div>
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.baseUrl') }}</label>
              <NInput v-model:value="form.base_url" :placeholder="baseUrlPlaceholder" />
            </div>
            <div class="settings__field">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <label class="settings__field-label" style="margin-bottom: 0;">Temperature</label>
                <span style="font-size: var(--font-size-sm); font-weight: 600; color: var(--color-primary);">{{ form.temperature }}</span>
              </div>
              <NSlider v-model:value="form.temperature" :min="0" :max="2" :step="0.1" />
            </div>
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.ai.maxTokens') }}</label>
              <NInputNumber v-model:value="form.max_tokens" :min="256" :max="65536" class="w-full" :placeholder="t('settings.ai.maxTokensPlaceholder')" />
            </div>
            <div class="settings__divider" />
            <div class="settings__actions">
              <NButton :loading="testing" @click="testConnection">{{ t('settings.ai.testConnection') }}</NButton>
              <span style="font-size: var(--font-size-xs); color: var(--color-text-muted); margin-left: 8px;">{{ t('settings.ai.testHint') }}</span>
              <NButton type="primary" class="btn-primary" :loading="saving" @click="saveSettings">{{ t('settings.ai.saveSettings') }}</NButton>
            </div>
            <p v-if="testResult" class="settings__result" :class="testResult.ok ? 'settings__result--ok' : 'settings__result--error'">
              {{ testResult.msg }}
            </p>
            <p v-if="saveMsg" class="settings__result settings__result--ok">{{ saveMsg }}</p>
          </div>
        </NCollapseItem>

        <NCollapseItem v-if="authStore.canAdmin" name="database" :title="t('settings.tabs.database')">
          <div class="settings__card">
            <ConnectionManager />
          </div>
        </NCollapseItem>

        <NCollapseItem name="smtp" :title="t('settings.tabs.smtp')">
          <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; padding: 12px; background: var(--color-primary-bg); border-radius: var(--radius-md); border: 1px solid var(--color-primary-border);">
            {{ t('settings.smtp.hint') }}
          </p>
          <div class="settings__card">
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.host') }}</label>
              <NInput v-model:value="smtpForm.host" placeholder="smtp.gmail.com" />
            </div>
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.port') }}</label>
              <NInputNumber v-model:value="smtpForm.port" :min="1" :max="65535" class="w-full" placeholder="587" />
            </div>
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.user') }}</label>
              <NInput v-model:value="smtpForm.user" placeholder="your@gmail.com" />
            </div>
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.password') }}</label>
              <NInput v-model:value="smtpForm.password" type="password" :placeholder="t('settings.smtp.passwordPlaceholder')" show-password-toggle />
              <p v-if="smtpMaskedPwd" class="settings__hint">{{ t('settings.smtp.currentKey', { key: smtpMaskedPwd }) }}</p>
            </div>
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.smtp.sender') }}</label>
              <NInput v-model:value="smtpForm.sender" :placeholder="t('settings.smtp.senderPlaceholder')" />
            </div>
            <div class="settings__row">
              <span class="settings__label">{{ t('settings.smtp.useTls') }}</span>
              <NSwitch :value="smtpForm.use_tls" @update:value="smtpForm.use_tls = $event" />
            </div>
            <div class="settings__divider" />
            <div class="settings__actions">
              <NButton :loading="smtpTesting" @click="testSmtpConnection">{{ t('settings.smtp.testConnection') }}</NButton>
              <span style="font-size: var(--font-size-xs); color: var(--color-text-muted); margin-left: 8px;">{{ t('settings.smtp.testHint') }}</span>
              <NButton type="primary" class="btn-primary" :loading="smtpSaving" @click="saveSmtpSettings">{{ t('settings.smtp.saveSettings') }}</NButton>
            </div>
            <p v-if="smtpTestResult" class="settings__result" :class="smtpTestResult.ok ? 'settings__result--ok' : 'settings__result--error'">
              {{ smtpTestResult.msg }}
            </p>
            <p v-if="smtpSaveMsg" class="settings__result settings__result--ok">{{ smtpSaveMsg }}</p>
          </div>
        </NCollapseItem>

        <NCollapseItem v-if="authStore.canAdmin" name="storage" :title="t('settings.tabs.storage')">
          <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin-bottom: 16px; padding: 12px; background: var(--color-primary-bg); border-radius: var(--radius-md); border: 1px solid var(--color-primary-border);">
            {{ t('settings.storage.hint') }}
          </p>
          <div class="settings__card">
            <div class="settings__row">
              <span class="settings__label">{{ t('settings.storage.currentBackend') }}</span>
              <span style="font-weight: 600; color: var(--color-primary);">{{ storageInfo.backend }}</span>
            </div>
            <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin: 4px 0 0 0;">{{ storageInfo.description }}</p>

            <template v-if="storageInfo.dialect">
              <div class="settings__divider" />
              <div class="settings__row">
                <span class="settings__label">{{ t('settings.storage.dialect') }}</span>
                <span>{{ storageInfo.dialect }}</span>
              </div>
              <div v-if="storageInfo.table_count !== null" class="settings__row">
                <span class="settings__label">{{ t('settings.storage.tableCount') }}</span>
                <span>{{ storageInfo.table_count }}</span>
              </div>
            </template>

            <div class="settings__divider" />

            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.storage.configSummary') }}</label>
              <div v-for="(value, key) in storageInfo.config" :key="key" class="settings__row">
                <span class="settings__label" style="font-family: monospace; min-width: 140px;">{{ key }}</span>
                <span style="font-family: monospace; word-break: break-all; text-align: right;">{{ value }}</span>
              </div>
            </div>

            <div class="settings__divider" />

            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.storage.switchHint') }}</label>
              <p style="font-size: var(--font-size-sm); color: var(--color-text-muted);">{{ t('settings.storage.switchHintText') }}</p>
              <p style="font-size: var(--font-size-xs); color: #e6a23c; margin-top: 8px;">⚠ {{ t('settings.storage.needRestart') }}</p>
            </div>

            <!-- Available backends with pros/cons -->
            <div class="settings__divider" />
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.storage.availableBackends') }}</label>
              <div v-for="opt in backendOptions" :key="opt.key"
                :style="{
                  border: '1px solid ' + (opt.key === storageInfo.backend ? 'var(--color-primary, #4f46e5)' : 'var(--color-border, #e0e0e0)'),
                  borderRadius: 'var(--radius-md, 8px)',
                  padding: '12px',
                  marginBottom: '8px',
                  backgroundColor: opt.key === storageInfo.backend ? 'var(--color-primary-bg, #eef2ff)' : 'transparent',
                }">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span style="font-weight: 600;">{{ opt.name }}</span>
                  <span v-if="opt.key === storageInfo.backend" style="font-size: var(--font-size-xs); color: var(--color-primary, #4f46e5); font-weight: 600;">✓ {{ t('settings.storage.currentBackend') }}</span>
                </div>
                <p style="font-size: var(--font-size-sm); color: var(--color-text-muted); margin: 0 0 8px 0;">{{ opt.scenario }}</p>
                <code style="display: block; font-size: var(--font-size-xs); background: var(--color-bg-secondary, #f5f5f5); padding: 4px 8px; border-radius: 4px; margin-bottom: 8px; word-break: break-all;">{{ opt.envValue }}</code>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: var(--font-size-sm);">
                  <div>
                    <p style="font-weight: 600; margin: 0 0 4px 0; color: #22c55e;">✅ {{ t('settings.storage.pros') }}</p>
                    <ul style="margin: 0; padding-left: 16px; color: var(--color-text-muted);">
                      <li v-for="(pro, i) in opt.pros" :key="i">{{ pro }}</li>
                    </ul>
                  </div>
                  <div>
                    <p style="font-weight: 600; margin: 0 0 4px 0; color: #ef4444;">❌ {{ t('settings.storage.cons') }}</p>
                    <ul style="margin: 0; padding-left: 16px; color: var(--color-text-muted);">
                      <li v-for="(con, i) in opt.cons" :key="i">{{ con }}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </NCollapseItem>

        <NCollapseItem name="language" :title="t('settings.tabs.language')">
          <div class="settings__card">
            <div class="settings__field">
              <label class="settings__field-label">{{ t('settings.language.label') }}</label>
              <NSelect v-model:value="currentLocale" :options="localeOptions" @update:value="onLocaleChange" />
              <p class="settings__hint">{{ t('settings.language.hint') }}</p>
            </div>
          </div>
        </NCollapseItem>
      </NCollapse>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAiApi } from '../composables/useWizardApi'
import { useApi } from '../composables/useApi'
import { useAuthStore } from '../stores/auth'
import { setLocale, AVAILABLE_LOCALES, type AppLocale } from '../i18n'
import { NButton, NInput, NSelect, NSwitch, NSlider, NInputNumber, NTabs, NTabPane, NCollapse, NCollapseItem, useMessage } from 'naive-ui'
import AppNavBar from '../components/common/AppNavBar.vue'
import ConnectionManager from '../components/common/ConnectionManager.vue'

interface AiSettingsForm {
  provider: string
  api_key: string
  base_url: string
  model: string
  temperature: number
  max_tokens: number
  enabled: boolean
}

const { getAiSettings, updateAiSettings, testAiConnection } = useAiApi()
const message = useMessage()
const authStore = useAuthStore()
const { t, tm, locale } = useI18n()

// ─── Available backend options (read from i18n) ───
interface BackendOption {
  key: string
  name: string
  envValue: string
  scenario: string
  pros: string[]
  cons: string[]
}
const backendOptions = computed<BackendOption[]>(() => {
  const raw = tm('settings.storage.backendOptions') as Record<string, Omit<BackendOption, 'key'>>
  return Object.entries(raw).map(([key, val]) => ({ key, ...val }))
})

// ─── Mobile detection ───
const isMobile = ref(window.innerWidth < 768)
function onResize() {
  isMobile.value = window.innerWidth < 768
}
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

const form = reactive<AiSettingsForm>({
  provider: 'openai', api_key: '', base_url: '', model: '',
  temperature: 0.7, max_tokens: 4096, enabled: false,
})

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Custom (OpenAI-compatible)', value: 'custom' },
]

const maskedKey = ref('')
const testing = ref(false)
const saving = ref(false)
const testResult = ref<{ ok: boolean; msg: string } | null>(null)
const saveMsg = ref('')

const defaultModel = computed(() => {
  if (form.provider === 'anthropic') return 'claude-sonnet-4-6'
  return 'gpt-4o'
})

const baseUrlPlaceholder = computed(() => {
  return form.provider === 'openai'
    ? t('settings.ai.baseUrlPlaceholderOpenai')
    : t('settings.ai.baseUrlPlaceholderRequired')
})

// ─── Language switcher ───
const currentLocale = ref<AppLocale>(locale.value as AppLocale)
const localeOptions = AVAILABLE_LOCALES.map(l => ({ label: l.label, value: l.value }))
function onLocaleChange(val: AppLocale) {
  setLocale(val)
  currentLocale.value = val
}

interface AiTestResponse {
  provider?: string
  model?: string
  latency_ms?: number
  detail?: string
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    await saveSettings()
    const { ok, data } = await testAiConnection()
    if (ok && data) {
      const resp = data as AiTestResponse
      const msg = t('settings.ai.connectionSuccess', {
        provider: resp.provider || '',
        model: resp.model || '',
        latency: resp.latency_ms ?? 0,
      })
      testResult.value = { ok: true, msg }
      message.success(msg)
    } else {
      const resp = data as AiTestResponse | null
      const msg = resp?.detail || t('settings.ai.connectionFailed')
      testResult.value = { ok: false, msg }
      message.error(msg)
    }
  } catch {
    const msg = t('settings.ai.networkError')
    testResult.value = { ok: false, msg }
    message.error(msg)
  } finally {
    testing.value = false
  }
}

async function saveSettings() {
  saving.value = true
  saveMsg.value = ''
  try {
    const body: Record<string, unknown> = { ...form }
    if (!body.api_key) body.api_key = null
    const ok = await updateAiSettings(body)
    if (ok) {
      saveMsg.value = t('settings.ai.saved')
      const data = await getAiSettings()
      if (data) maskedKey.value = data.api_key as string
      setTimeout(() => saveMsg.value = '', 3000)
    }
  } finally {
    saving.value = false
  }
}

// ─── SMTP Settings ───────────────────────────────────────
const { request: smtpRequest } = useApi()

interface SmtpSettingsForm {
  host: string
  port: number | null
  user: string
  password: string
  sender: string
  use_tls: boolean
}

const smtpForm = reactive<SmtpSettingsForm>({
  host: '', port: 587, user: '', password: '', sender: '', use_tls: true,
})

const smtpMaskedPwd = ref('')
const smtpTesting = ref(false)
const smtpSaving = ref(false)
const smtpTestResult = ref<{ ok: boolean; msg: string } | null>(null)
const smtpSaveMsg = ref('')

// ─── Storage backend info (read-only, admin only) ───
const { request: storageRequest } = useApi()

interface StorageBackendInfo {
  backend: string
  description: string
  dialect: string | null
  table_count: number | null
  config: Record<string, string>
}

const storageInfo = reactive<StorageBackendInfo>({
  backend: '', description: '', dialect: null, table_count: null, config: {},
})

onMounted(async () => {
  // Load AI settings
  const data = await getAiSettings()
  if (data) {
    form.provider = data.provider as string
    form.base_url = data.base_url as string
    form.model = data.model as string
    form.temperature = data.temperature as number
    form.max_tokens = data.max_tokens as number
    form.enabled = data.enabled as boolean
    maskedKey.value = data.api_key as string
  }

  // Load SMTP settings
  const smtpData = await smtpRequest<Record<string, unknown>>('GET', '/api/notifications/smtp-settings')
  if (smtpData) {
    smtpForm.host = (smtpData.host as string) || ''
    smtpForm.port = (smtpData.port as number) ?? 587
    smtpForm.user = (smtpData.user as string) || ''
    smtpForm.sender = (smtpData.sender as string) || ''
    smtpForm.use_tls = (smtpData.use_tls as boolean) ?? true
    smtpMaskedPwd.value = (smtpData.password as string) || ''
  }

  // Load storage backend info (admin only)
  if (authStore.canAdmin) {
    const storageData = await storageRequest<StorageBackendInfo>('GET', '/api/storage-backend')
    if (storageData) {
      Object.assign(storageInfo, storageData)
    }
  }
})

async function saveSmtpSettings() {
  smtpSaving.value = true
  smtpSaveMsg.value = ''
  try {
    const body: Record<string, unknown> = { ...smtpForm }
    if (!body.password) body.password = null
    const result = await smtpRequest<Record<string, unknown>>('PUT', '/api/notifications/smtp-settings', body)
    if (result) {
      smtpSaveMsg.value = t('settings.smtp.saved')
      smtpMaskedPwd.value = (result.password as string) || ''
      setTimeout(() => smtpSaveMsg.value = '', 3000)
    }
  } finally {
    smtpSaving.value = false
  }
}

async function testSmtpConnection() {
  smtpTesting.value = true
  smtpTestResult.value = null
  try {
    await saveSmtpSettings()
    const result = await smtpRequest<Record<string, unknown>>('POST', '/api/notifications/smtp-test')
    if (result) {
      smtpTestResult.value = { ok: !!result.success, msg: (result.message as string) || t('settings.smtp.testComplete') }
    } else {
      smtpTestResult.value = { ok: false, msg: t('settings.smtp.testFailed') }
    }
  } catch {
    smtpTestResult.value = { ok: false, msg: t('settings.smtp.networkError') }
  } finally {
    smtpTesting.value = false
  }
}
</script>

<style scoped>
/* Page body */
.settings__body {
  max-width: 600px;
  margin: 0 auto;
  padding: 40px 24px 80px;
}

.settings__title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 24px;
}

/* Card */
.settings__card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  padding: var(--space-card-padding);
  box-shadow: var(--shadow-md);
}

.settings__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}

.settings__label {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
}

.settings__divider {
  height: 1px;
  background: var(--color-border-light);
  margin: 14px 0;
}

.settings__field {
  margin-bottom: 14px;
}

.settings__field:last-of-type {
  margin-bottom: 0;
}

.settings__field-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 6px;
}

.settings__hint {
  margin: 4px 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
}

.settings__actions {
  display: flex;
  gap: 10px;
  padding-top: 4px;
}

.settings__result {
  margin-top: 10px;
  font-size: var(--font-size-sm);
}

.settings__result--ok {
  color: var(--color-success);
}

.settings__result--error {
  color: var(--color-error);
}

/* Responsive */
@media (max-width: 767px) {
  .settings__body {
    padding: 24px 16px 64px;
  }
  .settings__card {
    padding: 16px;
    border-radius: var(--radius-lg);
  }
  .settings__actions {
    flex-direction: column;
  }
  .settings__actions .n-button {
    min-height: 44px;
  }
}
</style>
