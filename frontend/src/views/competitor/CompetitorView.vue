<template>
  <div class="page-container">
    <el-card class="filter-card">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="竞品">
          <el-select v-model="query.competitor" clearable placeholder="全部" style="width: 140px">
            <el-option v-for="c in competitorOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="省份">
          <el-input v-model="query.province" placeholder="如：福建" clearable style="width: 130px" />
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="query.result" clearable placeholder="全部" style="width: 120px">
            <el-option label="中标" value="中标" />
            <el-option label="投标" value="投标" />
            <el-option label="未中标" value="未中标" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
        <el-form-item style="float: right; margin-right: 0">
          <el-button type="primary" plain @click="openCreate">添加记录</el-button>
          <el-button type="warning" plain @click="openKeywords">编辑关键词</el-button>
          <el-tag type="info" effect="plain" size="large">监测关键词：{{ keywords.join('、') || '-' }}</el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="15">
        <el-card>
          <div class="card-title">竞品中标/投标记录</div>
          <el-table v-loading="loading" :data="items" stripe>
            <el-table-column prop="competitor" label="竞品" width="110" />
            <el-table-column prop="province" label="省份" width="80">
              <template #default="{ row }">{{ row.province || '-' }}</template>
            </el-table-column>
            <el-table-column label="结果" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.result === '中标' ? 'success' : 'warning'">{{ row.result }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="金额(万元)" width="95" align="right">
              <template #default="{ row }">{{ row.amount ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="来源公告" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <span :title="row.announcement_title">{{ row.announcement_title || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="发现时间" width="150">
              <template #default="{ row }">{{ fmt(row.detected_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="70" align="center">
              <template #default="{ row }">
                <el-button link type="danger" @click="remove(row)">删除</el-button>
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
      </el-col>
      <el-col :span="9">
        <el-card>
          <div class="card-title">竞品区域活动分析</div>
          <EChart :option="regionOption" height="420px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 关键词编辑 -->
    <el-dialog v-model="kwVisible" title="竞品监测关键词" width="460px">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom: 12px"
        title="关键词将用于在解析核验通过的「中标/成交/结果」类公告中识别竞品品牌。保存后对新解析公告生效。" />
      <el-input v-model="kwText" type="textarea" :rows="5"
        placeholder="每行一个关键词，如：&#10;安居宝&#10;立林&#10;视得安罗格朗" />
      <template #footer>
        <el-button @click="kwVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveKeywords">保存</el-button>
      </template>
    </el-dialog>

    <!-- 手动添加记录 -->
    <el-dialog v-model="createVisible" title="添加竞品记录" width="460px">
      <el-form :model="recordForm" label-width="90px">
        <el-form-item label="竞品" required>
          <el-select v-model="recordForm.competitor" filterable allow-create default-first-option
            style="width: 100%" placeholder="选择或输入竞品品牌">
            <el-option v-for="c in competitorOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="省份">
          <el-input v-model="recordForm.province" placeholder="如：福建" />
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="recordForm.result" style="width: 100%">
            <el-option label="中标" value="中标" />
            <el-option label="投标" value="投标" />
            <el-option label="未中标" value="未中标" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额(万元)">
          <el-input-number v-model="recordForm.amount" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRecord">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import EChart from '@/components/EChart.vue'
import {
  listRecords, getAnalysis, getKeywords, saveKeywords as saveKeywordsApi, createRecord, deleteRecord,
} from '@/api/competitor'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const keywords = ref([])
const analysis = ref({ by_region: [], by_product: [] })
const competitorOptions = computed(() => keywords.value.length ? keywords.value : ['安居宝', '立林'])

const query = reactive({ page: 1, page_size: 10, competitor: '', province: '', result: '' })

const kwVisible = ref(false)
const kwText = ref('')
const saving = ref(false)

const createVisible = ref(false)
const recordForm = reactive({ competitor: '', province: '', result: '中标', amount: null })

const fmt = (t) => (t ? String(t).replace('T', ' ').slice(0, 16) : '-')

const regionOption = computed(() => {
  const list = analysis.value.by_region || []
  const grouped = {}
  list.forEach((i) => {
    grouped[i.competitor] = grouped[i.competitor] || []
    grouped[i.competitor].push(i)
  })
  const names = Object.keys(grouped)
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: [...new Set(list.map((i) => i.province))] },
    yAxis: { type: 'value' },
    series: names.map((n, idx) => ({
      name: n,
      type: 'bar',
      stack: 'total',
      barWidth: 20,
      itemStyle: { color: ['#1677ff', '#52c41a', '#fa8c16', '#722ed1', '#f56c6c'][idx % 5] },
      data: [...new Set(list.map((i) => i.province))].map((p) => {
        const found = grouped[n].find((g) => g.province === p)
        return found ? found.count : 0
      }),
    })),
  }
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await listRecords(query)
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

const openKeywords = () => {
  kwText.value = keywords.value.join('\n')
  kwVisible.value = true
}

const saveKeywords = async () => {
  saving.value = true
  try {
    const list = kwText.value.split('\n').map((s) => s.trim()).filter(Boolean)
    const res = await saveKeywordsApi(list)
    keywords.value = res.data?.keywords || []
    kwVisible.value = false
    ElMessage.success('关键词已保存')
  } finally {
    saving.value = false
  }
}

const openCreate = () => {
  Object.assign(recordForm, { competitor: '', province: '', result: '中标', amount: null })
  createVisible.value = true
}

const saveRecord = async () => {
  if (!recordForm.competitor) {
    ElMessage.warning('请填写竞品名称')
    return
  }
  saving.value = true
  try {
    await createRecord({
      competitor: recordForm.competitor,
      province: recordForm.province || null,
      result: recordForm.result,
      amount: recordForm.amount ?? null,
    })
    createVisible.value = false
    ElMessage.success('竞品记录已添加')
    loadData()
    getAnalysis().then((r) => { analysis.value = r.data || { by_region: [], by_product: [] } }).catch(() => {})
  } finally {
    saving.value = false
  }
}

const remove = async (row) => {
  await ElMessageBox.confirm(`确认删除「${row.competitor}」的竞品记录？`, '删除确认', { type: 'warning' })
  await deleteRecord(row.id)
  ElMessage.success('已删除')
  loadData()
  getAnalysis().then((r) => { analysis.value = r.data || { by_region: [], by_product: [] } }).catch(() => {})
}

onMounted(() => {
  loadData()
  getAnalysis().then((r) => { analysis.value = r.data || { by_region: [], by_product: [] } }).catch(() => {})
  getKeywords().then((r) => { keywords.value = r.data?.keywords || [] }).catch(() => {})
})
</script>
