<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <span class="logo-icon">🎯</span>
        <span class="logo-text">AI商机挖掘系统</span>
      </div>
      <el-menu :default-active="activeMenu" router background-color="#001529" text-color="#a6adb4" active-text-color="#fff" class="menu">
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon><span>驾驶舱</span></el-menu-item>
        <el-menu-item index="/opportunities"><el-icon><Tickets /></el-icon><span>商机列表</span></el-menu-item>
        <el-menu-item index="/map"><el-icon><Location /></el-icon><span>项目地图</span></el-menu-item>
        <el-menu-item index="/kanban"><el-icon><Postcard /></el-icon><span>跟进看板</span></el-menu-item>
        <el-menu-item index="/reports"><el-icon><DataAnalysis /></el-icon><span>报表中心</span></el-menu-item>
        <el-sub-menu index="intel">
          <template #title><el-icon><TrendCharts /></el-icon><span>智能商机挖掘</span></template>
          <el-menu-item index="/intel/legacy-projects">存量项目台账</el-menu-item>
          <el-menu-item index="/intel/update-opportunities">更新商机</el-menu-item>
          <el-menu-item index="/intel/strategic-customers">战略客户集采</el-menu-item>
          <el-menu-item index="/intel/sales-leads">销售线索</el-menu-item>
          <el-menu-item index="/intel/competitor-tracks">竞品追踪</el-menu-item>
          <el-menu-item index="/intel/appeal-hotspots">诉求热点</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="collect">
          <template #title><el-icon><Collection /></el-icon><span>数据与采集</span></template>
          <el-menu-item index="/announcements">公告管理</el-menu-item>
          <el-menu-item index="/data-sources">数据源管理</el-menu-item>
          <el-menu-item index="/knowledge">知识库</el-menu-item>
          <el-menu-item index="/knowledge/policies">政策信息库</el-menu-item>
          <el-menu-item index="/competitors">竞品监测</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="system">
          <template #title><el-icon><Setting /></el-icon><span>系统管理</span></template>
          <el-menu-item index="/system/users">用户管理</el-menu-item>
          <el-menu-item index="/system/roles">角色管理</el-menu-item>
          <el-menu-item index="/system/configs">系统配置</el-menu-item>
          <el-menu-item index="/system/audit">审计日志</el-menu-item>
          <el-menu-item index="/system/push">消息推送</el-menu-item>
          <el-menu-item index="/system/offices">办事处覆盖</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="$route.meta.title">{{ $route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag v-if="auth.user?.role_name" type="info" size="small" effect="plain">{{ auth.user.role_name }}</el-tag>
          <el-dropdown @command="handleCommand">
            <span class="user-name">
              <el-icon><UserFilled /></el-icon>
              {{ auth.user?.real_name || auth.user?.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => route.path)

const handleCommand = async (command) => {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  background: #001529;
  overflow-x: hidden;
}
.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.logo-icon {
  font-size: 22px;
}
.menu {
  border-right: none;
}
.menu :deep(.el-menu-item.is-active) {
  background: #1677ff;
}
.menu :deep(.el-menu-item:hover) {
  background: #0c1f38;
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 1;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-name {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #303133;
}
.main {
  background: #f0f2f5;
  padding: 0;
  overflow-y: auto;
}
</style>
