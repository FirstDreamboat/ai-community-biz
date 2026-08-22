<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-head">
        <div class="title">销售线索（线下渠道上报·智能评分）</div>
        <div class="actions">
          <el-input v-model="query.keyword" placeholder="项目/客户/详情" clearable style="width: 200px"
                    @keyup.enter="loadData" @clear="loadData" />
          <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="loadData">
            <el-option v-for="s in ['new', 'following', 'won', 'lost']" :key="s" :label="statusText[s]" :value="s" />
          </el-select>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button type="success" @click="openDialog()">上报线索</el-button>
        </div>
      </div>

      <el-alert type="info" :closable="false" style="margin-bottom: 12px"
                title="系统按行业相关度、阶段、渠道、预算四维自动评分（0-100）。高分段线索优先派单跟进。" />

      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="title" label="线索标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="customer_name" label="客户" width="140" show-overflow-tooltip />
        <el-table-column label="地区" width="110">
          <template #default="{ row }">{{ row.province }}{{ row.city }}</template>
        </el-table-column>
        <el-table-column label="预算(万)" width="90">
          <template #default="{ row }">{{ row.budget ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="阶段" width="100">
          <template #default="{ row }"><el-tag size="small">{{ row.stage || '-' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="channel" label="渠道" width="110" />
        <el-table-column label="评分" width="90">
          <template #default="{ row }">
            <el-progress :percentage="row.score" :stroke-width="12" :color="row.score >= 80 ? '#67c23a' : row.score >= 50 ? '#e6a23c' : '#909399'" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'won' ? 'success' : row.status === 'lost' ? 'info' : 'primary'" size="small">
              {{ statusText[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reporter_name" label="上报人" width="90" />
        <el-table-column label="操作" width="140" fixed="right">
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

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑线索' : '上报线索'" width="600px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="线索标题" required><el-input v-model="dialog.form.title" placeholder="如：滨湖新区智慧社区试点项目" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="客户名称"><el-input v-model="dialog.form.customer_name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预算(万)">
              <el-input-number v-model="dialog.form.budget" :min="0" style="width: 100%" />
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
            <el-form-item label="阶段">
              <el-select v-model="dialog.form.stage" style="width: 100%">
                <el-option v-for="s in ['初步接触', '需求确认', '方案报价', '投标', '合同谈判', '已成交', '已流失']" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="渠道">
              <el-select v-model="dialog.form.channel" style="width: 100%">
                <el-option v-for="c in ['全网招标', '采购意向', '改造计划', '立项审批', '土地出让', '竞品中标', '销售报备', '展会', '行业活动', '电话营销', '老客户转介绍', '其他']" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="上报人"><el-input v-model="dialog.form.reporter_name" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="dialog.form.status" style="width: 100%">
                <el-option v-for="s in ['new', 'following', 'won', 'lost']" :key="s" :label="statusText[s]" :value="s" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="需求详情"><el-input v-model="dialog.form.detail" type="textarea" :rows="3" placeholder="描述客户需求、涉及产品、关键决策人等" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存并评分</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listSalesLeads, createSalesLead, updateSalesLead, deleteSalesLead } from '@/api/intel'

const statusText = { new: '新线索', following: '跟进中', won: '已成交', lost: '已流失' }
const items = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ keyword: '', status: '', page: 1, page_size: 20 })
const dialog = reactive({ visible: false, form: {} })

const emptyForm = () => ({
  id: null, title: '', customer_name: '', province: '', city: '', budget: null,
  stage: '初步接触', channel: '销售报备', reporter_name: '', detail: '', status: 'new',
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await listSalesLeads(query)
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
  if (!dialog.form.title) {
    ElMessage.warning('请填写线索标题')
    return
  }
  if (dialog.form.id) {
    await updateSalesLead(dialog.form.id, dialog.form)
    ElMessage.success('已更新并重新评分')
  } else {
    await createSalesLead(dialog.form)
    ElMessage.success('已上报并入池')
  }
  dialog.visible = false
  loadData()
}

const remove = (row) => {
  ElMessageBox.confirm(`确认删除「${row.title}」？`, '提示', { type: 'warning' }).then(async () => {
    await deleteSalesLead(row.id)
    ElMessage.success('已删除')
    loadData()
  })
}

onMounted(loadData)
</script>
