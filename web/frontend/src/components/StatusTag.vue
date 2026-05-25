<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    tone?: 'default' | 'success' | 'processing' | 'warning' | 'error';
  }>(),
  {
    tone: 'default',
  },
);

const color = computed(() => {
  if (props.tone === 'success') return 'success';
  if (props.tone === 'processing') return 'processing';
  if (props.tone === 'warning') return 'warning';
  if (props.tone === 'error') return 'error';
  return 'default';
});
</script>

<template>
  <a-tag class="status-tag" :color="color">
    <slot />
  </a-tag>
</template>
