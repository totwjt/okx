<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { fetchJobs, type WebJob } from '../api/jobs';
import StatusTag from '../components/StatusTag.vue';

const loading = ref(false);
const error = ref('');
const jobs = ref<WebJob[]>([]);

async function loadJobs() {
  loading.value = true;
  error.value = '';
  try {
    jobs.value = await fetchJobs(100);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '任务列表加载失败';
  } finally {
    loading.value = false;
  }
}

function statusTone(status: WebJob['status']): 'default' | 'success' | 'processing' | 'error' {
  if (status === 'success') return 'success';
  if (status === 'failed') return 'error';
  if (status === 'running') return 'processing';
  return 'default';
}

function statusText(status: WebJob['status']): string {
  const labels: Record<WebJob['status'], string> = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败',
  };
  return labels[status] ?? status;
}

function jobTypeText(type: string): string {
  const labels: Record<string, string> = {
    materialize: '生成运行产物',
    backtest: '回测',
    validation: '验证闸门',
  };
  return labels[type] ?? type;
}

function formatDate(value: string | null): string {
  if (!value) return '-';
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function compactJson(value: unknown): string {
  if (value == null) return '-';
  const text = JSON.stringify(value);
  return text.length > 92 ? `${text.slice(0, 92)}...` : text;
}

onMounted(loadJobs);
</script>

<template>
  <section class="page-grid">
    <div class="panel panel-wide">
      <div class="panel-header">
        <span>任务队列</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadJobs">
          刷新
        </button>
      </div>

      <div v-if="error" class="error-line">{{ error }}</div>

      <div class="table-wrap">
        <table class="dense-table jobs-table">
          <thead>
            <tr>
              <th>编号</th>
              <th>类型</th>
              <th>状态</th>
              <th>参数</th>
              <th>错误</th>
              <th>创建时间</th>
              <th>完成时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in jobs" :key="job.id">
              <td class="numeric">#{{ job.id }}</td>
              <td>{{ jobTypeText(job.job_type) }}</td>
              <td>
                <StatusTag :tone="statusTone(job.status)">{{ statusText(job.status) }}</StatusTag>
              </td>
              <td class="json-cell" :title="compactJson(job.payload)">
                {{ compactJson(job.payload) }}
              </td>
              <td class="error-cell" :title="job.error_summary ?? ''">
                {{ job.error_summary ?? '-' }}
              </td>
              <td>{{ formatDate(job.created_at) }}</td>
              <td>{{ formatDate(job.finished_at) }}</td>
            </tr>
            <tr v-if="!loading && jobs.length === 0">
              <td colspan="7">暂无任务</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
