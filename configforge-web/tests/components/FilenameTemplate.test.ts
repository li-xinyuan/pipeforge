import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

/**
 * FilenameTemplate 测试 — 文件名模板命名 widget（限制①第二阶段迁移）。
 *
 * 验证 tag 插入、文本拼接、tag 删除、清除、扩展名处理。
 * vi.mock naive-ui（NTag/NButton 用简单 stub）。
 */

vi.mock('naive-ui', () => ({
  NTag: {
    template: '<span data-test="n-tag" :data-type="type" :data-closable="closable" @click="$emit(\'click\')"><slot /><span v-if="closable" data-test="n-tag-close" @click.stop="$emit(\'close\')">×</span></span>',
    props: { type: String, closable: Boolean, bordered: Boolean, size: String },
    emits: ['click', 'close'],
  },
  NButton: {
    template: '<button data-test="n-button" @click="$emit(\'click\')"><slot /></button>',
    props: { text: Boolean, size: String, type: String },
    emits: ['click'],
  },
}))

import FilenameTemplate from '../../src/components/common/FilenameTemplate.vue'

function mountWidget(modelValue: string | null, extension = '.csv') {
  return mount(FilenameTemplate, {
    props: { modelValue, extension },
  })
}

describe('FilenameTemplate', () => {
  describe('渲染', () => {
    it('无扩展名时展示完整 modelValue', () => {
      const wrapper = mountWidget('report.csv')
      // NTag closable=false 的部分 + extension label
      const tags = wrapper.findAll('[data-test="n-tag"]')
      // "年月日" 和 "时分秒" 两个可点击 tag + 文本片段 tag
      expect(tags.length).toBeGreaterThanOrEqual(2)
    })

    it('展示扩展名', () => {
      const wrapper = mountWidget('report', '.xlsx')
      expect(wrapper.text()).toContain('.xlsx')
    })
  })

  describe('tag 插入', () => {
    it('点击"年月日"插入 {{date:%Y%m%d}} 标签', async () => {
      const wrapper = mountWidget('report', '.csv')
      // 第一个可点击 tag 是"年月日"
      const tags = wrapper.findAll('[data-test="n-tag"]')
      await tags[0].trigger('click')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      expect(events![0][0]).toBe('report{{date:%Y%m%d}}.csv')
    })

    it('点击"时分秒"插入 {{time:%H%M%S}} 标签', async () => {
      const wrapper = mountWidget('report', '.csv')
      const tags = wrapper.findAll('[data-test="n-tag"]')
      await tags[1].trigger('click')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      expect(events![0][0]).toBe('report{{time:%H%M%S}}.csv')
    })

    it('已有 tag 的文件名继续追加', async () => {
      const wrapper = mountWidget('report{{date:%Y%m%d}}', '.csv')
      const tags = wrapper.findAll('[data-test="n-tag"]')
      // tags[0]=年月日, tags[1]=时分秒, tags[2]=report 文本, tags[3]={{date}} tag(closable)
      await tags[1].trigger('click')
      const events = wrapper.emitted('update:modelValue')
      expect(events![0][0]).toBe('report{{date:%Y%m%d}}{{time:%H%M%S}}.csv')
    })
  })

  describe('清除文件名', () => {
    it('点击清除按钮重置为仅扩展名', async () => {
      const wrapper = mountWidget('report-20260101.csv', '.csv')
      const btn = wrapper.find('[data-test="n-button"]')
      await btn.trigger('click')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      expect(events![0][0]).toBe('.csv')
    })
  })

  describe('tag 删除', () => {
    it('点击 tag 的 close 删除对应片段', async () => {
      const wrapper = mountWidget('report{{date:%Y%m%d}}-suffix', '.csv')
      // filenameParts: [0]='report', [1]='{{date:%Y%m%d}}', [2]='-suffix'
      // close 按钮按顺序对应每个 part，点击第 2 个删除 {{date:%Y%m%d}}
      const closeBtns = wrapper.findAll('[data-test="n-tag-close"]')
      expect(closeBtns.length).toBe(3)
      await closeBtns[1].trigger('click')
      const events = wrapper.emitted('update:modelValue')
      expect(events).toBeTruthy()
      // 删除 {{date:%Y%m%d}} 后剩 report-suffix.csv
      expect(events![0][0]).toBe('report-suffix.csv')
    })

    it('删除第一个片段', async () => {
      const wrapper = mountWidget('report{{date:%Y%m%d}}', '.csv')
      const closeBtns = wrapper.findAll('[data-test="n-tag-close"]')
      await closeBtns[0].trigger('click')
      const events = wrapper.emitted('update:modelValue')
      expect(events![0][0]).toBe('{{date:%Y%m%d}}.csv')
    })
  })

  describe('扩展名处理', () => {
    it('modelValue 不含扩展名时 baseFilename 为原值', () => {
      const wrapper = mountWidget('myfile', '.xlsx')
      // 点击年月日追加
      const tags = wrapper.findAll('[data-test="n-tag"]')
      return tags[0].trigger('click').then(() => {
        const events = wrapper.emitted('update:modelValue')
        expect(events![0][0]).toBe('myfile{{date:%Y%m%d}}.xlsx')
      })
    })

    it('modelValue 含扩展名时剥离后处理', () => {
      const wrapper = mountWidget('myfile.xlsx', '.xlsx')
      const tags = wrapper.findAll('[data-test="n-tag"]')
      return tags[0].trigger('click').then(() => {
        const events = wrapper.emitted('update:modelValue')
        expect(events![0][0]).toBe('myfile{{date:%Y%m%d}}.xlsx')
      })
    })

    it('extension 未提供时按空串处理', () => {
      const wrapper = mount(FilenameTemplate, {
        props: { modelValue: 'myfile' },
      })
      const tags = wrapper.findAll('[data-test="n-tag"]')
      return tags[0].trigger('click').then(() => {
        const events = wrapper.emitted('update:modelValue')
        expect(events![0][0]).toBe('myfile{{date:%Y%m%d}}')
      })
    })
  })

  describe('null modelValue', () => {
    it('modelValue 为 null 时不报错', () => {
      const wrapper = mount(FilenameTemplate, {
        props: { modelValue: null, extension: '.csv' },
      })
      expect(wrapper.find('[data-test="n-button"]').exists()).toBe(false)
    })
  })
})
