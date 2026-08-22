import request from '@/utils/request'

export const listPushRecords = (params) => request.get('/push/records', { params })
export const createPushRecord = (data) => request.post('/push/records', data)
export const sendPushRecord = (id) => request.post(`/push/records/${id}/send`)
export const sendPendingPushes = (params) => request.post('/push/records/send-pending', null, { params })
export const testPushChannel = (data) => request.post('/push/test', data)
