<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <div class="card-title flex-between">
            <span>月度商机趋势</span>
            <el-button size="small" @click="loadMonthly">刷新</el-button>
          </div>
          <EChart :option="monthlyOption" height="340px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <div class="card-title">区域热度排行 Top10</div>
          <EChart :option="regionOption" height="340px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt16">
      <el-col :span="24">
        <el-card>
          <div class="card-title flex-between">
            <span>产品需求排行（改造内容标签分布）</span>
            <div>
              <el-button size="small" @click="loadProduct">刷新</el-button>
            </div>
          </div>
          <EChart :option="productOption" height="340px" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import EChart from '@/components/EChart.vue'
import { getTrends } from '@/api/dashboard'

const monthly = ref([])
const regionHot = ref([])
const productDemand = ref([])

const monthlyOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 50, right: 20, top: 30, bottom: 40 },
  xAxis: { type: 'category', data: monthly.value.map((i) => i.month) },
  yAxis: { type: 'value', name: '商机数' },
  series: [
    {
      name: '商机量',
      type: 'line',
      smooth: true,
      data: monthly.value.map((i) => i.count),
      areaStyle: { opacity: 0.15 },
      itemStyle: { color: '#1677ff' },
    },
  ],
}))

const regionOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 60, right: 30, top: 20, bottom: 30 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', inverse: true, data: regionHot.value.map((i) => i.region) },
  series: [
    {
      type: 'bar',
      data: regionHot.value.map((i) => i.count),
      itemStyle: { color: '#52c41a', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right' },
    },
  ],
}))

const productOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [
    {
      type: 'pie',
      radius: ['40%', '68%'],
      center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}: {c}' },
      data: productDemand.value.map((i) => ({ name: i.category, value: i.count })),
    },
  ],
}))

const loadMonthly = async () => {
  const res = await getTrends({ type: 'monthly' })
  monthly.value = res.data?.items || []
}
const loadRegion = async () => {
  const res = await getTrends({ type: 'region_hot' })
  regionHot.value = res.data?.items || []
}
const loadProduct = async () => {
  const res = await getTrends({ type: 'product_demand' })
  productDemand.value = res.data?.items || []
}

onMounted(() => {
  loadMonthly()
  loadRegion()
  loadProduct()
})
</script>

<style scoped>
.mt16 {
  margin-top: 16px;
}
</style>
