import { createRouter, createWebHistory } from 'vue-router';
import RuntimeView from '../views/RuntimeView.vue';
import PlaceholderView from '../views/PlaceholderView.vue';
import StrategiesView from '../views/StrategiesView.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/strategies' },
    {
      path: '/strategies',
      name: 'strategies',
      component: StrategiesView,
      meta: { title: '策略管理', section: 'Registry' },
    },
    {
      path: '/backtests',
      name: 'backtests',
      component: PlaceholderView,
      meta: { title: '回测验证', section: 'Validation' },
    },
    {
      path: '/runtime',
      name: 'runtime',
      component: RuntimeView,
      meta: { title: '运行系统', section: 'Runtime' },
    },
    {
      path: '/paper',
      name: 'paper',
      component: PlaceholderView,
      meta: { title: '模拟盘', section: 'Dry-run' },
    },
    {
      path: '/risk',
      name: 'risk',
      component: PlaceholderView,
      meta: { title: '风控看板', section: 'Risk' },
    },
    {
      path: '/factors',
      name: 'factors',
      component: PlaceholderView,
      meta: { title: '因子数据', section: 'Factors' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: PlaceholderView,
      meta: { title: '系统配置', section: 'Settings' },
    },
  ],
});
