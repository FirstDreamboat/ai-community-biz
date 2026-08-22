import request from '@/utils/request'

export const listOffices = (params) => request.get('/offices', { params })
export const matchOffice = (params) => request.get('/offices/match', { params })
export const getCoverage = () => request.get('/offices/coverage')
export const createOffice = (data) => request.post('/offices', data)
export const updateOffice = (id, data) => request.put(`/offices/${id}`, data)
export const deleteOffice = (id) => request.delete(`/offices/${id}`)
