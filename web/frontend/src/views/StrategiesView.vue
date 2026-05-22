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
    error.value = err instanceof Error ? err.message : 'strategy load failed';
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
    error.value = err instanceof Error ? err.message : 'strategy list failed';
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
            <span :class="['badge', statusClass(strategy.status)]">{{ strategy.status }}</span>
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
            {{ selectedSummary.status }}
          </span>
        </div>

        <div v-if="detailLoading" class="placeholder-body">loading</div>
        <div v-else-if="selectedStrategy" class="detail-grid">
          <div class="detail-cell">
            <span>slug</span>
            <strong>{{ selectedStrategy.slug }}</strong>
          </div>
          <div class="detail-cell">
            <span>active profile</span>
            <strong>{{ selectedStrategy.active_profile ?? '-' }}</strong>
          </div>
          <div class="detail-cell">
            <span>profiles</span>
            <strong>{{ selectedStrategy.profile_count }}</strong>
          </div>
          <div class="detail-cell">
            <span>updated</span>
            <strong>{{ formatDate(selectedStrategy.updated_at) }}</strong>
          </div>
          <div class="detail-cell detail-cell-wide">
            <span>description</span>
            <strong>{{ selectedStrategy.description ?? '-' }}</strong>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <span>Profile 状态</span>
          <span class="badge badge-muted">{{ activeProfiles.length }} active</span>
        </div>
        <div class="table-wrap">
          <table class="dense-table">
            <thead>
              <tr>
                <th>profile</th>
                <th>status</th>
                <th>active</th>
                <th>source</th>
                <th>overrides</th>
                <th>validation</th>
                <th>updated</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="profile in profiles" :key="profile.profile_name">
                <td class="name-cell">{{ profile.profile_name }}</td>
                <td>
                  <span :class="['badge', statusClass(profile.status)]">{{ profile.status }}</span>
                </td>
                <td>{{ profile.is_active ? 'yes' : '-' }}</td>
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
          <span>Spec 摘要</span>
          <span class="badge badge-muted">no generated code</span>
        </div>
        <div class="spec-summary">
          <div v-for="key in visibleSpecKeys" :key="key" class="spec-chip">
            <span>{{ key }}</span>
            <strong>{{ typeof selectedStrategy?.spec[key] }}</strong>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

