<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="跟进记录" name="logs">
        <el-card>
          <div class="flex-between" style="margin-bottom: 12px">
            <span class="card-title">全部跟进记录（共 {{ total }} 条）</span>
            <el-button size="small" @click="loadLogs">刷新</el-button>
          </div>
          <el-table v-loading="logLoading" :data="logs" stripe>
            <el-table-column label="商机" min-width="220">
              <template #default="{ row }">
                <el-link type="primary" @click="goOpp(row.opportunity_id)">商机 #{{ row.opportunity_id }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="action" label="动作" width="110" />
            <el-table-column label="状态流转" width="140" align="center">
              <template #default="{ row }">
                {{ statusNames[row.from_status] || '-' }} → <el-tag size="small">{{ statusNames[row.to_status] || row.to_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="说明" min-width="240" show-overflow-tooltip />
            <el-table-column prop="next_plan" label="下一步计划" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">{{ row.next_plan || '-' }}</template>
            </el-table-column>
            <el-table-column label="时间" width="160">
              <template #default="{ row }">{{ fmt(row.follow_time) }}</template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="logQuery.page"
            v-model:page-size="logQuery.page_size"
            :total="total"
            layout="total, prev, pager, next"
            style="margin-top: 12px; justify-content: flex-end"
            @current-change="loadLogs"
          />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="逾期提醒" name="overdue">
        <el-alert title="以下高评分商机超过 24 小时未完成首次跟进，请尽快处理" type="warning" :closable="false" style="margin-bottom: 12px" />
        <el-card>
          <el-table v-loading="overdueLoading" :data="overdue" stripe>
            <el-table-column label="商机" min-width="260">
              <template #default="{ row }">
                <el-link type="primary" @click="goOpp(row.id)">{{ row.title }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="province" label="省份" width="90">
              <template #default="{ row }">{{ row.province || '-' }}</template>
            </el-table-column>
            <el-table-column label="评分" width="80" align="center">
              <template #default="{ row }">
                <span class="score-high">{{ row.score }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ statusNames[row.status] || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="goOpp(row.id)">去跟进</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listFollowUps, listOverdue } from '@/api/followup'

const router = useRouter()
const activeTab = ref('logs')
const logLoading = ref(false)
const overdueLoading = ref(false)
const logs = ref([])
const total = ref(0)
const overdue = ref([])

const statusNames = { new: '新建', following: '跟进中', bid: '已投标', won: '已中标', lost: '已丢标', closed: '已关闭' }
const logQuery = reactive({ page: 1, page_size: 10 })

const fmt = (t) => (t ? String(t).replace('T', ' ').slice(0, 16) : '-')

const loadLogs = async () => {
  logLoading.value = true
  try {
    const res = await listFollowUps(logQuery)
    logs.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    logLoading.value = false
  }
}

const loadOverdue = async () => {
  overdueLoading.value = true
  try {
    const res = await listOverdue()
    overdue.value = res.data?.items || []
  } finally {
    overdueLoading.value = false
  }
}

const goOpp = (id) => router.push(`/opportunities/${id}`)

onMounted(() => {
  loadLogs()
  loadOverdue()
})
</script>
