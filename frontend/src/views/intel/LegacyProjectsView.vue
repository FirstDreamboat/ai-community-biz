<template>
  <div class="page">
    <el-card shadow="never">
      <div class="page-head">
        <div class="title">存量项目台账</div>
        <div class="actions">
          <el-input v-model="query.keyword" placeholder="项目/小区/单位" clearable style="width: 200px"
                    @keyup.enter="loadData" @clear="loadData" />
          <el-select v-model="query.province" placeholder="省份" clearable style="width: 120px" @change="loadData">
            <el-option v-for="p in provinces" :key="p" :label="p" :value="p" />
          </el-select>
          <el-button type="primary" @click="loadData">查询</el-button>
          <el-button type="success" @click="openDialog()">新增项目</el-button>
        </div>
      </div>

      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="community" label="小区/社区" width="120" show-overflow-tooltip />
        <el-table-column label="地区" width="120">
          <template #default="{ row }">{{ row.province }}{{ row.city }}</template>
        </el-table-column>
        <el-table-column prop="unit" label="管理单位" width="160" show-overflow-tooltip />
        <el-table-column label="子系统" width="160">
          <template #default="{ row }">
            <el-tag v-for="s in (row.systems || []).slice(0, 3)" :key="s" size="small" style="margin-right: 4px">{{ s }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="device_brand" label="在用品牌" width="90" />
        <el-table-column prop="install_year" label="安装年份" width="90" />
        <el-table-column label="服役年限" width="90">
          <template #default="{ row }">
            <el-tag :type="row.age_years >= 10 ? 'danger' : row.age_years >= 8 ? 'warning' : row.age_years >= 6 ? 'primary' : 'info'" size="small">
              {{ row.age_years }} 年
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新窗口" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.window_status === 'overdue'" type="danger" size="small">已超期</el-tag>
            <el-tag v-else-if="row.window_status === 'due'" type="warning" size="small">换新窗口</el-tag>
            <el-tag v-else-if="row.window_status === 'imminent'" size="small">临期</el-tag>
            <el-tag v-else type="info" size="small">服役期</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预估预算(万)" width="100">
          <template #default="{ row }">{{ row.est_budget ?? '-' }}</template>
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

    <el-dialog v-model="dialog.visible" :title="dialog.form.id ? '编辑存量项目' : '新增存量项目'" width="620px">
      <el-form :model="dialog.form" label-width="90px">
        <el-form-item label="项目名称" required>
          <el-input v-model="dialog.form.project_name" placeholder="如：幸福里小区智能化改造一期" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="小区/社区"><el-input v-model="dialog.form.community" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="管理单位"><el-input v-model="dialog.form.unit" /></el-form-item>
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
            <el-form-item label="安装年份" required>
              <el-input-number v-model="dialog.form.install_year" :min="2000" :max="2030" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预估预算(万)">
              <el-input-number v-model="dialog.form.est_budget" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="在用品牌"><el-input v-model="dialog.form.device_brand" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系人"><el-input v-model="dialog.form.contact" /></el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="子系统">
          <el-select v-model="dialog.form.systems" multiple filterable allow-create style="width: 100%"
                     placeholder="楼宇对讲 / 门禁 / 视频监控 / 智能家居 ...">
            <el-option v-for="s in ['楼宇对讲', '可视对讲', '门禁', '视频监控', '停车场', '智能家居', '医护对讲', '综合布线']" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="dialog.form.note" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listLegacyProjects, createLegacyProject, updateLegacyProject, deleteLegacyProject } from '@/api/intel'

const provinces = ['安徽', '江苏', '山东', '广东', '福建', '浙江', '河南', '湖北', '湖南', '四川', '陕西', '北京', '上海', '天津', '重庆']
const items = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ keyword: '', province: '', page: 1, page_size: 20 })
const dialog = reactive({ visible: false, saving: false, form: {} })

const emptyForm = () => ({
  id: null, project_name: '', community: '', province: '', city: '', unit: '',
  systems: [], device_brand: '', install_year: new Date().getFullYear() - 5,
  est_budget: null, contact: '', note: '', status: 0,
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await listLegacyProjects(query)
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
  if (!dialog.form.project_name || !dialog.form.install_year) {
    ElMessage.warning('请填写项目名称和安装年份')
    return
  }
  dialog.saving = true
  try {
    if (dialog.form.id) {
      await updateLegacyProject(dialog.form.id, dialog.form)
      ElMessage.success('已更新')
    } else {
      await createLegacyProject(dialog.form)
      ElMessage.success('已新增，可在「更新商机」中一键推算')
    }
    dialog.visible = false
    loadData()
  } finally {
    dialog.saving = false
  }
}

const remove = (row) => {
  ElMessageBox.confirm(`确认删除「${row.project_name}」？`, '提示', { type: 'warning' }).then(async () => {
    await deleteLegacyProject(row.id)
    ElMessage.success('已删除')
    loadData()
  })
}

onMounted(loadData)
</script>
