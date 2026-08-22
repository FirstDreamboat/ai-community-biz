<template>
  <div ref="el" class="echart" :style="{ height }"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, default: () => ({}) },
  height: { type: String, default: '300px' },
  onClick: { type: Function, default: null },
})

const el = ref()
let chart = null

const render = () => {
  if (!chart) return
  chart.setOption(props.option, true)
}

const resize = () => chart && chart.resize()

onMounted(async () => {
  await nextTick()
  chart = echarts.init(el.value)
  render()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart && chart.dispose()
  chart = null
})

watch(() => props.option, render, { deep: true })
</script>

<style scoped>
.echart {
  width: 100%;
}
</style>
