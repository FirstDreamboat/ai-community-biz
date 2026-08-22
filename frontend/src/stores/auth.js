import { defineStore } from 'pinia'
import { login as apiLogin, getMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    permissions: [],
  }),
  getters: {
    isLogin: (state) => !!state.token,
    isAdmin: (state) => state.user?.roles?.includes('admin'),
  },
  actions: {
    async login(username, password) {
      const res = await apiLogin({ username, password })
      const data = res.data || {}
      this.token = data.token
      this.user = data.user
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
      return data
    },
    async fetchMe() {
      try {
        const res = await getMe()
        const data = res.data || {}
        this.user = data.user || this.user
        this.permissions = data.permissions || []
        localStorage.setItem('user', JSON.stringify(this.user))
      } catch (e) {
        /* 忽略 */
      }
    },
    hasPerm(perm) {
      if (!perm) return true
      if (this.isAdmin) return true
      return this.permissions.includes(perm)
    },
    logout() {
      this.token = ''
      this.user = null
      this.permissions = []
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
