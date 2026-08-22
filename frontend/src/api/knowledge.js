import request from '@/utils/request'

export const listKnowledge = (params) => request.get('/knowledge', { params })
export const createKnowledge = (data) => request.post('/knowledge', data)
export const updateKnowledge = (id, data) => request.put(`/knowledge/${id}`, data)
export const deleteKnowledge = (id) => request.delete(`/knowledge/${id}`)
export const reindexKnowledge = () => request.post('/knowledge/reindex')

export const listPolicies = (params) => request.get('/knowledge/policies', { params })
export const createPolicy = (data) => request.post('/knowledge/policies', data)
export const updatePolicy = (id, data) => request.put(`/knowledge/policies/${id}`, data)
export const deletePolicy = (id) => request.delete(`/knowledge/policies/${id}`)
