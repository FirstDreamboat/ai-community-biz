<template>
  <div class="page-container">
    <el-card class="filter-card">
      <div class="flex-between">
        <div>
          <el-tag type="primary" effect="plain" size="large">
            当前层级：{{ levelText }} {{ currentRegion ? `（${currentRegion}）` : '' }}
          </el-tag>
          <el-tag v-if="level === 'district' && currentRegion" type="info" effect="plain" size="large" style="margin-left: 8px">
            {{ currentCityName }}
          </el-tag>
        </div>
        <div>
          <el-button size="small" :disabled="!history.length" @click="drillUp">返回上一级</el-button>
          <el-button size="small" @click="loadData">刷新</el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="18">
        <el-card>
          <div class="card-title">项目分布热力图（点击区域下钻）</div>
          <div ref="mapEl" style="width: 100%; height: 640px"></div>
          <div class="map-tip">
            提示：点击省份可下钻查看市级分布，点击城市可下钻查看区县级分布；直辖市点击后直接进入区县级。
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="card-title">{{ tableTitle }}</div>
          <el-table :data="tableData" size="small" max-height="580">
            <el-table-column prop="region" label="区域" />
            <el-table-column prop="count" label="项目数" width="80" align="right" sortable />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import chinaGeo from '@/assets/geo/china.json'
import { getHeatmap } from '@/api/dashboard'

const mapEl = ref()
let chart = null

const level = ref('province')
const currentRegion = ref('')          // 当前层级下的选中区域名
const currentCityName = ref('')        // 区县级时显示的城市名
const currentCityAdcode = ref('')      // 区县级使用的市级地图 adcode
const tableData = ref([])
const history = ref([])                // 下钻历史（用于返回）

const levelText = { province: '省级', city: '市级', district: '区县级' }
const MUNICIPAL = new Set(['北京市', '天津市', '上海市', '重庆市'])

// 省名 -> 省级 adcode（从全国地图提取）
const provinceAdcodeMap = {}
chinaGeo.features.forEach((f) => {
  const p = f.properties
  if (p && p.name && p.adcode) provinceAdcodeMap[p.name] = p.adcode
})

// 城市名 -> 市级 adcode（懒加载，从省级地图提取）
const cityAdcodeMap = ref({})

// 批量导入省级 / 市级地图 JSON（vite glob，key 形如 /src/assets/geo/province/340000.json）
const provinceMaps = import.meta.glob('/src/assets/geo/province/*.json')
const cityMaps = import.meta.glob('/src/assets/geo/city/*.json')

const registered = new Set()

const tableTitle = computed(() => {
  if (level.value === 'province') return '全国项目 Top10'
  if (level.value === 'city') return `${currentRegion.value} 各市项目`
  return `${currentCityName.value || currentRegion.value} 各区县项目`
})

const getMapJson = async (mods, adcode) => {
  const key = Object.keys(mods).find((k) => k.endsWith(`/${adcode}.json`))
  if (!key) return null
  const mod = await mods[key]()
  return mod.default || mod
}

const registerMap = (name, geo) => {
  if (!registered.has(name)) {
    echarts.registerMap(name, geo)
    registered.add(name)
  }
}

const initMap = async () => {
  echarts.registerMap('china', chinaGeo)
  registered.add('china')
  chart = echarts.init(mapEl.value)
  chart.on('click', (params) => {
    if (params.componentType === 'series' && params.name) {
      drillDown(params.name)
    }
  })
  window.addEventListener('resize', onResize)
}

const loadData = async () => {
  try {
    const res = await getHeatmap({ level: level.value, region: currentRegion.value || undefined })
    const items = res.data?.items || []
    tableData.value = items
    await renderMap(items)
  } catch (e) {
    ElMessage.warning('热力图数据加载失败，请确认后端已启动')
  }
}

const renderMap = async (items) => {
  let mapName = 'china'
  if (level.value === 'city') {
    const adcode = provinceAdcodeMap[currentRegion.value]
    if (!adcode) {
      ElMessage.warning('未找到该省地图数据')
      return
    }
    const geo = await getMapJson(provinceMaps, adcode)
    if (!geo) {
      ElMessage.warning(`暂未收录 ${currentRegion.value} 的地图数据`)
      return
    }
    registerMap(`p${adcode}`, geo)
    mapName = `p${adcode}`
    // 构建 城市名 -> adcode
    const map = {}
    geo.features.forEach((f) => {
      const p = f.properties
      if (p && p.name && p.adcode) map[p.name] = p.adcode
    })
    cityAdcodeMap.value = map
  } else if (level.value === 'district') {
    const adcode = currentCityAdcode.value
    if (!adcode) {
      ElMessage.warning('未找到该市地图数据')
      return
    }
    const geo = await getMapJson(cityMaps, adcode)
    if (!geo) {
      ElMessage.warning(`暂未收录该市地图数据，无法下钻到区县`)
      // 回退到省级视图
      level.value = 'city'
      currentRegion.value = ''
      await loadData()
      return
    }
    registerMap(`c${adcode}`, geo)
    mapName = `c${adcode}`
  }

  const max = Math.max(1, ...items.map((i) => i.count))
  const dataMap = {}
  items.forEach((i) => { dataMap[i.region] = i.count })
  chart.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: (p) => (p.name ? `${p.name}<br/>项目数：${dataMap[p.name] ?? 0}` : ''),
      },
      visualMap: {
        min: 0,
        max: max,
        left: 20,
        bottom: 20,
        text: ['高', '低'],
        calculable: true,
        inRange: { color: ['#e8f3ff', '#b3d7ff', '#5aa7ff', '#1677ff', '#0a3f8a'] },
      },
      series: [
        {
          type: 'map',
          map: mapName,
          roam: true,
          selectedMode: 'single',
          zoom: 1,
          center: undefined,
          label: { show: true, fontSize: 9 },
          itemStyle: { areaColor: '#eef2f7', borderColor: '#a6adb4' },
          emphasis: { label: { show: true }, itemStyle: { areaColor: '#ffd591' } },
          data: items.map((i) => ({ name: i.region, value: i.count })),
        },
      ],
    },
    true,
  )
}

const drillDown = (name) => {
  if (level.value === 'province') {
    const adcode = provinceAdcodeMap[name]
    if (!adcode) return
    // 直辖市一步到位：直接下钻到区县级
    if (MUNICIPAL.has(name)) {
      history.value.push({ level: 'province', region: '' })
      level.value = 'district'
      currentRegion.value = name
      currentCityName.value = name
      currentCityAdcode.value = adcode
    } else {
      history.value.push({ level: 'province', region: '' })
      level.value = 'city'
      currentRegion.value = name
      currentCityName.value = name
    }
    loadData()
  } else if (level.value === 'city') {
    const adcode = cityAdcodeMap.value[name]
    if (!adcode) {
      ElMessage.info('该地区暂无更多下钻数据')
      return
    }
    history.value.push({ level: 'city', region: currentRegion.value })
    level.value = 'district'
    currentRegion.value = name
    currentCityName.value = name
    currentCityAdcode.value = adcode
    loadData()
  }
  // district 级为最底层，不再下钻
}

const drillUp = () => {
  if (!history.value.length) return
  const prev = history.value.pop()
  level.value = prev.level
  currentRegion.value = prev.region
  currentCityAdcode.value = ''
  loadData()
}

const onResize = () => chart && chart.resize()

onMounted(async () => {
  await initMap()
  loadData()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart && chart.dispose()
})
</script>

<style scoped>
.map-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
