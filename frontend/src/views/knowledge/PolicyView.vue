<template>
  <div class="page-container">
    <el-card class="filter-card">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="级别">
          <el-select v-model="query.level" clearable placeholder="全部" style="width: 130px">
            <el-option label="国家级" value="国家级" />
            <el-option label="省级" value="省级" />
            <el-option label="市级" value="市级" />
          </el-select>
        </el-form-item>
        <el-form-item label="地区">
          <el-input v-model="query.region" placeholder="如：广东省" clearable style="width: 150px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" placeholder="标题搜索" clearable style="width: 180px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
        <el-form-item style="float: right; margin-right: 0">
          <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增政策</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="title" label="政策标题" min-width="260" show-overflow-tooltip />
        <el-table-column label="级别" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="levelType(row.level)">{{ row.level || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="region" label="地区" width="130" show-overflow-tooltip />
        <el-table-column prop="publish_time" label="发布时间" width="110" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="remove(row)">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑政策' : '新增政策'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="级别">
          <el-select v-model="form.level" clearable style="width: 100%">
            <el-option label="国家级" value="国家级" />
            <el-option label="省级" value="省级" />
            <el-option label="市级" value="市级" />
          </el-select>
        </el-form-item>
        <el-form-item label="地区">
          <el-input v-model="form.region" placeholder="如：广东省 广州市" />
        </el-form-item>
        <el-form-item label="发布时间">
          <el-date-picker v-model="form.publish_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="政策要点/原文摘要" />
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
import { listPolicies, createPolicy, updatePolicy, deletePolicy } from '@/api/knowledge'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()

const query = reactive({ page: 1, page_size: 10, level: '', region: '', keyword: '' })

const defaultForm = () => ({ id: null, title: '', level: '市级', region: '', content: '', publish_time: null })
const form = reactive(defaultForm())
const rules = {
  title: [{ required: true, message: '请输入政策标题', trigger: 'blur' }],
}

const levelType = (l) => (l === '国家级' ? 'danger' : l === '省级' ? 'warning' : 'primary')

const loadData = async () => {
  loading.value = true
  try {
    const res = await listPolicies(query)
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
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

const openEdit = (row) => {
  Object.assign(form, {
    ...row,
    publish_time: row.publish_time ? row.publish_time.replace(' ', 'T') : null,
  })
  dialogVisible.value = true
}

const submit = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = { ...form }
    delete payload.id
    if (form.id) {
      await updatePolicy(form.id, payload)
      ElMessage.success('已更新')
    } else {
      await createPolicy(payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const remove = async (row) => {
  await ElMessageBox.confirm(`确认删除政策「${row.title}」？`, '删除', { type: 'warning' })
  await deletePolicy(row.id)
  ElMessage.success('已删除')
  loadData()
}

onMounted(loadData)
</script>
