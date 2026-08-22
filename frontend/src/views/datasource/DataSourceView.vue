<template>
  <div class="page-container">
    <el-card>
      <div class="flex-between" style="margin-bottom: 12px">
        <span class="card-title">数据源管理</span>
        <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增数据源</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="source_name" label="数据源名称" min-width="180" />
        <el-table-column prop="source_type" label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ typeName(row.source_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="base_url" label="站点" min-width="200" show-overflow-tooltip />
        <el-table-column label="关键词" width="160">
          <template #default="{ row }">{{ (row.keywords || []).join('、') || '-' }}</template>
        </el-table-column>
        <el-table-column prop="schedule_cron" label="调度" width="110">
          <template #default="{ row }">{{ row.schedule_cron || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" @change="toggle(row)" />
          </template>
        </el-table-column>
        <el-table-column label="上次运行" width="160">
          <template #default="{ row }">
            <div>{{ fmt(row.last_run_at) }}</div>
            <el-tag v-if="row.last_run_status" size="small" :type="row.last_run_status === 'success' ? 'success' : 'danger'" effect="plain">
              {{ row.last_run_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="warning" :loading="runningId === row.id" @click="run(row)">采集</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card style="margin-top: 16px">
      <div class="card-title">采集任务记录</div>
      <el-table v-loading="taskLoading" :data="tasks" size="small">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="source_id" label="数据源" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="taskTag(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_found" label="发现" width="80" align="right" />
        <el-table-column prop="total_new" label="新增" width="80" align="right" />
        <el-table-column prop="message" label="说明" min-width="200" show-overflow-tooltip />
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ fmt(row.started_at || row.finished_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑数据源' : '新增数据源'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="source_name">
          <el-input v-model="form.source_name" placeholder="如：福建省公共资源交易中心" />
        </el-form-item>
        <el-form-item label="类型" prop="source_type">
          <el-select v-model="form.source_type" style="width: 100%">
            <el-option label="政府采购网" value="gov" />
            <el-option label="公共资源交易" value="trade" />
            <el-option label="官网公告" value="website" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="站点地址" prop="base_url">
          <el-input v-model="form.base_url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="关键词">
          <el-select v-model="form.keywords" multiple filterable allow-create default-first-option placeholder="输入关键词回车" style="width: 100%">
            <el-option v-for="k in keywordOptions" :key="k" :label="k" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="区域">
          <el-select v-model="form.regions" multiple filterable allow-create default-first-option placeholder="如：福建" style="width: 100%" />
        </el-form-item>
        <el-form-item label="调度时间">
          <el-input v-model="form.schedule_cron" placeholder="cron 表达式，如 0 8 * * *" />
        </el-form-item>
        <el-form-item label="启用代理">
          <el-switch v-model="form.proxy_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listDataSources, createDataSource, updateDataSource, deleteDataSource,
  toggleDataSource, runDataSource, listTasks,
} from '@/api/datasource'

const loading = ref(false)
const items = ref([])
const taskLoading = ref(false)
const tasks = ref([])
const dialogVisible = ref(false)
const submitting = ref(false)
const runningId = ref(null)
const formRef = ref()

const keywordOptions = ['老旧小区改造', '城市更新', '智慧社区', '社区智能化', '小区智能化', '楼宇对讲', '可视对讲', '对讲系统', '数字对讲', 'IP对讲', '无线对讲', '门口机', '室内机', '呼叫系统', '智能家居', '智能面板', '智能网关', '医护对讲', '病房呼叫', '护士站', '医院智能化', '智慧医院', '医疗信息化', '智能化工程', '弱电', '弱电工程', '综合布线', '系统集成', '楼宇自控', '信息发布', '广播系统', '会议系统', '能耗管理', '节能改造', '门禁', '安防', '监控', '视频监控', '周界防范', '报警系统', '电子围栏', '人脸识别', '车牌识别', '道闸', '停车场', '停车场管理', '智慧城市', '智慧园区', '智慧楼宇', '智慧医疗', '智慧养老', '医养结合', '康养', '物业管理', '物业服务', '校园广播', '电子班牌', '多媒体教室', '改造', '配套', '中标', '签约', '狄耐克']

const typeName = (t) => ({ gov: '政府采购', trade: '公共资源', website: '官网', other: '其他' }[t] || t)
const taskTag = (s) => ({ success: 'success', running: 'warning', failed: 'danger', pending: 'info' }[s] || 'info')
const fmt = (t) => (t ? String(t).replace('T', ' ').slice(0, 16) : '-')

const defaultForm = () => ({
  id: null, source_name: '', source_type: 'gov', base_url: '', keywords: [],
  regions: [], schedule_cron: '0 8 * * *', proxy_enabled: false,
})
const form = reactive(defaultForm())
const rules = {
  source_name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  base_url: [{ required: true, message: '请输入站点地址', trigger: 'blur' }],
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await listDataSources()
    items.value = res.data || []
  } finally {
    loading.value = false
  }
}

const loadTasks = async () => {
  taskLoading.value = true
  try {
    const res = await listTasks({ page_size: 20 })
    tasks.value = res.data?.items || []
  } finally {
    taskLoading.value = false
  }
}

const openCreate = () => {
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

const openEdit = (row) => {
  Object.assign(form, defaultForm(), { ...row, keywords: row.keywords || [], regions: row.regions || [] })
  dialogVisible.value = true
}

const submit = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = { ...form }
    delete payload.id
    if (form.id) {
      await updateDataSource(form.id, payload)
      ElMessage.success('已更新')
    } else {
      await createDataSource(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const toggle = async (row) => {
  await toggleDataSource(row.id)
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

const run = async (row) => {
  runningId.value = row.id
  try {
    const res = await runDataSource(row.id)
    ElMessage.success(`采集任务已触发：${res.data?.task_id || ''}`)
    loadTasks()
  } finally {
    runningId.value = null
  }
}

const remove = async (row) => {
  await ElMessageBox.confirm(`确认删除数据源「${row.source_name}」？`, '删除', { type: 'warning' })
  await deleteDataSource(row.id)
  ElMessage.success('已删除')
  loadData()
}

onMounted(() => {
  loadData()
  loadTasks()
})
</script>
