import { ref, onMounted, onUnmounted, type Ref } from 'vue'

export type Breakpoint = 'desktop' | 'tablet' | 'mobile'

export function useBreakpoint(): { breakpoint: Ref<Breakpoint> } {
  const breakpoint = ref<Breakpoint>('desktop')

  let tabletMql: MediaQueryList | null = null
  let mobileMql: MediaQueryList | null = null

  function update() {
    if (mobileMql?.matches) {
      breakpoint.value = 'mobile'
    } else if (tabletMql?.matches) {
      breakpoint.value = 'tablet'
    } else {
      breakpoint.value = 'desktop'
    }
  }

  onMounted(() => {
    tabletMql = window.matchMedia('(max-width: 1023px)')
    mobileMql = window.matchMedia('(max-width: 767px)')

    update()

    tabletMql.addEventListener('change', update)
    mobileMql.addEventListener('change', update)
  })

  onUnmounted(() => {
    tabletMql?.removeEventListener('change', update)
    mobileMql?.removeEventListener('change', update)
  })

  return { breakpoint }
}
