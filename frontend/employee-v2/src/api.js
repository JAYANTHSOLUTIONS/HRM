const BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

// Token storage
export const tokenStore = {
  get: () => localStorage.getItem('df_token'),
  set: (t) => localStorage.setItem('df_token', t),
  clear: () => { localStorage.removeItem('df_token'); localStorage.removeItem('df_refresh') },
  getRefresh: () => localStorage.getItem('df_refresh'),
  setRefresh: (t) => localStorage.setItem('df_refresh', t),
}

async function req(path, options = {}, skipAuth = false) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (!skipAuth) {
    const token = tokenStore.get()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`
    try { const b = await res.json(); msg = b?.error?.message || b?.detail || msg } catch {}
    throw new Error(msg)
  }
  return res.status === 204 ? null : res.json()
}

// ── Auth ───────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password, turnstile_token) =>
    req('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ email, password, turnstile_token }) }, true),
  
  forgotPassword: (email, turnstile_token) =>
    req('/api/v1/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email, turnstile_token }) }, true),

  signup: (data) => req('/api/v1/auth/signup', { method: 'POST', body: JSON.stringify(data) }, true),
  
  verifyOTP: (email, otp) =>
    req('/api/v1/auth/verify-otp', { method: 'POST', body: JSON.stringify({ email, otp }) }, true),
  
  resetPassword: (reset_token, new_password, confirm_password) =>
    req('/api/v1/auth/reset-password', { method: 'POST', body: JSON.stringify({ reset_token, new_password, confirm_password }) }, true),
  
  getMe: () => req('/api/v1/auth/me'),

  logout: (refresh_token) =>
    req('/api/v1/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token }) }),
  
  refresh: (refresh_token) =>
    req('/api/v1/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token }) }, true),
}

// ── Me (Self-service) ──────────────────────────────────────────────────────
export const meApi = {
  getProfile: () => req('/api/v1/me'),
  updateProfile: (data) => req('/api/v1/me', { method: 'PATCH', body: JSON.stringify(data) }),
  getDashboard: () => req('/api/v1/dashboard/employee'),

  // Attendance
  getAttendance: (weekStart) =>
    req(`/api/v1/me/attendance${weekStart ? `?week_start=${weekStart}` : ''}`),
  checkIn: () => req('/api/v1/me/attendance/check-in', { method: 'POST' }),
  checkOut: () => req('/api/v1/me/attendance/check-out', { method: 'POST' }),

  // Leave
  getLeaveBalances: () => req('/api/v1/me/leave/balances'),
  getLeaveRequests: (status) =>
    req(`/api/v1/me/leave/requests${status ? `?status=${status}` : ''}`),
  applyLeave: (data) =>
    req('/api/v1/me/leave/requests', { method: 'POST', body: JSON.stringify(data) }),
  cancelLeave: (id) => req(`/api/v1/me/leave/requests/${id}`, { method: 'DELETE' }),

  // Leave reference
  getLeaveTypes: () => req('/api/v1/leave-types'),

  // Salary
  getSalary: () => req('/api/v1/me/salary'),

  // Profile picture
  uploadProfilePicture: (employeeId, file) => {
    const form = new FormData()
    form.append('file', file)
    const headers = {}
    const token = tokenStore.get()
    if (token) headers['Authorization'] = `Bearer ${token}`
    return fetch(`${BASE}/api/v1/employees/${employeeId}/profile-picture`, {
      method: 'POST', headers, body: form,
    }).then(r => r.ok ? r.json() : r.json().then(b => Promise.reject(new Error(b?.error?.message || 'Upload failed'))))
  },
}
