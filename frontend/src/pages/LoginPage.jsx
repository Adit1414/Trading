import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Mail, Lock, Loader2, TrendingUp, User, Phone, Calendar } from 'lucide-react'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [isLogin, setIsLogin]             = useState(true)
  const [email, setEmail]                 = useState('')
  const [password, setPassword]           = useState('')
  const [loading, setLoading]             = useState(false)

  // ── NEW SIGNUP FIELDS ──────────────────────────────────────
  const [fullName, setFullName]           = useState('')
  const [dob, setDob]                     = useState('')
  const [contactInfo, setContactInfo]     = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordMismatch, setPasswordMismatch] = useState(false)
  // ──────────────────────────────────────────────────────────

  const { login, signup, user } = useAuthStore()

  if (user) return <Navigate to="/backtests" replace />

  // Reset extra fields when switching tabs
  const handleTabSwitch = (toLogin) => {
    setIsLogin(toLogin)
    setFullName(''); setDob(''); setContactInfo('')
    setConfirmPassword(''); setPasswordMismatch(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (isLogin) {
      if (!email || !password) { toast.error('Please fill in all fields.'); return }
    } else {
      // ── SIGNUP VALIDATION ──────────────────────────────────
      if (!fullName || !dob || !contactInfo || !email || !password || !confirmPassword) {
        toast.error('Please fill in all fields.'); return
      }
      if (password !== confirmPassword) {
        setPasswordMismatch(true); return
      }
      setPasswordMismatch(false)
      // ──────────────────────────────────────────────────────
    }

    setLoading(true)
    try {
      if (isLogin) {
        await login(email, password)
        toast.success('Welcome back!')
      } else {
        await signup(email, password, {
          full_name:    fullName,
          dob:          dob,
          contact_info: contactInfo,
        })
        toast.success('Account created!')
      }
    } catch (err) {
      toast.error(err.message || 'Authentication failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleGuest = () => {
    useAuthStore.getState().loginAsGuest()
    toast.success('Logged in as Guest!')
  }

  // Shared icon wrapper style (reused for all fields)
  const iconStyle = {
    position:'absolute', left:'14px', top:'50%',
    transform:'translateY(-50%)', color:'#334155', pointerEvents:'none'
  }

  // Shared input style (identical to existing fields)
  const inputStyle = {
    width:'100%', paddingLeft:'42px', paddingRight:'16px',
    paddingTop:'12px', paddingBottom:'12px',
    background:'rgba(0,0,0,0.3)', border:'1px solid rgba(255,255,255,0.07)',
    borderRadius:'12px', fontSize:'14px', color:'white',
    outline:'none', transition:'all 0.2s', boxSizing:'border-box',
    fontFamily:'inherit',
  }

  const labelStyle = {
    display:'block', fontSize:'12px', fontWeight:500,
    color:'#94a3b8', marginBottom:'8px', letterSpacing:'0.03em'
  }

  return (
    <>
      <style>{`
        @keyframes orb-drift {
          0%,100% { transform: scale(1) translate(0px,0px); }
          33%      { transform: scale(1.1) translate(20px,-25px); }
          66%      { transform: scale(0.92) translate(-15px,18px); }
        }
        @keyframes spin-ring-cw  { to { transform: rotate(360deg);  } }
        @keyframes spin-ring-ccw { to { transform: rotate(-360deg); } }
        @keyframes entry {
          from { opacity:0; transform:translateY(20px); }
          to   { opacity:1; transform:translateY(0); }
        }
        .login-card { animation: entry 0.6s cubic-bezier(0.16,1,0.3,1) forwards; }
        .login-field:focus {
          border-color: rgba(129,140,248,0.55) !important;
          box-shadow: 0 0 0 3px rgba(129,140,248,0.1) !important;
          background: rgba(0,0,0,0.4) !important;
        }
        .login-field::placeholder { color: #334155; }
        .login-tab-btn {
          flex:1; padding:9px; border-radius:9px; font-size:13px;
          font-weight:600; border:none; cursor:pointer; transition:all 0.22s;
          font-family:inherit;
        }
        .login-tab-btn.active {
          background: rgba(129,140,248,0.14);
          color: #a5b4fc;
          box-shadow: inset 0 0 0 1px rgba(129,140,248,0.22);
        }
        .login-tab-btn.idle { background:transparent; color:#475569; }
        .login-tab-btn.idle:hover { color:#94a3b8; }
        .login-submit {
          width:100%; padding:13px; border:none; border-radius:13px;
          font-size:14px; font-weight:600; color:white; cursor:pointer;
          font-family:inherit;
          background: linear-gradient(135deg,#818cf8 0%,#6366f1 100%);
          box-shadow: 0 4px 22px rgba(99,102,241,0.45);
          transition: opacity 0.18s, transform 0.18s;
          display:flex; align-items:center; justify-content:center; gap:8px;
        }
        .login-submit:hover:not(:disabled) { opacity:0.88; transform:translateY(-1px); }
        .login-submit:disabled { opacity:0.55; cursor:not-allowed; box-shadow:none; transform:none; }
        .login-guest {
          width:100%; padding:11px; background:rgba(255,255,255,0.03);
          border:1px solid rgba(255,255,255,0.07); border-radius:12px;
          color:#64748b; font-size:13px; font-weight:500; cursor:pointer;
          transition:all 0.2s; font-family:inherit;
        }
        .login-guest:hover {
          background:rgba(255,255,255,0.06);
          color:#94a3b8;
          border-color:rgba(255,255,255,0.13);
        }
      `}</style>

      <div style={{ minHeight:'100vh', background:'#0b1221', display:'flex', alignItems:'center', justifyContent:'center', padding:'24px', position:'relative', overflow:'hidden' }}>

        {/* ── Background layers ── */}
        <div style={{ position:'absolute', width:'700px', height:'700px', borderRadius:'50%', top:'-200px', left:'-200px', background:'radial-gradient(circle,rgba(99,102,241,0.28) 0%,rgba(99,102,241,0.06) 50%,transparent 70%)', animation:'orb-drift 11s ease-in-out infinite', pointerEvents:'none' }} />
        <div style={{ position:'absolute', width:'550px', height:'550px', borderRadius:'50%', bottom:'-120px', right:'-120px', background:'radial-gradient(circle,rgba(16,185,129,0.18) 0%,transparent 70%)', animation:'orb-drift 14s ease-in-out infinite', animationDelay:'-5s', pointerEvents:'none' }} />
        <div style={{ position:'absolute', width:'400px', height:'400px', borderRadius:'50%', top:'45%', left:'68%', transform:'translate(-50%,-50%)', background:'radial-gradient(circle,rgba(168,85,247,0.18) 0%,transparent 70%)', animation:'orb-drift 17s ease-in-out infinite', animationDelay:'-9s', pointerEvents:'none' }} />
        <div style={{ position:'absolute', inset:0, pointerEvents:'none', backgroundImage:'linear-gradient(rgba(129,140,248,0.035) 1px,transparent 1px),linear-gradient(90deg,rgba(129,140,248,0.035) 1px,transparent 1px)', backgroundSize:'64px 64px' }} />
        <div style={{ position:'absolute', inset:0, pointerEvents:'none', background:'radial-gradient(ellipse at center,transparent 30%,rgba(11,18,33,0.75) 100%)' }} />

        {/* ── Card ── */}
        <div className="login-card" style={{ position:'relative', zIndex:10, width:'100%', maxWidth:'420px' }}>
          <div style={{ background:'rgba(15,23,41,0.75)', backdropFilter:'blur(28px)', WebkitBackdropFilter:'blur(28px)', border:'1px solid rgba(255,255,255,0.09)', borderRadius:'24px', padding:'40px 36px', boxShadow:'0 32px 80px rgba(0,0,0,0.65), 0 0 0 0.5px rgba(255,255,255,0.05), inset 0 1px 0 rgba(255,255,255,0.08)' }}>

            {/* Logo */}
            <div style={{ textAlign:'center', marginBottom:'32px' }}>
              <div style={{ display:'inline-flex', alignItems:'center', justifyContent:'center', position:'relative', marginBottom:'16px' }}>
                <div style={{ position:'absolute', width:'76px', height:'76px', borderRadius:'50%', border:'1.5px solid transparent', borderTopColor:'rgba(129,140,248,0.7)', borderRightColor:'rgba(129,140,248,0.25)', borderBottomColor:'transparent', borderLeftColor:'rgba(129,140,248,0.45)', animation:'spin-ring-cw 20s linear infinite' }} />
                <div style={{ position:'absolute', width:'62px', height:'62px', borderRadius:'50%', border:'1px solid transparent', borderTopColor:'transparent', borderRightColor:'rgba(99,102,241,0.5)', borderBottomColor:'rgba(99,102,241,0.25)', borderLeftColor:'transparent', animation:'spin-ring-ccw 15s linear infinite' }} />
                <div style={{ width:'54px', height:'54px', borderRadius:'16px', position:'relative', background:'linear-gradient(135deg,#818cf8 0%,#6366f1 100%)', display:'flex', alignItems:'center', justifyContent:'center', boxShadow:'0 0 32px rgba(99,102,241,0.55)' }}>
                  <TrendingUp size={26} color="white" strokeWidth={2} />
                </div>
              </div>
              <h1 style={{ fontSize:'22px', fontWeight:700, color:'white', letterSpacing:'-0.02em', marginBottom:'4px' }}>Algo Kaisen</h1>
              <p style={{ fontSize:'13px', color:'#475569' }}>Algorithmic Trading Platform</p>
            </div>

            {/* Tab switcher */}
            <div style={{ display:'flex', background:'rgba(0,0,0,0.25)', borderRadius:'13px', padding:'4px', marginBottom:'24px', border:'1px solid rgba(255,255,255,0.05)', gap:'2px' }}>
              <button className={`login-tab-btn ${isLogin ? 'active' : 'idle'}`} onClick={() => handleTabSwitch(true)}>Sign In</button>
              <button className={`login-tab-btn ${!isLogin ? 'active' : 'idle'}`} onClick={() => handleTabSwitch(false)}>Sign Up</button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} style={{ display:'flex', flexDirection:'column', gap:'16px' }}>

              {/* ── SIGNUP-ONLY FIELDS ─────────────────────────────── */}
              {!isLogin && (
                <>
                  {/* Full Name */}
                  <div>
                    <label style={labelStyle}>Full Name</label>
                    <div style={{ position:'relative' }}>
                      <User size={15} style={iconStyle} />
                      <input
                        className="login-field"
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="John Doe"
                        autoComplete="name"
                        style={inputStyle}
                      />
                    </div>
                  </div>

                  {/* Date of Birth */}
                  <div>
                    <label style={labelStyle}>Date of Birth</label>
                    <div style={{ position:'relative' }}>
                      <Calendar size={15} style={iconStyle} />
                      <input
                        className="login-field"
                        type="text"
                        value={dob}
                        onChange={(e) => {
                          // Auto-insert slashes: dd/mm/yyyy
                          let val = e.target.value.replace(/[^\d]/g, '')
                          if (val.length >= 3 && val.length <= 4)      val = val.slice(0,2) + '/' + val.slice(2)
                          else if (val.length >= 5)                     val = val.slice(0,2) + '/' + val.slice(2,4) + '/' + val.slice(4,8)
                          setDob(val)
                        }}
                        placeholder="dd/mm/yyyy"
                        maxLength={10}
                        style={inputStyle}
                      />
                    </div>
                  </div>

                  {/* Contact Info */}
                  <div>
                    <label style={labelStyle}>Contact Info</label>
                    <div style={{ position:'relative' }}>
                      <Phone size={15} style={iconStyle} />
                      <input
                        className="login-field"
                        type="text"
                        value={contactInfo}
                        onChange={(e) => setContactInfo(e.target.value)}
                        placeholder="+91 9876543210"
                        autoComplete="tel"
                        style={inputStyle}
                      />
                    </div>
                  </div>
                </>
              )}
              {/* ─────────────────────────────────────────────────── */}

              {/* Email */}
              <div>
                <label style={labelStyle}>Email Address</label>
                <div style={{ position:'relative' }}>
                  <Mail size={15} style={iconStyle} />
                  <input
                    className="login-field"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    autoComplete="email"
                    style={inputStyle}
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label style={labelStyle}>Password</label>
                <div style={{ position:'relative' }}>
                  <Lock size={15} style={iconStyle} />
                  <input
                    className="login-field"
                    type="password"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setPasswordMismatch(false) }}
                    placeholder="••••••••"
                    autoComplete={isLogin ? 'current-password' : 'new-password'}
                    style={inputStyle}
                  />
                </div>
              </div>

              {/* ── CONFIRM PASSWORD (signup only) ─────────────────── */}
              {!isLogin && (
                <div>
                  <label style={labelStyle}>Confirm Password</label>
                  <div style={{ position:'relative' }}>
                    <Lock size={15} style={iconStyle} />
                    <input
                      className="login-field"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => { setConfirmPassword(e.target.value); setPasswordMismatch(false) }}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      style={{
                        ...inputStyle,
                        // Red border highlight on mismatch
                        ...(passwordMismatch ? {
                          borderColor:'rgba(239,68,68,0.6)',
                          boxShadow:'0 0 0 3px rgba(239,68,68,0.1)'
                        } : {})
                      }}
                    />
                  </div>
                  {/* Inline mismatch error */}
                  {passwordMismatch && (
                    <p style={{ marginTop:'6px', fontSize:'12px', color:'#f87171', fontWeight:500, letterSpacing:'0.01em' }}>
                      ✕ Password mismatch
                    </p>
                  )}
                </div>
              )}
              {/* ─────────────────────────────────────────────────── */}

              {/* Submit */}
              <button type="submit" disabled={loading} className="login-submit" style={{ marginTop:'4px' }}>
                {loading
                  ? <><Loader2 size={16} className="animate-spin" />{isLogin ? 'Signing in…' : 'Creating account…'}</>
                  : isLogin ? 'Sign In' : 'Create Account'
                }
              </button>
            </form>

            {/* Divider */}
            <div style={{ display:'flex', alignItems:'center', gap:'12px', margin:'20px 0' }}>
              <div style={{ flex:1, height:'1px', background:'rgba(255,255,255,0.06)' }} />
              <span style={{ fontSize:'11px', color:'#334155', userSelect:'none' }}>or</span>
              <div style={{ flex:1, height:'1px', background:'rgba(255,255,255,0.06)' }} />
            </div>

            {/* Guest */}
            <button type="button" onClick={handleGuest} className="login-guest">
              Continue as Guest →
            </button>

            {/* Footer */}
            <p style={{ textAlign:'center', fontSize:'11px', color:'#1e293b', marginTop:'20px', userSelect:'none' }}>
              Powered by Supabase Auth
            </p>
          </div>
        </div>
      </div>
    </>
  )
}