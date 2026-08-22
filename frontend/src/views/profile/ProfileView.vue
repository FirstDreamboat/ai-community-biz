<template>
  <div class="page-container">
    <el-card style="max-width: 640px">
      <div class="card-title">个人中心</div>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="账号">{{ auth.user?.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ auth.user?.real_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ auth.user?.role_name || (auth.user?.roles || []).join(', ') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="部门/办事处">{{ auth.user?.dept || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>修改密码</el-divider>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" style="max-width: 420px">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">保存修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'

const auth = useAuthStore()
const formRef = ref()
const submitting = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm_password: '' })

const validateConfirm = (rule, value, callback) => {
  if (value !== form.new_password) callback(new Error('两次输入的新密码不一致'))
  else callback()
}

const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 100, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

const handleSubmit = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    await changePassword({
      old_password: form.old_password,
      new_password: form.new_password,
    })
    ElMessage.success('密码修改成功，请重新登录')
    form.old_password = ''
    form.new_password = ''
    form.confirm_password = ''
    auth.logout()
  } finally {
    submitting.value = false
  }
}
</script>
