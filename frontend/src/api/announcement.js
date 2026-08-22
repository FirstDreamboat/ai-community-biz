import request from '@/utils/request'

export const listAnnouncements = (params) => request.get('/announcements', { params })
export const getAnnouncement = (id) => request.get(`/announcements/${id}`)
export const reParse = (id) => request.post(`/announcements/${id}/re-parse`)
export const batchParse = (params) => request.post('/announcements/batch-parse', params)
export const getBatchParseStatus = () => request.get('/announcements/batch-parse/status')
