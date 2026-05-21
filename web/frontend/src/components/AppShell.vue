<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import {
  AlertOutlined,
  ApiOutlined,
  BarChartOutlined,
  ControlOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FundOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue';

const route = useRoute();

const navItems = [
  { path: '/strategies', label: '策略', icon: DatabaseOutlined },
  { path: '/backtests', label: '回测', icon: BarChartOutlined },
  { path: '/runtime', label: '运行', icon: ApiOutlined },
  { path: '/paper', label: '模拟', icon: FundOutlined },
  { path: '/risk', label: '风控', icon: AlertOutlined },
  { path: '/factors', label: '因子', icon: ExperimentOutlined },
  { path: '/settings', label: '设置', icon: SettingOutlined },
];

const title = computed(() => String(route.meta.title ?? 'AI-OuYi'));
const section = computed(() => String(route.meta.section ?? 'System'));
</script>

<template>
  <div class="shell">
    <aside class="sidebar" aria-label="主导航">
      <div class="brand">
        <ControlOutlined class="brand-icon" />
        <div>
          <div class="brand-name">AI-OuYi</div>
          <div class="brand-sub">Web Console</div>
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
        <div class="topbar-actions">
          <span class="status-dot"></span>
          <span>Dark</span>
        </div>
      </header>

      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

