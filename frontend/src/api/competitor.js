import request from '@/utils/request'

export const listRecords = (params) => request.get('/competitors/records', { params })
export const getAnalysis = () => request.get('/competitors/analysis')
export const getKeywords = () => request.get('/competitors/keywords')
export const saveKeywords = (keywords) => request.post('/competitors/keywords', { keywords })
export const createRecord = (data) => request.post('/competitors/records', data)
export const deleteRecord = (id) => request.delete(`/competitors/records/${id}`)
