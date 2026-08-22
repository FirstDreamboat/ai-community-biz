<template>
  <div class="page-container">
    <el-card class="filter-card">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="渠道">
          <el-select v-model="query.channel" clearable placeholder="全部" style="width: 140px">
            <el-option v-for="c in channels" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 120px">
            <el-option label="待发送" value="pending" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="sendPending"><el-icon><Promotion /></el-icon>发送待推送</el-button>
        </el-form-item>
        <el-form-item style="float: right; margin-right: 0">
          <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新建推送</el-button>
          <el-button type="warning" @click="openTest"><el-icon><Connection /></el-icon>渠道测试</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="opportunity_id" label="商机ID" width="90" />
        <el-table-column label="渠道" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="channelTagType(row.push_channel)">{{ channelLabel(row.push_channel) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.content_snapshot?.title || '-' }}</template>
        </el-table-column>
        <el-table-column label="评分" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="success" effect="plain">{{ row.content_snapshot?.score || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="receiver" label="接收人/群" width="160" show-overflow-tooltip />
        <el-table-column prop="push_date" label="推送日期" width="110" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
              {{ row.status === 'success' ? '成功' : row.status === 'failed' ? '失败' : '待发送' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain :disabled="row.status === 'success'" @click="sendOne(row)">发送</el-button>
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

    <el-dialog v-model="dialogVisible" title="新建推送" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="商机ID" prop="opportunity_id">
          <el-input-number v-model="form.opportunity_id" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="推送渠道" prop="push_channel">
          <el-select v-model="form.push_channel" style="width: 100%">
            <el-option v-for="c in channels" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="接收人/群" prop="receiver">
          <el-input v-model="form.receiver" placeholder="如：销售一部群 / 张三" />
        </el-form-item>
        <el-form-item label="立即发送">
          <el-switch v-model="form.auto_send" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testVisible" title="渠道连通性测试" width="460px">
      <el-form label-width="110px">
        <el-form-item label="推送渠道">
          <el-select v-model="testForm.push_channel" style="width: 100%">
            <el-option v-for="c in channels" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试内容">
          <el-input v-model="testForm.content" type="textarea" :rows="3" placeholder="留空使用默认测试内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="testVisible = false">取消</el-button>
        <el-button type="primary" :loading="testing" @click="doTest">发送测试</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listPushRecords, createPushRecord, sendPushRecord, sendPendingPushes, testPushChannel } from '@/api/push'

const channels = [
  { value: 'wecom', label: '企业微信' },
  { value: 'dingtalk', label: '钉钉' },
  { value: 'webhook', label: '通用Webhook' },
]

const loading = ref(false)
const items = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const submitting = ref(false)
const testVisible = ref(false)
const testing = ref(false)
const formRef = ref()

const query = reactive({ page: 1, page_size: 10, channel: '', status: '' })
const form = reactive({ opportunity_id: null, push_channel: 'wecom', receiver: '', auto_send: true })
const testForm = reactive({ push_channel: 'wecom', content: '' })

const rules = {
  opportunity_id: [{ required: true, message: '请输入商机ID', trigger: 'blur' }],
  push_channel: [{ required: true, message: '请选择渠道', trigger: 'change' }],
  receiver: [{ required: true, message: '请输入接收人/群', trigger: 'blur' }],
}

const channelLabel = (v) => channels.find((c) => c.value === v)?.label || v
const channelTagType = (v) => (v === 'wecom' ? 'success' : v === 'dingtalk' ? 'warning' : 'primary')

const loadData = async () => {
  loading.value = true
  try {
    const res = await listPushRecords(query)
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

const openCreate = () => {
  Object.assign(form, { opportunity_id: null, push_channel: 'wecom', receiver: '', auto_send: true })
  dialogVisible.value = true
}

const submit = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    await createPushRecord({ ...form })
    ElMessage.success('已创建')
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const sendOne = async (row) => {
  const res = await sendPushRecord(row.id)
  if (res.data?.send_result?.ok) {
    ElMessage.success('发送成功')
  } else {
    ElMessage.error(res.data?.send_result?.error || '发送失败')
  }
  loadData()
}

const sendPending = async () => {
  const res = await sendPendingPushes({ limit: 50 })
  ElMessage.success(`已处理 ${res.data?.total || 0} 条，成功 ${res.data?.success || 0}，失败 ${res.data?.failed || 0}`)
  loadData()
}

const openTest = () => {
  Object.assign(testForm, { push_channel: 'wecom', content: '' })
  testVisible.value = true
}

const doTest = async () => {
  testing.value = true
  try {
    await testPushChannel({ ...testForm })
    ElMessage.success('渠道连通性测试通过')
    testVisible.value = false
  } finally {
    testing.value = false
  }
}

onMounted(loadData)
</script>
