<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-head">
        <div class="title">更新商机（设备生命周期推算）</div>
        <div class="actions">
          <el-select v-model="query.window_status" placeholder="更新窗口" clearable style="width: 130px" @change="loadData">
            <el-option label="已超期" value="overdue" />
            <el-option label="换新窗口" value="due" />
            <el-option label="临期" value="imminent" />
          </el-select>
          <el-select v-model="query.status" placeholder="跟进状态" clearable style="width: 120px" @change="loadData">
            <el-option v-for="s in ['new', 'following', 'converted', 'closed']" :key="s" :label="statusText[s]" :value="s" />
          </el-select>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button type="success" @click="generate" :loading="genLoading">扫描台账生成</el-button>
        </div>
      </div>

      <el-alert type="info" :closable="false" style="margin-bottom: 12px"
                title="系统按设备生命周期推算换新窗口：安装 6-8 年临期、8-10 年进入换新窗口、超过 10 年超期。点击「扫描台账生成」从存量项目自动生成更新商机。" />

      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="community" label="小区/社区" width="140" show-overflow-tooltip />
        <el-table-column label="地区" width="110">
          <template #default="{ row }">{{ row.province }}{{ row.city }}</template>
        </el-table-column>
        <el-table-column prop="age_years" label="已用年限" width="90">
          <template #default="{ row }">{{ row.age_years }} 年</template>
        </el-table-column>
        <el-table-column label="窗口" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.window_status === 'overdue'" type="danger" size="small">已超期</el-tag>
            <el-tag v-else-if="row.window_status === 'due'" type="warning" size="small">换新窗口</el-tag>
            <el-tag v-else type="primary" size="small">临期</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="recommend_action" label="推荐动作" min-width="260" show-overflow-tooltip />
        <el-table-column label="预估预算(万)" width="110">
          <template #default="{ row }">{{ row.est_budget ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'converted' ? 'success' : row.status === 'closed' ? 'info' : 'primary'" size="small">
              {{ statusText[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="owner_name" label="负责人" width="90" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openFollow(row)">跟进</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination style="margin-top: 12px; justify-content: flex-end" background layout="total, prev, pager, next"
                     :total="total" :page-size="query.page_size" :current-page="query.page"
                     @current-change="(p) => { query.page = p; loadData() }" />
    </el-card>

    <el-dialog v-model="dialog.visible" title="更新商机跟进" width="480px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="跟进状态">
          <el-select v-model="dialog.form.status" style="width: 100%">
            <el-option v-for="s in ['new', 'following', 'converted', 'closed']" :key="s" :label="statusText[s]" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人"><el-input v-model="dialog.form.owner_name" /></el-form-item>
        <el-form-item label="跟进备注"><el-input v-model="dialog.form.note" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveFollow">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUpdateOpportunities, generateUpdateOpportunities, updateUpdateOpportunity, deleteUpdateOpportunity } from '@/api/intel'

const statusText = { new: '新商机', following: '跟进中', converted: '已转化', closed: '已关闭' }
const items = ref([])
const total = ref(0)
const loading = ref(false)
const genLoading = ref(false)
const query = reactive({ window_status: '', status: '', page: 1, page_size: 20 })
const dialog = reactive({ visible: false, form: {} })

const loadData = async () => {
  loading.value = true
  try {
    const res = await listUpdateOpportunities(query)
    items.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const generate = async () => {
  genLoading.value = true
  try {
    const res = await generateUpdateOpportunities()
    const d = res.data
    ElMessage.success(`生成 ${d.created} 条，更新 ${d.updated} 条，服役期内跳过 ${d.skipped} 条`)
    loadData()
  } finally {
    genLoading.value = false
  }
}

const openFollow = (row) => {
  dialog.form = { id: row.id, status: row.status, owner_name: row.owner_name, note: row.note }
  dialog.visible = true
}

const saveFollow = async () => {
  await updateUpdateOpportunity(dialog.form.id, dialog.form)
  ElMessage.success('已保存')
  dialog.visible = false
  loadData()
}

const remove = (row) => {
  ElMessageBox.confirm('确认删除该更新商机？', '提示', { type: 'warning' }).then(async () => {
    await deleteUpdateOpportunity(row.id)
    ElMessage.success('已删除')
    loadData()
  })
}

onMounted(loadData)
</script>
