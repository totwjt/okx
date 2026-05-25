import { createRouter, createWebHistory } from 'vue-router';
import RuntimeView from '../views/RuntimeView.vue';
import BacktestsView from '../views/BacktestsView.vue';
import StrategiesView from '../views/StrategiesView.vue';
import LifecycleView from '../views/LifecycleView.vue';
import JobsView from '../views/JobsView.vue';
import PaperView from '../views/PaperView.vue';
import RiskView from '../views/RiskView.vue';
import FactorsView from '../views/FactorsView.vue';
import PlaceholderView from '../views/PlaceholderView.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/strategies' },
    {
      path: '/strategies',
      name: 'strategies',
      component: StrategiesView,
      meta: { title: '策略管理', section: '策略注册表' },
    },
    {
      path: '/lifecycle',
      name: 'lifecycle',
      component: LifecycleView,
      meta: { title: '生命周期工作台', section: '策略全流程' },
    },
    {
      path: '/backtests',
      name: 'backtests',
      component: BacktestsView,
      meta: { title: '回测验证', section: '验证闸门' },
    },
    {
      path: '/runtime',
      name: 'runtime',
      component: RuntimeView,
      meta: { title: '运行系统', section: '运行产物' },
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: JobsView,
      meta: { title: '任务系统', section: '任务队列' },
    },
    {
      path: '/paper',
      name: 'paper',
      component: PaperView,
      meta: { title: '模拟盘', section: '模拟运行' },
    },
    {
      path: '/risk',
      name: 'risk',
      component: RiskView,
      meta: { title: '风控看板', section: '风险控制' },
    },
    {
      path: '/factors',
      name: 'factors',
      component: FactorsView,
      meta: { title: '因子数据', section: '数据健康' },
    },
    {
      path: '/settings',
      name: 'settings',
      component: PlaceholderView,
      meta: { title: '系统配置', section: '配置中心' },
    },
  ],
});
