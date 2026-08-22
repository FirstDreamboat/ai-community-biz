<template>
  <div class="page-container" v-loading="loading">
    <el-page-header @back="$router.back()" style="margin-bottom: 16px">
      <template #content>
        <span class="page-title">{{ detail.opportunity?.title || '商机详情' }}</span>
        <el-tag v-if="detail.opportunity" :type="levelTag(detail.opportunity.level)" size="small" style="margin-left: 12px">
          {{ levelName(detail.opportunity.level) }} · {{ detail.opportunity.total_score }}分
        </el-tag>
      </template>
      <template #extra>
        <el-button type="primary" @click="openFollow">新增跟进</el-button>
        <el-button v-if="auth.isAdmin" @click="openAssign">分配商机</el-button>
      </template>
    </el-page-header>

    <el-row :gutter="16">
      <el-col :span="15">
        <!-- 项目画像 -->
        <el-card>
          <div class="card-title">项目信息</div>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="招标方">{{ profile.purchaser || '-' }}</el-descriptions-item>
            <el-descriptions-item label="预算金额">{{ profile.budget ? profile.budget + ' 万元' : '-' }}</el-descriptions-item>
            <el-descriptions-item label="省份/城市">{{ profile.province || '-' }}{{ profile.city ? ' / ' + profile.city : '' }}</el-descriptions-item>
            <el-descriptions-item label="项目阶段">{{ profile.stage || '-' }}</el-descriptions-item>
            <el-descriptions-item label="投标截止">{{ fmtTime(profile.bid_deadline) }}</el-descriptions-item>
            <el-descriptions-item label="开标时间">{{ fmtTime(profile.open_time) }}</el-descriptions-item>
            <el-descriptions-item label="涉及户数">{{ profile.household_cnt ?? '-' }} 户</el-descriptions-item>
            <el-descriptions-item label="楼栋数">{{ profile.building_cnt ?? '-' }}</el-descriptions-item>
            <el-descriptions-item label="建筑面积">{{ profile.area_m2 ?? '-' }} m²</el-descriptions-item>
            <el-descriptions-item label="资金来源">{{ profile.fund_source || '-' }}</el-descriptions-item>
            <el-descriptions-item label="资质要求" :span="2">{{ (profile.qualification || []).join('；') || '-' }}</el-descriptions-item>
            <el-descriptions-item label="改造内容" :span="2">
              <el-tag v-for="t in profile.contents" :key="t" size="small" style="margin-right: 6px">{{ t }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 评分明细 -->
        <el-card style="margin-top: 16px">
          <div class="card-title flex-between">
            <span>评分明细</span>
            <span class="text-secondary">规则版本：{{ detail.score_detail?.rules_version || '-' }}</span>
          </div>
          <el-row :gutter="16">
            <el-col :span="14">
              <EChart :option="scoreBarOption" height="260px" />
            </el-col>
            <el-col :span="10">
              <div class="score-total">
                <div class="score-total-num" :class="scoreClass(detail.score_detail?.total)">{{ detail.score_detail?.total }}</div>
                <div class="text-secondary">综合评分</div>
              </div>
              <div class="strategy-box">
                <div class="strategy-title">跟进策略</div>
                <ul class="strategy-list">
                  <li v-for="(a, i) in (detail.strategy?.actions || [])" :key="i">{{ a }}</li>
                  <li v-if="!(detail.strategy?.actions || []).length">暂无策略建议</li>
                </ul>
              </div>
            </el-col>
          </el-row>
          <div v-if="detail.opportunity?.recommend_reason" class="reason-box">
            <b>推荐理由：</b>{{ detail.opportunity.recommend_reason }}
          </div>
        </el-card>

        <!-- 公告原文 -->
      <el-card v-if="announcement" style="margin-top: 16px">
        <div class="card-title" style="display: flex; align-items: center; justify-content: space-between">
          <span>公告原文</span>
          <el-button
            v-if="announcement.source_url"
            type="primary"
            size="small"
            @click="openSource"
          >
            <el-icon style="margin-right: 4px"><View /></el-icon>查看原文
          </el-button>
          <el-tag v-else size="small" type="info">无原文链接</el-tag>
        </div>
          <el-collapse>
            <el-collapse-item :title="announcement.title" name="1">
              <pre class="ann-content">{{ announcement.content }}</pre>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>

      <el-col :span="9">
        <!-- 跟进记录 -->
        <el-card>
          <div class="card-title">跟进记录</div>
          <el-timeline v-if="(followLogs || []).length">
            <el-timeline-item
              v-for="log in followLogs"
              :key="log.id"
              :timestamp="fmtTime(log.follow_time)"
              :type="timelineType(log.action)"
            >
              <div class="log-action">{{ log.action }} <el-tag size="small" effect="plain">{{ statusNames[log.to_status] || log.to_status }}</el-tag></div>
              <div class="log-note">{{ log.note || '' }}</div>
              <div v-if="log.next_plan" class="log-next text-secondary">下一步：{{ log.next_plan }}</div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无跟进记录" :image-size="60" />
        </el-card>

        <!-- 竞品动态 -->
        <el-card style="margin-top: 16px">
          <div class="card-title">竞品动态</div>
          <el-table v-if="(competitors || []).length" :data="competitors" size="small">
            <el-table-column prop="competitor" label="竞品" width="90" />
            <el-table-column prop="result" label="结果" width="70" />
            <el-table-column prop="win_date" label="日期" width="100">
              <template #default="{ row }">{{ (row.win_date || '').slice(0, 10) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无竞品动态" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 新增跟进对话框 -->
    <el-dialog v-model="followVisible" title="新增跟进" width="480px">
      <el-form ref="followFormRef" :model="followForm" :rules="followRules" label-width="90px">
        <el-form-item label="跟进动作" prop="action">
          <el-select v-model="followForm.action" style="width: 100%">
            <el-option v-for="a in actions" :key="a" :label="a" :value="a" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标状态" prop="to_status">
          <el-select v-model="followForm.to_status" style="width: 100%">
            <el-option v-for="(v, k) in statusNames" :key="k" :label="v" :value="k" />
          </el-select>
        </el-form-item>
        <el-form-item label="跟进说明" prop="note">
          <el-input v-model="followForm.note" type="textarea" :rows="3" placeholder="记录本次沟通内容" />
        </el-form-item>
        <el-form-item label="下一步计划">
          <el-input v-model="followForm.next_plan" placeholder="下一步计划" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="followVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitFollow">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分配商机对话框 -->
    <el-dialog v-model="assignVisible" title="分配商机" width="400px">
      <el-form label-width="90px">
        <el-form-item label="负责人">
          <el-select v-model="assignForm.owner_id" style="width: 100%">
            <el-option v-for="u in userList" :key="u.id" :label="`${u.real_name || u.username} (${u.username})`" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitAssign">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import EChart from '@/components/EChart.vue'
import { getOpportunity, followUp, assignOpportunity } from '@/api/opportunity'
import { getAnnouncement } from '@/api/announcement'
import { listUsers } from '@/api/system'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const detail = ref({})
const announcement = ref(null)
const followLogs = ref([])
const competitors = ref([])

const followVisible = ref(false)
const assignVisible = ref(false)
const submitting = ref(false)
const followFormRef = ref()
const userList = ref([])

const statusNames = { new: '新建', following: '跟进中', bid: '已投标', won: '已中标', lost: '已丢标', closed: '已关闭' }
const actions = ['电话沟通', '上门拜访', '邮件沟通', '提交投标', '已中标', '已丢标', '其他']

const profile = computed(() => detail.value.profile || {})
const followForm = ref({ action: '电话沟通', to_status: 'following', note: '', next_plan: '' })
const followRules = {
  action: [{ required: true, message: '请选择跟进动作', trigger: 'change' }],
  to_status: [{ required: true, message: '请选择目标状态', trigger: 'change' }],
}
const assignForm = ref({ owner_id: null })

const fmtTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 16) : '-')
const levelName = (l) => ({ high: '高', medium: '中', low: '低' }[l] || l)
const levelTag = (l) => ({ high: 'danger', medium: 'warning', low: 'success' }[l] || 'info')
const scoreClass = (s) => (s >= 80 ? 'score-high' : s >= 60 ? 'score-medium' : 'score-low')
const timelineType = (a) => (a.includes('中标') ? 'success' : a.includes('丢标') ? 'danger' : 'primary')

const scoreBarOption = computed(() => {
  const s = detail.value.score_detail || {}
  const dims = [
    { key: 'demand', name: '需求匹配' },
    { key: 'budget', name: '预算规模' },
    { key: 'region', name: '区域价值' },
    { key: 'urgency', name: '紧迫度' },
    { key: 'competition', name: '竞争度' },
  ]
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 10, right: 10, top: 20, bottom: 10, containLabel: true },
    xAxis: { type: 'value', max: 40 },
    yAxis: { type: 'category', data: dims.map((d) => d.name) },
    series: [
      {
        type: 'bar',
        data: dims.map((d) => ({ value: s[d.key] ?? 0, itemStyle: { color: s[d.key] >= 30 ? '#f56c6c' : s[d.key] >= 15 ? '#fa8c16' : '#52c41a', borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right' },
        barWidth: 20,
      },
    ],
  }
})

const loadDetail = async () => {
  loading.value = true
  try {
    const id = route.params.id
    const res = await getOpportunity(id)
    detail.value = res.data || {}
    followLogs.value = detail.value.follow_logs || []
    competitors.value = detail.value.competitors || []
    if (detail.value.opportunity?.announcement_id) {
      getAnnouncement(detail.value.opportunity.announcement_id)
        .then((r) => { announcement.value = r.data || null })
        .catch(() => {})
    }
  } finally {
    loading.value = false
  }
}

const openSource = () => {
  if (announcement.value && announcement.value.source_url) {
    window.open(announcement.value.source_url, '_blank', 'noopener')
  }
}

const openFollow = () => {
  followForm.value = { action: '电话沟通', to_status: 'following', note: '', next_plan: '' }
  followVisible.value = true
}

const submitFollow = async () => {
  await followFormRef.value.validate()
  submitting.value = true
  try {
    await followUp(route.params.id, followForm.value)
    ElMessage.success('跟进记录已保存')
    followVisible.value = false
    loadDetail()
  } finally {
    submitting.value = false
  }
}

const openAssign = async () => {
  try {
    const res = await listUsers({ page_size: 100 })
    userList.value = res.data?.items || res.data || []
  } catch (e) {
    userList.value = []
  }
  assignForm.value = { owner_id: null }
  assignVisible.value = true
}

const submitAssign = async () => {
  if (!assignForm.value.owner_id) {
    ElMessage.warning('请选择负责人')
    return
  }
  submitting.value = true
  try {
    await assignOpportunity(route.params.id, { owner_id: assignForm.value.owner_id })
    ElMessage.success('分配成功')
    assignVisible.value = false
  } finally {
    submitting.value = false
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.page-title {
  font-size: 16px;
  font-weight: 600;
}
.score-total {
  text-align: center;
  padding: 16px 0 8px;
}
.score-total-num {
  font-size: 42px;
  font-weight: 800;
  line-height: 1.2;
}
.strategy-box {
  margin-top: 12px;
  background: #f6f9ff;
  border-radius: 8px;
  padding: 12px;
}
.strategy-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #1677ff;
}
.strategy-list {
  padding-left: 18px;
  line-height: 1.9;
  font-size: 13px;
}
.reason-box {
  margin-top: 12px;
  padding: 10px 12px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.7;
}
.log-action {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.log-note {
  margin-top: 4px;
  font-size: 13px;
  color: #606266;
}
.log-next {
  margin-top: 2px;
  font-size: 12px;
}
.ann-content {
  white-space: pre-wrap;
  word-break: break-all;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.8;
  color: #606266;
}
</style>
