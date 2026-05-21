<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { fetchSystemCheck, type SystemCheck } from '../api/system';

const loading = ref(false);
const error = ref('');
const systemCheck = ref<SystemCheck | null>(null);

async function loadSystemCheck() {
  loading.value = true;
  error.value = '';
  try {
    systemCheck.value = await fetchSystemCheck();
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'system check failed';
  } finally {
    loading.value = false;
  }
}

onMounted(loadSystemCheck);
</script>

<template>
  <section class="page-grid">
    <div class="panel panel-wide">
      <div class="panel-header">
        <span>系统检查</span>
        <button class="icon-button" type="button" :disabled="loading" @click="loadSystemCheck">
          刷新
        </button>
      </div>

      <div v-if="error" class="error-line">{{ error }}</div>

      <div v-if="systemCheck" class="check-grid">
        <div v-for="(check, name) in systemCheck.checks" :key="name" class="check-tile">
          <div class="check-title">
            <span>{{ name }}</span>
            <span :class="['badge', check.ok ? 'badge-ok' : 'badge-warn']">
              {{ check.ok ? 'OK' : 'WARN' }}
            </span>
          </div>
          <pre>{{ check }}</pre>
        </div>
      </div>

      <div v-else class="placeholder-body">
        <span>{{ loading ? 'loading' : 'no data' }}</span>
      </div>
    </div>
  </section>
</template>

