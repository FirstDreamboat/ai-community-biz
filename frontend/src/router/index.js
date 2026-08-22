import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/DashboardView.vue'), meta: { title: '驾驶舱' } },
      { path: 'opportunities', name: 'Opportunities', component: () => import('@/views/opportunity/OpportunityListView.vue'), meta: { title: '商机列表' } },
      { path: 'opportunities/:id', name: 'OpportunityDetail', component: () => import('@/views/opportunity/OpportunityDetailView.vue'), meta: { title: '商机详情' } },
      { path: 'map', name: 'Map', component: () => import('@/views/map/ProjectMapView.vue'), meta: { title: '项目地图' } },
      { path: 'kanban', name: 'Kanban', component: () => import('@/views/kanban/KanbanView.vue'), meta: { title: '跟进看板' } },
      { path: 'reports', name: 'Reports', component: () => import('@/views/reports/ReportsView.vue'), meta: { title: '报表中心' } },
      { path: 'announcements', name: 'Announcements', component: () => import('@/views/announcement/AnnouncementListView.vue'), meta: { title: '公告管理' } },
      { path: 'data-sources', name: 'DataSources', component: () => import('@/views/datasource/DataSourceView.vue'), meta: { title: '数据源管理' } },
      { path: 'knowledge', name: 'Knowledge', component: () => import('@/views/knowledge/KnowledgeView.vue'), meta: { title: '知识库' } },
      { path: 'competitors', name: 'Competitors', component: () => import('@/views/competitor/CompetitorView.vue'), meta: { title: '竞品监测' } },
      { path: 'intel/legacy-projects', name: 'LegacyProjects', component: () => import('@/views/intel/LegacyProjectsView.vue'), meta: { title: '存量项目台账' } },
      { path: 'intel/update-opportunities', name: 'UpdateOpportunities', component: () => import('@/views/intel/UpdateOpportunitiesView.vue'), meta: { title: '更新商机' } },
      { path: 'intel/strategic-customers', name: 'StrategicCustomers', component: () => import('@/views/intel/StrategicCustomersView.vue'), meta: { title: '战略客户集采' } },
      { path: 'intel/sales-leads', name: 'SalesLeads', component: () => import('@/views/intel/SalesLeadsView.vue'), meta: { title: '销售线索' } },
      { path: 'intel/competitor-tracks', name: 'CompetitorTracks', component: () => import('@/views/intel/CompetitorTracksView.vue'), meta: { title: '竞品追踪' } },
      { path: 'intel/appeal-hotspots', name: 'AppealHotspots', component: () => import('@/views/intel/AppealHotspotsView.vue'), meta: { title: '诉求热点' } },
      { path: 'system/users', name: 'Users', component: () => import('@/views/system/UserView.vue'), meta: { title: '用户管理' } },
      { path: 'system/roles', name: 'Roles', component: () => import('@/views/system/RoleView.vue'), meta: { title: '角色管理' } },
      { path: 'system/configs', name: 'Configs', component: () => import('@/views/system/ConfigView.vue'), meta: { title: '系统配置' } },
      { path: 'system/audit', name: 'Audit', component: () => import('@/views/system/AuditView.vue'), meta: { title: '审计日志' } },
      { path: 'system/push', name: 'Push', component: () => import('@/views/system/PushView.vue'), meta: { title: '消息推送' } },
      { path: 'system/offices', name: 'Offices', component: () => import('@/views/system/OfficeView.vue'), meta: { title: '办事处覆盖' } },
      { path: 'knowledge/policies', name: 'Policy', component: () => import('@/views/knowledge/PolicyView.vue'), meta: { title: '政策信息库' } },
      { path: 'profile', name: 'Profile', component: () => import('@/views/profile/ProfileView.vue'), meta: { title: '个人中心' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/dashboard'
  }
  document.title = `${to.meta.title || ''} - AI商机挖掘系统`
  return true
})

export default router
