import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useTheme } from '../../src/composables/useTheme'

describe('useTheme', () => {
  let getItemSpy: ReturnType<typeof vi.fn>
  let setItemSpy: ReturnType<typeof vi.fn>
  let originalMatchMedia: typeof window.matchMedia

  beforeEach(() => {
    getItemSpy = vi.fn()
    setItemSpy = vi.fn()
    vi.stubGlobal('localStorage', {
      getItem: getItemSpy,
      setItem: setItemSpy,
      removeItem: vi.fn(),
      clear: vi.fn(),
      length: 0,
    })
    originalMatchMedia = window.matchMedia
    document.documentElement.removeAttribute('data-theme')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    window.matchMedia = originalMatchMedia
    vi.restoreAllMocks()
  })

  function mockMatchMedia(prefersDark: boolean) {
    window.matchMedia = vi.fn((query: string) => ({
      matches: query.includes('dark') ? prefersDark : false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })) as unknown as typeof window.matchMedia
  }

  describe('initTheme', () => {
    it('initializes to dark when localStorage has "dark"', () => {
      getItemSpy.mockReturnValue('dark')
      mockMatchMedia(false)
      const { isDark, initTheme } = useTheme()
      initTheme()
      expect(isDark.value).toBe(true)
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    })

    it('initializes to light when localStorage has "light"', () => {
      getItemSpy.mockReturnValue('light')
      mockMatchMedia(true)
      const { isDark, initTheme } = useTheme()
      initTheme()
      expect(isDark.value).toBe(false)
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    })

    it('falls back to system preference when no stored value', () => {
      getItemSpy.mockReturnValue(null)
      mockMatchMedia(true)
      const { isDark, initTheme } = useTheme()
      initTheme()
      expect(isDark.value).toBe(true)
    })

    it('falls back to light when system prefers light and no stored value', () => {
      getItemSpy.mockReturnValue(null)
      mockMatchMedia(false)
      const { isDark, initTheme } = useTheme()
      initTheme()
      expect(isDark.value).toBe(false)
    })

    it('falls back to system preference when localStorage throws', () => {
      getItemSpy.mockImplementation(() => { throw new Error('denied') })
      mockMatchMedia(true)
      const { isDark, initTheme } = useTheme()
      initTheme()
      expect(isDark.value).toBe(true)
    })

    it('persists theme to localStorage on init', () => {
      getItemSpy.mockReturnValue('dark')
      mockMatchMedia(false)
      const { initTheme } = useTheme()
      initTheme()
      expect(setItemSpy).toHaveBeenCalledWith('configforge-theme', 'dark')
    })
  })

  describe('toggleTheme', () => {
    it('toggles from light to dark', () => {
      getItemSpy.mockReturnValue('light')
      mockMatchMedia(false)
      const { isDark, initTheme, toggleTheme } = useTheme()
      initTheme()
      expect(isDark.value).toBe(false)
      toggleTheme()
      expect(isDark.value).toBe(true)
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    })

    it('toggles from dark to light', () => {
      getItemSpy.mockReturnValue('dark')
      mockMatchMedia(true)
      const { isDark, initTheme, toggleTheme } = useTheme()
      initTheme()
      expect(isDark.value).toBe(true)
      toggleTheme()
      expect(isDark.value).toBe(false)
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    })

    it('persists toggled value to localStorage', () => {
      getItemSpy.mockReturnValue('light')
      mockMatchMedia(false)
      const { initTheme, toggleTheme } = useTheme()
      initTheme()
      setItemSpy.mockClear()
      toggleTheme()
      expect(setItemSpy).toHaveBeenCalledWith('configforge-theme', 'dark')
    })

    it('silently ignores localStorage write errors', () => {
      getItemSpy.mockReturnValue('light')
      setItemSpy.mockImplementation(() => { throw new Error('quota') })
      mockMatchMedia(false)
      const { isDark, initTheme, toggleTheme } = useTheme()
      initTheme()
      expect(() => toggleTheme()).not.toThrow()
      expect(isDark.value).toBe(true)
    })
  })

  describe('reactive state', () => {
    it('isDark is shared across composable calls', () => {
      getItemSpy.mockReturnValue('dark')
      mockMatchMedia(false)
      const a = useTheme()
      const b = useTheme()
      a.initTheme()
      expect(b.isDark.value).toBe(true)
    })
  })
})
