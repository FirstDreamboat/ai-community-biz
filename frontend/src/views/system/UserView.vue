<template>
  <div class="page-container">
    <el-card>
      <div class="flex-between" style="margin-bottom: 12px">
        <span class="card-title">用户管理</span>
        <el-button type="primary" @click="openDialog()"><el-icon><Plus /></el-icon>新增用户</el-button>
      </div>
      <el-table v-loading="loading" :data="items" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="账号" width="140" />
        <el-table-column prop="real_name" label="姓名" width="120">
          <template #default="{ row }">{{ row.real_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="dept" label="部门/办事处" width="160">
          <template #default="{ row }">{{ row.dept || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="150">
          <template #default="{ row }">
            <el-tag v-for="code in row.roles || []" :key="code" size="small" style="margin-right: 4px">{{ code }}</el-tag>
            <span v-if="!(row.roles || []).length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" width="160">
          <template #default="{ row }">{{ fmt(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" :disabled="row.username === 'admin'" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '新增用户'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" :disabled="editing" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="密码" :prop="editing ? '' : 'password'">
          <el-input v-model="form.password" type="password" show-password :placeholder="editing ? '留空则不修改' : '至少 6 位'" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="办事处">
          <el-input v-model="form.dept" />
        </el-form-item>
        <el-form-item label="角色" v-if="!editing">
          <el-select v-model="form.role_codes" multiple placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.role_code" :label="r.role_name" :value="r.role_code" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" v-else>
          <el-select v-model="form.role_codes" multiple placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.role_code" :label="r.role_name" :value="r.role_code" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" v-if="editing">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">{{ editing ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, createUser, updateUser, deleteUser, listRoles } from '@/api/system'

const loading = ref(false)
const items = ref([])
const roles = ref([])
const dialogVisible = ref(false)
const submitting = ref(false)
const editing = ref(false)
const formRef = ref()

const form = reactive({ id: null, username: '', password: '', real_name: '', dept: '', role_codes: [], status: 1 })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

const fmt = (t) => (t ? String(t).replace('T', ' ').slice(0, 16) : '-')

const loadData = async () => {
  loading.value = true
  try {
    const res = await listUsers()
    items.value = res.data || []
  } finally {
    loading.value = false
  }
}

const openDialog = (row) => {
  if (row) {
    editing.value = true
    Object.assign(form, {
      id: row.id, username: row.username, password: '', real_name: row.real_name || '',
      dept: row.dept || '', role_codes: [...(row.roles || [])], status: row.status ?? 1,
    })
  } else {
    editing.value = false
    Object.assign(form, { id: null, username: '', password: '', real_name: '', dept: '', role_codes: [], status: 1 })
  }
  dialogVisible.value = true
}

const submit = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (editing.value) {
      await updateUser(form.id, {
        real_name: form.real_name, dept: form.dept, status: form.status,
        password: form.password || undefined, role_codes: form.role_codes,
      })
      ElMessage.success('用户已更新')
    } else {
      await createUser(form)
      ElMessage.success('用户已创建')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

const remove = async (row) => {
  await ElMessageBox.confirm(`确认删除用户「${row.username}」？`, '删除', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('已删除')
  loadData()
}

onMounted(() => {
  loadData()
  listRoles().then((r) => { roles.value = r.data || [] }).catch(() => {})
})
</script>
