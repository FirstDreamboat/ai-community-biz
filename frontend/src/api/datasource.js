import request from '@/utils/request'

export const listDataSources = (params) => request.get('/data-sources', { params })
export const createDataSource = (data) => request.post('/data-sources', data)
export const updateDataSource = (id, data) => request.put(`/data-sources/${id}`, data)
export const deleteDataSource = (id) => request.delete(`/data-sources/${id}`)
export const toggleDataSource = (id) => request.post(`/data-sources/${id}/toggle`)
export const runDataSource = (id) => request.post(`/data-sources/${id}/run`)
export const listTasks = (params) => request.get('/data-sources/tasks', { params })
