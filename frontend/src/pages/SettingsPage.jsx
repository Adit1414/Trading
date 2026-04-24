import { useEffect, useState } from 'react'
import {
  User, Lock, Bell, BarChart2, Trash2,
  ShieldCheck, Eye, EyeOff, Camera, Check, AlertTriangle,
  Mail, Phone, Globe, Monitor,
  Volume2, VolumeX, Smartphone, TrendingUp, DollarSign,
  LogOut, RefreshCw, Download, Key,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabaseClient'
import toast from 'react-hot-toast'
import {
  deleteUserAccount,
  exportUserData,
  getActiveSessions,
  getNotificationPreferences,
  getProfile,
  getTradingPreferences,
  revokeAllSessions,
  setupTwoFA,
  updateAvatar,
  updateNotificationPreferences,
  updateProfile,
  updateTradingPreferences,
  getBinanceSettings,
  saveBinanceSettings,
} from '../api/settings'

/* ── Section IDs ────────────────────────────────────────────────── */
const SECTIONS = [
  { id: 'profile',       label: 'Profile',          icon: User },
  { id: 'security',      label: 'Security',         icon: Lock },
  { id: 'notifications', label: 'Notifications',    icon: Bell },
  { id: 'trading',       label: 'Trading',          icon: BarChart2 },
  { id: 'danger',        label: 'Danger Zone',      icon: Trash2 },
]

/* ── Reusable Sub-components ─────────────────────────────────────── */

function SectionCard({ id, title, subtitle, icon: Icon, color = '#818cf8', children }) {
  return (
    <div
      id={id}
      style={{
        background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '20px',
        overflow: 'hidden',
        boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
        scrollMarginTop: '24px',
      }}
    >
      {/* Card header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          padding: '22px 28px',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
        }}
      >
        <div
          style={{
            width: '38px', height: '38px', borderRadius: '11px', flexShrink: 0,
            background: `${color}18`, border: `1px solid ${color}30`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', color,
          }}
        >
          <Icon size={18} strokeWidth={2} />
        </div>
        <div>
          <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'white', letterSpacing: '-0.01em' }}>{title}</h2>
          {subtitle && <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>{subtitle}</p>}
        </div>
      </div>
      {/* Body */}
      <div style={{ padding: '24px 28px' }}>{children}</div>
    </div>
  )
}

function FieldRow({ label, hint, children }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(180px,1fr) minmax(0,2fr)',
        gap: '20px',
        alignItems: 'start',
        padding: '16px 0',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}
      className="settings-field-row"
    >
      <div>
        <p style={{ fontSize: '13px', fontWeight: 600, color: '#cbd5e1' }}>{label}</p>
        {hint && <p style={{ fontSize: '11px', color: '#475569', marginTop: '3px', lineHeight: 1.4 }}>{hint}</p>}
      </div>
      <div>{children}</div>
    </div>
  )
}

function StyledInput({ value, onChange, type = 'text', placeholder, disabled, icon: Icon, suffix }) {
  return (
    <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
      {Icon && (
        <Icon
          size={14}
          style={{
            position: 'absolute', left: '13px',
            color: '#475569', pointerEvents: 'none', flexShrink: 0,
          }}
        />
      )}
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        style={{
          width: '100%',
          padding: Icon ? '10px 12px 10px 36px' : '10px 14px',
          paddingRight: suffix ? '44px' : '14px',
          borderRadius: '10px',
          background: disabled ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: disabled ? '#475569' : 'white',
          fontSize: '13px',
          fontFamily: 'inherit',
          outline: 'none',
          transition: 'border-color 0.18s, background 0.18s',
          cursor: disabled ? 'not-allowed' : 'text',
        }}
        onFocus={(e) => { if (!disabled) e.target.style.borderColor = 'rgba(129,140,248,0.5)' }}
        onBlur={(e) => { e.target.style.borderColor = 'rgba(255,255,255,0.08)' }}
      />
      {suffix && (
        <span style={{
          position: 'absolute', right: '13px',
          fontSize: '11px', color: '#475569', pointerEvents: 'none',
        }}>
          {suffix}
        </span>
      )}
    </div>
  )
}

function ToggleSwitch({ checked, onChange, id }) {
  return (
    <button
      id={id}
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      style={{
        width: '42px', height: '24px', borderRadius: '12px',
        background: checked ? 'linear-gradient(135deg,#818cf8,#6366f1)' : 'rgba(255,255,255,0.1)',
        border: 'none', cursor: 'pointer', position: 'relative',
        transition: 'background 0.25s', flexShrink: 0,
        boxShadow: checked ? '0 0 12px rgba(99,102,241,0.4)' : 'none',
      }}
    >
      <span
        style={{
          position: 'absolute', top: '3px',
          left: checked ? '21px' : '3px',
          width: '18px', height: '18px', borderRadius: '50%',
          background: 'white',
          transition: 'left 0.25s cubic-bezier(0.16,1,0.3,1)',
          boxShadow: '0 1px 4px rgba(0,0,0,0.4)',
        }}
      />
    </button>
  )
}

function SaveButton({ loading, onClick, label = 'Save Changes' }) {
  return (
    <button
      id="save-btn"
      onClick={onClick}
      disabled={loading}
      style={{
        display: 'flex', alignItems: 'center', gap: '7px',
        padding: '10px 22px', borderRadius: '12px',
        background: loading ? 'rgba(99,102,241,0.5)' : 'linear-gradient(135deg,#818cf8 0%,#6366f1 100%)',
        border: 'none', color: 'white', fontSize: '13px', fontWeight: 700,
        cursor: loading ? 'not-allowed' : 'pointer',
        boxShadow: '0 4px 18px rgba(99,102,241,0.35)',
        transition: 'all 0.2s',
      }}
      onMouseEnter={(e) => { if (!loading) e.currentTarget.style.opacity = '0.88' }}
      onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
    >
      {loading ? <RefreshCw size={14} style={{ animation: 'spin-cw 1s linear infinite' }} /> : <Check size={14} />}
      {label}
    </button>
  )
}

function NotifRow({ label, hint, emailKey, pushKey, notif, setNotif }) {
  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
        gap: '24px',
      }}
    >
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: '13px', fontWeight: 600, color: '#cbd5e1' }}>{label}</p>
        {hint && <p style={{ fontSize: '11px', color: '#475569', marginTop: '2px' }}>{hint}</p>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexShrink: 0 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '9px', color: '#475569', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Email</span>
          <ToggleSwitch
            id={`notif-email-${emailKey}`}
            checked={notif[emailKey] ?? false}
            onChange={(v) => setNotif((p) => ({ ...p, [emailKey]: v }))}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '9px', color: '#475569', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Push</span>
          <ToggleSwitch
            id={`notif-push-${pushKey}`}
            checked={notif[pushKey] ?? false}
            onChange={(v) => setNotif((p) => ({ ...p, [pushKey]: v }))}
          />
        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────
   Main Page
───────────────────────────────────────────────────────────────── */
export default function SettingsPage() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  /* ── Profile ── */
  const [profile, setProfile] = useState({
    fullName: user?.user_metadata?.full_name ?? '',
    phone:    user?.user_metadata?.phone ?? '',
    timezone: user?.user_metadata?.timezone ?? 'UTC+05:30',
    bio:      user?.user_metadata?.bio ?? '',
  })
  const [profileLoading, setProfileLoading] = useState(false)
  const [avatarLoading, setAvatarLoading] = useState(false)

  /* ── Security ── */
  const [passwords, setPasswords] = useState({ current: '', newPass: '', confirm: '' })
  const [showPass, setShowPass] = useState({ current: false, newPass: false, confirm: false })
  const [twoFA, setTwoFA] = useState(false)
  const [secLoading, setSecLoading] = useState(false)
  const [sessions, setSessions] = useState([])
  const [sessionsLoading, setSessionsLoading] = useState(false)

  /* ── Notifications ── */
  const [notif, setNotif] = useState({
    tradeExecEmail: true,  tradeExecPush: true,
    botAlertEmail: true,   botAlertPush: false,
    pnlEmail: false,       pnlPush: true,
    newsEmail: false,      newsPush: false,
    systemEmail: true,     systemPush: true,
    soundAlerts: true,
  })
  const [notifLoading, setNotifLoading] = useState(false)

  /* ── Trading Preferences ── */
  const [trading, setTrading] = useState({
    defaultCapital: '10000',
    riskPerTrade: '2',
    defaultLeverage: '1',
    defaultExchange: 'binance',
    paperMode: true,
    autoStop: true,
    slippageTolerance: '0.1',
    currency: 'USD',
  })
  const [tradingLoading, setTradingLoading] = useState(false)
  const [binanceLoading, setBinanceLoading] = useState(false)
  const [binanceSaving, setBinanceSaving] = useState(false)
  const [binanceSettings, setBinanceSettings] = useState({
    connected: false,
    api_key_masked: null,
    has_secret: false,
  })
  const [binanceForm, setBinanceForm] = useState({
    apiKey: '',
    secret: '',
  })

  /* ── Active section (sidebar highlight) ── */
  const [activeSection, setActiveSection] = useState('profile')

  useEffect(() => {
    const loadBinanceSettings = async () => {
      setBinanceLoading(true)
      try {
        const data = await getBinanceSettings()
        setBinanceSettings({
          connected: Boolean(data?.connected),
          api_key_masked: data?.api_key_masked || null,
          has_secret: Boolean(data?.has_secret),
        })
      } catch (err) {
        console.error('Failed to load Binance settings:', err)
      } finally {
        setBinanceLoading(false)
      }
    }
    loadBinanceSettings()
  }, [])

  /* ── Sidebar scroll ── */
  const scrollTo = (id) => {
    setActiveSection(id)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  /* ── Handlers ── */
  const saveProfile = async () => {
    setProfileLoading(true)
    try {
      await updateProfile({
        full_name: profile.fullName,
        phone: profile.phone,
        timezone: profile.timezone,
        bio: profile.bio,
      })
      
      // Update Supabase Auth metadata so the session data (and initial load) reflects the new name permanently
      const { error: authError } = await supabase.auth.updateUser({
        data: { full_name: profile.fullName, phone: profile.phone, timezone: profile.timezone, bio: profile.bio }
      })
      if (authError) {
        console.error('Failed to sync auth metadata:', authError)
      }

      toast.success('Profile updated successfully.')
    } catch (err) {
      toast.error(err.message || 'Failed to update profile.')
    } finally {
      setProfileLoading(false)
    }
  }

  const savePassword = async () => {
    if (!passwords.newPass || passwords.newPass !== passwords.confirm) {
      toast.error('Passwords do not match.')
      return
    }
    if (passwords.newPass.length < 8) {
      toast.error('Password must be at least 8 characters.')
      return
    }
    setSecLoading(true)
    try {
      const { error } = await supabase.auth.updateUser({ password: passwords.newPass })
      if (error) throw error
      toast.success('Password updated.')
      setPasswords({ current: '', newPass: '', confirm: '' })
    } catch (err) {
      toast.error(err.message || 'Failed to update password.')
    } finally {
      setSecLoading(false)
    }
  }

  const saveTradingPrefs = async () => {
    setTradingLoading(true)
    try {
      await updateTradingPreferences(trading)
      toast.success('Trading preferences saved.')
    } catch (err) {
      toast.error(err.message || 'Failed to save trading preferences.')
    } finally {
      setTradingLoading(false)
    }
  }

  const saveBinanceKeys = async () => {
    if (!binanceForm.apiKey.trim() || !binanceForm.secret.trim()) {
      toast.error('Please provide both Binance API key and secret.')
      return
    }
    setBinanceSaving(true)
    try {
      await saveBinanceSettings({
        binance_api_key: binanceForm.apiKey.trim(),
        binance_secret: binanceForm.secret.trim(),
      })
      const refreshed = await getBinanceSettings()
      setBinanceSettings({
        connected: Boolean(refreshed?.connected),
        api_key_masked: refreshed?.api_key_masked || null,
        has_secret: Boolean(refreshed?.has_secret),
      })
      setBinanceForm({ apiKey: '', secret: '' })
      toast.success('Binance API credentials saved securely.')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to save Binance settings.')
    } finally {
      setBinanceSaving(false)
    }
  }

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm(
      'Are you absolutely sure? This action CANNOT be undone. All your bots, backtests and data will be permanently deleted.'
    )
    if (!confirmed) return
    try {
      await deleteUserAccount()
      toast.success('Account deleted.')
      await logout()
      navigate('/login')
    } catch (err) {
      toast.error(err.message || 'Failed to delete account.')
    }
  }

  const handleExportData = async () => {
    try {
      const data = await exportUserData()
      const serialized = JSON.stringify(data, null, 2)
      const blob = new Blob([serialized], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = 'algokaisen_export.json'; a.click()
      URL.revokeObjectURL(url)
      toast.success('Data exported.')
    } catch (err) {
      toast.error(err.message || 'Failed to export data.')
    }
  }

  const saveNotificationPrefs = async () => {
    setNotifLoading(true)
    try {
      await updateNotificationPreferences(notif)
      toast.success('Notification preferences saved.')
    } catch (err) {
      toast.error(err.message || 'Failed to save notification preferences.')
    } finally {
      setNotifLoading(false)
    }
  }

  const loadSettings = async () => {
    try {
      const [profileData, notifData, tradingData, sessionsData] = await Promise.all([
        getProfile(),
        getNotificationPreferences(),
        getTradingPreferences(),
        getActiveSessions(),
      ])
      const metadata = user?.user_metadata || {}
      setProfile({
        fullName: profileData.full_name || metadata.full_name || '',
        phone: profileData.phone || metadata.phone || metadata.contact_info || '',
        timezone: profileData.timezone || metadata.timezone || 'UTC+05:30',
        bio: profileData.bio || metadata.bio || '',
      })
      setNotif((prev) => ({ ...prev, ...notifData }))
      setTrading((prev) => ({ ...prev, ...tradingData }))
      setSessions(sessionsData || [])
    } catch (err) {
      toast.error(err.message || 'Failed to load settings.')
    }
  }

  useEffect(() => {
    loadSettings()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleAvatarChange = async () => {
    const url = window.prompt('Enter avatar image URL')
    if (!url) return
    setAvatarLoading(true)
    try {
      await updateAvatar({ avatar_url: url })
      await loadSettings()
      toast.success('Avatar updated.')
    } catch (err) {
      toast.error(err.message || 'Failed to update avatar.')
    } finally {
      setAvatarLoading(false)
    }
  }

  const handleToggle2FA = async (value) => {
    setTwoFA(value)
    if (!value) return
    try {
      const data = await setupTwoFA()
      toast.success(`2FA secret generated: ${data.secret}`)
    } catch (err) {
      toast.error(err.message || 'Failed to setup 2FA.')
      setTwoFA(false)
    }
  }

  const handleRevokeAllSessions = async () => {
    setSessionsLoading(true)
    try {
      await revokeAllSessions()
      const fresh = await getActiveSessions()
      setSessions(fresh || [])
      toast.success('Other sessions revoked.')
    } catch (err) {
      toast.error(err.message || 'Failed to revoke sessions.')
    } finally {
      setSessionsLoading(false)
    }
  }

  const handleSignOutEverywhere = async () => {
    await handleRevokeAllSessions()
    await logout()
    navigate('/login')
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 28px' }}>
      {/* ── Page Header ── */}
      <div style={{ marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '6px' }}>
          <div
            style={{
              width: '46px', height: '46px', borderRadius: '14px',
              background: 'rgba(129,140,248,0.1)', border: '1px solid rgba(129,140,248,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8',
            }}
          >
            <User size={22} strokeWidth={2} />
          </div>
          <div>
            <h1 style={{ fontSize: '26px', fontWeight: 700, color: 'white', letterSpacing: '-0.02em', lineHeight: 1 }}>
              Account Settings
            </h1>
            <p style={{ fontSize: '13px', color: '#64748b', marginTop: '5px' }}>
              Manage your profile, security, preferences and more.
            </p>
          </div>
        </div>
      </div>

      {/* ── Two-column layout ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '24px', alignItems: 'start' }} className="settings-grid">

        {/* ── Left Sidebar ── */}
        <div
          style={{
            background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '18px',
            padding: '12px',
            position: 'sticky',
            top: '24px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
          }}
        >
          {/* Avatar hint */}
          <div
            style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '10px 10px 14px',
              borderBottom: '1px solid rgba(255,255,255,0.05)',
              marginBottom: '8px',
            }}
          >
            <div
              style={{
                width: '36px', height: '36px', borderRadius: '50%', flexShrink: 0,
                background: 'rgba(129,140,248,0.15)', border: '1px solid rgba(129,140,248,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#818cf8' }}>
                {user?.email?.[0]?.toUpperCase() ?? 'U'}
              </span>
            </div>
            <div style={{ minWidth: 0 }}>
              <p style={{ fontSize: '12px', fontWeight: 600, color: 'white' }} className="truncate">
                {user?.user_metadata?.full_name || 'User'}
              </p>
              <p style={{ fontSize: '10px', color: '#475569', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user?.email || '—'}
              </p>
            </div>
          </div>

          {/* Nav links */}
          <nav>
            {SECTIONS.map(({ id, label, icon: Icon }) => {
              const isActive = activeSection === id
              const isDanger = id === 'danger'
              return (
                <button
                  key={id}
                  id={`nav-${id}`}
                  onClick={() => scrollTo(id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '9px',
                    width: '100%', padding: '9px 12px', borderRadius: '10px',
                    background: isActive
                      ? isDanger ? 'rgba(244,63,94,0.08)' : 'rgba(129,140,248,0.1)'
                      : 'transparent',
                    border: isActive
                      ? isDanger ? '1px solid rgba(244,63,94,0.2)' : '1px solid rgba(129,140,248,0.22)'
                      : '1px solid transparent',
                    color: isActive
                      ? isDanger ? '#f43f5e' : 'white'
                      : isDanger ? '#64748b' : '#64748b',
                    fontSize: '13px', fontWeight: 500, cursor: 'pointer',
                    transition: 'all 0.18s', textAlign: 'left', marginBottom: '2px',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = isDanger ? 'rgba(244,63,94,0.05)' : 'rgba(255,255,255,0.04)'
                      e.currentTarget.style.color = isDanger ? '#f43f5e' : 'white'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent'
                      e.currentTarget.style.color = isDanger ? '#64748b' : '#64748b'
                    }
                  }}
                >
                  <Icon
                    size={15}
                    style={{ color: isActive ? (isDanger ? '#f43f5e' : '#818cf8') : '#475569', flexShrink: 0 }}
                  />
                  {label}
                </button>
              )
            })}
          </nav>
        </div>

        {/* ── Right Content ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

          {/* ── 1. PROFILE ─────────────────────────────────────────── */}
          <SectionCard id="profile" title="Profile" subtitle="Your public identity on Numatix" icon={User}>

            {/* Avatar row */}
            <div
              style={{
                display: 'flex', alignItems: 'center', gap: '20px',
                padding: '0 0 20px',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
                marginBottom: '4px',
              }}
            >
              <div style={{ position: 'relative' }}>
                <div
                  style={{
                    width: '72px', height: '72px', borderRadius: '50%',
                    background: 'radial-gradient(circle at 30% 30%, rgba(129,140,248,0.3), rgba(99,102,241,0.1))',
                    border: '2px solid rgba(129,140,248,0.3)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  <span style={{ fontSize: '26px', fontWeight: 700, color: '#818cf8' }}>
                    {(profile.fullName || user?.email || 'U')[0].toUpperCase()}
                  </span>
                </div>
                <button
                  title="Change avatar"
                  onClick={handleAvatarChange}
                  disabled={avatarLoading}
                  style={{
                    position: 'absolute', bottom: 0, right: 0,
                    width: '24px', height: '24px', borderRadius: '50%',
                    background: '#6366f1', border: '2px solid #0b1221',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    cursor: 'pointer', color: 'white',
                  }}
                >
                  <Camera size={11} />
                </button>
              </div>
              <div>
                <p style={{ fontSize: '14px', fontWeight: 600, color: 'white' }}>
                  {profile.fullName || 'Your Name'}
                </p>
                <p style={{ fontSize: '12px', color: '#475569', marginTop: '2px' }}>{user?.email}</p>
                <p style={{ fontSize: '10px', color: '#818cf8', marginTop: '6px', fontWeight: 600 }}>Pro Plan · Active</p>
              </div>
            </div>

            <FieldRow label="Full Name" hint="Displayed across the platform">
              <StyledInput
                icon={User}
                value={profile.fullName}
                onChange={(e) => setProfile((p) => ({ ...p, fullName: e.target.value }))}
                placeholder="e.g. John Doe"
              />
            </FieldRow>

            <FieldRow label="Email Address" hint="Used for login and notifications">
              <StyledInput
                icon={Mail}
                value={user?.email ?? ''}
                disabled
                placeholder="your@email.com"
              />
            </FieldRow>

            <FieldRow label="Phone Number" hint="Optional — for SMS trade alerts">
              <StyledInput
                icon={Phone}
                value={profile.phone}
                onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))}
                placeholder="+91 98765 43210"
              />
            </FieldRow>

            <FieldRow label="Timezone" hint="Used for trade timestamps and reports">
              <div style={{ position: 'relative' }}>
                <Globe size={14} style={{ position: 'absolute', left: '13px', top: '50%', transform: 'translateY(-50%)', color: '#475569', pointerEvents: 'none' }} />
                <select
                  value={profile.timezone}
                  onChange={(e) => setProfile((p) => ({ ...p, timezone: e.target.value }))}
                  style={{
                    width: '100%', padding: '10px 14px 10px 36px',
                    borderRadius: '10px',
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    color: 'white', fontSize: '13px', fontFamily: 'inherit',
                    outline: 'none', cursor: 'pointer', appearance: 'none',
                  }}
                >
                  {['UTC-08:00', 'UTC-05:00', 'UTC+00:00', 'UTC+01:00', 'UTC+03:00', 'UTC+05:30', 'UTC+08:00', 'UTC+09:00'].map((tz) => (
                    <option key={tz} value={tz} style={{ background: '#0f1729' }}>{tz}</option>
                  ))}
                </select>
              </div>
            </FieldRow>

            <FieldRow label="Bio" hint="Short description visible on your profile">
              <textarea
                value={profile.bio}
                onChange={(e) => setProfile((p) => ({ ...p, bio: e.target.value }))}
                placeholder="Algo trader · Quant enthusiast"
                rows={3}
                style={{
                  width: '100%', padding: '10px 14px', borderRadius: '10px',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: 'white', fontSize: '13px', fontFamily: 'inherit',
                  resize: 'vertical', outline: 'none', transition: 'border-color 0.18s', lineHeight: 1.5,
                }}
                onFocus={(e) => { e.target.style.borderColor = 'rgba(129,140,248,0.5)' }}
                onBlur={(e) => { e.target.style.borderColor = 'rgba(255,255,255,0.08)' }}
              />
            </FieldRow>

            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '12px' }}>
              <SaveButton loading={profileLoading} onClick={saveProfile} />
            </div>
          </SectionCard>

          {/* ── 2. SECURITY ────────────────────────────────────────── */}
          <SectionCard id="security" title="Security" subtitle="Password, 2FA and session management" icon={Lock} color="#10b981">

            <FieldRow label="Current Password" hint="Verify your identity before changing">
              <div style={{ position: 'relative' }}>
                <StyledInput
                  icon={Key}
                  type={showPass.current ? 'text' : 'password'}
                  value={passwords.current}
                  onChange={(e) => setPasswords((p) => ({ ...p, current: e.target.value }))}
                  placeholder="••••••••"
                />
                <button
                  onClick={() => setShowPass((p) => ({ ...p, current: !p.current }))}
                  style={{
                    position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#475569', padding: '4px',
                  }}
                >
                  {showPass.current ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </FieldRow>

            <FieldRow label="New Password" hint="At least 8 characters">
              <div style={{ position: 'relative' }}>
                <StyledInput
                  icon={Lock}
                  type={showPass.newPass ? 'text' : 'password'}
                  value={passwords.newPass}
                  onChange={(e) => setPasswords((p) => ({ ...p, newPass: e.target.value }))}
                  placeholder="••••••••"
                />
                <button
                  onClick={() => setShowPass((p) => ({ ...p, newPass: !p.newPass }))}
                  style={{
                    position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#475569', padding: '4px',
                  }}
                >
                  {showPass.newPass ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {/* Password strength bar */}
              {passwords.newPass && (
                <div style={{ marginTop: '8px' }}>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {[4, 8, 12].map((threshold, i) => (
                      <div
                        key={i}
                        style={{
                          flex: 1, height: '3px', borderRadius: '2px',
                          background: passwords.newPass.length >= threshold
                            ? i === 0 ? '#f43f5e' : i === 1 ? '#f59e0b' : '#10b981'
                            : 'rgba(255,255,255,0.08)',
                          transition: 'background 0.3s',
                        }}
                      />
                    ))}
                  </div>
                  <p style={{ fontSize: '10px', color: '#475569', marginTop: '4px' }}>
                    {passwords.newPass.length < 4 ? 'Too weak' : passwords.newPass.length < 8 ? 'Weak' : passwords.newPass.length < 12 ? 'Good' : 'Strong'}
                  </p>
                </div>
              )}
            </FieldRow>

            <FieldRow label="Confirm Password" hint="Re-enter your new password">
              <div style={{ position: 'relative' }}>
                <StyledInput
                  icon={ShieldCheck}
                  type={showPass.confirm ? 'text' : 'password'}
                  value={passwords.confirm}
                  onChange={(e) => setPasswords((p) => ({ ...p, confirm: e.target.value }))}
                  placeholder="••••••••"
                />
                <button
                  onClick={() => setShowPass((p) => ({ ...p, confirm: !p.confirm }))}
                  style={{
                    position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#475569', padding: '4px',
                  }}
                >
                  {showPass.confirm ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              {passwords.confirm && passwords.newPass !== passwords.confirm && (
                <p style={{ fontSize: '11px', color: '#f43f5e', marginTop: '5px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <AlertTriangle size={11} /> Passwords do not match
                </p>
              )}
            </FieldRow>

            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '12px', marginBottom: '20px' }}>
              <SaveButton loading={secLoading} onClick={savePassword} label="Update Password" />
            </div>

            {/* 2FA */}
            <div
              style={{
                padding: '16px 18px',
                borderRadius: '14px',
                background: 'rgba(16,185,129,0.04)',
                border: '1px solid rgba(16,185,129,0.1)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <ShieldCheck size={20} style={{ color: '#10b981' }} />
                  <div>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: 'white' }}>Two-Factor Authentication</p>
                    <p style={{ fontSize: '11px', color: '#475569', marginTop: '2px' }}>
                      Add an extra layer of security to your account
                    </p>
                  </div>
                </div>
                <ToggleSwitch id="2fa-toggle" checked={twoFA} onChange={handleToggle2FA} />
              </div>
              {twoFA && (
                <div
                  style={{
                    marginTop: '14px', padding: '12px 14px', borderRadius: '10px',
                    background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.15)',
                    fontSize: '12px', color: '#6ee7b7',
                  }}
                >
                  2FA seed generated. Add it to your authenticator app and verify with the backend verify endpoint.
                </div>
              )}
            </div>

            {/* Active Sessions */}
            <div style={{ marginTop: '20px' }}>
              <p style={{ fontSize: '12px', fontWeight: 700, color: '#64748b', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '12px' }}>
                Active Sessions
              </p>
              {sessions.map((session, idx) => (
                <div
                  key={session.id || idx}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 14px', borderRadius: '12px', marginBottom: '8px',
                    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {idx === 0 ? <Monitor size={15} style={{ color: '#818cf8' }} /> : <Smartphone size={15} style={{ color: '#818cf8' }} />}
                    <div>
                      <p style={{ fontSize: '12px', fontWeight: 600, color: 'white' }}>{session.device}</p>
                      <p style={{ fontSize: '10px', color: '#475569' }}>{session.location} · {session.last_active}</p>
                    </div>
                  </div>
                  {session.current
                    ? <span style={{ fontSize: '10px', fontWeight: 700, color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '3px 8px', borderRadius: '5px' }}>Current</span>
                    : <button style={{ fontSize: '11px', color: '#f43f5e', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }} onClick={handleRevokeAllSessions}>Revoke</button>
                  }
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
                <button
                  onClick={handleRevokeAllSessions}
                  disabled={sessionsLoading}
                  style={{
                    fontSize: '12px',
                    color: '#f43f5e',
                    background: 'rgba(244,63,94,0.08)',
                    border: '1px solid rgba(244,63,94,0.2)',
                    borderRadius: '9px',
                    padding: '7px 12px',
                    cursor: sessionsLoading ? 'not-allowed' : 'pointer',
                  }}
                >
                  Revoke Other Sessions
                </button>
              </div>
            </div>
          </SectionCard>

          {/* ── 3. NOTIFICATIONS ───────────────────────────────────── */}
          <SectionCard id="notifications" title="Notifications" subtitle="Control how and when you are alerted" icon={Bell} color="#f59e0b">

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
              <div style={{ display: 'flex', gap: '32px', paddingRight: '4px' }}>
                <span style={{ fontSize: '10px', color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Mail size={11} /> Email
                </span>
                <span style={{ fontSize: '10px', color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Bell size={11} /> Push
                </span>
              </div>
            </div>

            <NotifRow label="Trade Executions" hint="When a bot opens or closes a position" emailKey="tradeExecEmail" pushKey="tradeExecPush" notif={notif} setNotif={setNotif} />
            <NotifRow label="Bot Alerts" hint="Stop-loss hits, circuit breakers, errors" emailKey="botAlertEmail" pushKey="botAlertPush" notif={notif} setNotif={setNotif} />
            <NotifRow label="P&L Reports" hint="Daily and weekly performance summaries" emailKey="pnlEmail" pushKey="pnlPush" notif={notif} setNotif={setNotif} />
            <NotifRow label="Market News" hint="Macro events affecting your open trades" emailKey="newsEmail" pushKey="newsPush" notif={notif} setNotif={setNotif} />
            <NotifRow label="System Updates" hint="Platform maintenance and new features" emailKey="systemEmail" pushKey="systemPush" notif={notif} setNotif={setNotif} />

            {/* Sound alerts */}
            <div
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '16px 0 0',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {notif.soundAlerts ? <Volume2 size={16} style={{ color: '#f59e0b' }} /> : <VolumeX size={16} style={{ color: '#475569' }} />}
                <div>
                  <p style={{ fontSize: '13px', fontWeight: 600, color: '#cbd5e1' }}>Sound Alerts</p>
                  <p style={{ fontSize: '11px', color: '#475569', marginTop: '2px' }}>Play audio chimes on trade events</p>
                </div>
              </div>
              <ToggleSwitch id="sound-toggle" checked={notif.soundAlerts} onChange={(v) => setNotif((p) => ({ ...p, soundAlerts: v }))} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '16px' }}>
              <SaveButton
                loading={notifLoading}
                onClick={saveNotificationPrefs}
                label="Save Preferences"
              />
            </div>
          </SectionCard>

          {/* ── 4. TRADING PREFERENCES ─────────────────────────────── */}
          <SectionCard id="trading" title="Trading" subtitle="Default parameters for new bots and backtests" icon={BarChart2} color="#06b6d4">
            <div
              style={{
                padding: '14px',
                borderRadius: '12px',
                background: 'rgba(129,140,248,0.08)',
                border: '1px solid rgba(129,140,248,0.2)',
                marginBottom: '16px',
              }}
            >
              <p style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '8px' }}>
                Binance Connection Status
              </p>
              {binanceLoading ? (
                <p style={{ fontSize: '12px', color: '#64748b' }}>Loading connection status…</p>
              ) : (
                <div style={{ display: 'flex', gap: '18px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '12px', color: binanceSettings.connected ? '#10b981' : '#f43f5e', fontWeight: 700 }}>
                    {binanceSettings.connected ? 'Connected' : 'Not connected'}
                  </span>
                  <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                    API Key: {binanceSettings.api_key_masked || 'Not set'}
                  </span>
                  <span style={{ fontSize: '12px', color: '#cbd5e1' }}>
                    Secret: {binanceSettings.has_secret ? 'Stored' : 'Not stored'}
                  </span>
                </div>
              )}
            </div>

            <FieldRow label="Binance API Key" hint="Stored encrypted in backend">
              <StyledInput
                icon={Key}
                value={binanceForm.apiKey}
                onChange={(e) => setBinanceForm((p) => ({ ...p, apiKey: e.target.value }))}
                placeholder="Paste your Binance API key"
              />
            </FieldRow>

            <FieldRow label="Binance API Secret" hint="Stored encrypted, never shown in plaintext">
              <StyledInput
                icon={ShieldCheck}
                type="password"
                value={binanceForm.secret}
                onChange={(e) => setBinanceForm((p) => ({ ...p, secret: e.target.value }))}
                placeholder="Paste your Binance API secret"
              />
            </FieldRow>

            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '12px', marginBottom: '12px' }}>
              <SaveButton loading={binanceSaving} onClick={saveBinanceKeys} label="Save Binance Keys" />
            </div>

            <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', marginBottom: '12px' }} />

            <FieldRow label="Default Capital" hint="Starting capital for new strategies (USD)">
              <StyledInput
                icon={DollarSign}
                type="number"
                value={trading.defaultCapital}
                onChange={(e) => setTrading((p) => ({ ...p, defaultCapital: e.target.value }))}
                placeholder="10000"
                suffix="USD"
              />
            </FieldRow>

            <FieldRow label="Risk Per Trade" hint="Max % of capital risked on a single trade">
              <StyledInput
                icon={TrendingUp}
                type="number"
                value={trading.riskPerTrade}
                onChange={(e) => setTrading((p) => ({ ...p, riskPerTrade: e.target.value }))}
                placeholder="2"
                suffix="%"
              />
            </FieldRow>

            <FieldRow label="Default Leverage" hint="Applied to new futures bots (1 = spot)">
              <StyledInput
                type="number"
                value={trading.defaultLeverage}
                onChange={(e) => setTrading((p) => ({ ...p, defaultLeverage: e.target.value }))}
                placeholder="1"
                suffix="×"
              />
            </FieldRow>

            <FieldRow label="Slippage Tolerance" hint="Maximum accepted slippage per order">
              <StyledInput
                type="number"
                value={trading.slippageTolerance}
                onChange={(e) => setTrading((p) => ({ ...p, slippageTolerance: e.target.value }))}
                placeholder="0.1"
                suffix="%"
              />
            </FieldRow>


            <FieldRow label="Paper Trading Mode" hint="Simulate trades without real money">
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <ToggleSwitch id="paper-mode-toggle" checked={trading.paperMode} onChange={(v) => setTrading((p) => ({ ...p, paperMode: v }))} />
                <span style={{ fontSize: '12px', color: trading.paperMode ? '#10b981' : '#475569', fontWeight: 600 }}>
                  {trading.paperMode ? 'Paper Mode ON' : 'Live Mode'}
                </span>
              </div>
            </FieldRow>

            <FieldRow label="Auto Stop-Loss" hint="Automatically apply calculated stop orders">
              <ToggleSwitch id="auto-stop-toggle" checked={trading.autoStop} onChange={(v) => setTrading((p) => ({ ...p, autoStop: v }))} />
            </FieldRow>

            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '12px' }}>
              <SaveButton loading={tradingLoading} onClick={saveTradingPrefs} label="Save Trading Prefs" />
            </div>
          </SectionCard>

          {/* ── 5. DANGER ZONE ─────────────────────────────────────── */}
          <SectionCard id="danger" title="Danger Zone" subtitle="Irreversible actions — proceed with care" icon={Trash2} color="#f43f5e">

            {/* Export */}
            <div
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '16px 18px', borderRadius: '14px',
                background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                marginBottom: '12px',
              }}
            >
              <div>
                <p style={{ fontSize: '13px', fontWeight: 600, color: 'white' }}>Export My Data</p>
                <p style={{ fontSize: '11px', color: '#475569', marginTop: '3px' }}>
                  Download a copy of your account data and settings as JSON
                </p>
              </div>
              <button
                id="export-data-btn"
                onClick={handleExportData}
                style={{
                  display: 'flex', alignItems: 'center', gap: '7px',
                  padding: '9px 16px', borderRadius: '10px',
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#94a3b8', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                  flexShrink: 0, transition: 'all 0.2s', whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; e.currentTarget.style.color = 'white' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = '#94a3b8' }}
              >
                <Download size={13} /> Export Data
              </button>
            </div>

            {/* Sign out all */}
            <div
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '16px 18px', borderRadius: '14px',
                background: 'rgba(244,63,94,0.03)', border: '1px solid rgba(244,63,94,0.1)',
                marginBottom: '12px',
              }}
            >
              <div>
                <p style={{ fontSize: '13px', fontWeight: 600, color: 'white' }}>Sign Out Everywhere</p>
                <p style={{ fontSize: '11px', color: '#475569', marginTop: '3px' }}>
                  Revoke all active sessions on all devices immediately
                </p>
              </div>
              <button
                id="signout-all-btn"
                onClick={handleSignOutEverywhere}
                style={{
                  display: 'flex', alignItems: 'center', gap: '7px',
                  padding: '9px 16px', borderRadius: '10px',
                  background: 'rgba(244,63,94,0.08)',
                  border: '1px solid rgba(244,63,94,0.2)',
                  color: '#f43f5e', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
                  flexShrink: 0, transition: 'all 0.2s', whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(244,63,94,0.15)' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(244,63,94,0.08)' }}
              >
                <LogOut size={13} /> Sign Out All
              </button>
            </div>

            {/* Delete Account */}
            <div
              style={{
                padding: '16px 18px', borderRadius: '14px',
                background: 'rgba(244,63,94,0.04)',
                border: '2px solid rgba(244,63,94,0.18)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '14px' }}>
                <AlertTriangle size={18} style={{ color: '#f43f5e', flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <p style={{ fontSize: '13px', fontWeight: 700, color: '#f87171' }}>Delete Account</p>
                  <p style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px', lineHeight: 1.5 }}>
                    Permanently delete your account and all associated data — bots, backtests, strategies, and history.
                    This action is <strong style={{ color: '#f43f5e' }}>irreversible</strong>.
                  </p>
                </div>
              </div>
              <button
                id="delete-account-btn"
                onClick={handleDeleteAccount}
                style={{
                  display: 'flex', alignItems: 'center', gap: '7px',
                  padding: '10px 20px', borderRadius: '10px',
                  background: 'rgba(244,63,94,0.12)',
                  border: '1px solid rgba(244,63,94,0.3)',
                  color: '#f43f5e', fontSize: '13px', fontWeight: 700, cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(244,63,94,0.22)' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(244,63,94,0.12)' }}
              >
                <Trash2 size={14} /> Delete My Account
              </button>
            </div>
          </SectionCard>

        </div>
      </div>

      {/* ── Responsive styles ── */}
      <style>{`
        @media (max-width: 860px) {
          .settings-grid {
            grid-template-columns: 1fr !important;
          }
          .settings-field-row {
            grid-template-columns: 1fr !important;
            gap: 8px !important;
          }
        }
      `}</style>
    </div>
  )
}
