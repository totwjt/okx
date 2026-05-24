<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { fetchSystemCheck, type SystemCheck } from '../api/system';
import { fetchStrategies, type StrategySummary } from '../api/strategies';
import {
  fetchRuntimeArtifacts,
  materializeRuntime,
  type RuntimeArtifact,
} from '../api/runtime';

const loading = ref(false);
const materializing = ref(false);
const error = ref('');
const systemCheck = ref<SystemCheck | null>(null);
const strategies = ref<StrategySummary[]>([]);
const selectedStrategy = ref('');
const artifacts = ref<RuntimeArtifact[]>([]);

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
  const confirmed = window.confirm(`为 ${selectedStrategy.value} 生成运行产物？`);
  if (!confirmed) {
    return;
  }
  materializing.value = true;
  error.value = '';
  try {
    await materializeRuntime(selectedStrategy.value);
    artifacts.value = await fetchRuntimeArtifacts(50);
    systemCheck.value = await fetchSystemCheck();
  } catch (err) {
    error.value = err instanceof Error ? err.message : '运行产物生成失败';
  } finally {
    materializing.value = false;
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
  };
  return labels[type] ?? type;
}

onMounted(loadRuntimeData);
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
          生成
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
        <div class="runtime-note">操作会写入运行策略目录，并刷新产物元数据列表。</div>
      </div>
    </div>

    <div class="panel panel-wide">
      <div class="panel-header">
        <span>运行产物</span>
        <span class="badge badge-muted">{{ artifacts.length }}</span>
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
            <span :class="['badge', check.ok ? 'badge-ok' : 'badge-warn']">
              {{ check.ok ? '正常' : '警告' }}
            </span>
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
