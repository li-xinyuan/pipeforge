<template>
  <div class="cm-editor-wrapper" :class="{ 'cm-editor-wrapper--dark': isDark }">
    <div ref="editorRef"></div>
    <textarea
      v-if="fallbackMode"
      ref="fallbackRef"
      :value="modelValue"
      @input="onFallbackInput"
      :placeholder="placeholder"
      :readonly="readOnly"
      :style="{ minHeight: minHeight || '120px' }"
      class="cf-code-editor"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { EditorView, keymap, lineNumbers, highlightActiveLineGutter, highlightSpecialChars, drawSelection, highlightActiveLine, rectangularSelection, crosshairCursor } from '@codemirror/view'
import { EditorState, Compartment } from '@codemirror/state'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { syntaxHighlighting, indentOnInput, bracketMatching, foldGutter, foldKeymap, defaultHighlightStyle, HighlightStyle } from '@codemirror/language'
import { autocompletion, completionKeymap, closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete'
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search'
import { sql, StandardSQL } from '@codemirror/lang-sql'
import { pythonLanguage } from '@codemirror/lang-python'
import { yaml } from '@codemirror/lang-yaml'
import { tags, Tag } from '@lezer/highlight'
import { useTheme } from '../../composables/useTheme'

const props = defineProps<{
  modelValue: string
  language: 'sql' | 'python' | 'yaml'
  placeholder?: string
  readOnly?: boolean
  minHeight?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { isDark: isDarkFromTheme } = useTheme()
// Local reactive isDark that syncs with both useTheme and data-theme attribute
const isDark = ref(isDarkFromTheme.value || document.documentElement.getAttribute('data-theme') === 'dark')

// Sync with useTheme ref
watch(isDarkFromTheme, (val) => {
  isDark.value = val
})

// Also observe data-theme attribute changes as fallback (handles HMR module duplication)
let themeObserver: MutationObserver | null = null
const editorRef = ref<HTMLDivElement>()
const fallbackRef = ref<HTMLTextAreaElement>()
const fallbackMode = ref(false)
let editorView: EditorView | null = null
const themeCompartment = new Compartment()
const langCompartment = new Compartment()

// Custom light theme for better contrast
const lightTheme = EditorView.theme({
  '&': { fontSize: '13px', border: '1px solid var(--color-border)', borderRadius: '8px', backgroundColor: 'var(--color-surface)' },
  '.cm-content': { fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", Menlo, Monaco, Consolas, monospace', padding: '8px 0', color: 'var(--color-text)' },
  '.cm-focused': { outline: 'none', borderColor: 'var(--color-primary-light)' },
  '.cm-gutters': { backgroundColor: 'var(--color-bg-secondary)', borderRight: '1px solid var(--color-border-light)', color: 'var(--color-text-muted)' },
  '.cm-activeLineGutter': { backgroundColor: 'var(--color-surface-hover)' },
  '.cm-activeLine': { backgroundColor: 'var(--color-surface-hover)' },
  '.cm-selectionBackground': { backgroundColor: 'var(--color-primary-bg) !important' },
  '.cm-cursor': { borderLeftColor: 'var(--color-primary-light)' },
  '.cm-placeholder': { color: 'var(--color-text-muted)', fontStyle: 'italic' },
  '.cm-matchingBracket': { backgroundColor: 'var(--color-primary-bg)', outline: '1px solid var(--color-primary-light)' },
}, { dark: false })

// Custom dark theme
const darkTheme = EditorView.theme({
  '&': { fontSize: '13px', border: '1px solid var(--color-border)', borderRadius: '8px', backgroundColor: 'var(--color-code-bg)' },
  '.cm-content': { fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", Menlo, Monaco, Consolas, monospace', padding: '8px 0', color: '#abb2bf', caretColor: '#528bff' },
  '.cm-focused': { outline: 'none', borderColor: 'var(--color-primary-light)' },
  '.cm-gutters': { backgroundColor: 'var(--color-code-bg)', borderRight: '1px solid var(--color-border)', color: '#636d83' },
  '.cm-activeLineGutter': { backgroundColor: '#2c313a' },
  '.cm-activeLine': { backgroundColor: '#2c313a' },
  '.cm-selectionBackground': { backgroundColor: 'var(--color-primary-bg) !important' },
  '.cm-cursor': { borderLeftColor: '#528bff' },
  '.cm-placeholder': { color: '#636d83', fontStyle: 'italic' },
  '.cm-matchingBracket': { backgroundColor: 'var(--color-primary-bg)', outline: '1px solid var(--color-primary-light)' },
}, { dark: true })

// Custom SQL highlight style for light mode (lazy, may fail in happy-dom)
let sqlHighlight: ReturnType<typeof HighlightStyle.define> | null = null
let sqlDarkHighlight: ReturnType<typeof HighlightStyle.define> | null = null
let pythonHighlight: ReturnType<typeof HighlightStyle.define> | null = null
let pythonDarkHighlight: ReturnType<typeof HighlightStyle.define> | null = null
let yamlHighlight: ReturnType<typeof HighlightStyle.define> | null = null
let yamlDarkHighlight: ReturnType<typeof HighlightStyle.define> | null = null

// Python decorator tag — not included in the standard tags set
const decoratorTag = Tag.define(tags.meta)

try {
  sqlHighlight = HighlightStyle.define([
    { tag: tags.keyword, color: '#0369a1', fontWeight: 'bold' },
    { tag: tags.string, color: '#15803d' },
    { tag: tags.number, color: '#c2410c' },
    { tag: tags.comment, color: '#6b7280', fontStyle: 'italic' },
    { tag: tags.function(tags.variableName), color: '#7c3aed' },
    { tag: tags.operator, color: '#be185d' },
    { tag: tags.variableName, color: '#1e293b' },
    { tag: tags.typeName, color: '#0369a1' },
    { tag: tags.propertyName, color: '#475569' },
  ])
  sqlDarkHighlight = HighlightStyle.define([
    { tag: tags.keyword, color: '#67d4f8', fontWeight: 'bold' },
    { tag: tags.string, color: '#a5d6a7' },
    { tag: tags.number, color: '#ffa726' },
    { tag: tags.comment, color: '#9e9e9e', fontStyle: 'italic' },
    { tag: tags.function(tags.variableName), color: '#ce93d8' },
    { tag: tags.operator, color: '#f48fb1' },
    { tag: tags.variableName, color: '#e2e8f0' },
    { tag: tags.typeName, color: '#67d4f8' },
    { tag: tags.propertyName, color: '#b0bec5' },
  ])
} catch { /* happy-dom: tags.id undefined */ }

try {
  pythonHighlight = HighlightStyle.define([
    { tag: tags.keyword, color: '#7c3aed', fontWeight: 'bold' },
    { tag: tags.string, color: '#15803d' },
    { tag: tags.number, color: '#c2410c' },
    { tag: tags.comment, color: '#6b7280', fontStyle: 'italic' },
    { tag: tags.function(tags.variableName), color: '#0369a1' },
    { tag: decoratorTag, color: '#c2410c' },
    { tag: tags.operator, color: '#be185d' },
    { tag: tags.variableName, color: '#1e293b' },
    { tag: tags.self, color: '#be185d', fontStyle: 'italic' },
    { tag: tags.bool, color: '#0369a1' },
    { tag: tags.null, color: '#0369a1' },
  ])
  pythonDarkHighlight = HighlightStyle.define([
    { tag: tags.keyword, color: '#ce93d8', fontWeight: 'bold' },
    { tag: tags.string, color: '#a5d6a7' },
    { tag: tags.number, color: '#ffa726' },
    { tag: tags.comment, color: '#9e9e9e', fontStyle: 'italic' },
    { tag: tags.function(tags.variableName), color: '#67d4f8' },
    { tag: decoratorTag, color: '#ffa726' },
    { tag: tags.operator, color: '#f48fb1' },
    { tag: tags.variableName, color: '#e2e8f0' },
    { tag: tags.self, color: '#f48fb1', fontStyle: 'italic' },
    { tag: tags.bool, color: '#67d4f8' },
    { tag: tags.null, color: '#67d4f8' },
  ])
} catch { /* happy-dom: tags.id undefined */ }

try {
  yamlHighlight = HighlightStyle.define([
    { tag: tags.keyword, color: '#0369a1', fontWeight: 'bold' },
    { tag: tags.string, color: '#15803d' },
    { tag: tags.number, color: '#c2410c' },
    { tag: tags.comment, color: '#6b7280', fontStyle: 'italic' },
    { tag: tags.propertyName, color: '#7c3aed' },
    { tag: tags.bool, color: '#0369a1' },
    { tag: tags.null, color: '#0369a1' },
    { tag: tags.monospace, color: '#c2410c' },
  ])
  yamlDarkHighlight = HighlightStyle.define([
    { tag: tags.keyword, color: '#67d4f8', fontWeight: 'bold' },
    { tag: tags.string, color: '#a5d6a7' },
    { tag: tags.number, color: '#ffa726' },
    { tag: tags.comment, color: '#9e9e9e', fontStyle: 'italic' },
    { tag: tags.propertyName, color: '#ce93d8' },
    { tag: tags.bool, color: '#67d4f8' },
    { tag: tags.null, color: '#67d4f8' },
    { tag: tags.monospace, color: '#ffa726' },
  ])
} catch { /* happy-dom: tags.id undefined */ }

function getLanguageExtension() {
  if (props.language === 'sql') {
    return sql({ dialect: StandardSQL })
  }
  if (props.language === 'yaml') {
    return yaml()
  }
  return pythonLanguage
}

function getHighlightExtension() {
  let h: ReturnType<typeof HighlightStyle.define> | null
  if (props.language === 'sql') {
    h = isDark.value ? sqlDarkHighlight : sqlHighlight
  } else if (props.language === 'yaml') {
    h = isDark.value ? yamlDarkHighlight : yamlHighlight
  } else {
    h = isDark.value ? pythonDarkHighlight : pythonHighlight
  }
  return h ? syntaxHighlighting(h) : []
}

function getThemeExtension() {
  return isDark.value
    ? [darkTheme, getHighlightExtension()]
    : [lightTheme, getHighlightExtension()]
}

function onFallbackInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value)
}

onMounted(() => {
  // Set up MutationObserver to watch for data-theme changes
  themeObserver = new MutationObserver(() => {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark'
    if (isDark.value !== dark) {
      isDark.value = dark
    }
  })
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })

  if (!editorRef.value) return

  try {
    const startState = EditorState.create({
      doc: props.modelValue,
      extensions: [
        lineNumbers(),
        highlightActiveLineGutter(),
        highlightSpecialChars(),
        history(),
        foldGutter(),
        drawSelection(),
        indentOnInput(),
        bracketMatching(),
        closeBrackets(),
        highlightActiveLine(),
        rectangularSelection(),
        crosshairCursor(),
        highlightSelectionMatches(),
        keymap.of([
          ...closeBracketsKeymap,
          ...defaultKeymap,
          ...searchKeymap,
          ...historyKeymap,
          ...foldKeymap,
          ...completionKeymap,
          indentWithTab,
        ]),
        autocompletion(),
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            emit('update:modelValue', update.state.doc.toString())
          }
        }),
        EditorView.lineWrapping,
        langCompartment.of(getLanguageExtension()),
        themeCompartment.of(getThemeExtension()),
        EditorState.readOnly.of(props.readOnly ?? false),
        props.placeholder ? EditorView.contentAttributes.of({ 'data-placeholder': props.placeholder }) : [],
        props.minHeight ? EditorView.theme({ '&': { minHeight: props.minHeight } }) : [],
      ],
    })

    editorView = new EditorView({
      state: startState,
      parent: editorRef.value,
    })
  } catch {
    // Fallback to textarea in environments where CodeMirror can't initialize (e.g., happy-dom)
    fallbackMode.value = true
  }
})

// Watch for external modelValue changes
watch(() => props.modelValue, (newVal) => {
  if (fallbackMode.value) return
  if (!editorView) return
  const currentVal = editorView.state.doc.toString()
  if (newVal !== currentVal) {
    editorView.dispatch({
      changes: { from: 0, to: editorView.state.doc.length, insert: newVal },
    })
  }
})

// Watch for dark mode changes
watch(() => isDark.value, () => {
  if (!editorView) return
  try {
    editorView.dispatch({
      effects: themeCompartment.reconfigure(getThemeExtension()),
    })
  } catch { /* ignore reconfigure errors */ }
})

onBeforeUnmount(() => {
  themeObserver?.disconnect()
  themeObserver = null
  editorView?.destroy()
  editorView = null
})

// Expose methods for parent components
function focus() {
  if (editorView) editorView.focus()
  else fallbackRef.value?.focus()
}

function getSelectionRange(): { start: number; end: number } | null {
  if (fallbackMode.value && fallbackRef.value) {
    return { start: fallbackRef.value.selectionStart, end: fallbackRef.value.selectionEnd }
  }
  if (!editorView) return null
  const sel = editorView.state.selection.main
  return { start: sel.from, end: sel.to }
}

function insertAtCursor(text: string) {
  if (fallbackMode.value && fallbackRef.value) {
    const el = fallbackRef.value
    const start = el.selectionStart
    const end = el.selectionEnd
    const val = el.value
    el.value = val.slice(0, start) + text + val.slice(end)
    el.setSelectionRange(start + text.length, start + text.length)
    emit('update:modelValue', el.value)
    el.focus()
    return
  }
  if (!editorView) return
  const sel = editorView.state.selection.main
  editorView.dispatch({
    changes: { from: sel.from, to: sel.to, insert: text },
    selection: { anchor: sel.from + text.length },
  })
  editorView.focus()
}

defineExpose({ focus, getSelectionRange, insertAtCursor })
</script>

<style scoped>
.cm-editor-wrapper {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.cm-editor-wrapper :deep(.cm-editor) {
  height: 100%;
}

.cm-editor-wrapper :deep(.cm-scroller) {
  overflow: auto;
  min-height: 120px;
}

.cf-code-editor {
  width: 100%;
  background: var(--color-code-bg, #1e293b);
  color: var(--color-code-text, #e2e8f0);
  font-family: 'JetBrains Mono', 'Fira Code', Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 10px;
  border: 1px solid var(--color-border, #334155);
  border-radius: 8px;
  resize: vertical;
  outline: none;
}
</style>
