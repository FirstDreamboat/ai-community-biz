import request from '@/utils/request'

export const getOverview = () => request.get('/dashboard/overview')
export const getHeatmap = (params) => request.get('/dashboard/heatmap', { params })
export const getTrends = (params) => request.get('/dashboard/trends', { params })
