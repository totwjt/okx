<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { fetchSystemCheck, type SystemCheck } from '../api/system';
import { fetchStrategies, type StrategySummary } from '../api/strategies';
import {
  fetchRuntimeArtifacts,
  materializeRuntime,
  type RuntimeArtifact,
} from '../api/runtime';
import type { WebJob } from '../api/jobs';
import StatusTag from '../components/StatusTag.vue';
import { confirmAction } from '../services/confirm';
import { realtimeClient, type RealtimeStatus, type TopicMessage } from '../services/realtime';

const loading = ref(false);
const materializing = ref(false);
const error = ref('');
const systemCheck = ref<SystemCheck | null>(null);
const strategies = ref<StrategySummary[]>([]);
const selectedStrategy = ref('');
const artifacts = ref<RuntimeArtifact[]>([]);
const pendingJobId = ref<number | null>(null);
const realtimeStatus = ref<RealtimeStatus>('closed');
const unsubs: Array<() => void> = [];

async function loadRuntimeData() {
  loading.value = true;
  error.value = '';
  try {
    const [check, strategyRows, artifactRows] = await Promise.all([
      fetchSystemCheck(),
      fetchStrategies(),
      fetchRuntimeArtifacts(50),
    ]);
    systemCheck.value = check;
    strategies.value = strategyRows;
    artifacts.value = artifactRows;
    if (!selectedStrategy.value && strategyRows.length > 0) {
      selectedStrategy.value = strategyRows[0].slug;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '运行数据加载失败';
  } finally {
    loading.value = false;
  }
}

async function runMaterialize() {
  if (!selectedStrategy.value) {
    return;
  }
  const confirmed = await confirmAction({
    title: '生成运行产物',
    content: `将为 ${selectedStrategy.value} 生成 Freqtrade 运行策略文件和参数文件。完成后列表会通过实时通道自动刷新。`,
    okText: '生成',
  });
  if (!confirmed) {
    return;
  }
  materializing.value = true;
  error.value = '';
  try {
    const job = await materializeRuntime(selectedStrategy.value);
    pendingJobId.value = job.id;
    if (job.status === 'failed') {
      throw new Error(job.error_summary ?? '运行产物生成失败');
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '运行产物生成失败';
    materializing.value = false;
    pendingJobId.value = null;
  }
}

async function refreshRuntimeArtifacts() {
  try {
    artifacts.value = await fetchRuntimeArtifacts(50);
    systemCheck.value = await fetchSystemCheck();
  } catch (err) {
    error.value = err instanceof Error ? err.message : '运行产物刷新失败';
  }
}

function handleRuntimeTopic(message: TopicMessage<{ items?: RuntimeArtifact[] }>) {
  if (message.event !== 'changed') {
    return;
  }
  if (Array.isArray(message.payload.items)) {
    artifacts.value = message.payload.items;
  } else {
    void refreshRuntimeArtifacts();
  }
}

function handleJobsTopic(message: TopicMessage<{ items?: WebJob[] }>) {
  if (message.event !== 'changed' || pendingJobId.value === null) {
    return;
  }
  const job = message.payload.items?.find((item) => item.id === pendingJobId.value);
  if (!job) {
    return;
  }
  if (job.status === 'success') {
    materializing.value = false;
    pendingJobId.value = null;
    void refreshRuntimeArtifacts();
  }
  if (job.status === 'failed') {
    materializing.value = false;
    pendingJobId.value = null;
    error.value = job.error_summary ?? '运行产物生成失败';
  }
}

function shortHash(value: string): string {
  return value.slice(0, 12);
}

function fileName(value: string): string {
  return value.split('/').pop() ?? value;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function checkNameText(name: string | number): string {
  const labels: Record<string, string> = {
    postgres: 'PostgreSQL 数据库',
    registry: '策略注册表',
    runtime_dir: '运行目录',
    docker: 'Docker',
    freqtrade: 'Freqtrade 容器',
    freqtrade_api: 'Freqtrade API',
  };
  return labels[String(name)] ?? String(name);
}

function artifactTypeText(type: string): string {
  const labels: Record<string, string> = {
    strategy_py: '策略代码',
    params_json: '参数文件',
    strategy_json: '策略参数',
    freqtrade_strategy_py: '策略代码',
    freqtrade_params_json: '参数文件',
  };
  return labels[type] ?? type;
}

onMounted(() => {
  void loadRuntimeData();
  unsubs.push(
    realtimeClient.onStatus((status) => {
      realtimeStatus.value = status;
    }),
    realtimeClient.subscribe('runtime.artifacts', handleRuntimeTopic as (message: TopicMessage) => void),
    realtimeClient.subscribe('jobs', handleJobsTopic as (message: TopicMessage) => void),
  );
});

onBeforeUnmount(() => {
  unsubs.splice(0).forEach((unsubscribe) => unsubscribe());
});
</script>

<template>
  <section class="page-grid">
    <div class="panel panel-wide">
      <div class="panel-header">
        <span>生成运行产物</span>
        <button
          class="icon-button"
          type="button"
          :disabled="materializing || !selectedStrategy"
          @click="runMaterialize"
        >
          {{ materializing ? '生成中' : '生成' }}
        </button>
      </div>

      <div class="runtime-action-row">
        <label class="field-label">
          <span>策略</span>
          <select v-model="selectedStrategy" class="select-input">
            <option v-for="strategy in strategies" :key="strategy.slug" :value="strategy.slug">
              {{ strategy.slug }} / {{ strategy.active_profile ?? '当前生效' }}
            </option>
          </select>
        </label>
        <div class="runtime-note">
          操作会写入运行策略目录；实时通道 {{ realtimeStatus === 'open' ? '已连接' : '连接中' }}，完成后自动刷新。
        </div>
      </div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>运行产物</span>
        <StatusTag>{{ artifacts.length }}</StatusTag>
      </div>
      <div class="table-wrap">
        <table class="dense-table artifact-table">
          <thead>
            <tr>
              <th>策略</th>
              <th>参数档案</th>
              <th>类型</th>
              <th>文件</th>
              <th>哈希</th>
              <th>生成时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="artifact in artifacts" :key="artifact.id">
              <td>{{ artifact.strategy_slug }}</td>
              <td>{{ artifact.profile_name }}</td>
              <td>{{ artifactTypeText(artifact.artifact_type) }}</td>
              <td class="path-cell" :title="artifact.artifact_path">
                {{ fileName(artifact.artifact_path) }}
              </td>
              <td class="numeric" :title="artifact.artifact_hash">
                {{ shortHash(artifact.artifact_hash) }}
              </td>
              <td>{{ formatDate(artifact.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>系统检查</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadRuntimeData">
          刷新
        </button>
      </div>

      <div v-if="error" class="error-line">{{ error }}</div>

      <div v-if="systemCheck" class="check-grid">
        <div v-for="(check, name) in systemCheck.checks" :key="name" class="check-tile">
          <div class="check-title">
            <span>{{ checkNameText(name) }}</span>
            <StatusTag :tone="check.ok ? 'success' : 'warning'">
              {{ check.ok ? '正常' : '警告' }}
            </StatusTag>
          </div>
          <pre>{{ check }}</pre>
        </div>
      </div>

      <div v-else class="placeholder-body">
        <span>{{ loading ? '加载中' : '暂无数据' }}</span>
      </div>
    </div>
  </section>
</template>
