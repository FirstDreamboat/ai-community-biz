<template>
  <div class="page-container">
    <el-card>
      <div class="card-header">
        <div class="card-title">角色管理</div>
        <el-button type="primary" @click="openDialog()">新增角色</el-button>
      </div>

      <el-table :data="roles" v-loading="loading" border stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="role_name" label="角色名称" min-width="120" />
        <el-table-column prop="role_code" label="角色编码" min-width="120" />
        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column label="权限数" width="90">
          <template #default="{ row }">{{ (row.perm_codes || []).length }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.role_code !== 'admin'" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button v-if="row.role_code !== 'admin'" size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            <el-tag v-else size="small" type="info">内置</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑角色' : '新增角色'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="角色名称" prop="role_name">
          <el-input v-model="form.role_name" placeholder="如：区域经理" />
        </el-form-item>
        <el-form-item label="角色编码" prop="role_code" v-if="!form.id">
          <el-input v-model="form.role_code" placeholder="如：region_manager" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="权限分配">
          <div class="perm-box">
            <el-checkbox
              v-for="perm in permissions"
              :key="perm.perm_code"
              :label="perm.perm_code"
              v-model="form.perm_codes"
              border
            >{{ perm.perm_name }}（{{ perm.perm_code }}）</el-checkbox>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listRoles, createRole, updateRole, deleteRole, listPermissions } from '@/api/system'

const loading = ref(false)
const submitting = ref(false)
const roles = ref([])
const permissions = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({ id: null, role_name: '', role_code: '', remark: '', perm_codes: [] })

const rules = {
  role_name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  role_code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }],
}

const loadRoles = async () => {
  loading.value = true
  try {
    const res = await listRoles()
    roles.value = res.data || []
  } finally {
    loading.value = false
  }
}

const loadPermissions = async () => {
  const res = await listPermissions()
  permissions.value = res.data || []
}

const openDialog = (row) => {
  if (row) {
    Object.assign(form, { id: row.id, role_name: row.role_name, role_code: row.role_code, remark: row.remark, perm_codes: [...(row.perm_codes || [])] })
  } else {
    Object.assign(form, { id: null, role_name: '', role_code: '', remark: '', perm_codes: [] })
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (form.id) {
      await updateRole(form.id, { role_name: form.role_name, remark: form.remark, perm_codes: form.perm_codes })
      ElMessage.success('角色已更新')
    } else {
      await createRole({ role_name: form.role_name, role_code: form.role_code, remark: form.remark, perm_codes: form.perm_codes })
      ElMessage.success('角色已创建')
    }
    dialogVisible.value = false
    loadRoles()
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  await ElMessageBox.confirm(`确认删除角色「${row.role_name}」？`, '提示', { type: 'warning' })
  await deleteRole(row.id)
  ElMessage.success('已删除')
  loadRoles()
}

onMounted(() => {
  loadRoles()
  loadPermissions()
})
</script>

<style scoped>
.perm-box {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
