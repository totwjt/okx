<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import {
  fetchStrategies,
  fetchStrategy,
  fetchStrategyProfiles,
  type StrategyDetail,
  type StrategyProfile,
  type StrategySummary,
} from '../api/strategies';

const loading = ref(false);
const detailLoading = ref(false);
const error = ref('');
const strategies = ref<StrategySummary[]>([]);
const selectedSlug = ref('');
const selectedStrategy = ref<StrategyDetail | null>(null);
const profiles = ref<StrategyProfile[]>([]);

const selectedSummary = computed(() =>
  strategies.value.find((strategy) => strategy.slug === selectedSlug.value),
);
const activeProfiles = computed(() => profiles.value.filter((profile) => profile.is_active));
const visibleSpecKeys = computed(() => {
  if (!selectedStrategy.value) {
    return [];
  }
  const hiddenKeys = new Set(['entry_conditions', 'exit_conditions', 'derived_indicators']);
  return Object.keys(selectedStrategy.value.spec).filter((key) => !hiddenKeys.has(key)).sort();
});

function statusClass(status: string): string {
  const normalized = status.toLowerCase();
  if (['validated', 'paper_active'].includes(normalized)) {
    return 'badge-ok';
  }
  if (['candidate', 'live_candidate'].includes(normalized)) {
    return 'badge-info';
  }
  if (normalized === 'live_active') {
    return 'badge-danger';
  }
  if (normalized === 'archived') {
    return 'badge-muted';
  }
  return 'badge-warn';
}

function statusText(status: string): string {
  const labels: Record<string, string> = {
    draft: '草稿',
    generated: '已生成',
    backtested: '已回测',
    validated: '已验证',
    paper_active: '模拟盘生效',
    live_candidate: '实盘候选',
    live_active: '实盘生效',
    archived: '已归档',
    candidate: '候选',
  };
  return labels[status.toLowerCase()] ?? status;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function countKeys(value: Record<string, unknown>): number {
  return Object.keys(value ?? {}).length;
}

function valueTypeText(value: unknown): string {
  const rawType = typeof value;
  const labels: Record<string, string> = {
    object: '对象',
    string: '文本',
    number: '数字',
    boolean: '布尔',
    undefined: '未定义',
  };
  return labels[rawType] ?? rawType;
}

async function selectStrategy(slug: string) {
  selectedSlug.value = slug;
  detailLoading.value = true;
  error.value = '';
  try {
    const [detail, profileRows] = await Promise.all([
      fetchStrategy(slug),
      fetchStrategyProfiles(slug),
    ]);
    selectedStrategy.value = detail;
    profiles.value = profileRows;
  } catch (err) {
    error.value = err instanceof Error ? err.message : '策略详情加载失败';
  } finally {
    detailLoading.value = false;
  }
}

async function loadStrategies() {
  loading.value = true;
  error.value = '';
  try {
    strategies.value = await fetchStrategies();
    if (strategies.value.length > 0) {
      await selectStrategy(strategies.value[0].slug);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '策略列表加载失败';
  } finally {
    loading.value = false;
  }
}

onMounted(loadStrategies);
</script>

<template>
  <section class="strategy-layout">
    <div class="panel strategy-list-panel">
      <div class="panel-header">
        <span>策略注册表</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadStrategies">
          刷新
        </button>
      </div>

      <div v-if="error" class="error-line">{{ error }}</div>

      <div class="strategy-list">
        <button
          v-for="strategy in strategies"
          :key="strategy.slug"
          type="button"
          :class="['strategy-row', strategy.slug === selectedSlug ? 'strategy-row-active' : '']"
          @click="selectStrategy(strategy.slug)"
        >
          <span class="strategy-row-main">
            <strong>{{ strategy.name }}</strong>
            <small>{{ strategy.slug }}</small>
          </span>
          <span class="strategy-row-meta">
            <span :class="['badge', statusClass(strategy.status)]">{{ statusText(strategy.status) }}</span>
            <span class="numeric">{{ strategy.profile_count }}</span>
          </span>
        </button>
      </div>
    </div>

    <div class="strategy-main">
      <div class="panel">
        <div class="panel-header">
          <span>{{ selectedSummary?.name ?? '策略详情' }}</span>
          <span v-if="selectedSummary" :class="['badge', statusClass(selectedSummary.status)]">
            {{ statusText(selectedSummary.status) }}
          </span>
        </div>

        <div v-if="detailLoading" class="placeholder-body">加载中</div>
        <div v-else-if="selectedStrategy" class="detail-grid">
          <div class="detail-cell">
            <span>策略标识</span>
            <strong>{{ selectedStrategy.slug }}</strong>
          </div>
          <div class="detail-cell">
            <span>当前参数档案</span>
            <strong>{{ selectedStrategy.active_profile ?? '-' }}</strong>
          </div>
          <div class="detail-cell">
            <span>参数档案数</span>
            <strong>{{ selectedStrategy.profile_count }}</strong>
          </div>
          <div class="detail-cell">
            <span>更新时间</span>
            <strong>{{ formatDate(selectedStrategy.updated_at) }}</strong>
          </div>
          <div class="detail-cell detail-cell-wide">
            <span>说明</span>
            <strong>{{ selectedStrategy.description ?? '-' }}</strong>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <span>参数档案状态</span>
          <span class="badge badge-muted">{{ activeProfiles.length }} 个生效</span>
        </div>
        <div class="table-wrap">
          <table class="dense-table">
            <thead>
              <tr>
                <th>参数档案</th>
                <th>状态</th>
                <th>生效</th>
                <th>来源</th>
                <th>覆盖参数</th>
                <th>验证信息</th>
                <th>更新时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="profile in profiles" :key="profile.profile_name">
                <td class="name-cell">{{ profile.profile_name }}</td>
                <td>
                  <span :class="['badge', statusClass(profile.status)]">{{ statusText(profile.status) }}</span>
                </td>
                <td>{{ profile.is_active ? '是' : '-' }}</td>
                <td>{{ profile.source ?? '-' }}</td>
                <td class="numeric">{{ countKeys(profile.overrides) }}</td>
                <td class="numeric">{{ countKeys(profile.validation) }}</td>
                <td>{{ formatDate(profile.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <span>策略定义摘要</span>
          <span class="badge badge-muted">不展示生成代码</span>
        </div>
        <div class="spec-summary">
          <div v-for="key in visibleSpecKeys" :key="key" class="spec-chip">
            <span>{{ key }}</span>
            <strong>{{ valueTypeText(selectedStrategy?.spec[key]) }}</strong>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
