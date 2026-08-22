<template>
  <div class="page-container">
    <el-card class="filter-card">
      <el-form :inline="true" :model="query" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="标题/招标方" clearable style="width: 180px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="省份">
          <el-input v-model="query.province" placeholder="如：福建省" clearable style="width: 130px" />
        </el-form-item>
        <el-form-item label="评分">
          <el-input-number v-model="query.min_score" :min="0" :max="100" controls-position="right" placeholder="最低" style="width: 100px" />
          <span class="range-sep">-</span>
          <el-input-number v-model="query.max_score" :min="0" :max="100" controls-position="right" placeholder="最高" style="width: 100px" />
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="query.level" clearable placeholder="全部" style="width: 110px">
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 120px">
            <el-option v-for="(v, k) in statusNames" :key="k" :label="v" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search"><el-icon><Search /></el-icon>查询</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <div class="flex-between" style="margin-bottom: 12px">
        <span class="card-title">商机列表（共 {{ total }} 条）</span>
        <div>
          <el-button size="small" @click="loadData">刷新</el-button>
          <el-button size="small" type="success" plain @click="doExport"><el-icon><Download /></el-icon>导出CSV</el-button>
        </div>
      </div>
      <el-table v-loading="loading" :data="items" stripe @row-click="goDetail" style="cursor: pointer">
        <el-table-column prop="title" label="项目名称" min-width="260" show-overflow-tooltip />
        <el-table-column prop="province" label="省份" width="90">
          <template #default="{ row }">{{ row.province || '-' }}</template>
        </el-table-column>
        <el-table-column prop="city" label="城市" width="90">
          <template #default="{ row }">{{ row.city || '-' }}</template>
        </el-table-column>
        <el-table-column prop="purchaser" label="招标方" width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.purchaser || '-' }}</template>
        </el-table-column>
        <el-table-column label="预算(万元)" width="100" align="right">
          <template #default="{ row }">{{ row.budget ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="评分" width="90" align="center">
          <template #default="{ row }">
            <span :class="scoreClass(row.total_score)">{{ row.total_score ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="级别" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="levelTag(row.level)" size="small">{{ levelName(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ statusNames[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="核验" width="90" align="center">
          <template #default="{ row }">
            <el-tooltip v-if="row.verify_status" :content="row.verify_note || ''" placement="top">
              <el-tag :type="verifyTag(row.verify_status)" size="small">{{ verifyText(row.verify_status) }}</el-tag>
            </el-tooltip>
            <el-tag v-else type="info" size="small">未核验</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="publish_time" label="发布时间" width="160">
          <template #default="{ row }">{{ (row.publish_time || '').replace('T', ' ').slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="来源" width="90" align="center">
          <template #default="{ row }">
            <el-tooltip :content="row.source_url || '无原文链接'" placement="top">
              <el-button
                v-if="row.source_url"
                link
                type="primary"
                size="small"
                @click.stop="openSource(row)"
              >
                <el-icon style="margin-right: 2px"><View /></el-icon>原文
              </el-button>
              <span v-else class="text-muted">-</span>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 12px; justify-content: flex-end"
        @size-change="loadData"
        @current-change="loadData"
      />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { exportOpportunities, listOpportunities } from '@/api/opportunity'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const items = ref([])
const total = ref(0)

const statusNames = { new: '新建', following: '跟进中', bid: '已投标', won: '已中标', lost: '已丢标', closed: '已关闭' }

const query = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  province: '',
  city: '',
  min_score: undefined,
  max_score: undefined,
  level: route.query.level || '',
  status: route.query.status || '',
})

const scoreClass = (s) => (s >= 80 ? 'score-high' : s >= 60 ? 'score-medium' : 'score-low')
const levelName = (l) => ({ high: '高', medium: '中', low: '低' }[l] || l)
const levelTag = (l) => ({ high: 'danger', medium: 'warning', low: 'success' }[l] || 'info')
const verifyText = (s) => ({ 0: '未核验', 1: '通过', 2: '不通过', 3: '待人工' }[s] || s)
const verifyTag = (s) => ({ 0: 'info', 1: 'success', 2: 'danger', 3: 'warning' }[s] || 'info')

const loadData = async () => {
  loading.value = true
  try {
    const params = { ...query }
    const res = await listOpportunities(params)
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

const search = () => {
  query.page = 1
  loadData()
}

const reset = () => {
  Object.assign(query, {
    page: 1,
    keyword: '',
    province: '',
    city: '',
    min_score: undefined,
    max_score: undefined,
    level: '',
    status: '',
  })
  loadData()
}

const goDetail = (row) => router.push(`/opportunities/${row.id}`)

const doExport = async () => {
  try {
    const res = await exportOpportunities(query)
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `商机列表_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败：' + (e.response?.data?.detail || e.message))
  }
}

const openSource = (row) => {
  if (row.source_url) window.open(row.source_url, '_blank', 'noopener')
}

onMounted(loadData)
</script>

<style scoped>
.range-sep {
  margin: 0 6px;
  color: #909399;
}
</style>
