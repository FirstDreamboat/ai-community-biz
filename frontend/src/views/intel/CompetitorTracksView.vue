<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-head">
        <div class="title">竞品中标后续追踪</div>
        <div class="actions">
          <el-select v-model="query.competitor" placeholder="竞品" clearable style="width: 130px" @change="loadData">
            <el-option v-for="c in ['安居宝', '立林', '麦驰', '慧锐通', '太川', '视得安罗格朗']" :key="c" :label="c" :value="c" />
          </el-select>
          <el-select v-model="query.status" placeholder="状态" clearable style="width: 110px" @change="loadData">
            <el-option v-for="s in ['tracking', 'done', 'dropped']" :key="s" :label="statusText[s]" :value="s" />
          </el-select>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button type="success" @click="generate" :loading="genLoading">从中标记录生成</el-button>
          <el-button type="primary" plain @click="openDialog()">手动新增</el-button>
        </div>
      </div>

      <el-alert type="info" :closable="false" style="margin-bottom: 12px"
                title="竞品在某小区中标后，跟踪该小区后续标段、增补工程、维保招标——竞品替你验证了真实需求。点击「从中标记录生成」自动由竞品监测的中标公告创建追踪。" />

      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="competitor" label="竞品" width="100">
          <template #default="{ row }"><el-tag type="danger" size="small">{{ row.competitor }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="community" label="小区/项目" width="150" show-overflow-tooltip />
        <el-table-column label="地区" width="110">
          <template #default="{ row }">{{ row.province }}{{ row.city }}</template>
        </el-table-column>
        <el-table-column prop="won_at" label="竞品中标日" width="110">
          <template #default="{ row }">{{ row.won_at || '-' }}</template>
        </el-table-column>
        <el-table-column prop="track_type" label="追踪类型" width="110" />
        <el-table-column prop="note" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="原文" width="70">
          <template #default="{ row }">
            <el-button v-if="row.source_url" link type="primary" size="small"
                       @click.stop="openUrl(row.source_url)">查看</el-button>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'done' ? 'success' : row.status === 'dropped' ? 'info' : 'warning'" size="small">
              {{ statusText[row.status] }}
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

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑追踪' : '新增追踪'" width="560px">
      <el-form :model="dialog.form" label-width="100px">
        <el-form-item label="竞品" required>
          <el-input v-model="dialog.form.competitor" placeholder="安居宝 / 立林 / 麦驰 ..." />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="小区/项目"><el-input v-model="dialog.form.community" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="追踪类型">
              <el-select v-model="dialog.form.track_type" style="width: 100%">
                <el-option v-for="t in ['后续标段', '增补工程', '维保服务', '整体换新']" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
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
            <el-form-item label="中标日期"><el-date-picker v-model="dialog.form.won_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="dialog.form.status" style="width: 100%">
                <el-option v-for="s in ['tracking', 'done', 'dropped']" :key="s" :label="statusText[s]" :value="s" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="原文链接"><el-input v-model="dialog.form.source_url" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="dialog.form.note" type="textarea" :rows="3" /></el-form-item>
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
import { listCompetitorTracks, createCompetitorTrack, updateCompetitorTrack, deleteCompetitorTrack, generateTracksFromRecords } from '@/api/intel'

const statusText = { tracking: '追踪中', done: '已完成', dropped: '已放弃' }
const items = ref([])
const total = ref(0)
const loading = ref(false)
const genLoading = ref(false)
const query = reactive({ competitor: '', status: '', page: 1, page_size: 20 })
const dialog = reactive({ visible: false, form: {} })

const openUrl = (url) => window.open(url, '_blank', 'noopener')

const emptyForm = () => ({
  id: null, competitor: '', community: '', province: '', city: '',
  won_at: null, track_type: '后续标段', source_url: '', status: 'tracking', note: '',
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await listCompetitorTracks(query)
    items.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const generate = async () => {
  genLoading.value = true
  try {
    const res = await generateTracksFromRecords()
    const d = res.data
    ElMessage.success(`从中标记录生成 ${d.created} 条，已存在 ${d.existed} 条`)
    loadData()
  } finally {
    genLoading.value = false
  }
}

const openDialog = (row) => {
  dialog.form = row ? { ...emptyForm(), ...row } : emptyForm()
  dialog.visible = true
}

const save = async () => {
  if (!dialog.form.competitor) {
    ElMessage.warning('请填写竞品名称')
    return
  }
  if (dialog.form.id) {
    await updateCompetitorTrack(dialog.form.id, dialog.form)
    ElMessage.success('已更新')
  } else {
    await createCompetitorTrack(dialog.form)
    ElMessage.success('已新增')
  }
  dialog.visible = false
  loadData()
}

const remove = (row) => {
  ElMessageBox.confirm('确认删除该追踪？', '提示', { type: 'warning' }).then(async () => {
    await deleteCompetitorTrack(row.id)
    ElMessage.success('已删除')
    loadData()
  })
}

onMounted(loadData)
</script>
