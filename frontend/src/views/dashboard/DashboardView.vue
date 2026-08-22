<template>
  <div class="page-container">
    <!-- KPI 卡片 -->
    <el-row :gutter="16">
      <el-col v-for="card in kpiCards" :key="card.label" :span="4">
        <el-card shadow="hover" class="kpi-card" @click="gotoList(card.key)">
          <div class="kpi-icon" :style="{ background: card.bg }">
            <el-icon :size="22" color="#fff"><component :is="card.icon" /></el-icon>
          </div>
          <div class="kpi-body">
            <div class="kpi-value">{{ card.value ?? '-' }}</div>
            <div class="kpi-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="16" class="mt16">
      <el-col :span="16">
        <el-card>
          <div class="card-title">区域分布（Top 省份商机量）</div>
          <EChart :option="regionOption" height="320px" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="card-title">评分分布</div>
          <EChart :option="scoreOption" height="320px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt16">
      <el-col :span="16">
        <el-card>
          <div class="card-title flex-between">
            <span>月度商机趋势</span>
            <el-radio-group v-model="trendType" size="small" @change="loadTrends">
              <el-radio-button value="monthly">按月</el-radio-button>
              <el-radio-button value="region_hot">区域热度</el-radio-button>
              <el-radio-button value="product_demand">产品需求</el-radio-button>
            </el-radio-group>
          </div>
          <EChart :option="trendOption" height="320px" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <div class="card-title">跟进状态漏斗</div>
          <EChart :option="funnelOption" height="320px" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import EChart from '@/components/EChart.vue'
import { getOverview, getTrends } from '@/api/dashboard'

const router = useRouter()
const overview = ref({})
const trendType = ref('monthly')
const trendData = ref([])

const STATUS_NAMES = {
  new: '新建',
  following: '跟进中',
  bid: '已投标',
  won: '已中标',
  lost: '已丢标',
  closed: '已关闭',
}

const kpiCards = computed(() => [
  { label: '商机总量', key: 'all', value: overview.value.total_opportunities, icon: 'DataBoard', bg: '#1677ff' },
  { label: '今日新增', key: 'today', value: overview.value.today_new, icon: 'TrendCharts', bg: '#52c41a' },
  { label: '高评分商机', key: 'high', value: overview.value.high_level_count, icon: 'Star', bg: '#f56c6c' },
  { label: '跟进中', key: 'following', value: overview.value.following_count, icon: 'Postcard', bg: '#fa8c16' },
  { label: '已中标', key: 'won', value: overview.value.won_count, icon: 'Trophy', bg: '#722ed1' },
])

const regionOption = computed(() => {
  const list = overview.value.region_distribution || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: list.map((i) => i.province),
      axisLabel: { rotate: list.length > 8 ? 30 : 0 },
    },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: list.map((i) => i.count),
        barWidth: '55%',
        itemStyle: { borderRadius: [4, 4, 0, 0], color: '#1677ff' },
      },
    ],
  }
})

const scoreOption = computed(() => {
  const list = overview.value.score_distribution || []
  const colors = ['#f56c6c', '#fa8c16', '#e6a23c', '#67c23a']
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: list.map((i, idx) => ({ name: i.range, value: i.count, itemStyle: { color: colors[idx % colors.length] } })),
      },
    ],
  }
})

const trendOption = computed(() => {
  const items = trendData.value || []
  if (trendType.value === 'product_demand') {
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 60, right: 20, top: 20, bottom: 60 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: items.map((i) => i.category) },
      series: [{ type: 'bar', data: items.map((i) => i.count), itemStyle: { color: '#52c41a', borderRadius: [0, 4, 4, 0] } }],
    }
  }
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: items.map((i) => i.month || i.region) },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'line',
        smooth: true,
        data: items.map((i) => i.count),
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: '#1677ff' },
      },
    ],
  }
})

const funnelOption = computed(() => {
  const list = overview.value.status_funnel || []
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [
      {
        type: 'funnel',
        left: '10%',
        width: '80%',
        top: 10,
        bottom: 10,
        sort: 'descending',
        gap: 4,
        label: { formatter: '{b} {c}' },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        data: list.map((i) => ({ name: STATUS_NAMES[i.status] || i.status, value: i.count })),
      },
    ],
  }
})

const loadOverview = async () => {
  const res = await getOverview()
  overview.value = res.data || {}
}

const loadTrends = async () => {
  const res = await getTrends({ type: trendType.value })
  trendData.value = res.data?.items || []
}

const gotoList = (key) => {
  const query = {}
  if (key === 'high') query.level = 'high'
  if (key === 'following') query.status = 'following'
  if (key === 'won') query.status = 'won'
  router.push({ path: '/opportunities', query })
}

onMounted(() => {
  loadOverview().catch(() => ElMessage.warning('驾驶舱数据加载失败'))
  loadTrends()
})
</script>

<style scoped>
.mt16 {
  margin-top: 16px;
}
.kpi-card {
  cursor: pointer;
  transition: transform 0.2s;
}
.kpi-card:hover {
  transform: translateY(-2px);
}
.kpi-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 12px;
}
.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: #1f2d3d;
}
.kpi-label {
  font-size: 12px;
  color: #909399;
}
</style>
