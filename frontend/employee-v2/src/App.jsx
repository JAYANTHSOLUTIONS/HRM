import { useState, useEffect, useCallback, createContext, useContext, useRef } from 'react'
import { authApi, meApi, tokenStore } from './api'
import loginBanner from './login_banner.jpg'
import logoImg from './logo.png'
import rocketIcon from './rocket_icon.jpg'
import employeeBanner from './employee_banner.jpg'
import faviconImg from './favicon.png'

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
    <div className="d-flex align-items-center justify-content-center min-vh-100" style={{ background: "#dce4f7", padding: "30px" }}>
      <div className="shadow-lg d-flex p-4 p-lg-5" style={{ maxWidth: "1040px", width: "100%", minHeight: "580px", borderRadius: "28px", background: "#ffffff" }}>
        <div className="row w-100 g-4 g-lg-5 align-items-center">
          
          {/* Left Column: Isometric illustration and text */}
          <div className="col-md-6 d-none d-md-block">
            <div className="d-flex flex-column h-100 justify-content-center">
              <img 
                src={employeeBanner} 
                alt="Workspace Illustration" 
                style={{ width: "100%", maxHeight: "330px", objectFit: "contain" }} 
              />
              <div className="mt-4 d-flex justify-content-between align-items-end">
                <div style={{ maxWidth: "340px" }}>
                  <h4 style={{ color: "#2d1299", fontWeight: 700, fontSize: "18px", marginBottom: "8px" }}>
                    Manage your workforce the easiest way
                  </h4>
                  <p className="text-muted mb-0" style={{ fontSize: "12.5px", lineHeight: "1.5" }}>
                    Enjoy an easy to use management system for the growth of your business projects.
                  </p>
                </div>
                {/* 3 Pagination dots */}
                <div className="d-flex flex-column gap-1 ms-3">
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#2d1299" }} />
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#cbd5e1" }} />
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#cbd5e1" }} />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Purple styled login form */}
          <div className="col-md-6 col-12">
            <div className="px-lg-4" style={{ maxWidth: "420px", margin: "0 auto" }}>
              
              <h2 className="mb-4" style={{ color: "#2d1299", fontWeight: 800, fontSize: "30px", letterSpacing: "-0.5px" }}>
                Hello,<br />Welcome Back!
              </h2>

              <form onSubmit={handleSubmit}>
                <Alert msg={error} onClose={() => setError('')} />
                
                {/* Light grey rounded login input */}
                <div className="mb-3">
                  <input 
                    className="w-100 py-3 px-4 border-0" 
                    style={{ background: "#f1f3f9", borderRadius: "10px", outline: "none", fontSize: "14.5px" }} 
                    type="email" 
                    placeholder="Email or username" 
                    value={email} 
                    onChange={e => setEmail(e.target.value)} 
                    required 
                    autoFocus 
                  />
                </div>
                
                {/* Light grey rounded password input */}
                <div className="mb-3">
                  <div className="position-relative">
                    <input 
                      className="w-100 py-3 px-4 pe-5 border-0" 
                      style={{ background: "#f1f3f9", borderRadius: "10px", outline: "none", fontSize: "14.5px" }} 
                      type={showPass ? 'text' : 'password'} 
                      placeholder="Password" 
                      value={password} 
                      onChange={e => setPassword(e.target.value)} 
                      required 
                    />
                    <button 
                      type="button" 
                      className="btn position-absolute end-0 top-50 translate-middle-y border-0 pe-4" 
                      onClick={() => setShowPass(!showPass)}
                    >
                      <i className={`bi ${showPass ? 'bi-eye-slash text-muted' : 'bi-eye text-muted'}`} />
                    </button>
                  </div>
                </div>

                {/* Turnstile widget wrapper */}
                <div className="mb-4">
                  <TurnstileWidget onToken={setTurnstileToken} />
                </div>

                {/* Remember me & Forgot Password */}
                <div className="d-flex justify-content-between align-items-center mb-4" style={{ fontSize: "13.5px" }}>
                  <label className="d-flex align-items-center gap-2 text-muted" style={{ cursor: "pointer", fontWeight: 500 }}>
                    <input type="checkbox" className="form-check-input m-0" style={{ accentColor: "#2d1299" }} />
                    Remember me
                  </label>
                  <button type="button" className="btn btn-link p-0 text-decoration-none" style={{ color: "#2d1299", fontWeight: 600, fontSize: "13.5px" }} onClick={onForgot}>
                    Forgot password?
                  </button>
                </div>

                {/* Clean purple submit button */}
                <button className="w-100 py-3 text-white border-0 shadow-sm" style={{ background: "#2d1299", borderRadius: "10px", fontWeight: 700, fontSize: "15px" }} disabled={loading}>
                  {loading ? 'Please wait...' : 'Login'}
                </button>

                {/* Register redirection */}
                <div className="mt-4 text-start" style={{ fontSize: "13.5px" }}>
                  <span className="text-muted">Don't have an account, </span>
                  <button type="button" className="btn btn-link p-0 text-decoration-none fw-bold" style={{ color: "#2d1299", fontSize: "13.5px" }} onClick={onRegister}>
                    Click here
                  </button>
                </div>
              </form>

            </div>
          </div>

        </div>
      </div>
    </div>
  );
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
    <div className="d-flex align-items-center justify-content-center min-vh-100" style={{ background: "#dce4f7", padding: "30px" }}>
      <div className="shadow-lg d-flex p-4 p-lg-5" style={{ maxWidth: "1040px", width: "100%", minHeight: "580px", borderRadius: "28px", background: "#ffffff" }}>
        <div className="row w-100 g-4 g-lg-5 align-items-center">
          
          {/* Left Column: Isometric illustration and text */}
          <div className="col-md-6 d-none d-md-block">
            <div className="d-flex flex-column h-100 justify-content-center">
              <img 
                src={employeeBanner} 
                alt="Workspace Illustration" 
                style={{ width: "100%", maxHeight: "330px", objectFit: "contain" }} 
              />
              <div className="mt-4 d-flex justify-content-between align-items-end">
                <div style={{ maxWidth: "340px" }}>
                  <h4 style={{ color: "#2d1299", fontWeight: 700, fontSize: "18px", marginBottom: "8px" }}>
                    Manage your workforce the easiest way
                  </h4>
                  <p className="text-muted mb-0" style={{ fontSize: "12.5px", lineHeight: "1.5" }}>
                    Enjoy an easy to use management system for the growth of your business projects.
                  </p>
                </div>
                {/* 3 Pagination dots */}
                <div className="d-flex flex-column gap-1 ms-3">
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#2d1299" }} />
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#cbd5e1" }} />
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#cbd5e1" }} />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Purple styled registration form */}
          <div className="col-md-6 col-12">
            <div className="px-lg-4" style={{ maxWidth: "420px", margin: "0 auto" }}>
              <div className="mb-4 text-start">
                <img src={logoImg} alt="Dayflow Logo" style={{ height: "35px", display: "block", marginBottom: "8px" }} />
                <p className="text-muted small">Create your account</p>
              </div>

              <Alert msg={error} onClose={() => setError('')} />
              
              {success ? (
                <>
                  <div className="alert alert-success">{success}</div>
                  <button className="w-100 py-3 text-white border-0" style={{ background: "#2d1299", borderRadius: "10px", fontWeight: 700 }} onClick={onBackToLogin}>
                    Back to Sign In
                  </button>
                </>
              ) : (
                <form onSubmit={handleSubmit}>
                  <div className="row g-2 mb-2">
                    <div className="col">
                      <input className="w-100 py-2.5 px-3 border-0" style={{ background: "#f1f3f9", borderRadius: "8px", outline: "none", fontSize: "13.5px" }} placeholder="First name" value={form.first_name} onChange={e => update('first_name', e.target.value)} required />
                    </div>
                    <div className="col">
                      <input className="w-100 py-2.5 px-3 border-0" style={{ background: "#f1f3f9", borderRadius: "8px", outline: "none", fontSize: "13.5px" }} placeholder="Last name" value={form.last_name} onChange={e => update('last_name', e.target.value)} required />
                    </div>
                  </div>
                  
                  <div className="mb-2">
                    <input className="w-100 py-2.5 px-3 border-0" style={{ background: "#f1f3f9", borderRadius: "8px", outline: "none", fontSize: "13.5px" }} type="email" placeholder="Email address" value={form.email} onChange={e => update('email', e.target.value)} required />
                  </div>
                  
                  <div className="row g-2 mb-2">
                    <div className="col">
                      <input className="w-100 py-2.5 px-3 border-0" style={{ background: "#f1f3f9", borderRadius: "8px", outline: "none", fontSize: "13.5px" }} type="number" min="1" placeholder="Dept ID" value={form.department_id} onChange={e => update('department_id', e.target.value)} required />
                    </div>
                    <div className="col">
                      <input className="w-100 py-2.5 px-3 border-0" style={{ background: "#f1f3f9", borderRadius: "8px", outline: "none", fontSize: "13.5px" }} type="number" min="1" placeholder="Desig ID" value={form.designation_id} onChange={e => update('designation_id', e.target.value)} required />
                    </div>
                  </div>
                  
                  <div className="mb-2">
                    <input className="w-100 py-2.5 px-3 border-0" style={{ background: "#f1f3f9", borderRadius: "8px", outline: "none", fontSize: "13.5px", color: form.joining_date ? "#212529" : "#6c757d" }} type="date" placeholder="Joining Date" value={form.joining_date} onChange={e => update('joining_date', e.target.value)} required />
                  </div>
                  
                  <div className="mb-2">
                    <input className="w-100 py-2.5 px-3 border-0" style={{ background: "#f1f3f9", borderRadius: "8px", outline: "none", fontSize: "13.5px" }} type="password" placeholder="Password" value={form.password} onChange={e => update('password', e.target.value)} required />
                    <PasswordStrengthMeter password={form.password} />
                  </div>
                  
                  <div className="mb-3">
                    <input className="w-100 py-2.5 px-3 border-0" style={{ background: "#f1f3f9", borderRadius: "8px", outline: "none", fontSize: "13.5px" }} type="password" placeholder="Confirm password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required />
                  </div>
                  
                  <div className="mb-3">
                    <TurnstileWidget onToken={setTurnstileToken} />
                  </div>

                  <button className="w-100 py-3 text-white border-0 shadow-sm mt-2" style={{ background: "#2d1299", borderRadius: "10px", fontWeight: 700, fontSize: "15px" }} disabled={loading}>
                    {loading ? 'Creating Account...' : 'Create Account'}
                  </button>
                  
                  <div className="text-center mt-3" style={{ fontSize: "13.5px" }}>
                    <span className="text-muted">Already have an account? </span>
                    <button type="button" className="btn btn-link p-0 text-decoration-none fw-bold" style={{ color: "#2d1299", fontSize: "13.5px" }} onClick={onBackToLogin}>
                      Sign In
                    </button>
                  </div>
                </form>
              )}

            </div>
          </div>

        </div>
      </div>
    </div>
  );
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
  const [turnstileToken, setTurnstileToken] = useState('')

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
      const res = await authApi.forgotPassword(email, turnstileToken)
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
    <div className="d-flex align-items-center justify-content-center min-vh-100" style={{ background: "#dce4f7", padding: "30px" }}>
      <div className="shadow-lg d-flex p-4 p-lg-5" style={{ maxWidth: "1040px", width: "100%", minHeight: "580px", borderRadius: "28px", background: "#ffffff" }}>
        <div className="row w-100 g-4 g-lg-5 align-items-center">
          
          {/* Left Column: Isometric illustration and text */}
          <div className="col-md-6 d-none d-md-block">
            <div className="d-flex flex-column h-100 justify-content-center">
              <img 
                src={employeeBanner} 
                alt="Workspace Illustration" 
                style={{ width: "100%", maxHeight: "330px", objectFit: "contain" }} 
              />
              <div className="mt-4 d-flex justify-content-between align-items-end">
                <div style={{ maxWidth: "340px" }}>
                  <h4 style={{ color: "#2d1299", fontWeight: 700, fontSize: "18px", marginBottom: "8px" }}>
                    Manage your workforce the easiest way
                  </h4>
                  <p className="text-muted mb-0" style={{ fontSize: "12.5px", lineHeight: "1.5" }}>
                    Enjoy an easy to use management system for the growth of your business projects.
                  </p>
                </div>
                {/* 3 Pagination dots */}
                <div className="d-flex flex-column gap-1 ms-3">
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#2d1299" }} />
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#cbd5e1" }} />
                  <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#cbd5e1" }} />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Purple styled password reset form */}
          <div className="col-md-6 col-12">
            <div className="px-lg-4" style={{ maxWidth: "420px", margin: "0 auto" }}>
              <div className="mb-4 text-start">
                <img src={logoImg} alt="Dayflow Logo" style={{ height: "35px", display: "block", marginBottom: "8px" }} />
                <h2 className="fs-4 fw-bold mb-1" style={{ color: "#2d1299" }}>
                  {stage === 'forgot' && 'Reset Password'}
                  {stage === 'verify_otp' && 'Enter OTP Code'}
                  {stage === 'reset' && 'Create New Password'}
                  {stage === 'success' && 'Password Reset'}
                </h2>
                <p className="text-muted small">
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
                    <input 
                      className="w-100 py-3 px-4 border-0" 
                      style={{ background: "#f1f3f9", borderRadius: "10px", outline: "none", fontSize: "14.5px" }} 
                      type="email" 
                      placeholder="you@company.com" 
                      value={email} 
                      onChange={e => setEmail(e.target.value)} 
                      required 
                      autoFocus 
                    />
                  </div>

                  <div className="mb-4">
                    <TurnstileWidget onToken={setTurnstileToken} />
                  </div>

                  <button className="w-100 py-3 text-white border-0 shadow-sm" style={{ background: "#2d1299", borderRadius: "10px", fontWeight: 700 }} disabled={loading}>
                    {loading ? 'Sending OTP...' : 'Send Reset OTP'}
                  </button>
                  <button type="button" className="btn btn-link w-100 text-decoration-none mt-2 fw-bold" style={{ color: "#2d1299", fontSize: "13.5px" }} onClick={onBackToLogin}>
                    ← Back to Sign In
                  </button>
                </form>
              )}

              {stage === 'verify_otp' && (
                <form onSubmit={handleVerifyOTP}>
                  <div className="mb-3">
                    <label className="text-muted d-block mb-3" style={{ fontSize: "13.5px", fontWeight: 600 }}>6-Digit Verification Code</label>
                    <div className="d-flex gap-2 justify-content-center mb-3">
                      {otpDigits.map((digit, idx) => (
                        <input
                          key={idx}
                          id={`otp-input-${idx}`}
                          type="text"
                          inputMode="numeric"
                          maxLength={1}
                          className="form-control text-center fw-bold fs-4"
                          style={{ width: 44, height: 50, borderRadius: 8, border: '1px solid #cbd5e1', background: '#f1f3f9' }}
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

                  <button className="w-100 py-3 text-white border-0 shadow-sm" style={{ background: "#2d1299", borderRadius: "10px", fontWeight: 700 }} disabled={loading || otpDigits.join('').length !== 6}>
                    {loading ? 'Verifying...' : 'Verify OTP Code'}
                  </button>

                  <div className="text-center mt-3">
                    <button
                      type="button"
                      className="btn btn-link text-decoration-none p-0 fw-bold"
                      style={{ color: "#2d1299", fontSize: "13.5px" }}
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
                    <input 
                      className="w-100 py-3 px-4 border-0" 
                      style={{ background: "#f1f3f9", borderRadius: "10px", outline: "none", fontSize: "14.5px" }} 
                      type="password" 
                      placeholder="New password" 
                      value={newPassword} 
                      onChange={e => setNewPassword(e.target.value)} 
                      required 
                      autoFocus 
                    />
                    <PasswordStrengthMeter password={newPassword} />
                  </div>

                  <div className="mb-4">
                    <input 
                      className="w-100 py-3 px-4 border-0" 
                      style={{ background: "#f1f3f9", borderRadius: "10px", outline: "none", fontSize: "14.5px" }} 
                      type="password" 
                      placeholder="Confirm new password" 
                      value={confirmPassword} 
                      onChange={e => setConfirmPassword(e.target.value)} 
                      required 
                    />
                  </div>

                  <button className="w-100 py-3 text-white border-0 shadow-sm" style={{ background: "#2d1299", borderRadius: "10px", fontWeight: 700 }} disabled={loading}>
                    {loading ? 'Resetting...' : 'Reset Password'}
                  </button>
                </form>
              )}

              {stage === 'success' && (
                <div className="text-center py-3">
                  <div className="mx-auto mb-3 p-3 fs-3 text-success bg-success-subtle" style={{ borderRadius: '50%', width: 64, height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <i className="bi bi-check-lg" />
                  </div>
                  <p className="text-muted mb-4" style={{ fontSize: "13px", lineHeight: "1.6" }}>Your password has been reset using Argon2 hashing. You may now sign in with your new credentials.</p>
                  <button className="w-100 py-3 text-white border-0 shadow-sm" style={{ background: "#2d1299", borderRadius: "10px", fontWeight: 700 }} onClick={onBackToLogin}>
                    Go to Sign In
                  </button>
                </div>
              )}

            </div>
          </div>

        </div>
      </div>
    </div>
  );
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
  const [dropdownOpen, setDropdownOpen] = useState(false)

  return (
    <header className="df-navbar">
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <img src={logoImg} alt="Dayflow Logo" style={{ height: "35px" }} />
      </div>
      <nav className="d-flex gap-1">
        {NAV.map(n => (
          <button key={n.id} className={`df-nav-link ${page === n.id ? 'active' : ''}`} onClick={() => onNav(n.id)}>
            <i className={`bi ${n.icon}`} /> <span className="label">{n.label}</span>
          </button>
        ))}
      </nav>
      <div className="ms-auto d-flex align-items-center gap-3 position-relative">
        <div 
          className="d-flex align-items-center gap-2" 
          style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: 6 }}
          onClick={() => setDropdownOpen(!dropdownOpen)}
        >
          <div className="df-avatar" style={{ width: 30, height: 30, fontSize: 12, background: 'var(--df-blue)', color: '#fff', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%' }}>
            {profile?.profile_picture_url ? (
              <img src={`http://localhost:8000${profile.profile_picture_url}`} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              (profile?.full_name || 'U').slice(0, 2).toUpperCase()
            )}
          </div>
          <div className="d-none d-md-block text-white" style={{ fontSize: 13, fontWeight: 600 }}>
            {profile?.full_name || 'Employee'}
          </div>
          <i className="bi bi-chevron-down text-white-50" style={{ fontSize: 11 }} />
        </div>

        {dropdownOpen && (
          <>
            <div 
              style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 999 }}
              onClick={() => setDropdownOpen(false)}
            />
            <div 
              className="df-card p-2 position-absolute end-0" 
              style={{ 
                top: '100%', 
                width: 150, 
                zIndex: 1000, 
                background: '#fff', 
                borderRadius: 8, 
                border: '1px solid var(--df-border)', 
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                marginTop: 8
              }}
            >
              <button 
                className="w-100 text-start border-0 bg-transparent py-2 px-3 rounded-2 text-danger d-flex align-items-center gap-2" 
                style={{ fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                onClick={() => {
                  setDropdownOpen(false);
                  onLogout();
                }}
              >
                <i className="bi bi-box-arrow-right" />
                Sign Out
              </button>
            </div>
          </>
        )}
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
    <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header section with Greeting and Check In/Out */}
      <div className="row mb-4 align-items-center g-3">
        <div className="col-md-8">
          <h1 className="fw-extrabold mb-1" style={{ color: "#2d1299", fontSize: "32px", fontWeight: 800 }}>
            Hi, {data?.full_name?.split(' ')[0] || 'there'}! <br />
            What are your plans for today?
          </h1>
          <p className="text-muted" style={{ fontSize: "14px", maxWidth: "480px" }}>
            This platform is designed to revolutionize the way you manage and execute your workspace routines.
          </p>
        </div>
        
        {/* Quick Check-in/out Action */}
        <div className="col-md-4 text-md-end">
          <div className="d-inline-flex gap-2 p-2 bg-white rounded-4 shadow-sm align-items-center border">
            <span className="small text-muted px-2" style={{ fontWeight: 600 }}>Status:</span>
            {!hasCheckedIn && (
              <button className="btn text-white px-3 py-1.5" style={{ background: "#2d1299", borderRadius: "12px", border: "none", fontSize: "13px", fontWeight: 600 }} onClick={doCheckIn} disabled={actionLoading}>
                <i className="bi bi-box-arrow-in-right me-1" /> Check In
              </button>
            )}
            {canCheckOut && (
              <button className="btn text-white px-3 py-1.5" style={{ background: "#d92c2c", borderRadius: "12px", border: "none", fontSize: "13px", fontWeight: 600 }} onClick={doCheckOut} disabled={actionLoading}>
                <i className="bi bi-box-arrow-right me-1" /> Check Out
              </button>
            )}
            {hasCheckedOut && <Badge status="APPROVED" />}
          </div>
        </div>
      </div>

      {error && <Alert msg={error} onClose={() => setError('')} />}
      {actionMsg && <div className="alert alert-info py-2 px-3 small mb-3">{actionMsg}</div>}

      {/* Vector image icon row cards */}
      <div className="row g-3 mb-4">
        {/* Card 1: Stay Organized */}
        <div className="col-md-4">
          <div className="df-card d-flex flex-column justify-content-between p-4" style={{ minHeight: "180px", borderRadius: "20px" }}>
            <div className="d-flex justify-content-between align-items-start">
              <div>
                <h5 className="fw-bold mb-1" style={{ color: "#2d1299" }}>Stay organized</h5>
                <p className="text-muted small mb-0">A clear structure for your logs.</p>
              </div>
              {/* SVG Calendar icon */}
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2d1299" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6"></line>
                <line x1="8" y1="2" x2="8" y2="6"></line>
                <line x1="3" y1="10" x2="21" y2="10"></line>
              </svg>
            </div>
            <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top">
              <span className="small text-muted">Active Duty:</span>
              <span className="badge bg-success-subtle text-success px-2.5 py-1.5" style={{ fontSize: "11.5px", borderRadius: "8px" }}>
                {data?.today_status ? data.today_status : 'Offline'}
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Sync Your Logs */}
        <div className="col-md-4">
          <div className="df-card d-flex flex-column justify-content-between p-4" style={{ minHeight: "180px", borderRadius: "20px" }}>
            <div className="d-flex justify-content-between align-items-start">
              <div>
                <h5 className="fw-bold mb-1" style={{ color: "#2d1299" }}>Sync your logs</h5>
                <p className="text-muted small mb-0">Ensure time cards are updated.</p>
              </div>
              {/* SVG Sync Sheets icon */}
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2d1299" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
              </svg>
            </div>
            <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top">
              <span className="small text-muted">Worked today:</span>
              <span className="fw-bold" style={{ color: "#2d1299" }}>
                {data?.work_hours_today ? `${Number(data.work_hours_today).toFixed(1)} hours` : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Collaborate and Share */}
        <div className="col-md-4">
          <div className="df-card d-flex flex-column justify-content-between p-4" style={{ minHeight: "180px", borderRadius: "20px" }}>
            <div className="d-flex justify-content-between align-items-start">
              <div>
                <h5 className="fw-bold mb-1" style={{ color: "#2d1299" }}>Profile Directory</h5>
                <p className="text-muted small mb-0">Manage details with team mates.</p>
              </div>
              {/* SVG Collaborate Folder icon */}
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#2d1299" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="13" r="3"></circle>
              </svg>
            </div>
            <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top">
              <span className="small text-muted">Role designation:</span>
              <span className="fw-bold" style={{ color: "#2d1299", fontSize: "12px" }}>
                {data?.designation || 'Employee'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main stats layout */}
      <div className="row g-3 mb-4">
        {/* Left Side: Leaves and Balances */}
        <div className="col-lg-8 d-flex flex-column gap-3">
          <div className="row g-3">
            <div className="col-sm-4">
              <div className="df-card h-100 p-4" style={{ borderRadius: "20px" }}>
                <div className="df-section-title fs-6 mb-2" style={{ color: "#2d1299" }}><i className="bi bi-calendar-week me-2" />This Week</div>
                <div className="df-stat-value fs-1 mb-1" style={{ color: "#2d1299", fontWeight: 800 }}>{data?.this_week_present_days ?? 0}</div>
                <div className="df-stat-sub">days present so far</div>
              </div>
            </div>
            <div className="col-sm-4">
              <div className="df-card h-100 p-4" style={{ borderRadius: "20px" }}>
                <div className="df-section-title fs-6 mb-2" style={{ color: "#e07a5f" }}><i className="bi bi-hourglass-split me-2" />Pending Leaves</div>
                <div className="df-stat-value fs-1 mb-1" style={{ color: "#e07a5f", fontWeight: 800 }}>{data?.pending_leave_requests ?? 0}</div>
                <div className="df-stat-sub">awaiting approval</div>
              </div>
            </div>
            <div className="col-sm-4">
              <div className="df-card h-100 p-4" style={{ borderRadius: "20px" }}>
                <div className="df-section-title fs-6 mb-2" style={{ color: "#2b9348" }}><i className="bi bi-check-circle me-2" />Approved Leaves</div>
                <div className="df-stat-value fs-1 mb-1" style={{ color: "#2b9348", fontWeight: 800 }}>{data?.approved_leave_requests ?? 0}</div>
                <div className="df-stat-sub">upcoming approved</div>
              </div>
            </div>
          </div>

          {data?.leave_balances?.length > 0 && (
            <div className="df-card p-4" style={{ borderRadius: "20px" }}>
              <div className="df-section-title fs-6 mb-3" style={{ color: "#2d1299" }}><i className="bi bi-wallet2 me-2" />Leave Balances</div>
              <div className="row g-3">
                {data.leave_balances.map(b => (
                  <div key={b.leave_type_id} className="col-sm-6">
                    <div className="p-3 border rounded-3 bg-light">
                      <div className="df-stat-label text-dark mb-1">{b.leave_type_name}</div>
                      <div className="df-stat-value fs-2 text-primary" style={{ fontWeight: 800 }}>{Number(b.remaining_days).toFixed(0)}</div>
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
        </div>

        {/* Right Side: Promotion banner / Actions list */}
        <div className="col-lg-4 d-flex flex-column gap-3">
          {/* Go Premium status styled card */}
          <div className="df-card text-white p-4 d-flex flex-column justify-content-between" style={{ background: "#2d1299", borderRadius: "20px", minHeight: "220px" }}>
            <div>
              <h5 className="fw-bold mb-2">Time-clock Status</h5>
              <p className="small text-white-50" style={{ fontSize: "12px", lineHeight: "1.5", opacity: 0.8 }}>
                Remember to record your arrival and departure times daily for accurate payroll and attendance calculations.
              </p>
            </div>
            <div className="mt-3">
              <button className="btn btn-light btn-sm w-100 fw-bold py-2" style={{ color: "#2d1299", borderRadius: "10px" }} onClick={() => onNav('attendance')}>
                View Attendance Logs
              </button>
            </div>
          </div>

          <div className="df-card p-4" style={{ borderRadius: "20px" }}>
            <h5 className="fw-bold mb-3" style={{ color: "#2d1299" }}>Today tasks</h5>
            <div className="d-flex flex-column gap-2">
              <div className="d-flex align-items-center gap-2 py-2 border-bottom">
                <i className="bi bi-check-square text-success" />
                <span className="small text-dark" style={{ fontWeight: 500 }}>Update resume profile</span>
              </div>
              <div className="d-flex align-items-center gap-2 py-2 border-bottom">
                <i className="bi bi-square text-muted" />
                <span className="small text-dark" style={{ fontWeight: 500 }}>Check weekly timeslips</span>
              </div>
              <div className="d-flex align-items-center gap-2 py-2">
                <i className="bi bi-square text-muted" />
                <span className="small text-dark" style={{ fontWeight: 500 }}>Submit time-off requests</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick links block */}
      <div className="row g-3">
        {[
          { label: 'View Attendance', icon: 'bi-clock-history', page: 'attendance' },
          { label: 'Request Time Off', icon: 'bi-calendar-plus', page: 'timeoff' },
          { label: 'My Profile', icon: 'bi-person-fill', page: 'profile' },
          { label: 'View Salary', icon: 'bi-currency-dollar', page: 'salary' },
        ].map(q => (
          <div key={q.label} className="col-6 col-md-3">
            <button className="df-card w-100 text-start d-flex align-items-center gap-3 border transition-all p-3" onClick={() => onNav(q.page)} style={{ cursor: 'pointer', borderRadius: "16px" }}>
              <i className={`bi ${q.icon} fs-4`} style={{ color: "#2d1299" }} />
              <span className="fw-semibold text-dark" style={{ fontSize: "13.5px" }}>{q.label}</span>
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
function ProfilePage({ onPreviewPhoto }) {
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

  // Resume editing state
  const [resumeData, setResumeData] = useState({
    about: 'Professional software engineering specialist dedicated to designing, building, and launching secure, scalable software systems.',
    whatILove: 'Tackling complex engineering challenges, architecting robust backend systems, and collaborating with cross-functional teams.',
    interests: 'Exploring cutting-edge AI agent systems, contributing to open source projects, cycling, and reading technical blogs.',
    skills: [
      { id: 1, name: 'JavaScript' }, { id: 2, name: 'TypeScript' }, { id: 3, name: 'React' },
      { id: 4, name: 'Node.js' }, { id: 5, name: 'Python' }, { id: 6, name: 'FastAPI' },
      { id: 7, name: 'PostgreSQL' }, { id: 8, name: 'Docker' },
    ],
    certifications: [
      { id: 1, title: 'Google Certified Professional Cloud Architect', issuer: 'Google Cloud', issueDate: 'Feb 2025' },
      { id: 2, title: 'AWS Certified Solutions Architect', issuer: 'Amazon Web Services', issueDate: 'Sep 2024' },
    ],
  })
  const [resumeEditField, setResumeEditField] = useState(null) // null | 'about' | 'whatILove' | 'interests'
  const [resumeEditValue, setResumeEditValue] = useState('')
  const [showSkillModal, setShowSkillModal] = useState(false)
  const [showCertModal, setShowCertModal] = useState(false)
  const [newSkillName, setNewSkillName] = useState('')
  const [newCert, setNewCert] = useState({ title: '', issuer: '', issueDate: '' })

  function openResumeEdit(field) {
    setResumeEditField(field)
    setResumeEditValue(resumeData[field] || '')
  }
  async function saveResumeEdit() {
    const backendFields = {}
    if (resumeEditField === 'about') backendFields.about = resumeEditValue
    if (resumeEditField === 'whatILove') backendFields.what_i_love = resumeEditValue
    if (resumeEditField === 'interests') backendFields.interests = resumeEditValue
    try {
      await meApi.updateResume(profile.employee_id, backendFields)
      setResumeData(prev => ({ ...prev, [resumeEditField]: resumeEditValue }))
      setResumeEditField(null)
    } catch (err) {
      setError(err.message || 'Failed to save changes')
    }
  }
  async function addSkill() {
    const name = newSkillName.trim()
    if (!name) return
    const nextSkills = [...resumeData.skills.map(s => s.name || s), name]
    try {
      await meApi.updateResume(profile.employee_id, { skills: nextSkills })
      setResumeData(prev => ({ ...prev, skills: [...prev.skills, { id: Date.now(), name }] }))
      setNewSkillName('')
      setShowSkillModal(false)
    } catch (err) {
      setError(err.message || 'Failed to add skill')
    }
  }
  async function removeSkill(id) {
    const skillToRemove = resumeData.skills.find(s => s.id === id)
    if (!skillToRemove) return
    const nextSkills = resumeData.skills.filter(s => s.id !== id).map(s => s.name || s)
    try {
      await meApi.updateResume(profile.employee_id, { skills: nextSkills })
      setResumeData(prev => ({ ...prev, skills: prev.skills.filter(s => s.id !== id) }))
    } catch (err) {
      setError(err.message || 'Failed to remove skill')
    }
  }
  async function addCert() {
    if (!newCert.title.trim()) return
    const nextCerts = [...resumeData.certifications, { id: Date.now(), ...newCert }]
    try {
      await meApi.updateResume(profile.employee_id, { certifications: nextCerts })
      setResumeData(prev => ({ ...prev, certifications: nextCerts }))
      setNewCert({ title: '', issuer: '', issueDate: '' })
      setShowCertModal(false)
    } catch (err) {
      setError(err.message || 'Failed to add certification')
    }
  }
  async function removeCert(id) {
    const nextCerts = resumeData.certifications.filter(c => c.id !== id)
    try {
      await meApi.updateResume(profile.employee_id, { certifications: nextCerts })
      setResumeData(prev => ({ ...prev, certifications: nextCerts }))
    } catch (err) {
      setError(err.message || 'Failed to remove certification')
    }
  }

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
        if (p?.employee_id) {
          meApi.getResume(p.employee_id)
            .then(res => {
              if (res) {
                setResumeData({
                  about: res.about || '',
                  whatILove: res.what_i_love || '',
                  interests: res.interests || '',
                  skills: (res.skills || []).map((s, idx) => typeof s === 'string' ? { id: idx + 1, name: s } : s),
                  certifications: res.certifications || []
                })
              }
            })
            .catch(() => {})
        }
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
        <div 
          className="df-avatar position-relative" 
          style={{ width: 80, height: 80, fontSize: 26, background: 'var(--df-blue)', color: '#fff', cursor: 'pointer', overflow: 'hidden', borderRadius: '50%' }}
          onClick={onPreviewPhoto}
          title="Click to view profile picture"
        >
          {profile?.profile_picture_url
            ? <img src={`http://localhost:8000${profile.profile_picture_url}`} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : <span>{(profile?.full_name || 'U').slice(0, 2).toUpperCase()}</span>
          }
          <div 
            className="position-absolute bottom-0 start-0 w-100 text-center py-1" 
            style={{ background: 'rgba(0,0,0,0.6)', color: '#fff', fontSize: 10, pointerEvents: 'none' }}
          >
            View
          </div>
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
            <div className="df-card mb-4" style={{ padding: '24px' }}>
              {/* About */}
              <div className="d-flex align-items-center justify-content-between mb-2">
                <h3 className="df-section-title fs-6 mb-0">About</h3>
                <button className="df-btn-secondary btn-sm" style={{ padding: '3px 10px', fontSize: 12 }} onClick={() => openResumeEdit('about')}>
                  <i className="bi bi-pencil me-1" />Edit
                </button>
              </div>
              <p className="text-muted" style={{ fontSize: 13.5, lineHeight: 1.6 }}>
                {resumeData.about || <em>No description yet. Click Edit to add.</em>}
              </p>

              {/* What I love */}
              <div className="d-flex align-items-center justify-content-between mt-4 mb-2 pt-3 border-top">
                <h3 className="df-section-title fs-6 mb-0">What I love about my job</h3>
                <button className="df-btn-secondary btn-sm" style={{ padding: '3px 10px', fontSize: 12 }} onClick={() => openResumeEdit('whatILove')}>
                  <i className="bi bi-pencil me-1" />Edit
                </button>
              </div>
              <p className="text-muted" style={{ fontSize: 13.5, lineHeight: 1.6 }}>
                {resumeData.whatILove || <em>No preferences yet. Click Edit to add.</em>}
              </p>

              {/* Interests */}
              <div className="d-flex align-items-center justify-content-between mt-4 mb-2 pt-3 border-top">
                <h3 className="df-section-title fs-6 mb-0">My interests and hobbies</h3>
                <button className="df-btn-secondary btn-sm" style={{ padding: '3px 10px', fontSize: 12 }} onClick={() => openResumeEdit('interests')}>
                  <i className="bi bi-pencil me-1" />Edit
                </button>
              </div>
              <p className="text-muted" style={{ fontSize: 13.5, lineHeight: 1.6 }}>
                {resumeData.interests || <em>No interests yet. Click Edit to add.</em>}
              </p>
            </div>
          </div>

          <div className="col-lg-5 col-md-12">
            {/* Skills */}
            <div className="df-card mb-4" style={{ padding: '24px' }}>
              <div className="d-flex align-items-center justify-content-between mb-3">
                <h3 className="df-section-title fs-6 mb-0">Skills <span className="badge bg-light text-dark border ms-1" style={{ fontSize: 11 }}>{resumeData.skills.length}</span></h3>
                <button className="df-btn-secondary btn-sm" style={{ padding: '3px 10px', fontSize: 12 }} onClick={() => setShowSkillModal(true)}>
                  <i className="bi bi-plus-lg me-1" />Add
                </button>
              </div>
              <div className="d-flex flex-wrap gap-2">
                {resumeData.skills.length === 0
                  ? <span className="text-muted" style={{ fontSize: 13 }}>No skills yet.</span>
                  : resumeData.skills.map(s => (
                    <span key={s.id} className="badge bg-light text-dark border d-inline-flex align-items-center gap-1" style={{ fontSize: 12, padding: '5px 10px' }}>
                      {s.name}
                      <button
                        type="button"
                        onClick={() => removeSkill(s.id)}
                        style={{ background: 'none', border: 'none', padding: '0 0 0 4px', cursor: 'pointer', color: '#666', fontSize: 13, lineHeight: 1 }}
                        title="Remove skill"
                      >×</button>
                    </span>
                  ))
                }
              </div>
            </div>

            {/* Certifications */}
            <div className="df-card" style={{ padding: '24px' }}>
              <div className="d-flex align-items-center justify-content-between mb-3">
                <h3 className="df-section-title fs-6 mb-0">Certifications <span className="badge bg-light text-dark border ms-1" style={{ fontSize: 11 }}>{resumeData.certifications.length}</span></h3>
                <button className="df-btn-secondary btn-sm" style={{ padding: '3px 10px', fontSize: 12 }} onClick={() => setShowCertModal(true)}>
                  <i className="bi bi-plus-lg me-1" />Add
                </button>
              </div>
              <div className="d-flex flex-column gap-3">
                {resumeData.certifications.length === 0
                  ? <span className="text-muted" style={{ fontSize: 13 }}>No certifications yet.</span>
                  : resumeData.certifications.map(c => (
                    <div key={c.id} className="d-flex align-items-start justify-content-between p-3 border rounded bg-light">
                      <div className="d-flex gap-3 align-items-start">
                        <div style={{ width: 30, height: 30, borderRadius: 6, background: 'var(--df-blue-light, #EFF6FF)', color: 'var(--df-blue, #2563EB)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, flexShrink: 0, marginTop: 2 }}>
                          <i className="bi bi-award-fill" />
                        </div>
                        <div>
                          <div className="fw-semibold text-dark" style={{ fontSize: 13.5 }}>{c.title}</div>
                          <small className="text-muted">{c.issuer}{c.issueDate ? ` · ${c.issueDate}` : ''}</small>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeCert(c.id)}
                        className="btn btn-sm btn-outline-danger border-0 p-1"
                        title="Remove"
                        style={{ fontSize: 14, lineHeight: 1 }}
                      ><i className="bi bi-trash" /></button>
                    </div>
                  ))
                }
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

      {tab === 'salary' && (
        <div>
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

      {/* Edit About Modal */}
      {resumeEditField && (
        <div className="df-modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(40,59,89,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050 }} onClick={() => setResumeEditField(null)}>
          <div className="df-card p-4" style={{ width: 450, background: '#fff', borderRadius: 12 }} onClick={e => e.stopPropagation()}>
            <h3 className="df-section-title fs-6 mb-3" style={{ textTransform: 'capitalize' }}>Edit {resumeEditField === 'whatILove' ? 'What I love about my job' : resumeEditField}</h3>
            <textarea
              className="df-input w-100 mb-3"
              rows={4}
              value={resumeEditValue}
              onChange={e => setResumeEditValue(e.target.value)}
              placeholder={`Enter details about ${resumeEditField}...`}
            />
            <div className="d-flex justify-content-end gap-2">
              <button className="df-btn-secondary py-2 px-3" onClick={() => setResumeEditField(null)}>Cancel</button>
              <button className="df-btn-primary py-2 px-3" onClick={saveResumeEdit}>Save Changes</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Skill Modal */}
      {showSkillModal && (
        <div className="df-modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(40,59,89,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050 }} onClick={() => setShowSkillModal(false)}>
          <div className="df-card p-4" style={{ width: 400, background: '#fff', borderRadius: 12 }} onClick={e => e.stopPropagation()}>
            <h3 className="df-section-title fs-6 mb-3">Add Skill</h3>
            <input
              type="text"
              className="df-input w-100 mb-3"
              value={newSkillName}
              onChange={e => setNewSkillName(e.target.value)}
              placeholder="e.g. React, Python, Cloud Architecture..."
              autoFocus
              onKeyDown={e => e.key === 'Enter' && addSkill()}
            />
            <div className="d-flex justify-content-end gap-2">
              <button className="df-btn-secondary py-2 px-3" onClick={() => setShowSkillModal(false)}>Cancel</button>
              <button className="df-btn-primary py-2 px-3" onClick={addSkill}>Add Skill</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Certification Modal */}
      {showCertModal && (
        <div className="df-modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(40,59,89,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1050 }} onClick={() => setShowCertModal(false)}>
          <div className="df-card p-4" style={{ width: 450, background: '#fff', borderRadius: 12 }} onClick={e => e.stopPropagation()}>
            <h3 className="df-section-title fs-6 mb-3">Add Certification</h3>
            <div className="mb-3">
              <label className="df-stat-label mb-1">Certification Title</label>
              <input
                type="text"
                className="df-input w-100"
                value={newCert.title}
                onChange={e => setNewCert(prev => ({ ...prev, title: e.target.value }))}
                placeholder="e.g. AWS Solutions Architect"
              />
            </div>
            <div className="mb-3">
              <label className="df-stat-label mb-1">Issuing Organization</label>
              <input
                type="text"
                className="df-input w-100"
                value={newCert.issuer}
                onChange={e => setNewCert(prev => ({ ...prev, issuer: e.target.value }))}
                placeholder="e.g. Amazon Web Services"
              />
            </div>
            <div className="mb-4">
              <label className="df-stat-label mb-1">Issue Date</label>
              <input
                type="text"
                className="df-input w-100"
                value={newCert.issueDate}
                onChange={e => setNewCert(prev => ({ ...prev, issueDate: e.target.value }))}
                placeholder="e.g. Sep 2024 or Feb 2025"
              />
            </div>
            <div className="d-flex justify-content-end gap-2">
              <button className="df-btn-secondary py-2 px-3" onClick={() => setShowCertModal(false)}>Cancel</button>
              <button className="df-btn-primary py-2 px-3" onClick={addCert}>Add Certification</button>
            </div>
          </div>
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
  const [resume, setResume] = useState('')

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
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [sidebarHovered, setSidebarHovered] = useState(false)
  const [showPhotoPreview, setShowPhotoPreview] = useState(false)

  const loadProfile = useCallback(() => {
    meApi.getProfile().then(setProfile).catch(() => {})
  }, [])

  useEffect(() => {
    loadProfile()
  }, [loadProfile])

  const pages = { 
    dashboard: <DashboardPage onNav={setPage} />, 
    attendance: <AttendancePage />, 
    timeoff: <TimeOffPage />, 
    profile: <ProfilePage onPreviewPhoto={() => setShowPhotoPreview(true)} />, 
    salary: <SalaryPage /> 
  }

  return (
    <div className="d-flex min-vh-100" style={{ background: '#f4f6fc', color: '#110e3d' }}>
      {/* Left Sidebar (Curved vertical panel with expand on hover) */}
      <aside 
        className="d-flex flex-column py-4 text-white position-fixed top-0 bottom-0 start-0" 
        onMouseEnter={() => setSidebarHovered(true)}
        onMouseLeave={() => setSidebarHovered(false)}
        style={{ 
          width: sidebarHovered ? '200px' : '80px', 
          background: 'var(--df-blue)', 
          borderTopRightRadius: '32px', 
          borderBottomRightRadius: '32px',
          zIndex: 1000,
          transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s',
          boxShadow: '4px 0 24px rgba(94, 90, 219, 0.15)',
          alignItems: sidebarHovered ? 'flex-start' : 'center',
          paddingLeft: sidebarHovered ? '20px' : '0',
          paddingRight: sidebarHovered ? '20px' : '0'
        }}
      >
        {/* Brand Icon / Logo */}
        <div 
          className="mb-5 d-flex align-items-center justify-content-center bg-white rounded-3 shadow-sm" 
          style={{ 
            width: sidebarHovered ? '160px' : '42px', 
            height: '42px', 
            cursor: 'pointer',
            overflow: 'hidden',
            transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
          }} 
          onClick={() => setPage('dashboard')}
        >
          {sidebarHovered ? (
            <img src={logoImg} alt="Dayflow Logo" style={{ width: '130px', height: '28px', objectFit: 'contain' }} />
          ) : (
            <img src={faviconImg} alt="Dayflow Logo Icon" style={{ width: '28px', height: '28px', objectFit: 'contain' }} />
          )}
        </div>

        {/* Navigation Icons */}
        <div className="d-flex flex-column gap-3 w-100" style={{ alignItems: sidebarHovered ? 'stretch' : 'center' }}>
          {NAV.map(n => (
            <button 
              key={n.id} 
              className="d-flex align-items-center border-0 rounded-3" 
              style={{ 
                width: sidebarHovered ? '100%' : '46px', 
                height: '46px', 
                paddingLeft: sidebarHovered ? '14px' : '0',
                justifyContent: sidebarHovered ? 'flex-start' : 'center',
                background: page === n.id ? '#ffffff' : 'transparent',
                color: page === n.id ? 'var(--df-blue)' : 'rgba(255,255,255,0.85)',
                fontSize: '18px',
                cursor: 'pointer',
                transition: 'width 0.3s ease, padding 0.3s ease, background 0.2s',
                outline: 'none'
              }}
              title={sidebarHovered ? '' : n.label}
              onClick={() => setPage(n.id)}
            >
              <i className={`bi ${n.icon}`} style={{ fontSize: '20px' }} />
              {sidebarHovered && (
                <span className="ms-3 fw-semibold" style={{ fontSize: '13.5px', letterSpacing: '0.1px' }}>
                  {n.label}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Bottom Profile / Sign Out Action */}
        <div className="mt-auto position-relative" style={{ width: sidebarHovered ? '100%' : 'auto' }}>
          <div 
            className="d-flex align-items-center cursor-pointer p-1" 
            style={{ 
              borderRadius: '16px', 
              background: sidebarHovered ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
              width: '100%',
              cursor: 'pointer'
            }}
            onClick={() => setDropdownOpen(!dropdownOpen)}
          >
            <div 
              className="rounded-circle shadow-sm d-flex align-items-center justify-content-center flex-shrink-0" 
              style={{ width: '40px', height: '40px', background: '#ffffff', color: 'var(--df-blue)', fontSize: '13px', fontWeight: 700, overflow: 'hidden' }}
            >
              {profile?.profile_picture_url ? (
                <img src={`http://localhost:8000${profile.profile_picture_url}`} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                (profile?.full_name || 'U').slice(0, 2).toUpperCase()
              )}
            </div>
            {sidebarHovered && (
              <div className="ms-2 text-start text-white overflow-hidden" style={{ width: '90px' }}>
                <div className="fw-bold text-truncate" style={{ fontSize: '12px' }}>
                  {profile?.full_name?.split(' ')[0] || 'User'}
                </div>
                <div className="small text-white-50 text-truncate" style={{ fontSize: '10px' }}>
                  My Settings
                </div>
              </div>
            )}
            {sidebarHovered && (
              <i className="bi bi-chevron-up ms-auto me-1 small opacity-75" />
            )}
          </div>

          {dropdownOpen && (
            <>
              <div style={{ position: 'fixed', inset: 0, zIndex: 999 }} onClick={() => setDropdownOpen(false)} />
              <div 
                className="df-card p-2 position-absolute" 
                style={{ 
                  bottom: '55px', 
                  left: sidebarHovered ? '0' : '10px', 
                  width: sidebarHovered ? '160px' : '140px', 
                  zIndex: 1000, 
                  background: '#fff', 
                  borderRadius: 12, 
                  border: '1px solid #e1e0f6', 
                  boxShadow: '0 8px 24px rgba(0,0,0,0.12)' 
                }}
              >
                <button 
                  className="w-100 text-start border-0 bg-transparent py-2 px-3 rounded-2 text-dark d-flex align-items-center gap-2" 
                  style={{ fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                  onClick={() => {
                    setDropdownOpen(false);
                    setShowPhotoPreview(true);
                  }}
                >
                  <i className="bi bi-eye-fill text-muted" />
                  View Photo
                </button>
                <hr className="my-1" style={{ borderColor: '#e1e0f6' }} />
                <button 
                  className="w-100 text-start border-0 bg-transparent py-2 px-3 rounded-2 text-danger d-flex align-items-center gap-2" 
                  style={{ fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                  onClick={() => {
                    setDropdownOpen(false);
                    onLogout();
                  }}
                >
                  <i className="bi bi-box-arrow-right" />
                  Sign Out
                </button>
              </div>
            </>
          )}
        </div>
      </aside>

      {/* Main Content Area (Shifts dynamically on sidebar hover) */}
      <div 
        className="flex-grow-1" 
        style={{ 
          marginLeft: sidebarHovered ? '200px' : '80px', 
          minHeight: '100vh', 
          width: sidebarHovered ? 'calc(100% - 200px)' : 'calc(100% - 80px)',
          transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1), width 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
        }}
      >
        {/* Top Header bar */}
        <header className="d-flex align-items-center justify-content-between px-4 py-3" style={{ background: '#ffffff', borderBottom: '1px solid #e1e0f6', position: 'sticky', top: 0, zIndex: 100 }}>
          <div>
            <h2 className="fs-5 fw-bold mb-0" style={{ color: 'var(--df-blue)', textTransform: 'capitalize' }}>
              {page === 'dashboard' ? 'Dashboard' : page.replace('-', ' ')}
            </h2>
          </div>
          <div className="d-flex gap-3 align-items-center">
            {/* Search Input bar */}
            <div className="position-relative d-none d-md-block">
              <i className="bi bi-search position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)', fontSize: '13px' }} />
              <input 
                type="text" 
                placeholder="Search or type command..." 
                className="py-1.5 pe-3" 
                style={{ width: '220px', paddingLeft: '32px', background: '#f4f6fc', border: 'none', borderRadius: '20px', fontSize: '13px', outline: 'none' }}
              />
            </div>
            
            {/* Export data button */}
            <button className="btn btn-sm d-flex align-items-center gap-1 px-3 py-1.5" style={{ background: '#f4f6fc', color: 'var(--df-blue)', border: 'none', borderRadius: '20px', fontSize: '12px', fontWeight: 600 }}>
              <i className="bi bi-download" /> Export data
            </button>
          </div>
        </header>

        <main className="p-4" style={{ background: '#f4f6fc' }}>
          {pages[page] || pages.dashboard}
        </main>
      </div>

      {/* Lightbox Profile Photo Preview Modal */}
      {showPhotoPreview && (
        <div 
          className="df-modal-overlay" 
          style={{ 
            position: 'fixed', 
            inset: 0, 
            background: 'rgba(17,14,61,0.65)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            zIndex: 2000 
          }} 
          onClick={() => setShowPhotoPreview(false)}
        >
          <div 
            className="p-4 text-center position-relative" 
            style={{ maxWidth: '420px', width: '90%', background: '#fff', borderRadius: '28px', boxShadow: '0 20px 50px rgba(0,0,0,0.15)' }} 
            onClick={e => e.stopPropagation()}
          >
            <button 
              className="btn position-absolute border-0 bg-light rounded-circle" 
              style={{ top: '15px', right: '15px', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center' }} 
              onClick={() => setShowPhotoPreview(false)}
            >
              <i className="bi bi-x-lg text-dark" />
            </button>
            <h4 className="fw-bold mb-3 mt-1" style={{ color: 'var(--df-blue)' }}>Profile Photo</h4>
            <div className="mx-auto rounded-circle overflow-hidden shadow mb-3" style={{ width: '220px', height: '220px', background: 'var(--df-blue-light)', border: '4px solid var(--df-blue)' }}>
              {profile?.profile_picture_url ? (
                <img 
                  src={`http://localhost:8000${profile.profile_picture_url}`} 
                  alt="Profile" 
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
                />
              ) : (
                <div className="h-100 w-100 d-flex align-items-center justify-content-center fw-bold fs-1 text-primary">
                  {(profile?.full_name || 'U').slice(0, 2).toUpperCase()}
                </div>
              )}
            </div>
            <div className="fw-bold text-dark fs-5">{profile?.full_name}</div>
            <div className="text-muted small mb-2">{profile?.designation_title} · {profile?.department_name}</div>
            <button 
              className="btn text-white mt-3 px-4 py-2.5 w-100" 
              style={{ background: 'var(--df-blue)', borderRadius: '12px', border: 'none', fontWeight: 700, fontSize: '14.5px' }}
              onClick={() => document.getElementById('profile-avatar-input-shell')?.click()}
            >
              <i className="bi bi-camera-fill me-2" /> Upload New Photo
            </button>
            <input
              id="profile-avatar-input-shell"
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                try {
                  await meApi.uploadProfilePicture(profile.employee_id, file);
                  loadProfile();
                  setShowPhotoPreview(false);
                } catch (err) {
                  alert(err.message || 'Failed to upload profile picture.');
                }
              }}
            />
          </div>
        </div>
      )}
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
