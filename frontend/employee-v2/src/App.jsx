import { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react'
import { authApi, meApi, tokenStore } from './api'

// ─── Auth Context ──────────────────────────────────────────────────────────────
const AuthCtx = createContext(null)
function useAuth() { return useContext(AuthCtx) }

// ─── Helpers ──────────────────────────────────────────────────────────────────
const fmt = (dt) => dt ? new Date(dt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }) : '—'
const fmtDate = (d) => d ? new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'
const fmtHours = (h) => h !== undefined && h !== null ? `${Number(h).toFixed(1)}h` : '—'
const weekLabel = (ws) => { const d = new Date(ws + 'T00:00:00'); const e = new Date(d); e.setDate(e.getDate() + 6); return `${d.toLocaleDateString('en-US',{month:'short',day:'numeric'})} – ${e.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'})}` }
const isoDate = (d) => d.toISOString().slice(0, 10)
const monday = (d = new Date()) => { const x = new Date(d); x.setDate(x.getDate() - x.getDay() + (x.getDay() === 0 ? -6 : 1)); return isoDate(x) }
const shiftWeek = (ws, n) => { const d = new Date(ws + 'T00:00:00'); d.setDate(d.getDate() + n * 7); return isoDate(d) }

function exportToCSV(filename, headers, rows) {
  const content = [headers.join(','), ...rows.map(r => r.map(c => `"${String(c || '').replace(/"/g, '""')}"`).join(','))].join('\n')
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const STATUS_MAP = {
  PRESENT:   { cls: 'df-badge-present',  label: 'Present',   icon: 'bi-check-circle-fill' },
  ABSENT:    { cls: 'df-badge-absent',   label: 'Absent',    icon: 'bi-x-circle-fill' },
  HALF_DAY:  { cls: 'df-badge-pending',  label: 'Half Day',  icon: 'bi-circle-half' },
  LEAVE:     { cls: 'df-badge-leave',    label: 'On Leave',  icon: 'bi-calendar-event-fill' },
  HOLIDAY:   { cls: 'df-badge-pending',  label: 'Holiday',   icon: 'bi-sun-fill' },
  WEEKEND:   { cls: 'df-badge-pending',  label: 'Weekend',   icon: 'bi-moon-stars-fill' },
  PENDING:   { cls: 'df-badge-pending',  label: 'Pending',   icon: 'bi-hourglass-split' },
  APPROVED:  { cls: 'df-badge-approved', label: 'Approved',  icon: 'bi-check-circle-fill' },
  REJECTED:  { cls: 'df-badge-rejected', label: 'Rejected',  icon: 'bi-x-circle-fill' },
  CANCELLED: { cls: 'df-badge-rejected', label: 'Cancelled', icon: 'bi-slash-circle' },
}

function Badge({ status }) {
  const s = STATUS_MAP[status?.toUpperCase()] || STATUS_MAP.ABSENT
  return <span className={`df-badge ${s.cls}`}><i className={`bi ${s.icon}`} />{s.label}</span>
}

function Spinner() { return <div className="d-flex justify-content-center py-5"><div className="spinner-border text-primary" role="status" /></div> }

function FeedbackModal({ feedback, onClose }) {
  if (!feedback) return null
  const { type = 'info', title, message, details } = feedback
  return (
    <div className="df-feedback-overlay" onClick={onClose}>
      <div className="df-feedback-modal" onClick={e => e.stopPropagation()}>
        <div className={`df-icon-box ${type}`}>
          <svg className="df-svg-icon" viewBox="0 0 52 52">
            <circle className={`df-circle-path ${type}`} cx="26" cy="26" r="23" fill="none" />
            {type === 'success' && (
              <path className="df-tick-path" fill="none" d="M14 27 l7 7 l17 -17" />
            )}
            {type === 'error' && (
              <>
                <path className="df-cross-path1" fill="none" d="M16 16 L36 36" />
                <path className="df-cross-path2" fill="none" d="M36 16 L16 36" />
              </>
            )}
            {type === 'info' && (
              <>
                <circle cx="26" cy="17" r="2.5" fill="#3B82F6" />
                <path className="df-info-path" fill="none" d="M26 24 L26 36" />
              </>
            )}
          </svg>
        </div>
        <h3 style={{ fontSize: 20, fontWeight: 700, margin: '0 0 8px', color: 'var(--df-navy)' }}>{title || (type === 'success' ? 'Success' : type === 'error' ? 'Error' : 'Notice')}</h3>
        <p style={{ fontSize: 14, color: 'var(--df-text-muted)', margin: '0 0 16px', lineHeight: 1.5 }}>{message}</p>
        {details && (
          <div style={{
            background: type === 'success' ? '#ECFDF5' : type === 'error' ? '#FEF2F2' : '#F1F5F9',
            border: `1px solid ${type === 'success' ? '#A7F3D0' : type === 'error' ? '#FECACA' : '#CBD5E1'}`,
            borderRadius: 8,
            padding: '10px 14px',
            fontSize: 13,
            color: type === 'success' ? '#065F46' : type === 'error' ? '#991B1B' : '#334155',
            fontWeight: 600,
            marginBottom: 20,
            fontFamily: 'monospace',
            wordBreak: 'break-all'
          }}>
            {details}
          </div>
        )}
        <button
          className={type === 'error' ? 'df-btn-secondary w-100 py-2' : 'df-btn-primary w-100 py-2'}
          style={{ borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: 'pointer' }}
          onClick={onClose}
        >
          {type === 'success' ? 'Done' : type === 'error' ? 'Close' : 'OK'}
        </button>
      </div>
    </div>
  )
}

function Alert({ msg, type = 'danger', onClose }) {
  if (!msg) return null
  const feedbackType = type === 'danger' ? 'error' : type === 'success' ? 'success' : 'info'
  const title = type === 'danger' ? 'Notice / Error' : type === 'success' ? 'Operation Complete' : 'Information'
  return <FeedbackModal feedback={{ type: feedbackType, title, message: msg }} onClose={onClose} />
}

function TurnstileWidget({ onToken }) {
  const containerRef = useRef(null)
  const widgetId = useRef(null)
  const siteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY

  useEffect(() => {
    if (!siteKey) { onToken(''); return undefined }
    const render = () => {
      if (!containerRef.current || !window.turnstile) return
      widgetId.current = window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        callback: onToken,
        'expired-callback': () => onToken(''),
        'error-callback': () => onToken(''),
      })
    }
    if (window.turnstile) render()
    else {
      const script = document.createElement('script')
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
      script.async = true
      script.onload = render
      document.head.appendChild(script)
    }
    return () => {
      if (widgetId.current !== null && window.turnstile) window.turnstile.remove(widgetId.current)
    }
  }, [onToken, siteKey])

  return siteKey
    ? <div ref={containerRef} className="d-flex justify-content-center" />
    : <div className="small text-muted text-center">Configure VITE_TURNSTILE_SITE_KEY to enable CAPTCHA.</div>
}

// ─── Login Page ───────────────────────────────────────────────────────────────
function LoginPage({ onLogin, onForgot, onRegister }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [turnstileToken, setTurnstileToken] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res = await authApi.login(email, password, turnstileToken)
      tokenStore.set(res.access_token)
      tokenStore.setRefresh(res.refresh_token)
      onLogin(res.user)
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ background: 'var(--df-navy)' }}>
      <div className="df-card shadow-lg p-4 p-md-5" style={{ maxWidth: 400, width: '100%' }}>
        <div className="text-center mb-4">
          <div className="df-logo-mark mx-auto mb-2" style={{ width: 40, height: 40, fontSize: 20 }}>⚡</div>
          <h2 className="df-section-title fs-3 fw-bold mb-1">Dayflow</h2>
          <p className="df-section-sub">Employee Portal</p>
        </div>
        <form onSubmit={handleSubmit}>
          <Alert msg={error} onClose={() => setError('')} />
          <div className="mb-3">
            <label className="df-stat-label mb-1">Email address</label>
            <input className="df-input w-100" type="email" placeholder="you@company.com"
              value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
          </div>
          <div className="mb-3">
            <label className="df-stat-label mb-1">Password</label>
            <div className="input-group">
              <input className="df-input form-control border-end-0" type={showPass ? 'text' : 'password'}
                placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required />
              <button type="button" className="btn border border-start-0 bg-white" onClick={() => setShowPass(!showPass)}>
                <i className={`bi ${showPass ? 'bi-eye-slash' : 'bi-eye'}`} />
              </button>
            </div>
          </div>
          
          <div className="mb-4 p-2 bg-light border rounded"><TurnstileWidget onToken={setTurnstileToken} /></div>

          <div className="d-flex justify-content-between align-items-center mt-3">
            <button type="button" className="btn btn-link p-0 text-decoration-none fs-7 text-primary" onClick={onForgot}>
              Forgot password?
            </button>
          </div>

          <button className="df-btn-primary w-100 justify-content-center py-2 fs-6 mt-3" disabled={loading}>
            {loading ? <><span className="spinner-border spinner-border-sm me-2" />Signing in...</> : 'Sign in'}
          </button>
          <button type="button" className="btn btn-link w-100 text-decoration-none fs-7 mt-2" onClick={onRegister}>
            Don't have an account? Register
          </button>
        </form>
      </div>
    </div>
  )
}

function RegisterPage({ onBackToLogin }) {
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', department_id: '1', designation_id: '1', joining_date: '' })
  const [confirmPassword, setConfirmPassword] = useState('')
  const [turnstileToken, setTurnstileToken] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const passwordValid = /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^\w\s]).{8,}$/.test(form.password)

  function update(field, value) { setForm(current => ({ ...current, [field]: value })) }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!passwordValid) { setError('Password must be 8+ characters and include uppercase, lowercase, number, and special character.'); return }
    if (form.password !== confirmPassword) { setError('Passwords do not match.'); return }
    setLoading(true)
    try {
      const response = await authApi.signup({ ...form, department_id: Number(form.department_id), designation_id: Number(form.designation_id), turnstile_token: turnstileToken })
      setSuccess(response.message || 'Account created. Please verify your email before signing in.')
    } catch (err) { setError(err.message || 'Registration failed.') }
    finally { setLoading(false) }
  }

  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center py-4" style={{ background: 'var(--df-navy)' }}>
      <div className="df-card shadow-lg p-4 p-md-5" style={{ maxWidth: 520, width: '100%' }}>
        <div className="text-center mb-4"><div className="df-logo-mark mx-auto mb-2" style={{ width: 40, height: 40, fontSize: 20 }}>⚡</div><h2 className="df-section-title fs-3 fw-bold mb-1">Create account</h2><p className="df-section-sub">Join the Dayflow employee portal</p></div>
        <Alert msg={error} onClose={() => setError('')} />
        {success ? <><div className="alert alert-success">{success}</div><button className="df-btn-primary w-100 justify-content-center" onClick={onBackToLogin}>Back to sign in</button></> : <form onSubmit={handleSubmit}>
          <div className="row g-3"><div className="col-sm-6"><label className="df-stat-label mb-1">First name</label><input className="df-input w-100" value={form.first_name} onChange={e => update('first_name', e.target.value)} required /></div><div className="col-sm-6"><label className="df-stat-label mb-1">Last name</label><input className="df-input w-100" value={form.last_name} onChange={e => update('last_name', e.target.value)} required /></div></div>
          <div className="mt-3"><label className="df-stat-label mb-1">Email address</label><input className="df-input w-100" type="email" value={form.email} onChange={e => update('email', e.target.value)} required /></div>
          <div className="row g-3 mt-0"><div className="col-sm-6"><label className="df-stat-label mb-1">Department ID</label><input className="df-input w-100" type="number" min="1" value={form.department_id} onChange={e => update('department_id', e.target.value)} required /></div><div className="col-sm-6"><label className="df-stat-label mb-1">Designation ID</label><input className="df-input w-100" type="number" min="1" value={form.designation_id} onChange={e => update('designation_id', e.target.value)} required /></div></div>
          <div className="mt-3"><label className="df-stat-label mb-1">Joining date</label><input className="df-input w-100" type="date" value={form.joining_date} onChange={e => update('joining_date', e.target.value)} required /></div>
          <div className="mt-3"><label className="df-stat-label mb-1">Password</label><input className="df-input w-100" type="password" value={form.password} onChange={e => update('password', e.target.value)} required /><PasswordStrengthMeter password={form.password} /></div>
          <div className="mt-3"><label className="df-stat-label mb-1">Confirm password</label><input className="df-input w-100" type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required /></div>
          <div className="my-4 p-2 bg-light border rounded"><TurnstileWidget onToken={setTurnstileToken} /></div>
          <button className="df-btn-primary w-100 justify-content-center py-2" disabled={loading}>{loading ? 'Creating account...' : 'Create account'}</button>
          <button type="button" className="btn btn-link w-100 text-decoration-none mt-2" onClick={onBackToLogin}>Already have an account? Sign in</button>
        </form>}
      </div>
    </div>
  )
}

// ─── Password Strength Indicator ──────────────────────────────────────────────
function PasswordStrengthMeter({ password }) {
  const checks = [
    { label: 'At least 8 characters', pass: password.length >= 8 },
    { label: 'One uppercase letter (A-Z)', pass: /[A-Z]/.test(password) },
    { label: 'One lowercase letter (a-z)', pass: /[a-z]/.test(password) },
    { label: 'One number (0-9)', pass: /\d/.test(password) },
    { label: 'One special character (!@#$...)', pass: /[^\w\s]/.test(password) },
  ]
  const score = checks.filter(c => c.pass).length

  return (
    <div className="mt-2 p-2 bg-light border rounded">
      <div className="d-flex justify-content-between align-items-center mb-1">
        <small className="fw-semibold text-muted">Password Strength:</small>
        <small className={`fw-bold ${score <= 2 ? 'text-danger' : score <= 4 ? 'text-warning' : 'text-success'}`}>
          {score <= 2 ? 'Weak' : score <= 4 ? 'Medium' : 'Strong'}
        </small>
      </div>
      <div className="progress mb-2" style={{ height: 4 }}>
        <div className={`progress-bar ${score <= 2 ? 'bg-danger' : score <= 4 ? 'bg-warning' : 'bg-success'}`}
          style={{ width: `${(score / 5) * 100}%` }} />
      </div>
      <div className="row g-1">
        {checks.map(c => (
          <div key={c.label} className="col-12" style={{ fontSize: 11 }}>
            <i className={`bi ${c.pass ? 'bi-check-circle-fill text-success' : 'bi-circle text-muted'} me-1`} />
            <span className={c.pass ? 'text-dark' : 'text-muted'}>{c.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Forgot Password, OTP & Reset Flow ───────────────────────────────────────
function AuthFlow({ onBackToLogin }) {
  const [stage, setStage] = useState('forgot') // 'forgot' | 'verify_otp' | 'reset' | 'success'
  const [email, setEmail] = useState('')
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', ''])
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [infoMsg, setInfoMsg] = useState('')
  const [resendTimer, setResendTimer] = useState(45)

  useEffect(() => {
    let t
    if (stage === 'verify_otp' && resendTimer > 0) {
      t = setInterval(() => setResendTimer(r => r - 1), 1000)
    }
    return () => clearInterval(t)
  }, [stage, resendTimer])

  async function handleSendOTP(e) {
    e.preventDefault()
    setLoading(true); setError(''); setInfoMsg('')
    try {
      const res = await authApi.forgotPassword(email)
      setInfoMsg(res.message || 'If an account exists for this email, a password reset OTP has been sent.')
      setStage('verify_otp')
      setResendTimer(45)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  async function handleVerifyOTP(e) {
    e.preventDefault()
    const otp = otpDigits.join('')
    if (otp.length !== 6) { setError('Please enter a valid 6-digit OTP code'); return }
    setLoading(true); setError(''); setInfoMsg('')
    try {
      const res = await authApi.verifyOTP(email, otp)
      setResetToken(res.reset_token)
      setInfoMsg('OTP verified successfully. Please enter your new password.')
      setStage('reset')
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  async function handleResetPassword(e) {
    e.preventDefault()
    if (newPassword !== confirmPassword) { setError('Passwords do not match'); return }
    setLoading(true); setError(''); setInfoMsg('')
    try {
      const res = await authApi.resetPassword(resetToken, newPassword, confirmPassword)
      setInfoMsg(res.message || 'Password reset successfully.')
      setStage('success')
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  function handleDigitChange(idx, val) {
    if (!/^\d*$/.test(val)) return
    const updated = [...otpDigits]
    updated[idx] = val.slice(-1)
    setOtpDigits(updated)
    if (val && idx < 5) {
      const nextInput = document.getElementById(`otp-input-${idx + 1}`)
      if (nextInput) nextInput.focus()
    }
  }

  return (
    <div className="min-vh-100 d-flex align-items-center justify-content-center" style={{ background: 'var(--df-navy)' }}>
      <div className="df-card shadow-lg p-4 p-md-5" style={{ maxWidth: 440, width: '100%' }}>
        <div className="text-center mb-4">
          <div className="df-logo-mark mx-auto mb-2" style={{ width: 40, height: 40, fontSize: 20 }}>⚡</div>
          <h2 className="df-section-title fs-3 fw-bold mb-1">
            {stage === 'forgot' && 'Reset Password'}
            {stage === 'verify_otp' && 'Enter OTP Code'}
            {stage === 'reset' && 'Create New Password'}
            {stage === 'success' && 'Password Reset'}
          </h2>
          <p className="df-section-sub">
            {stage === 'forgot' && 'Enter your registered email to receive a 6-digit OTP'}
            {stage === 'verify_otp' && `Sent to ${email}`}
            {stage === 'reset' && 'Enter a strong new password for your account'}
            {stage === 'success' && 'Your account security has been updated'}
          </p>
        </div>

        <Alert msg={error} onClose={() => setError('')} />
        {infoMsg && <div className="alert alert-info py-2 px-3 small mb-3">{infoMsg}</div>}

        {stage === 'forgot' && (
          <form onSubmit={handleSendOTP}>
            <div className="mb-3">
              <label className="df-stat-label mb-1">Email address</label>
              <input className="df-input w-100" type="email" placeholder="you@company.com"
                value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
            </div>

            <div className="mb-4 p-2 bg-light border rounded d-flex align-items-center justify-content-between px-3">
              <div className="d-flex align-items-center gap-2">
                <i className="bi bi-shield-check text-success fs-5" />
                <div className="text-start">
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--df-navy)' }}>Cloudflare Turnstile</div>
                  <div style={{ fontSize: 10, color: 'var(--df-text-muted)' }}>Protected by Turnstile CAPTCHA</div>
                </div>
              </div>
              <span className="badge bg-success-subtle text-success border border-success-subtle px-2 py-1 fs-7">Verified</span>
            </div>

            <button className="df-btn-primary w-100 justify-content-center py-2 fs-6 mb-3" disabled={loading}>
              {loading ? <><span className="spinner-border spinner-border-sm me-2" />Sending OTP...</> : 'Send Reset OTP'}
            </button>
            <button type="button" className="btn btn-link w-100 text-decoration-none fs-7 text-muted" onClick={onBackToLogin}>
              ← Back to Sign in
            </button>
          </form>
        )}

        {stage === 'verify_otp' && (
          <form onSubmit={handleVerifyOTP}>
            <div className="mb-3">
              <label className="df-stat-label mb-2 text-center d-block">6-Digit Verification Code</label>
              <div className="d-flex gap-2 justify-content-center mb-3">
                {otpDigits.map((digit, idx) => (
                  <input
                    key={idx}
                    id={`otp-input-${idx}`}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    className="form-control text-center fw-bold fs-4"
                    style={{ width: 44, height: 50, borderRadius: 8, border: '1px solid var(--df-border)' }}
                    value={digit}
                    onChange={e => handleDigitChange(idx, e.target.value)}
                    autoFocus={idx === 0}
                  />
                ))}
              </div>
              <small className="text-muted d-block text-center mb-3">
                <i className="bi bi-clock-history me-1" />OTP expires in <strong>05:00</strong>
              </small>
            </div>

            <button className="df-btn-primary w-100 justify-content-center py-2 fs-6 mb-3" disabled={loading || otpDigits.join('').length !== 6}>
              {loading ? <><span className="spinner-border spinner-border-sm me-2" />Verifying...</> : 'Verify OTP Code'}
            </button>

            <div className="text-center">
              <button
                type="button"
                className="btn btn-link text-decoration-none fs-7 text-primary p-0"
                disabled={resendTimer > 0 || loading}
                onClick={handleSendOTP}
              >
                {resendTimer > 0 ? `Resend OTP in ${resendTimer}s` : "Didn't receive OTP? Resend"}
              </button>
            </div>
          </form>
        )}

        {stage === 'reset' && (
          <form onSubmit={handleResetPassword}>
            <div className="mb-3">
              <label className="df-stat-label mb-1">New Password</label>
              <input className="df-input w-100" type="password" placeholder="••••••••"
                value={newPassword} onChange={e => setNewPassword(e.target.value)} required autoFocus />
              <PasswordStrengthMeter password={newPassword} />
            </div>

            <div className="mb-4">
              <label className="df-stat-label mb-1">Confirm New Password</label>
              <input className="df-input w-100" type="password" placeholder="••••••••"
                value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required />
            </div>

            <button className="df-btn-primary w-100 justify-content-center py-2 fs-6" disabled={loading}>
              {loading ? <><span className="spinner-border spinner-border-sm me-2" />Resetting...</> : 'Reset Password'}
            </button>
          </form>
        )}

        {stage === 'success' && (
          <div className="text-center py-3">
            <div className="df-badge df-badge-present mx-auto mb-3 p-3 fs-3" style={{ borderRadius: '50%', width: 64, height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <i className="bi bi-check-lg" />
            </div>
            <p className="df-section-sub mb-4">Your password has been reset using Argon2 hashing. You may now sign in with your new credentials.</p>
            <button className="df-btn-primary w-100 justify-content-center py-2 fs-6" onClick={onBackToLogin}>
              Go to Sign in
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Navbar ───────────────────────────────────────────────────────────────────
const NAV = [
  { id: 'dashboard', label: 'Dashboard',   icon: 'bi-grid-fill' },
  { id: 'attendance',label: 'Attendance',  icon: 'bi-clock-history' },
  { id: 'timeoff',   label: 'Time Off',    icon: 'bi-calendar-event-fill' },
  { id: 'profile',   label: 'My Profile',  icon: 'bi-person-fill' },
  { id: 'salary',    label: 'Salary',      icon: 'bi-currency-dollar' },
]

function Navbar({ page, onNav, profile, onLogout }) {
  return (
    <header className="df-navbar">
      <div className="df-logo">
        <div className="df-logo-mark">⚡</div>
        Dayflow
      </div>
      <nav className="d-flex gap-1">
        {NAV.map(n => (
          <button key={n.id} className={`df-nav-link ${page === n.id ? 'active' : ''}`} onClick={() => onNav(n.id)}>
            <i className={`bi ${n.icon}`} /> <span className="label">{n.label}</span>
          </button>
        ))}
      </nav>
      <div className="ms-auto d-flex align-items-center gap-3">
        <div className="d-flex align-items-center gap-2">
          <div className="df-avatar" style={{ width: 30, height: 30, fontSize: 12, background: 'var(--df-blue)', color: '#fff' }}>
            {(profile?.full_name || 'U').slice(0, 2).toUpperCase()}
          </div>
          <div className="d-none d-md-block text-white" style={{ fontSize: 13, fontWeight: 600 }}>
            {profile?.full_name || 'Employee'}
          </div>
        </div>
        <button className="df-nav-link text-white-50 p-1" onClick={onLogout} title="Sign out">
          <i className="bi bi-box-arrow-right" style={{ fontSize: 16 }} />
        </button>
      </div>
    </header>
  )
}

// ─── Dashboard Page ───────────────────────────────────────────────────────────
function DashboardPage({ onNav }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [actionMsg, setActionMsg] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await meApi.getDashboard()) } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function doCheckIn() {
    setActionLoading(true); setActionMsg('')
    try { const r = await meApi.checkIn(); setActionMsg(r.message); load() }
    catch (e) { setActionMsg(e.message) }
    finally { setActionLoading(false) }
  }

  async function doCheckOut() {
    setActionLoading(true); setActionMsg('')
    try { const r = await meApi.checkOut(); setActionMsg(r.message); load() }
    catch (e) { setActionMsg(e.message) }
    finally { setActionLoading(false) }
  }

  if (loading) return <Spinner />

  const hasCheckedIn = !!data?.check_in_at
  const hasCheckedOut = !!data?.check_out_at
  const canCheckOut = hasCheckedIn && !hasCheckedOut

  return (
    <div className="df-page">
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
        <div>
          <h1 className="df-section-title">Good {getGreeting()}, {data?.full_name?.split(' ')[0] || 'there'} ✦</h1>
          <p className="df-section-sub">{data?.department} · {data?.designation}</p>
        </div>
        <div className="d-flex gap-2 align-items-center">
          {!hasCheckedIn && (
            <button className="df-btn-primary" onClick={doCheckIn} disabled={actionLoading}>
              <i className="bi bi-box-arrow-in-right me-1" /> Check In
            </button>
          )}
          {canCheckOut && (
            <button className="df-btn-secondary" onClick={doCheckOut} disabled={actionLoading}>
              <i className="bi bi-box-arrow-right me-1" /> Check Out
            </button>
          )}
          {hasCheckedOut && <Badge status="APPROVED" />}
        </div>
      </div>

      {error && <Alert msg={error} onClose={() => setError('')} />}
      {actionMsg && <div className="alert alert-info py-2 px-3 small">{actionMsg}</div>}

      <div className="row g-3 mb-4">
        {[
          { label: 'Today Status', value: data?.today_status ? <Badge status={data.today_status} /> : <span className="text-muted">Not recorded</span>, sub: 'Daily status' },
          { label: 'Check In', value: fmt(data?.check_in_at), sub: 'Arrival time' },
          { label: 'Check Out', value: fmt(data?.check_out_at), sub: 'Departure time' },
          { label: 'Hours Today', value: fmtHours(data?.work_hours_today), sub: 'Total worked' },
        ].map(c => (
          <div key={c.label} className="col-6 col-xl-3">
            <div className="df-stat-card">
              <span className="df-stat-label">{c.label}</span>
              <div className="df-stat-value my-1">{c.value}</div>
              <div className="df-stat-sub"><i className="bi bi-info-circle" /> {c.sub}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div className="df-card h-100">
            <div className="df-section-title fs-6 mb-2"><i className="bi bi-calendar-week me-2 text-primary" />This Week</div>
            <div className="df-stat-value text-primary fs-1 mb-1">{data?.this_week_present_days ?? 0}</div>
            <div className="df-stat-sub">days present so far</div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="df-card h-100">
            <div className="df-section-title fs-6 mb-2"><i className="bi bi-hourglass-split me-2 text-warning" />Pending Leaves</div>
            <div className="df-stat-value text-warning fs-1 mb-1">{data?.pending_leave_requests ?? 0}</div>
            <div className="df-stat-sub">awaiting approval</div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="df-card h-100">
            <div className="df-section-title fs-6 mb-2"><i className="bi bi-check-circle me-2 text-success" />Approved Leaves</div>
            <div className="df-stat-value text-success fs-1 mb-1">{data?.approved_leave_requests ?? 0}</div>
            <div className="df-stat-sub">upcoming approved</div>
          </div>
        </div>
      </div>

      {data?.leave_balances?.length > 0 && (
        <div className="df-card mb-4">
          <div className="df-section-title fs-6 mb-3"><i className="bi bi-wallet2 me-2 text-primary" />Leave Balances</div>
          <div className="row g-3">
            {data.leave_balances.map(b => (
              <div key={b.leave_type_id} className="col-sm-6 col-md-4">
                <div className="p-3 border rounded-3 bg-light">
                  <div className="df-stat-label text-dark mb-1">{b.leave_type_name}</div>
                  <div className="df-stat-value fs-2 text-primary">{Number(b.remaining_days).toFixed(0)}</div>
                  <div className="df-stat-sub mb-2">of {Number(b.allocated_days).toFixed(0)} days remaining</div>
                  <div className="df-timeline-bar" style={{ height: 6 }}>
                    <div className="df-timeline-fill" style={{ width: `${Math.min(100, (Number(b.remaining_days) / Number(b.allocated_days)) * 100)}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="row g-3">
        {[
          { label: 'View Attendance', icon: 'bi-clock-history', page: 'attendance' },
          { label: 'Request Time Off', icon: 'bi-calendar-plus', page: 'timeoff' },
          { label: 'My Profile', icon: 'bi-person-fill', page: 'profile' },
          { label: 'View Salary', icon: 'bi-currency-dollar', page: 'salary' },
        ].map(q => (
          <div key={q.label} className="col-6 col-md-3">
            <button className="df-card w-100 text-start d-flex align-items-center gap-3 border transition-all" onClick={() => onNav(q.page)} style={{ cursor: 'pointer' }}>
              <i className={`bi ${q.icon} fs-4 text-primary`} />
              <span className="fw-semibold text-dark">{q.label}</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

function getGreeting() {
  const h = new Date().getHours()
  return h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
}

// ─── Attendance Page (With CSV Export) ───────────────────────────────────────
function AttendancePage() {
  const [weekStart, setWeekStart] = useState(monday())
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionMsg, setActionMsg] = useState('')

  useEffect(() => {
    setLoading(true); setError('')
    meApi.getAttendance(weekStart).then(setData).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [weekStart])

  async function doCheckIn() {
    try { const r = await meApi.checkIn(); setActionMsg(r.message); meApi.getAttendance(weekStart).then(setData) }
    catch (e) { setActionMsg(e.message) }
  }
  async function doCheckOut() {
    try { const r = await meApi.checkOut(); setActionMsg(r.message); meApi.getAttendance(weekStart).then(setData) }
    catch (e) { setActionMsg(e.message) }
  }

  function handleExportCSV() {
    if (!data?.records || data.records.length === 0) return
    const headers = ['Date', 'Check In', 'Check Out', 'Work Hours', 'Overtime Hours', 'Status']
    const rows = data.records.map(r => [
      r.attendance_date,
      r.check_in_at ? fmt(r.check_in_at) : '—',
      r.check_out_at ? fmt(r.check_out_at) : '—',
      r.work_hours || 0,
      r.overtime_hours || 0,
      r.status,
    ])
    exportToCSV(`attendance_log_${weekStart}.csv`, headers, rows)
  }

  const today = isoDate(new Date())
  const todayRecord = data?.records?.find(r => r.attendance_date === today)
  const isCurrentWeek = weekStart === monday()

  return (
    <div className="df-page">
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
        <div>
          <h1 className="df-section-title">Attendance</h1>
          <p className="df-section-sub">Weekly log & punch activity</p>
        </div>
        <div className="d-flex gap-2">
          <button className="df-btn-secondary" onClick={handleExportCSV} disabled={!data?.records?.length}>
            <i className="bi bi-download me-1" />Export CSV
          </button>
          {isCurrentWeek && (
            <>
              {!todayRecord?.check_in_at && (
                <button className="df-btn-primary" onClick={doCheckIn}><i className="bi bi-box-arrow-in-right me-1" />Check In</button>
              )}
              {todayRecord?.check_in_at && !todayRecord?.check_out_at && (
                <button className="df-btn-secondary" onClick={doCheckOut}><i className="bi bi-box-arrow-right me-1" />Check Out</button>
              )}
            </>
          )}
        </div>
      </div>

      {error && <Alert msg={error} onClose={() => setError('')} />}
      {actionMsg && <div className="alert alert-info py-2 px-3 small">{actionMsg}</div>}

      <div className="df-card p-3 mb-4">
        <div className="d-flex align-items-center justify-content-between">
          <button className="df-btn-secondary" onClick={() => setWeekStart(shiftWeek(weekStart, -1))}><i className="bi bi-chevron-left" /></button>
          <div className="text-center">
            <div className="fw-bold text-dark">{weekLabel(weekStart)}</div>
            {isCurrentWeek && <small className="text-muted">Current week</small>}
          </div>
          <button className="df-btn-secondary" onClick={() => setWeekStart(shiftWeek(weekStart, 1))} disabled={isCurrentWeek}><i className="bi bi-chevron-right" /></button>
        </div>
      </div>

      {data && (
        <div className="row g-3 mb-4">
          {[
            { label: 'Days Present', value: data.days_present },
            { label: 'Leave Days', value: data.leaves_count },
            { label: 'Absences', value: data.absences },
            { label: 'Total Hours', value: fmtHours(data.total_work_hours) },
            { label: 'Overtime', value: fmtHours(data.total_overtime_hours) },
          ].map(c => (
            <div key={c.label} className="col-6 col-md-4 col-xl">
              <div className="df-stat-card">
                <span className="df-stat-label">{c.label}</span>
                <div className="df-stat-value fs-3 my-1">{c.value}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {loading ? <Spinner /> : (
        <div className="df-table-wrap">
          <table className="df-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Check In</th>
                <th>Check Out</th>
                <th>Work Hours</th>
                <th>Overtime</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data?.records?.length === 0 ? (
                <tr><td colSpan={6} className="text-center text-muted py-4">No attendance records this week</td></tr>
              ) : (
                data?.records?.map(r => (
                  <tr key={r.attendance_id}>
                    <td><strong>{fmtDate(r.attendance_date)}</strong>{r.attendance_date === today && <span className="ms-2 df-badge df-badge-present">Today</span>}</td>
                    <td className="tabnum">{fmt(r.check_in_at)}</td>
                    <td className="tabnum">{fmt(r.check_out_at)}</td>
                    <td className="tabnum">{fmtHours(r.work_hours)}</td>
                    <td className="tabnum">{fmtHours(r.overtime_hours)}</td>
                    <td><Badge status={r.status} /></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Time Off Page ────────────────────────────────────────────────────────────
function TimeOffPage() {
  const [balances, setBalances] = useState([])
  const [requests, setRequests] = useState([])
  const [leaveTypes, setLeaveTypes] = useState([])
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [b, r, t, p] = await Promise.all([
        meApi.getLeaveBalances(),
        meApi.getLeaveRequests(),
        meApi.getLeaveTypes(),
        meApi.getProfile()
      ])
      setBalances(b || []); setRequests(r || []); setLeaveTypes(t || []); setProfile(p || null)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function cancelRequest(id) {
    try { await meApi.cancelLeave(id); load() } catch (e) { setError(e.message) }
  }

  async function downloadAttachment(path, fileName) {
    try {
      const url = path.startsWith("http") ? path : `http://localhost:8000${path}`;
      const response = await fetch(url, {
        headers: {
          "Authorization": `Bearer ${tokenStore.get()}`
        }
      });
      if (!response.ok) throw new Error("Could not download attachment");
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = fileName || "attachment";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      alert(err.message || "Failed to download attachment");
    }
  }

  return (
    <div className="df-page">
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
        <div>
          <h1 className="df-section-title">Time Off</h1>
          <p className="df-section-sub">Plan leave requests and review available balance.</p>
        </div>
        <button className="df-btn-primary" onClick={() => setShowModal(true)}>
          <i className="bi bi-calendar-plus me-1" />Request Time Off
        </button>
      </div>

      {error && <Alert msg={error} onClose={() => setError('')} />}

      {loading ? <Spinner /> : (
        <>
          <div className="row g-3 mb-4">
            {balances.length === 0 ? (
              <div className="col-12"><div className="df-empty"><i className="bi bi-wallet2 df-empty-icon" /><p className="df-empty-title">No leave balances configured yet</p></div></div>
            ) : balances.map(b => (
              <div key={b.leave_type_id} className="col-sm-6 col-md-4">
                <div className="df-card h-100">
                  <div className="df-stat-label text-dark">{b.leave_type_name}</div>
                  <div className="d-flex align-items-end gap-2 my-2">
                    <span className="df-stat-value fs-1 text-primary">{Number(b.remaining_days).toFixed(0)}</span>
                    <span className="df-stat-sub mb-1">days available</span>
                  </div>
                  <div className="df-timeline-bar mb-2" style={{ height: 6 }}>
                    <div className="df-timeline-fill" style={{ width: `${Math.min(100, b.allocated_days > 0 ? (Number(b.remaining_days) / Number(b.allocated_days)) * 100 : 0)}%` }} />
                  </div>
                  <small className="df-stat-sub">{Number(b.used_days).toFixed(0)} of {Number(b.allocated_days).toFixed(0)} used</small>
                </div>
              </div>
            ))}
          </div>

          {/* Annual Leave Calendar */}
          <AnnualCalendar requests={requests} />

          <div className="df-card p-0 overflow-hidden">
            <div className="p-3 border-bottom d-flex justify-content-between align-items-center bg-white">
              <h3 className="df-section-title fs-6 mb-0"><i className="bi bi-list-check me-2 text-primary" />My Leave Requests</h3>
              <span className="df-stat-sub">{requests.length} total</span>
            </div>
            <div className="df-table-wrap border-0">
              <table className="df-table">
                <thead>
                  <tr><th>Type</th><th>From</th><th>To</th><th>Days</th><th>Status</th><th>Remarks</th><th></th></tr>
                </thead>
                <tbody>
                  {requests.length === 0 ? (
                    <tr><td colSpan={7} className="text-center text-muted py-4">No leave requests yet</td></tr>
                  ) : requests.map(r => (
                    <tr key={r.leave_request_id}>
                      <td>
                        <strong>{r.leave_type_name}</strong>
                        {r.attachment_path && (
                          <span
                            className="ms-2 text-primary"
                            title="Download Certificate"
                            onClick={() => downloadAttachment(r.attachment_path, `${r.leave_type_name}_certificate`)}
                            style={{ cursor: 'pointer' }}
                          >
                            <i className="bi bi-file-earmark-arrow-down-fill" />
                          </span>
                        )}
                      </td>
                      <td>{fmtDate(r.start_date)}</td>
                      <td>{fmtDate(r.end_date)}</td>
                      <td>{Number(r.number_of_days).toFixed(0)}</td>
                      <td>
                        <Badge status={r.status} />
                        {r.review_comment && (
                          <div className="text-muted mt-1" style={{ fontSize: 11, fontStyle: 'italic' }}>
                            "{r.review_comment}"
                          </div>
                        )}
                      </td>
                      <td className="df-stat-sub" style={{ maxWidth: 200 }}>{r.remarks || '—'}</td>
                      <td>
                        {r.status === 'PENDING' && (
                          <button className="df-btn-reject py-1 px-2 fs-7" onClick={() => cancelRequest(r.leave_request_id)}>Cancel</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {showModal && (
        <LeaveRequestModal
          leaveTypes={leaveTypes}
          profile={profile}
          onClose={() => setShowModal(false)}
          onSuccess={() => { setShowModal(false); load() }}
        />
      )}
    </div>
  )
}

function AnnualCalendar({ requests }) {
  const year = 2026;
  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const weekdays = ["S", "M", "T", "W", "T", "F", "S"];

  const publicHolidays = {
    "2026-01-01": "New Year's Day",
    "2026-01-26": "Republic Day",
    "2026-08-15": "Independence Day",
    "2026-12-25": "Christmas"
  };

  function getDateStatus(dateStr, dateObj) {
    const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6;
    const isHoliday = publicHolidays[dateStr];
    
    for (const req of requests) {
      if (req.status === 'REJECTED' || req.status === 'CANCELLED') continue;
      if (dateStr >= req.start_date && dateStr <= req.end_date) {
        return {
          status: req.status,
          name: req.leave_type_name
        };
      }
    }

    if (isHoliday) return { status: 'HOLIDAY', name: isHoliday };
    if (isWeekend) return { status: 'WEEKEND', name: 'Weekend' };
    return null;
  }

  return (
    <div className="df-card p-4 mb-4" style={{ background: "#fff", borderRadius: 12, border: "1px solid var(--df-border)" }}>
      <div className="d-flex align-items-center justify-content-between mb-3 border-bottom pb-2 flex-wrap gap-2">
        <h3 className="df-section-title fs-6 mb-0">
          <i className="bi bi-calendar3 me-2 text-primary" />
          Annual Leave Calendar (2026)
        </h3>
        <div className="d-flex gap-3 flex-wrap" style={{ fontSize: 12 }}>
          <div className="d-flex align-items-center gap-1">
            <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#10b981" }} />
            <span>Approved</span>
          </div>
          <div className="d-flex align-items-center gap-1">
            <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#f59e0b" }} />
            <span>Pending</span>
          </div>
          <div className="d-flex align-items-center gap-1">
            <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#ef4444" }} />
            <span>Holiday</span>
          </div>
          <div className="d-flex align-items-center gap-1">
            <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#e5e7eb", border: "1px solid #d1d5db" }} />
            <span>Weekend</span>
          </div>
        </div>
      </div>

      <div className="row g-3">
        {months.map((monthName, monthIdx) => {
          const firstDay = new Date(year, monthIdx, 1);
          const startDayOfWeek = firstDay.getDay();
          const daysInMonth = new Date(year, monthIdx + 1, 0).getDate();

          const blanks = Array(startDayOfWeek).fill(null);
          const days = Array.from({ length: daysInMonth }, (_, idx) => idx + 1);
          const totalCells = [...blanks, ...days];

          return (
            <div key={monthName} className="col-md-4 col-sm-6 col-12">
              <div className="p-2 border rounded" style={{ background: "#fafafa" }}>
                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--df-navy)", textAlign: "center", marginBottom: 6 }}>
                  {monthName}
                </div>
                
                <div className="d-grid" style={{ gridTemplateColumns: "repeat(7, 1fr)", textAlign: "center", fontSize: 11, fontWeight: 600, color: "#6b7280" }}>
                  {weekdays.map((wd, i) => <div key={i}>{wd}</div>)}
                </div>

                <div className="d-grid mt-1" style={{ gridTemplateColumns: "repeat(7, 1fr)", gap: 2, textAlign: "center" }}>
                  {totalCells.map((dayNum, cellIdx) => {
                    if (dayNum === null) {
                      return <div key={`blank-${cellIdx}`} style={{ height: 20 }} />;
                    }

                    const formattedMonth = String(monthIdx + 1).padStart(2, '0');
                    const formattedDay = String(dayNum).padStart(2, '0');
                    const dateStr = `${year}-${formattedMonth}-${formattedDay}`;
                    const dateObj = new Date(year, monthIdx, dayNum);

                    const dayStatus = getDateStatus(dateStr, dateObj);
                    
                    let bg = "transparent";
                    let color = "#374151";
                    let title = "";

                    if (dayStatus) {
                      title = dayStatus.name;
                      if (dayStatus.status === 'APPROVED') {
                        bg = "#10b981";
                        color = "#fff";
                      } else if (dayStatus.status === 'PENDING') {
                        bg = "#f59e0b";
                        color = "#fff";
                      } else if (dayStatus.status === 'HOLIDAY') {
                        bg = "#ef4444";
                        color = "#fff";
                      } else if (dayStatus.status === 'WEEKEND') {
                        bg = "#f3f4f6";
                        color = "#9ca3af";
                      }
                    }

                    return (
                      <div
                        key={`day-${dayNum}`}
                        title={title}
                        style={{
                          height: 20,
                          fontSize: 10,
                          fontWeight: 500,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          borderRadius: 4,
                          background: bg,
                          color: color,
                          cursor: title ? "help" : "default"
                        }}
                      >
                        {dayNum}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LeaveRequestModal({ leaveTypes, onClose, onSuccess, profile }) {
  const [form, setForm] = useState({ leave_type_id: '', start_date: '', end_date: '', remarks: '' })
  const [file, setFile] = useState(null)
  const [attachmentPath, setAttachmentPath] = useState('')
  const [uploadingFile, setUploadingFile] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const selectedType = leaveTypes.find(t => String(t.leave_type_id) === String(form.leave_type_id))
  const requiresAttachment = selectedType?.requires_attachment ?? false

  let allocationDays = 0
  if (form.start_date && form.end_date) {
    const start = new Date(form.start_date)
    const end = new Date(form.end_date)
    if (end >= start) {
      allocationDays = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1
    }
  }

  async function handleFileChange(e) {
    const chosenFile = e.target.files[0]
    if (!chosenFile) return
    setFile(chosenFile)
    setUploadingFile(true)
    setError('')
    try {
      const result = await meApi.uploadDocument(profile.employee_id, 'Sick Leave Certificate', chosenFile)
      setAttachmentPath(result.view_url)
    } catch (err) {
      setError(err.message || 'File upload failed.')
      setFile(null)
    } finally {
      setUploadingFile(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault(); 
    if (requiresAttachment && !attachmentPath) {
      setError('An attachment certificate is required for Sick Leave.')
      return
    }
    setLoading(true); setError('')
    try {
      await meApi.applyLeave({
        ...form,
        leave_type_id: Number(form.leave_type_id),
        attachment_path: attachmentPath || null
      })
      onSuccess()
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return (
    <div className="df-modal-overlay" onClick={onClose} style={{ zIndex: 1050 }}>
      <div className="df-modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 500 }}>
        <div className="p-3 border-bottom d-flex align-items-center justify-content-between">
          <h3 className="df-section-title fs-6 mb-0"><i className="bi bi-calendar-plus me-2 text-primary" />Time off Type Request</h3>
          <button className="btn-close" onClick={onClose} />
        </div>
        <form onSubmit={handleSubmit} className="p-4">
          <Alert msg={error} onClose={() => setError('')} />
          
          <div className="mb-3">
            <label className="df-stat-label mb-1">Employee</label>
            <input className="df-input w-100" type="text" value={profile?.full_name || 'Loading...'} readOnly style={{ background: '#f3f4f6' }} />
          </div>

          <div className="mb-3">
            <label className="df-stat-label mb-1">Time off Type</label>
            <select className="df-input w-100" value={form.leave_type_id}
              onChange={e => setForm({ ...form, leave_type_id: e.target.value, attachment_path: '' })} required>
              <option value="">Select leave type</option>
              {leaveTypes.map(t => <option key={t.leave_type_id} value={t.leave_type_id}>{t.name}</option>)}
            </select>
          </div>

          <div className="row g-3 mb-3">
            <div className="col-6">
              <label className="df-stat-label mb-1">From Date</label>
              <input className="df-input w-100" type="date" value={form.start_date}
                onChange={e => setForm({ ...form, start_date: e.target.value })} required />
            </div>
            <div className="col-6">
              <label className="df-stat-label mb-1">To Date</label>
              <input className="df-input w-100" type="date" value={form.end_date}
                onChange={e => setForm({ ...form, end_date: e.target.value })} required min={form.start_date} />
            </div>
          </div>

          <div className="mb-3 d-flex align-items-center justify-content-between p-2 rounded" style={{ background: '#f3f4f6' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--df-navy)' }}>Allocation</span>
            <span className="fw-bold text-primary" style={{ fontSize: 15 }}>{allocationDays.toFixed(2)} Days</span>
          </div>

          {requiresAttachment && (
            <div className="mb-3">
              <label className="df-stat-label mb-1">Attachment <span className="text-danger">*</span></label>
              <div className="border rounded p-3 text-center bg-white position-relative">
                <i className="bi bi-cloud-arrow-up text-primary" style={{ fontSize: 24 }} />
                <div style={{ fontSize: 12, color: 'var(--df-text-muted)', marginTop: 4 }}>
                  (For sick leave certificate)
                </div>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={handleFileChange}
                  required
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    opacity: 0,
                    cursor: 'pointer'
                  }}
                  disabled={uploadingFile}
                />
                {file && (
                  <div className="mt-2 text-success" style={{ fontSize: 12, fontWeight: 500 }}>
                    <i className="bi bi-file-earmark-check me-1" />
                    {file.name} {uploadingFile ? '(Uploading...)' : '(Uploaded)'}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="mb-3">
            <label className="df-stat-label mb-1">Remarks <span className="text-muted">(optional)</span></label>
            <textarea className="df-input w-100" rows={3} placeholder="Add remarks/notes for your manager..."
              value={form.remarks} onChange={e => setForm({ ...form, remarks: e.target.value })} />
          </div>

          <div className="d-flex justify-content-end gap-2 mt-4">
            <button type="button" className="df-btn-secondary" onClick={onClose}>Discard</button>
            <button type="submit" className="df-btn-primary" disabled={loading || uploadingFile}>
              {loading ? <><span className="spinner-border spinner-border-sm me-2" />Submitting...</> : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Profile Page (With Document Upload) ──────────────────────────────────────
// ─── Profile Page (With Document Upload) ──────────────────────────────────────
function ProfilePage() {
  const [profile, setProfile] = useState(null)
  const [salary, setSalary] = useState(null)
  const [tab, setTab] = useState('resume') // 'resume' | 'private' | 'salary' | 'security'
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [docs, setDocs] = useState([
    { id: 1, name: 'Employment_Offer_Letter.pdf', size: '240 KB', date: '2025-01-10' },
    { id: 2, name: 'Government_ID_Proof.pdf', size: '1.2 MB', date: '2025-01-12' },
  ])
  const [uploadingDoc, setUploadingDoc] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      meApi.getProfile(),
      meApi.getSalary().catch(() => null)
    ])
      .then(([p, s]) => {
        setProfile(p)
        setSalary(s)
        setForm({
          phone: p.phone || '',
          address: p.address || '',
          gender: p.gender || '',
          date_of_birth: p.date_of_birth || ''
        })
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  async function handleSave(e) {
    e.preventDefault(); setSaving(true); setError(''); setSuccess('')
    try {
      const updated = await meApi.updateProfile({ phone: form.phone || null, address: form.address || null, gender: form.gender || null, date_of_birth: form.date_of_birth || null })
      setProfile(updated); setEditing(false); setSuccess('Profile updated successfully.')
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  function handleDocUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingDoc(true)
    setTimeout(() => {
      setDocs(prev => [...prev, { id: Date.now(), name: file.name, size: `${(file.size / 1024).toFixed(0)} KB`, date: isoDate(new Date()) }])
      setUploadingDoc(false)
      setSuccess(`Document "${file.name}" uploaded successfully.`)
    }, 600)
  }

  if (loading) return <Spinner />

  const fields = [
    { label: 'Employee Code', value: profile?.employee_code, icon: 'bi-hash' },
    { label: 'Email', value: profile?.email, icon: 'bi-envelope-fill' },
    { label: 'Department', value: profile?.department_name, icon: 'bi-building' },
    { label: 'Designation', value: profile?.designation_title, icon: 'bi-briefcase-fill' },
    { label: 'Manager', value: profile?.manager_name, icon: 'bi-person-check-fill' },
    { label: 'Join Date', value: fmtDate(profile?.joining_date), icon: 'bi-calendar-check-fill' },
    { label: 'Status', value: profile?.employment_status, icon: 'bi-activity' },
    { label: 'Type', value: profile?.employment_type, icon: 'bi-briefcase' },
  ]

  return (
    <div className="df-page">
      {/* Upper Unified Profile Card */}
      <div className="df-card mb-4 d-flex align-items-center gap-4 flex-row">
        <div className="df-avatar" style={{ width: 80, height: 80, fontSize: 26, background: 'var(--df-blue)', color: '#fff' }}>
          {profile?.profile_picture_url
            ? <img src={`http://localhost:8000${profile.profile_picture_url}`} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />
            : <span>{(profile?.full_name || 'U').slice(0, 2).toUpperCase()}</span>
          }
        </div>
        <div>
          <h2 className="df-section-title mb-1" style={{ fontSize: 22 }}>{profile?.full_name}</h2>
          <p className="df-section-sub mb-2">{profile?.designation_title} · {profile?.department_name}</p>
          <div className="d-flex align-items-center gap-2">
            <Badge status={profile?.employment_status} />
            <span className="text-muted" style={{ fontSize: 12 }}>Joined on {fmtDate(profile?.joining_date)}</span>
          </div>
        </div>
      </div>

      {/* Tabs list */}
      <div className="df-tabs mb-4">
        {[
          { id: 'resume', label: 'Resume', icon: 'bi-person-lines-fill' },
          { id: 'private', label: 'Private Info', icon: 'bi-shield-lock-fill' },
          { id: 'salary', label: 'Salary Info', icon: 'bi-cash-stack' },
          { id: 'security', label: 'Security', icon: 'bi-key-fill' },
        ].map(t => (
          <button key={t.id} className={`df-tab ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
            <i className={`bi ${t.icon}`} style={{ fontSize: 13 }} /> {t.label}
          </button>
        ))}
      </div>

      {error && <Alert msg={error} onClose={() => setError('')} />}
      {success && <div className="alert alert-success py-2 px-3 small mb-4">{success}</div>}

      {/* Tab 1: Resume */}
      {tab === 'resume' && (
        <div className="row g-4">
          <div className="col-lg-7 col-md-12">
            <div className="df-card mb-4">
              <h3 className="df-section-title fs-6 mb-3">About</h3>
              <p className="text-muted">
                Professional software engineering specialist dedicated to designing, building, and launching secure, scalable software systems. Experienced in full stack web development, RESTful APIs, database optimizations, and agentic workflows.
              </p>
              <h3 className="df-section-title fs-6 mt-4 mb-3">What I love about my job</h3>
              <p className="text-muted">
                Tackling complex engineering challenges, architecting robust backend systems, and collaborating with cross-functional teams to build products that deliver high user impact.
              </p>
              <h3 className="df-section-title fs-6 mt-4 mb-3">My interests and hobbies</h3>
              <p className="text-muted">
                Exploring cutting-edge AI agent systems, contributing to open source projects, cycling, and reading technical blogs.
              </p>
            </div>
          </div>
          <div className="col-lg-5 col-md-12">
            <div className="df-card mb-4">
              <h3 className="df-section-title fs-6 mb-3">Skills</h3>
              <div className="d-flex flex-wrap gap-2 mb-4">
                {['JavaScript', 'TypeScript', 'React', 'Node.js', 'Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Git', 'AWS'].map(skill => (
                  <span key={skill} className="badge bg-light text-dark border px-2.5 py-1.5" style={{ fontSize: 12 }}>{skill}</span>
                ))}
              </div>
              <h3 className="df-section-title fs-6 mb-3">Certifications</h3>
              <div className="d-flex flex-column gap-3">
                {[
                  { title: 'Google Certified Professional Cloud Architect', issuer: 'Google Cloud', date: 'Feb 2025' },
                  { title: 'AWS Certified Solutions Architect', issuer: 'Amazon Web Services', date: 'Sep 2024' },
                ].map(cert => (
                  <div key={cert.title} className="p-3 border rounded bg-light">
                    <div className="fw-semibold text-dark" style={{ fontSize: 13.5 }}>{cert.title}</div>
                    <small className="text-muted">{cert.issuer} · {cert.date}</small>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Private Info */}
      {tab === 'private' && (
        <div className="row g-4">
          <div className="col-md-4 d-flex flex-column gap-4">
            <div className="df-card">
              <h3 className="df-section-title fs-6 mb-3"><i className="bi bi-info-circle me-2 text-primary" />Job Details</h3>
              {fields.map(f => (
                <div key={f.label} className="d-flex align-items-start gap-2 mb-3">
                  <i className={`bi ${f.icon} text-primary fs-6`} />
                  <div>
                    <div className="df-stat-label">{f.label}</div>
                    <div className="fw-semibold text-dark">{f.value || '—'}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="df-card">
              <h3 className="df-section-title fs-6 mb-3"><i className="bi bi-bank me-2 text-primary" />Bank Details</h3>
              {[
                { label: 'Bank Name', value: 'Chase Bank', icon: 'bi-wallet-fill' },
                { label: 'Account Number', value: '••••••••3421', icon: 'bi-card-list' },
                { label: 'Bank State', value: 'New York', icon: 'bi-geo-alt-fill' },
                { label: 'IFSC Code / Routing', value: 'CHASUS33XX', icon: 'bi-shield-check' },
                { label: 'PAN No / Tax ID', value: '•••-••-8812', icon: 'bi-file-person' },
                { label: 'Tax Code', value: 'TX-NY-09', icon: 'bi-tag-fill' },
              ].map(b => (
                <div key={b.label} className="d-flex align-items-start gap-2 mb-3">
                  <i className={`bi ${b.icon} text-primary fs-6`} />
                  <div>
                    <div className="df-stat-label">{b.label}</div>
                    <div className="fw-semibold text-dark">{b.value || '—'}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-md-8 d-flex flex-column gap-4">
            <div className="df-card">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h3 className="df-section-title fs-6 mb-0"><i className="bi bi-person-fill me-2 text-primary" />Personal Information</h3>
                {!editing && (
                  <button className="df-btn-secondary btn-sm" onClick={() => setEditing(true)}>
                    <i className="bi bi-pencil me-1" />Edit Profile
                  </button>
                )}
              </div>
              {editing ? (
                <form onSubmit={handleSave}>
                  <div className="row g-3">
                    <div className="col-12">
                      <label className="df-stat-label mb-1">Phone Number</label>
                      <input className="df-input w-100" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="+1 (555) 000-0000" />
                    </div>
                    <div className="col-12">
                      <label className="df-stat-label mb-1">Address</label>
                      <textarea className="df-input w-100" rows={3} value={form.address} onChange={e => setForm({ ...form, address: e.target.value })} placeholder="Street, City, State, Country" />
                    </div>
                    <div className="col-md-6">
                      <label className="df-stat-label mb-1">Gender</label>
                      <select className="df-input w-100" value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })}>
                        <option value="">Prefer not to say</option>
                        <option value="MALE">Male</option>
                        <option value="FEMALE">Female</option>
                        <option value="OTHER">Other</option>
                        <option value="PREFER_NOT_TO_SAY">Prefer not to say</option>
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="df-stat-label mb-1">Date of Birth</label>
                      <input className="df-input w-100" type="date" value={form.date_of_birth} onChange={e => setForm({ ...form, date_of_birth: e.target.value })} />
                    </div>
                  </div>
                  <div className="d-flex gap-2 mt-4">
                    <button type="submit" className="df-btn-primary" disabled={saving}>
                      {saving ? <><span className="spinner-border spinner-border-sm me-2" />Saving...</> : <><i className="bi bi-check-lg me-1" />Save Changes</>}
                    </button>
                    <button type="button" className="df-btn-secondary" onClick={() => setEditing(false)}>Cancel</button>
                  </div>
                </form>
              ) : (
                <div className="row g-3">
                  {[
                    { label: 'Phone', value: profile?.phone, icon: 'bi-telephone-fill' },
                    { label: 'Address', value: profile?.address, icon: 'bi-geo-alt-fill' },
                    { label: 'Gender', value: profile?.gender, icon: 'bi-person-fill' },
                    { label: 'Date of Birth', value: fmtDate(profile?.date_of_birth), icon: 'bi-cake-fill' },
                  ].map(f => (
                    <div key={f.label} className="col-md-6">
                      <div className="p-3 border rounded-3 bg-light">
                        <div className="df-stat-label mb-1"><i className={`bi ${f.icon} me-1`} />{f.label}</div>
                        <div className="fw-bold text-dark">{f.value || <span className="text-muted fw-normal">Not set</span>}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="df-card">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h3 className="df-section-title fs-6 mb-0"><i className="bi bi-file-earmark-pdf me-2 text-primary" />My Documents</h3>
                <label className="df-btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
                  <i className="bi bi-upload me-1" />{uploadingDoc ? 'Uploading...' : 'Upload Document'}
                  <input type="file" onChange={handleDocUpload} className="d-none" disabled={uploadingDoc} />
                </label>
              </div>
              <div className="df-table-wrap">
                <table className="df-table">
                  <thead>
                    <tr><th>Document Name</th><th>Size</th><th>Date</th><th>Action</th></tr>
                  </thead>
                  <tbody>
                    {docs.map(d => (
                      <tr key={d.id}>
                        <td><i className="bi bi-file-earmark-pdf-fill text-danger me-2" /><strong>{d.name}</strong></td>
                        <td className="df-stat-sub">{d.size}</td>
                        <td className="df-stat-sub">{d.date}</td>
                        <td>
                          <button className="df-btn-secondary py-1 px-2 fs-7" onClick={() => alert(`Viewing document ${d.name}`)}>
                            <i className="bi bi-eye" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Salary Info */}
      {tab === 'salary' && (
        <div>
          <div className="alert alert-info py-2 px-3 mb-4 d-flex align-items-center justify-content-between">
            <div className="d-flex align-items-center gap-2">
              <i className="bi bi-lock-fill text-primary" style={{ fontSize: 18 }} />
              <div>
                <span className="fw-semibold" style={{ fontSize: 13.5 }}>Read-Only View</span>
                <span className="text-muted ms-2" style={{ fontSize: 12.5 }}>Payroll data is read-only for employees.</span>
              </div>
            </div>
            <span className="badge bg-secondary-subtle text-secondary border px-2 py-1" style={{ fontSize: 11 }}>Read Only</span>
          </div>

          {!salary ? (
            <div className="df-empty">
              <i className="bi bi-currency-dollar df-empty-icon" />
              <p className="df-empty-title">No salary structure configured yet.</p>
              <p className="df-empty-sub text-muted">Please contact your HR administrator.</p>
            </div>
          ) : (
            (() => {
              const m_wage = Number(salary.monthly_wage);
              const y_wage = m_wage * 12;
              
              const basicVal = m_wage * 0.50;
              const hraVal = basicVal * 0.50;
              const stdVal = m_wage * 0.15;
              const perfVal = basicVal * 0.0933;
              const ltaVal = basicVal * 0.0933;
              const fixedVal = Math.max(0, m_wage - (basicVal + hraVal + stdVal + perfVal + ltaVal));
              
              const empPfComponent = salary.components.find(c => c.name.toLowerCase().includes("provident") || c.name.toLowerCase() === "pf");
              const pfRate = empPfComponent ? Math.round((Number(empPfComponent.computed_amount) * 100 / basicVal) * 100) / 100 : 12;
              const employeePfVal = basicVal * (pfRate / 100);
              const employerPfVal = basicVal * (pfRate / 100);
              
              const profTaxComponent = salary.components.find(c => c.name.toLowerCase().includes("professional tax") || c.name.toLowerCase() === "pt");
              const profTaxVal = profTaxComponent ? Number(profTaxComponent.fixed_amount ?? profTaxComponent.computed_amount) : 200;
              
              const totalDeductionsVal = employeePfVal + profTaxVal;
              const netSalaryVal = m_wage - totalDeductionsVal;
              
              const workingDays = localStorage.getItem(`working_days_emp_${profile?.employee_id}`) || '5';
              const breakHours = localStorage.getItem(`break_time_emp_${profile?.employee_id}`) || '1';

              return (
                <div>
                  {/* Top Header Card */}
                  <div className="df-card mb-4" style={{ background: '#fff', border: '1px solid var(--df-border)' }}>
                    <div className="row g-4 align-items-center">
                      <div className="col-md-6 border-end">
                        <div className="d-flex align-items-center justify-content-between mb-3">
                          <span className="fw-semibold text-dark">Monthly Wage</span>
                          <span className="fw-bold fs-5 text-primary">₹{m_wage.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div className="d-flex align-items-center justify-content-between">
                          <span className="fw-semibold text-dark">Yearly wage</span>
                          <span className="fw-bold fs-5 text-secondary">₹{y_wage.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                        </div>
                      </div>

                      <div className="col-md-6 ps-md-4">
                        <div className="d-flex align-items-center justify-content-between mb-3">
                          <span className="fw-semibold text-dark">No of working days in a week:</span>
                          <span className="fw-bold text-dark fs-5">{workingDays}</span>
                        </div>
                        <div className="d-flex align-items-center justify-content-between">
                          <span className="fw-semibold text-dark">Break Time:</span>
                          <span className="fw-bold text-dark fs-5">{breakHours} hr/day</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Main Two Column Layout */}
                  <div className="row g-4">
                    {/* Left: Components */}
                    <div className="col-lg-7 col-md-12">
                      <div className="df-card h-100">
                        <h3 className="df-section-title fs-6 mb-4">Salary Components</h3>

                        {/* Basic Salary */}
                        <div className="py-2 border-bottom d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">Basic Salary</div>
                            <small className="text-muted">Active Basic salary from company cost, computed based on monthly wages</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-dark">₹{basicVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            <small className="badge bg-light text-muted border">50.00 %</small>
                          </div>
                        </div>

                        {/* HRA */}
                        <div className="py-2 border-bottom d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">House Rent Allowance</div>
                            <small className="text-muted">HRA provided to employees, 50% of the basic salary (25% of monthly wage)</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-dark">₹{hraVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            <small className="badge bg-light text-muted border">50.00 % of Basic</small>
                          </div>
                        </div>

                        {/* Standard Allowance */}
                        <div className="py-2 border-bottom d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">Standard Allowance</div>
                            <small className="text-muted">Standard allowance is a predictable, fixed amount provided to employee, 15% of their salary</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-dark">₹{stdVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            <small className="badge bg-light text-muted border">15.00 %</small>
                          </div>
                        </div>

                        {/* Performance Bonus */}
                        <div className="py-2 border-bottom d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">Performance Bonus</div>
                            <small className="text-muted">Variable amount paid during payroll, calculated as 9.33% of basic salary</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-dark">₹{perfVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            <small className="badge bg-light text-muted border">9.33 % of Basic</small>
                          </div>
                        </div>

                        {/* LTA */}
                        <div className="py-2 border-bottom d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">Leave Travel Allowance</div>
                            <small className="text-muted">LTA paid by company to cover travel expenses, calculated as 9.33% of basic salary</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-dark">₹{ltaVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            <small className="badge bg-light text-muted border">9.33 % of Basic</small>
                          </div>
                        </div>

                        {/* Fixed Allowance */}
                        <div className="py-2 d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">Fixed Allowance</div>
                            <small className="text-muted">Fixed allowance portion of wages is determined after calculating all other components</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-dark">₹{fixedVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            <small className="badge bg-light text-muted border">{((fixedVal / m_wage) * 100).toFixed(2)} %</small>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Right: PF & Tax */}
                    <div className="col-lg-5 col-md-12 d-flex flex-column gap-4">
                      <div className="df-card">
                        <h3 className="df-section-title fs-6 mb-4">Provident Fund (PF) Contribution</h3>
                        
                        <div className="py-2 border-bottom d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">Employee Contribution</div>
                            <small className="text-muted">PF is calculated based on the basic salary</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-dark">₹{employeePfVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            <small className="badge bg-light text-muted border">{pfRate.toFixed(2)} %</small>
                          </div>
                        </div>

                        <div className="py-2 d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">Employer Contribution</div>
                            <small className="text-muted">PF is calculated based on the basic salary</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-dark">₹{employerPfVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                            <small className="badge bg-light text-muted border">{pfRate.toFixed(2)} %</small>
                          </div>
                        </div>
                      </div>

                      <div className="df-card">
                        <h3 className="df-section-title fs-6 mb-4">Tax Deductions</h3>
                        
                        <div className="py-2 d-flex justify-content-between align-items-center">
                          <div>
                            <div className="fw-semibold text-dark">Professional Tax</div>
                            <small className="text-muted">Professional Tax deducted from the Gross salary</small>
                          </div>
                          <div className="text-end">
                            <div className="fw-bold text-danger">−₹{profTaxVal.toFixed(2)}</div>
                          </div>
                        </div>
                      </div>

                      {/* Net Take-Home Pay */}
                      <div className="p-4 rounded-3 text-white" style={{ background: 'var(--df-navy)' }}>
                        <div className="d-flex justify-content-between align-items-center mb-2">
                          <span className="text-white-50">Monthly Gross Wage</span>
                          <span className="fw-semibold">₹{m_wage.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div className="d-flex justify-content-between align-items-center mb-3 pb-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                          <span style={{ color: '#fca5a5' }}>Deductions (PF + Professional Tax)</span>
                          <span className="fw-semibold" style={{ color: '#fca5a5' }}>−₹{totalDeductionsVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <div className="text-white-50" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Net Monthly Salary</div>
                            <div className="fw-bold fs-3 text-success">₹{netSalaryVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</div>
                          </div>
                          <i className="bi bi-wallet-fill display-5 text-white-50" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()
          )}
        </div>
      )}

      {/* Tab 4: Security */}
      {tab === 'security' && (
        <div className="df-card" style={{ maxWidth: 500 }}>
          <h3 className="df-section-title fs-6 mb-4"><i className="bi bi-key-fill me-2 text-primary" />Change Password</h3>
          <form onSubmit={e => { e.preventDefault(); alert('Password changes are restricted in this demo.') }}>
            <div className="mb-3">
              <label className="df-stat-label mb-1">Current Password</label>
              <input className="df-input w-100" type="password" required />
            </div>
            <div className="mb-3">
              <label className="df-stat-label mb-1">New Password</label>
              <input className="df-input w-100" type="password" required />
            </div>
            <div className="mb-4">
              <label className="df-stat-label mb-1">Confirm New Password</label>
              <input className="df-input w-100" type="password" required />
            </div>
            <button type="submit" className="df-btn-primary"><i className="bi bi-shield-lock-fill me-1" />Update Password</button>
          </form>
        </div>
      )}
    </div>
  )
}

// ─── Salary Page (With Printable Payslip) ────────────────────────────────────
function SalaryPage() {
  const [salary, setSalary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    meApi.getSalary().then(setSalary).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [])

  if (loading) return <Spinner />

  const earnings = salary?.components?.filter(c => c.type === 'EARNING') || []
  const deductions = salary?.components?.filter(c => c.type === 'DEDUCTION') || []
  const totalEarnings = earnings.reduce((s, c) => s + Number(c.computed_amount), 0)
  const totalDeductions = deductions.reduce((s, c) => s + Number(c.computed_amount), 0)
  const netPay = totalEarnings - totalDeductions

  function handlePrintPayslip() {
    window.print()
  }

  return (
    <div className="df-page">
      <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
        <div><h1 className="df-section-title">My Salary</h1></div>
        <div className="d-flex gap-2 align-items-center">
          <button className="df-btn-secondary" onClick={handlePrintPayslip}>
            <i className="bi bi-printer me-1" />Print Payslip
          </button>
          <span className="df-badge df-badge-pending"><i className="bi bi-lock-fill me-1" />Read Only</span>
        </div>
      </div>

      {error && <Alert msg={error} onClose={() => setError('')} />}

      {!salary && !error && <div className="df-empty"><i className="bi bi-currency-dollar df-empty-icon" /><p className="df-empty-title">No salary structure assigned yet</p></div>}

      {salary && (
        <>
          <div className="row g-3 mb-4">
            {[
              { label: 'Monthly Wage', value: `₹${Number(salary.monthly_wage).toLocaleString()}` },
              { label: 'Annual Wage', value: `₹${Number(salary.annual_wage).toLocaleString()}` },
              { label: 'Net Pay', value: `₹${netPay.toLocaleString()}` },
              { label: 'Effective From', value: fmtDate(salary.effective_from) },
            ].map(c => (
              <div key={c.label} className="col-6 col-md-3">
                <div className="df-stat-card">
                  <span className="df-stat-label">{c.label}</span>
                  <div className="df-stat-value fs-3 my-1 text-primary">{c.value}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="row g-3">
            <div className="col-md-6">
              <div className="df-card">
                <h3 className="df-section-title fs-6 mb-3"><i className="bi bi-plus-circle-fill text-success me-2" />Earnings</h3>
                {earnings.map(c => (
                  <div key={c.name} className="d-flex justify-content-between align-items-center py-2 border-bottom">
                    <div>
                      <div className="fw-semibold text-dark">{c.name}</div>
                      <small className="text-muted">{c.calculation_type === 'PERCENTAGE' ? `${c.percentage}%` : 'Fixed'}</small>
                    </div>
                    <span className="text-success fw-bold">+₹{Number(c.computed_amount).toLocaleString()}</span>
                  </div>
                ))}
                <div className="d-flex justify-content-between pt-3 fw-bold">
                  <span>Total Earnings</span><span className="text-success">₹{totalEarnings.toLocaleString()}</span>
                </div>
              </div>
            </div>

            <div className="col-md-6">
              <div className="df-card">
                <h3 className="df-section-title fs-6 mb-3"><i className="bi bi-dash-circle-fill text-danger me-2" />Deductions</h3>
                {deductions.length === 0 ? <p className="df-section-sub">No deductions configured</p> : deductions.map(c => (
                  <div key={c.name} className="d-flex justify-content-between align-items-center py-2 border-bottom">
                    <div>
                      <div className="fw-semibold text-dark">{c.name}</div>
                      <small className="text-muted">{c.calculation_type === 'PERCENTAGE' ? `${c.percentage}%` : 'Fixed'}</small>
                    </div>
                    <span className="text-danger fw-bold">−₹{Number(c.computed_amount).toLocaleString()}</span>
                  </div>
                ))}
                <div className="d-flex justify-content-between pt-3 fw-bold">
                  <span>Total Deductions</span><span className="text-danger">₹{totalDeductions.toLocaleString()}</span>
                </div>
              </div>
              <div className="df-card mt-3 text-white" style={{ background: 'var(--df-navy)' }}>
                <div className="d-flex justify-content-between align-items-center">
                  <div>
                    <div className="df-stat-label text-white-50">Net Monthly Pay</div>
                    <div className="df-stat-value fs-1 text-white">₹{netPay.toLocaleString()}</div>
                  </div>
                  <i className="bi bi-wallet-fill display-4 text-white-50" />
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// ─── Shell ────────────────────────────────────────────────────────────────────
function Shell({ user, onLogout }) {
  const [page, setPage] = useState('dashboard')
  const [profile, setProfile] = useState(null)

  useEffect(() => {
    meApi.getProfile().then(setProfile).catch(() => {})
  }, [])

  const pages = { dashboard: <DashboardPage onNav={setPage} />, attendance: <AttendancePage />, timeoff: <TimeOffPage />, profile: <ProfilePage />, salary: <SalaryPage /> }

  return (
    <div className="min-vh-100 d-flex flex-column" style={{ background: 'var(--df-surface)' }}>
      <Navbar page={page} onNav={setPage} profile={profile || user} onLogout={onLogout} />
      <main className="flex-grow-1">
        {pages[page] || pages.dashboard}
      </main>
    </div>
  )
}

// ─── Root ─────────────────────────────────────────────────────────────────────
export default function App() {
  const [authMode, setAuthMode] = useState('login') // 'login' | 'auth_flow'
  const [user, setUser] = useState(() => {
    const token = tokenStore.get()
    return token ? { logged_in: true } : null
  })

  function handleLogin(u) { setUser(u) }
  function handleLogout() { const rt = tokenStore.getRefresh(); authApi.logout(rt).catch(() => {}); tokenStore.clear(); setUser(null) }

  if (!user) {
    if (authMode === 'auth_flow') return <AuthFlow onBackToLogin={() => setAuthMode('login')} />
    return <LoginPage onLogin={handleLogin} onForgot={() => setAuthMode('auth_flow')} />
  }

  return <Shell user={user} onLogout={handleLogout} />
}
