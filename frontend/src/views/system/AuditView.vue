<template>
  <div class="page-container">
    <el-card class="filter-card">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="模块">
          <el-input v-model="query.module" placeholder="如 system" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="search">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-card>
      <div class="card-title">审计日志（共 {{ total }} 条）</div>
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="user_id" label="用户ID" width="80" />
        <el-table-column prop="action" label="动作" width="140" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="target_id" label="对象" width="100">
          <template #default="{ row }">{{ row.target_id || '-' }}</template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.detail || '-' }}</template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { listAuditLogs } from '@/api/system'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10, module: '' })

const fmt = (t) => (t ? String(t).replace('T', ' ').slice(0, 16) : '-')

const loadData = async () => {
  loading.value = true
  try {
    const res = await listAuditLogs(query)
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

onMounted(loadData)
</script>
