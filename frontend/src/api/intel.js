import request from '@/utils/request'

// 存量项目台账
export const listLegacyProjects = (params) => request.get('/intel/legacy-projects', { params })
export const createLegacyProject = (data) => request.post('/intel/legacy-projects', data)
export const updateLegacyProject = (id, data) => request.put(`/intel/legacy-projects/${id}`, data)
export const deleteLegacyProject = (id) => request.delete(`/intel/legacy-projects/${id}`)

// 更新商机
export const listUpdateOpportunities = (params) => request.get('/intel/update-opportunities', { params })
export const generateUpdateOpportunities = () => request.post('/intel/update-opportunities/generate', {})
export const updateUpdateOpportunity = (id, data) => request.put(`/intel/update-opportunities/${id}`, data)
export const deleteUpdateOpportunity = (id) => request.delete(`/intel/update-opportunities/${id}`)

// 战略客户集采
export const listStrategicCustomers = (params) => request.get('/intel/strategic-customers', { params })
export const createStrategicCustomer = (data) => request.post('/intel/strategic-customers', data)
export const updateStrategicCustomer = (id, data) => request.put(`/intel/strategic-customers/${id}`, data)
export const deleteStrategicCustomer = (id) => request.delete(`/intel/strategic-customers/${id}`)

// 销售线索
export const listSalesLeads = (params) => request.get('/intel/sales-leads', { params })
export const createSalesLead = (data) => request.post('/intel/sales-leads', data)
export const updateSalesLead = (id, data) => request.put(`/intel/sales-leads/${id}`, data)
export const deleteSalesLead = (id) => request.delete(`/intel/sales-leads/${id}`)

// 竞品中标后续追踪
export const listCompetitorTracks = (params) => request.get('/intel/competitor-tracks', { params })
export const createCompetitorTrack = (data) => request.post('/intel/competitor-tracks', data)
export const updateCompetitorTrack = (id, data) => request.put(`/intel/competitor-tracks/${id}`, data)
export const deleteCompetitorTrack = (id) => request.delete(`/intel/competitor-tracks/${id}`)
export const generateTracksFromRecords = () => request.post('/intel/competitor-tracks/generate-from-records', {})

// 诉求热点
export const listAppealHotspots = (params) => request.get('/intel/appeal-hotspots', { params })
export const createAppealHotspot = (data) => request.post('/intel/appeal-hotspots', data)
export const updateAppealHotspot = (id, data) => request.put(`/intel/appeal-hotspots/${id}`, data)
export const deleteAppealHotspot = (id) => request.delete(`/intel/appeal-hotspots/${id}`)
