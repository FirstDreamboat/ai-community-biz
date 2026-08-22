<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-head">
        <div class="title">12345 诉求热点（痛点商机）</div>
        <div class="actions">
          <el-input v-model="query.keyword" placeholder="小区名" clearable style="width: 180px"
                    @keyup.enter="loadData" @clear="loadData" />
          <el-select v-model="query.sort" style="width: 130px" @change="loadData">
            <el-option label="按热力分" value="hot" />
            <el-option label="按诉求数" value="count" />
          </el-select>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button type="success" @click="openDialog()">新增热点</el-button>
        </div>
      </div>

      <el-alert type="warning" :closable="false" style="margin-bottom: 12px"
                title="聚合 12345 热线诉求：小区诉求密度越高，门禁/对讲/安防改造意愿越强。高热点小区优先拜访业主委员会与物业。" />

      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="community" label="小区/社区" width="150" show-overflow-tooltip />
        <el-table-column label="地区" width="110">
          <template #default="{ row }">{{ row.province }}{{ row.city }}</template>
        </el-table-column>
        <el-table-column label="热力" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.hot_score" :stroke-width="12"
                         :color="row.hot_score >= 80 ? '#f56c6c' : row.hot_score >= 60 ? '#e6a23c' : '#909399'" />
          </template>
        </el-table-column>
        <el-table-column prop="appeal_count" label="诉求数" width="80" />
        <el-table-column label="高频诉求" width="200">
          <template #default="{ row }">
            <el-tag v-for="t in (row.topics || []).slice(0, 3)" :key="t" type="danger" size="small" style="margin-right: 4px">{{ t }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="period" label="统计周期" width="100" />
        <el-table-column prop="note" label="商机提示" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 2 ? 'success' : row.status === 1 ? 'primary' : 'warning'" size="small">
              {{ ['待跟进', '跟进中', '已转化'][row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination style="margin-top: 12px; justify-content: flex-end" background layout="total, prev, pager, next"
                     :total="total" :page-size="query.page_size" :current-page="query.page"
                     @current-change="(p) => { query.page = p; loadData() }" />
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑热点' : '新增热点'" width="580px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="小区/社区" required><el-input v-model="dialog.form.community" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="省份"><el-input v-model="dialog.form.province" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="城市"><el-input v-model="dialog.form.city" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="诉求数量">
              <el-input-number v-model="dialog.form.appeal_count" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="热力分">
              <el-input-number v-model="dialog.form.hot_score" :min="0" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="高频诉求">
          <el-select v-model="dialog.form.topics" multiple filterable allow-create style="width: 100%"
                     placeholder="门禁损坏 / 对讲失灵 / 监控缺失 / 停车难 ...">
            <el-option v-for="t in ['门禁损坏', '对讲失灵', '监控缺失', '停车难', '安防缺失', '楼道照明']" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="诉求样例">
          <el-select v-model="dialog.form.sample_titles" multiple filterable allow-create style="width: 100%"
                     placeholder="典型诉求标题（可自建）" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="统计周期"><el-input v-model="dialog.form.period" placeholder="如：2026年7月" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="dialog.form.status" style="width: 100%">
                <el-option label="待跟进" :value="0" />
                <el-option label="跟进中" :value="1" />
                <el-option label="已转化" :value="2" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="商机提示"><el-input v-model="dialog.form.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listAppealHotspots, createAppealHotspot, updateAppealHotspot, deleteAppealHotspot } from '@/api/intel'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ keyword: '', sort: 'hot', page: 1, page_size: 20 })
const dialog = reactive({ visible: false, form: {} })

const emptyForm = () => ({
  id: null, community: '', province: '', city: '', appeal_count: 0, hot_score: 0,
  topics: [], sample_titles: [], source_url: '', period: '', status: 0, note: '',
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await listAppealHotspots(query)
    items.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const openDialog = (row) => {
  dialog.form = row ? { ...emptyForm(), ...row } : emptyForm()
  dialog.visible = true
}

const save = async () => {
  if (!dialog.form.community) {
    ElMessage.warning('请填写小区/社区')
    return
  }
  if (dialog.form.id) {
    await updateAppealHotspot(dialog.form.id, dialog.form)
    ElMessage.success('已更新')
  } else {
    await createAppealHotspot(dialog.form)
    ElMessage.success('已新增')
  }
  dialog.visible = false
  loadData()
}

const remove = (row) => {
  ElMessageBox.confirm(`确认删除「${row.community}」热点？`, '提示', { type: 'warning' }).then(async () => {
    await deleteAppealHotspot(row.id)
    ElMessage.success('已删除')
    loadData()
  })
}

onMounted(loadData)
</script>
