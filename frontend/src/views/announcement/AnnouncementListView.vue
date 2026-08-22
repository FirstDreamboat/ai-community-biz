<template>
  <div class="page-container">
    <el-card class="filter-card">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="公告标题" clearable style="width: 200px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="解析状态">
          <el-select v-model="query.parse_status" clearable placeholder="全部" style="width: 130px">
            <el-option label="未解析" :value="0" />
            <el-option label="已解析" :value="1" />
            <el-option label="解析失败" :value="2" />
            <el-option label="待人工" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="核验状态">
          <el-select v-model="query.verify_status" clearable placeholder="全部" style="width: 130px">
            <el-option label="未核验" :value="0" />
            <el-option label="核验通过" :value="1" />
            <el-option label="核验不通过" :value="2" />
            <el-option label="待人工" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="reset">重置</el-button>
          <el-button type="success" :disabled="batchRunning" :loading="batchRunning" @click="handleBatchParse">
            {{ batchRunning ? '批量解析中' : '批量解析未解析' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="batchRunning">
      <el-alert type="info" :closable="false" style="margin-bottom: 8px">
        <template #title>
          批量解析进行中：已处理 {{ batchState.processed }}/{{ batchState.total }} 条
          · 通过 {{ batchState.success }} · 不通过 {{ batchState.rejected }}
          · 待人工 {{ batchState.manual }} · 失败 {{ batchState.failed }}
        </template>
      </el-alert>
      <div class="batch-logs">
        <div v-for="(log, i) in batchState.logs" :key="i" class="log-line">{{ log }}</div>
      </div>
    </el-card>

    <el-card>
      <div class="card-title">公告列表（共 {{ total }} 条）</div>
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="公告标题" min-width="300" show-overflow-tooltip />
        <el-table-column prop="source_id" label="数据源" width="80" />
        <el-table-column prop="category" label="分类" width="90">
          <template #default="{ row }">{{ row.category || '-' }}</template>
        </el-table-column>
        <el-table-column label="解析状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="parseTag(row.parse_status)" size="small">{{ parseText(row.parse_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="核验状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="verifyTag(row.verify_status)" size="small">{{ verifyText(row.verify_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" width="160">
          <template #default="{ row }">{{ fmt(row.publish_time) }}</template>
        </el-table-column>
        <el-table-column label="采集时间" width="160">
          <template #default="{ row }">{{ fmt(row.crawl_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">查看</el-button>
            <el-button size="small" type="primary" :loading="reparsingId === row.id" @click="handleReparse(row)">重新解析</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.page_size"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 12px; justify-content: flex-end"
        @current-change="loadData"
      />
    </el-card>

    <!-- 公告详情 -->
    <el-dialog v-model="detailVisible" title="公告详情" width="760px" top="6vh">
      <div v-loading="detailLoading">
        <h3>{{ detail.title }}</h3>
        <div class="text-secondary" style="margin: 8px 0">
          发布时间：{{ fmt(detail.publish_time) }} · 原文链接：
          <el-link v-if="detail.source_url" :href="detail.source_url" target="_blank" type="primary">{{ detail.source_url }}</el-link>
          <span v-else>-</span>
        </div>
        <el-alert v-if="detail.parse_status === 2" type="error" title="上次解析失败" :closable="false" style="margin-bottom: 8px" />
        <el-descriptions v-if="detail.verify_status" :column="1" border size="small" style="margin-bottom: 8px">
          <el-descriptions-item label="核验状态">
            <el-tag :type="verifyTag(detail.verify_status)" size="small">{{ verifyText(detail.verify_status) }}</el-tag>
            <span v-if="detail.verify_result?.reason" style="margin-left: 8px">{{ detail.verify_result.reason }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.verify_result?.risk_points?.length" label="风险点">
            <span v-for="(r, i) in detail.verify_result.risk_points" :key="i" style="display: block">{{ r }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.verify_result?.unsupported_fields?.length" label="无依据字段">
            {{ detail.verify_result.unsupported_fields.join('、') }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.verify_result?.suggested_relevance" label="建议相关度">
            {{ detail.verify_result.suggested_relevance }}
          </el-descriptions-item>
        </el-descriptions>
        <pre class="ann-content">{{ detail.content }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listAnnouncements, getAnnouncement, reParse, batchParse, getBatchParseStatus } from '@/api/announcement'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const reparsingId = ref(null)
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref({})

const batchRunning = ref(false)
const batchState = ref({ logs: [] })
let batchTimer = null

const query = reactive({ page: 1, page_size: 10, keyword: '', parse_status: undefined, verify_status: undefined })

const parseText = (s) => ({ 0: '未解析', 1: '已解析', 2: '失败', 3: '待人工' }[s] || s)
const parseTag = (s) => ({ 0: 'info', 1: 'success', 2: 'danger', 3: 'warning' }[s] || 'info')
const verifyText = (s) => ({ 0: '未核验', 1: '通过', 2: '不通过', 3: '待人工' }[s] || s)
const verifyTag = (s) => ({ 0: 'info', 1: 'success', 2: 'danger', 3: 'warning' }[s] || 'info')
const fmt = (t) => (t ? String(t).replace('T', ' ').slice(0, 16) : '-')

const loadData = async () => {
  loading.value = true
  try {
    const res = await listAnnouncements(query)
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
  Object.assign(query, { page: 1, keyword: '', parse_status: undefined, verify_status: undefined })
  loadData()
}

const viewDetail = async (row) => {
  detailVisible.value = true
  detailLoading.value = true
  try {
    const res = await getAnnouncement(row.id)
    detail.value = res.data || {}
  } finally {
    detailLoading.value = false
  }
}

const handleReparse = async (row) => {
  await ElMessageBox.confirm(`确认重新解析公告「${row.title.slice(0, 30)}...」？将触发 AI 解析并二次核验，核验通过才生成商机。`, '重新解析', { type: 'warning' })
  reparsingId.value = row.id
  try {
    const res = await reParse(row.id)
    const v = res.data?.verify_status
    const note = { 1: '核验通过，已生成商机', 2: '核验不通过，未生成商机', 3: '待人工复核，未生成商机' }[v] || ''
    ElMessage.success(`${note}${res.data?.opportunity_id ? `（商机ID=${res.data.opportunity_id}）` : ''}`)
    loadData()
  } catch (e) {
    /* 已由拦截器提示 */
  } finally {
    reparsingId.value = null
  }
}

const handleBatchParse = async () => {
  await ElMessageBox.confirm('将批量处理所有"未解析/未核验"公告：AI 解析 + 二次核验，核验通过才生成商机。继续？', '批量解析', { type: 'warning' })
  try {
    await batchParse({ limit: 100, reparse_failed: false, with_verify: true })
    batchRunning.value = true
    batchState.value = { logs: [] }
    batchTimer = setInterval(pollBatch, 3000)
    pollBatch()
  } catch (e) {
    if (e?.response?.status === 409) {
      batchRunning.value = true
      batchTimer = setInterval(pollBatch, 3000)
      pollBatch()
    }
  }
}

const pollBatch = async () => {
  try {
    const res = await getBatchParseStatus()
    batchState.value = res.data || { logs: [] }
    if (!batchState.value.running) {
      batchRunning.value = false
      clearInterval(batchTimer)
      batchTimer = null
      loadData()
      if (batchState.value.finished_at) {
        ElMessage.success(`批量解析完成：通过 ${batchState.value.success}，不通过 ${batchState.value.rejected}，待人工 ${batchState.value.manual}，失败 ${batchState.value.failed}`)
      }
    }
  } catch (e) {
    /* 忽略轮询错误 */
  }
}

onMounted(loadData)
</script>

<style scoped>
.ann-content {
  white-space: pre-wrap;
  word-break: break-all;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.8;
  color: #606266;
  max-height: 420px;
  overflow-y: auto;
  background: #f8f9fb;
  padding: 12px;
  border-radius: 6px;
}
.batch-logs {
  max-height: 160px;
  overflow-y: auto;
  background: #f8f9fb;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
}
.log-line {
  line-height: 1.8;
  color: #909399;
}
</style>
