<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import StatusTag from '../components/StatusTag.vue';

const route = useRoute();
const title = computed(() => String(route.meta.title ?? '模块'));
</script>

<template>
  <section class="page-grid">
    <div class="panel">
      <div class="panel-header">
        <span>{{ title }}</span>
        <StatusTag>TASK 待接入</StatusTag>
      </div>
      <div class="placeholder-body">
        <div class="metric-row">
          <span>数据源</span>
          <strong>PostgreSQL Registry</strong>
        </div>
        <div class="metric-row">
          <span>执行层</span>
          <strong>Freqtrade Runtime</strong>
        </div>
        <div class="metric-row">
          <span>模式</span>
          <strong>只读优先</strong>
        </div>
      </div>
    </div>
  </section>
</template>
