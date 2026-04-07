import { request } from './index'
import type { User, LoginForm, RegisterForm, TokenResponse } from '@/types'

export const authApi = {
  login(data: LoginForm): Promise<TokenResponse> {
    const formData = new URLSearchParams()
    formData.append('username', data.username)
    formData.append('password', data.password)
    return request.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },

  register(data: RegisterForm): Promise<User> {
    return request.post('/auth/register', data)
  },

  getCurrentUser(): Promise<User> {
    return request.get('/auth/me')
  },

  refreshToken(): Promise<TokenResponse> {
    return request.post('/auth/refresh-token')
  },

  logout(): Promise<void> {
    return request.post('/auth/logout')
  }
}
