<template>
  <div class="min-h-screen bg-slate-50 font-sans text-slate-900 antialiased">
    <router-view />
    <router-link
      to="/settings"
      class="fixed bottom-6 right-6 w-10 h-10 flex items-center justify-center bg-white border border-slate-200 rounded-full shadow-md hover:bg-slate-50 text-slate-500 hover:text-slate-700 transition-colors"
      title="AI 设置"
    >⚙</router-link>
  </div>
</template>
