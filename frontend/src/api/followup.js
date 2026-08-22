import request from '@/utils/request'

export const listFollowUps = (params) => request.get('/follow-ups', { params })
export const listOverdue = () => request.get('/follow-ups/overdue')
