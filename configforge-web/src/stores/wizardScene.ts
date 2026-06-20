import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SceneInfo } from '../types/wizard'

export const useWizardSceneStore = defineStore('wizardScene', () => {
  const scene = ref<SceneInfo>({ name: '', description: '', version: '1.0' })

  function reset() {
    scene.value = { name: '', description: '', version: '1.0' }
  }

  function loadScene(data: { name?: string; description?: string; version?: string }) {
    scene.value = {
      name: data.name || '',
      description: data.description || '',
      version: data.version || '1.0',
    }
  }

  return { scene, reset, loadScene }
}, {
  persist: { key: 'wizard_scene_v1', storage: localStorage }
})
