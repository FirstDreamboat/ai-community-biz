<template>
  <div class="page-container">
    <el-card>
      <div class="card-title">系统配置</div>
      <el-alert title="配置修改将影响评分与推送行为，请谨慎操作" type="warning" :closable="false" style="margin-bottom: 16px" />
      <el-table v-loading="loading" :data="configList" stripe>
        <el-table-column prop="key" label="配置键" width="220">
          <template #default="{ row }"><code>{{ row.key }}</code></template>
        </el-table-column>
        <el-table-column label="配置值" min-width="320">
          <template #default="{ row }">
            <el-input
              v-model="row.editing"
              type="textarea"
              :rows="row.isObject ? 3 : 1"
              :placeholder="row.isObject ? 'JSON 格式' : '文本值'"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" type="primary" :loading="row.saving" @click="save(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, updateConfig } from '@/api/system'

const loading = ref(false)
const configList = ref([])

const CONFIG_KEYS = [
  { key: 'scoring.weights', label: '评分权重', isObject: true },
  { key: 'push.channels', label: '推送渠道', isObject: true },
  { key: 'push.daily_cron', label: '每日推送时间', isObject: false },
  { key: 'dedup.content_threshold', label: '去重阈值', isObject: false },
]

const loadData = async () => {
  loading.value = true
  try {
    const list = []
    for (const cfg of CONFIG_KEYS) {
      try {
        const res = await getConfig(cfg.key)
        const value = res.data?.value
        list.push({
          key: cfg.key,
          isObject: cfg.isObject,
          editing: cfg.isObject ? JSON.stringify(value ?? {}, null, 2) : String(value ?? ''),
          saving: false,
        })
      } catch (e) {
        list.push({ key: cfg.key, isObject: cfg.isObject, editing: '', saving: false })
      }
    }
    configList.value = list
  } finally {
    loading.value = false
  }
}

const save = async (row) => {
  row.saving = true
  try {
    let value = row.editing
    if (row.isObject) {
      JSON.parse(value) // 校验 JSON
    }
    await updateConfig(row.key, { config_value: value })
    ElMessage.success(`${row.key} 已保存`)
  } catch (e) {
    if (e instanceof SyntaxError) {
      ElMessage.error('JSON 格式错误')
    } else {
      ElMessage.error(e.message || '保存失败')
    }
  } finally {
    row.saving = false
  }
}

onMounted(loadData)
</script>
