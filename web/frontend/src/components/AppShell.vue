<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import {
  AlertOutlined,
  ApiOutlined,
  BarChartOutlined,
  ControlOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FundOutlined,
  PartitionOutlined,
  ScheduleOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue';

const route = useRoute();

const navItems = [
  { path: '/strategies', label: '策略', icon: DatabaseOutlined },
  { path: '/lifecycle', label: '生命周期', icon: PartitionOutlined },
  { path: '/backtests', label: '回测', icon: BarChartOutlined },
  { path: '/runtime', label: '运行', icon: ApiOutlined },
  { path: '/jobs', label: '任务', icon: ScheduleOutlined },
  { path: '/paper', label: '模拟', icon: FundOutlined },
  { path: '/risk', label: '风控', icon: AlertOutlined },
  { path: '/factors', label: '因子', icon: ExperimentOutlined },
  { path: '/settings', label: '设置', icon: SettingOutlined },
];

const title = computed(() => String(route.meta.title ?? 'AI-OuYi'));
const section = computed(() => String(route.meta.section ?? '系统'));
const theme = ref<'dark' | 'light'>('dark');
const themeLabel = computed(() => (theme.value === 'dark' ? '深色模式' : '浅色模式'));

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark';
}

watch(theme, (value) => {
  document.documentElement.dataset.theme = value;
  document.documentElement.style.colorScheme = value;
  localStorage.setItem('ai-ouyi-theme', value);
});

onMounted(() => {
  const savedTheme = localStorage.getItem('ai-ouyi-theme');
  theme.value = savedTheme === 'light' ? 'light' : 'dark';
});
</script>

<template>
  <div class="shell">
    <aside class="sidebar" aria-label="主导航">
      <div class="brand">
        <ControlOutlined class="brand-icon" />
        <div>
          <div class="brand-name">AI-OuYi</div>
          <div class="brand-sub">管理控制台</div>
        </div>
      </div>

      <nav class="nav-list">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="nav-item-active"
        >
          <component :is="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>

    <div class="workspace">
      <header class="topbar">
        <div class="topbar-title">
          <span class="section-label">{{ section }}</span>
          <h1>{{ title }}</h1>
        </div>
        <button class="topbar-actions theme-toggle" type="button" @click="toggleTheme">
          <span class="status-dot"></span>
          <span>{{ themeLabel }}</span>
        </button>
      </header>

      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>
