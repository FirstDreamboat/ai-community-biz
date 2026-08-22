import request from '@/utils/request'

// 用户管理
export const listUsers = (params) => request.get('/users', { params })
export const createUser = (data) => request.post('/users', data)
export const updateUser = (id, data) => request.put(`/users/${id}`, data)
export const deleteUser = (id) => request.delete(`/users/${id}`)

// 角色
export const listRoles = () => request.get('/roles')
export const listPermissions = () => request.get('/permissions')
export const createRole = (data) => request.post('/roles', data)
export const updateRole = (id, data) => request.put(`/roles/${id}`, data)
export const deleteRole = (id) => request.delete(`/roles/${id}`)

// 系统配置
export const getConfig = (key) => request.get(`/configs/${key}`)
export const updateConfig = (key, data) => request.put(`/configs/${key}`, data)

// 审计日志
export const listAuditLogs = (params) => request.get('/audit-logs', { params })
