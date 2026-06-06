<template>
  <div class="guide">
    <AppNavBar current-route="guide" />

    <main class="guide__content">
      <article class="guide__article">
        <h1>ConfigForge 使用指南</h1>
        <p class="guide__intro">
          ConfigForge 是一个数据流水线配置工具，通过 5 步向导帮助你将数据处理需求转化为可执行的流水线配置，支持 AI 辅助 SQL 生成与列映射。
        </p>

        <section class="guide__section">
          <h2>概述</h2>
          <p>ConfigForge 的核心工作流是：<strong>定义场景 → 上传输入源 → 编写 SQL → 配置输出 → 预览导出</strong>。整个过程在一个流畅的单页向导中完成，右侧 AI 助手可在任意步骤提供帮助。</p>
        </section>

        <section class="guide__section">
          <h2>第一步：场景信息</h2>
          <p>填写流水线的基本信息：</p>
          <ul>
            <li><strong>场景名称</strong>：为你的数据处理流水线起一个描述性名称，例如"销售报表生成"。</li>
            <li><strong>版本号</strong>：流水线的版本标识，默认为 1.0。</li>
            <li><strong>场景描述</strong>：简要描述这个流水线的用途，帮助后续识别和管理。</li>
          </ul>
          <p>完成后点击"下一步"进入下一步。</p>
        </section>

        <section class="guide__section">
          <h2>第二步：输入源</h2>
          <p>添加数据处理流水线的输入数据：</p>
          <ul>
            <li>点击 <strong>+ Excel</strong> 或 <strong>+ CSV</strong> 添加输入源。</li>
            <li>上传数据文件（.xlsx / .xls / .csv 格式，最大 50MB）。</li>
            <li>设置数据表名，后续 SQL 中将以此表名引用数据。</li>
            <li>参数键（param_key）用于在运行时指定文件路径，可留空使用默认值。</li>
          </ul>
          <p>每个输入源会以表的形式加载到 SQLite 引擎中供后续 SQL 查询使用。</p>
        </section>

        <section class="guide__section">
          <h2>第三步：数据处理</h2>
          <p>编写 SQL 查询或 Python 脚本对输入数据进行处理：</p>
          <ul>
            <li><strong>SQL 查询</strong>：在 SQL 编辑器中直接编写查询语句，引用上一步设置的表名。</li>
            <li><strong>Python 脚本</strong>：使用 <code>def process(ctx)</code> 编写自定义数据处理逻辑，支持 API 调用、复杂计算等。</li>
            <li>点击 <strong>AI 生成代码</strong>，用自然语言描述需求，AI 将自动生成代码并填入编辑器。</li>
            <li>设置<strong>输出表名</strong>，查询结果将保存到此表中供输出步骤使用。</li>
            <li>点击 <strong>预览结果</strong> 可实时查看 SQL 执行结果。</li>
          </ul>
          <p>SQL 引擎为 SQLite，支持标准 SQL 语法。Python 脚本通过 ctx.db API 访问数据库。</p>
        </section>

        <section class="guide__section">
          <h2>第四步：输出配置</h2>
          <p>配置输出文件的格式和内容：</p>
          <ul>
            <li>选择输出格式：<strong>Excel</strong> 或 <strong>CSV</strong>。</li>
            <li><strong>Excel 输出</strong>：可上传模板文件定义样式，系统会将数据填充到模板中。</li>
            <li><strong>CSV 输出</strong>：可设置分隔符和编码。</li>
            <li><strong>列映射</strong>：设置源列到目标列的映射关系。点击 <strong>AI 自动列映射</strong> 或 <strong>从代码自动推断列</strong> 可自动完成。</li>
            <li><strong>输入源表</strong>：选择要输出的源表（来自 SQL 处理的结果表）。</li>
            <li><strong>输出目录</strong>和<strong>文件名</strong>：指定输出文件的保存位置和名称。执行下载时文件名中的日期会自动替换为实际执行时间。</li>
          </ul>
        </section>

        <section class="guide__section">
          <h2>第五步：预览与导出</h2>
          <p>查看生成的 YAML 配置并执行导出：</p>
          <ul>
            <li><strong>YAML 预览</strong>：查看将要执行的完整流水线配置。</li>
            <li><strong>复制</strong>：将 YAML 复制到剪贴板。</li>
            <li><strong>下载 YAML</strong>：将 YAML 配置文件下载到本地。</li>
            <li><strong>下载结果文件</strong>：使用当前配置执行流水线并下载输出文件。</li>
            <li><strong>保存配置</strong>：将当前配置保存到服务器，方便后续编辑和复用。首次保存创建新配置，再次保存更新同一配置。</li>
          </ul>
        </section>

        <section class="guide__section">
          <h2>AI 助手</h2>
          <p>右侧 AI 面板可在任意步骤提供帮助：</p>
          <ul>
            <li><strong>AI 分析列</strong>：分析上传文件的列结构。</li>
            <li><strong>AI 生成 SQL</strong>：输入自然语言描述，AI 生成对应 SQL。</li>
            <li><strong>AI 自动列映射</strong>：自动匹配源列和目标列的映射关系。</li>
            <li><strong>生成场景描述</strong>：根据配置信息生成场景描述并自动填入步骤一。</li>
          </ul>
          <p>使用 AI 功能前，请先在 <router-link to="/settings">设置页面</router-link> 配置 API Key。</p>
        </section>

        <section class="guide__section">
          <h2>设置</h2>
          <p>在 <router-link to="/settings">设置页面</router-link> 可配置：</p>
          <ul>
            <li><strong>AI 服务</strong>：选择 OpenAI 兼容的 API，填写 API Key、Base URL 和模型名称。</li>
            <li>支持 OpenAI、Anthropic 等兼容接口。</li>
            <li>API Key 在保存时会加密存储，查询时脱敏返回。</li>
          </ul>
        </section>

        <section class="guide__section">
          <h2>暗色模式与响应式</h2>
          <ul>
            <li><strong>暗色模式</strong>：点击导航栏右侧的 🌙 / ☀️ 按钮切换暗色/亮色主题，偏好会自动保存。</li>
            <li><strong>响应式布局</strong>：支持桌面（≥1024px）、平板（768-1023px）、手机（<768px）三端自适应。</li>
          </ul>
        </section>

        <section class="guide__section">
          <h2>安全说明</h2>
          <ul>
            <li>所有数据处理在本地完成，上传的文件不会发送到外部服务。</li>
            <li>AI 请求通过加密通道发送到你配置的 API 端点。</li>
            <li>上传文件在 24 小时后自动清理。</li>
            <li>API Key 使用 Fernet 加密存储。</li>
          </ul>
        </section>
      </article>
    </main>
  </div>
</template>

<script setup lang="ts">
import AppNavBar from '../components/common/AppNavBar.vue'
</script>

<style scoped>
.guide {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg);
}

.guide__content {
  flex: 1;
  padding: 24px 20px 60px;
  max-width: 780px;
  margin: 0 auto;
  width: 100%;
}

.guide__article h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
}

.guide__intro {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: 32px;
}

.guide__section {
  margin-bottom: 28px;
}

.guide__section h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 2px solid var(--color-primary-border);
}

.guide__section p {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: 8px;
}

.guide__section ul {
  padding-left: 20px;
  margin-bottom: 8px;
}

.guide__section li {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: 4px;
}

.guide__section a {
  color: var(--color-primary);
  text-decoration: none;
}

.guide__section a:hover {
  text-decoration: underline;
}

@media (max-width: 767px) {
  .guide__content {
    padding: 16px 14px 40px;
  }
  .guide__article h1 {
    font-size: 22px;
  }
  .guide__section h2 {
    font-size: 17px;
  }
}
</style>
