<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-head">
        <div class="title">战略客户集采台账</div>
        <div class="actions">
          <el-switch v-model="query.warning_only" active-text="仅看到期预警" style="margin-right: 12px" @change="loadData" />
          <el-input v-model="query.keyword" placeholder="客户名/合作类型" clearable style="width: 200px"
                    @keyup.enter="loadData" @clear="loadData" />
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button type="success" @click="openDialog()">新增客户</el-button>
        </div>
      </div>

      <el-alert type="warning" :closable="false" style="margin-bottom: 12px"
                title="集采到期预警：距到期 ≤ 1 年自动预警，需提前 6 个月启动续约谈判；到期超 1 年未动作标记流失。" />

      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="customer_name" label="客户名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="coop_type" label="合作类型" width="90" />
        <el-table-column label="产品线" width="150">
          <template #default="{ row }">
            <el-tag v-for="p in (row.product_lines || []).slice(0, 2)" :key="p" size="small" style="margin-right: 4px">{{ p }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contract_year" label="签约年" width="80" />
        <el-table-column prop="contract_end_year" label="到期年" width="80" />
        <el-table-column label="预警" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.warning_level === 2" type="danger" size="small">已流失</el-tag>
            <el-tag v-else-if="row.warning_level === 1" type="warning" size="small">即将到期</el-tag>
            <el-tag v-else type="success" size="small">正常</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="年金额(万)" width="100">
          <template #default="{ row }">{{ row.annual_amount ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="contact" label="联系人" width="140" show-overflow-tooltip />
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

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑战略客户' : '新增战略客户'" width="560px">
      <el-form :model="dialog.form" label-width="100px">
        <el-form-item label="客户名称" required><el-input v-model="dialog.form.customer_name" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="合作类型">
              <el-select v-model="dialog.form.coop_type" style="width: 100%">
                <el-option label="集采" value="集采" />
                <el-option label="战略" value="战略" />
                <el-option label="区域代理" value="区域代理" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="年金额(万)">
              <el-input-number v-model="dialog.form.annual_amount" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="签约年份">
              <el-input-number v-model="dialog.form.contract_year" :min="2010" :max="2035" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="到期年份" required>
              <el-input-number v-model="dialog.form.contract_end_year" :min="2010" :max="2040" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="产品线">
          <el-select v-model="dialog.form.product_lines" multiple filterable allow-create style="width: 100%">
            <el-option v-for="p in ['楼宇对讲', '可视对讲', '智能家居', '医护对讲', '门禁', '智慧停车']" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系人"><el-input v-model="dialog.form.contact" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="dialog.form.note" type="textarea" :rows="2" /></el-form-item>
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
import { listStrategicCustomers, createStrategicCustomer, updateStrategicCustomer, deleteStrategicCustomer } from '@/api/intel'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ keyword: '', warning_only: false, page: 1, page_size: 20 })
const dialog = reactive({ visible: false, form: {} })

const emptyForm = () => ({
  id: null, customer_name: '', coop_type: '集采', product_lines: [],
  contract_year: new Date().getFullYear() - 2, contract_end_year: new Date().getFullYear() + 2,
  annual_amount: null, contact: '', note: '',
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await listStrategicCustomers(query)
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
  if (!dialog.form.customer_name || !dialog.form.contract_end_year) {
    ElMessage.warning('请填写客户名称和到期年份')
    return
  }
  if (dialog.form.id) {
    await updateStrategicCustomer(dialog.form.id, dialog.form)
    ElMessage.success('已更新')
  } else {
    await createStrategicCustomer(dialog.form)
    ElMessage.success('已新增')
  }
  dialog.visible = false
  loadData()
}

const remove = (row) => {
  ElMessageBox.confirm(`确认删除「${row.customer_name}」？`, '提示', { type: 'warning' }).then(async () => {
    await deleteStrategicCustomer(row.id)
    ElMessage.success('已删除')
    loadData()
  })
}

onMounted(loadData)
</script>
