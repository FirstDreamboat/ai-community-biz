import request from '@/utils/request'

export const listOpportunities = (params) => request.get('/opportunities', { params })
export const getOpportunity = (id) => request.get(`/opportunities/${id}`)
export const followUp = (id, data) => request.post(`/opportunities/${id}/follow-up`, data)
export const assignOpportunity = (id, data) => request.post(`/opportunities/${id}/assign`, data)
export const recalcOpportunity = (id) => request.post(`/opportunities/${id}/recalc`)
export const exportOpportunities = (params) =>
  request.get('/opportunities/export', { params, responseType: 'blob' })
