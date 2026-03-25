import { useState, useEffect } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import {
  LayoutDashboard, TrendingUp, Bot, Sparkles,
  Settings, LogOut, Menu, X, ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'

const NAV_MENU = [
  { name: 'Dashboard',    path: '/dashboard',  icon: LayoutDashboard },
  { name: 'Backtest',     path: '/backtests',  icon: TrendingUp },
  { name: 'Trading Bots', path: '/bots',        icon: Bot },
  { name: 'Strategies',   path: '/strategies', icon: Sparkles },
  { name: 'Settings',     path: '/settings',   icon: Settings },
]

const PAGE_TITLES = {
  '/dashboard':  'Dashboard',
  '/backtests':  'Backtests',
  '/bots':       'Trading Bots',
  '/strategies': 'Strategies',
  '/settings':   'Settings',
}

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate   = useNavigate()
  const location   = useLocation()
  const [open, setOpen] = useState(false)

  /* Close on navigation */
  useEffect(() => { setOpen(false) }, [location.pathname])

  /* Close on Escape */
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  /* Lock body scroll when sidebar is open */
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  const handleLogout = async () => {
    await logout()
    toast.success('Logged out.')
    navigate('/login')
  }

  const currentTitle =
    Object.entries(PAGE_TITLES).find(([p]) => location.pathname.startsWith(p))?.[1] ?? 'Dashboard'

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-white font-sans selection:bg-[#818cf8]/30">

      {/* ── Backdrop ── */}
      <div
        onClick={() => setOpen(false)}
        className="fixed inset-0 z-40 transition-all duration-300"
        style={{
          background: open ? 'rgba(0,0,0,0.65)' : 'transparent',
          backdropFilter: open ? 'blur(4px)' : 'blur(0px)',
          WebkitBackdropFilter: open ? 'blur(4px)' : 'blur(0px)',
          pointerEvents: open ? 'auto' : 'none',
        }}
      />

      {/* ── Sidebar ── */}
      <aside
        className="fixed inset-y-0 left-0 z-50 flex flex-col"
        style={{
          width: '260px',
          background: 'linear-gradient(180deg, #0f1729 0%, #0b1221 100%)',
          borderRight: '1px solid rgba(255,255,255,0.06)',
          transform: open ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          boxShadow: open ? '20px 0 60px rgba(0,0,0,0.5)' : 'none',
        }}
      >
        {/* Brand row */}
        <div
          className="flex items-center justify-between shrink-0"
          style={{ height: '70px', padding: '0 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex items-center justify-center shrink-0"
              style={{
                width: '36px', height: '36px', borderRadius: '10px',
                background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)',
                boxShadow: '0 0 18px rgba(99,102,241,0.45)',
              }}
            >
              <span className="text-white font-bold text-sm leading-none">N</span>
            </div>
            <div>
              <p className="text-white font-bold text-[15px] leading-none tracking-wide">Numatix</p>
              <p className="text-[10px] mt-0.5" style={{ color: '#475569' }}>Trading Platform</p>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="flex items-center justify-center rounded-lg transition-colors"
            style={{ width: '30px', height: '30px', color: '#475569' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'white' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#475569' }}
          >
            <X size={17} />
          </button>
        </div>

        {/* Section label */}
        <div style={{ padding: '20px 20px 8px' }}>
          <p style={{ fontSize: '10px', fontWeight: 600, color: '#334155', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Menu
          </p>
        </div>

        {/* Nav links */}
        <nav className="flex-1 overflow-y-auto" style={{ padding: '0 12px' }}>
          <div className="space-y-1">
            {NAV_MENU.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => isActive ? '_nav-active' : '_nav-idle'}
                style={({ isActive }) => ({
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px 14px',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: 500,
                  textDecoration: 'none',
                  transition: 'all 0.18s ease',
                  border: isActive ? '1px solid rgba(129,140,248,0.22)' : '1px solid transparent',
                  background: isActive ? 'rgba(129,140,248,0.1)' : 'transparent',
                  color: isActive ? 'white' : '#64748b',
                })}
              >
                {({ isActive }) => (
                  <>
                    <item.icon
                      size={17}
                      strokeWidth={isActive ? 2.5 : 2}
                      style={{ color: isActive ? '#818cf8' : '#475569', flexShrink: 0 }}
                    />
                    <span style={{ flex: 1 }}>{item.name}</span>
                    {isActive && (
                      <ChevronRight size={13} style={{ color: 'rgba(129,140,248,0.5)' }} />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        </nav>

        {/* User panel */}
        <div style={{ padding: '12px', borderTop: '1px solid rgba(255,255,255,0.06)', flexShrink: 0 }}>
          <div
            className="flex items-center gap-3 rounded-xl transition-colors cursor-default"
            style={{
              padding: '10px 12px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            {/* Avatar */}
            <div
              className="flex items-center justify-center shrink-0"
              style={{
                width: '32px', height: '32px', borderRadius: '50%',
                background: 'rgba(129,140,248,0.15)',
                border: '1px solid rgba(129,140,248,0.3)',
              }}
            >
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#818cf8' }}>
                {user?.email?.[0]?.toUpperCase() || 'G'}
              </span>
            </div>
            {/* Info */}
            <div className="flex-1 min-w-0">
              <p style={{ fontSize: '12px', fontWeight: 600, color: 'white' }} className="truncate">
                {user?.email || 'Guest'}
              </p>
              <p style={{ fontSize: '10px', color: '#475569' }}>Pro Plan</p>
            </div>
            {/* Logout */}
            <button
              onClick={handleLogout}
              title="Sign out"
              className="flex items-center justify-center rounded-lg transition-colors"
              style={{ width: '28px', height: '28px', color: '#475569', flexShrink: 0 }}
              onMouseEnter={(e) => { e.currentTarget.style.color = '#f43f5e'; e.currentTarget.style.background = 'rgba(244,63,94,0.1)' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = '#475569'; e.currentTarget.style.background = 'transparent' }}
            >
              <LogOut size={15} strokeWidth={2} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Page Shell ── */}
      <div className="flex flex-col min-h-screen">

        {/* Sticky Topbar */}
        <header
          className="sticky top-0 z-30 flex items-center shrink-0"
          style={{
            height: '70px',
            padding: '0 20px',
            background: 'rgba(11,18,33,0.85)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            gap: '14px',
          }}
        >
          {/* Hamburger */}
          <button
            onClick={() => setOpen(true)}
            className="flex items-center justify-center rounded-xl transition-all"
            style={{ width: '40px', height: '40px', color: '#64748b', flexShrink: 0 }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'white' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#64748b' }}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>

          {/* Brand */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div
              className="flex items-center justify-center"
              style={{
                width: '28px', height: '28px', borderRadius: '8px',
                background: 'linear-gradient(135deg, #818cf8, #6366f1)',
              }}
            >
              <span className="text-white font-bold text-xs leading-none">N</span>
            </div>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'white' }} className="hidden sm:block">
              Numatix
            </span>
          </div>

          {/* Divider + page title */}
          <div
            className="hidden sm:block"
            style={{ width: '1px', height: '18px', background: 'rgba(255,255,255,0.08)', flexShrink: 0 }}
          />
          <span
            className="hidden sm:block"
            style={{ fontSize: '13px', color: '#64748b', fontWeight: 500 }}
          >
            {currentTitle}
          </span>

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Right: Avatar */}
          <button
            onClick={() => setOpen(true)}
            className="flex items-center gap-2 rounded-xl transition-all"
            style={{ padding: '6px 10px', border: '1px solid transparent' }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent' }}
          >
            <div
              className="flex items-center justify-center shrink-0"
              style={{
                width: '28px', height: '28px', borderRadius: '50%',
                background: 'rgba(129,140,248,0.15)',
                border: '1px solid rgba(129,140,248,0.3)',
              }}
            >
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#818cf8' }}>
                {user?.email?.[0]?.toUpperCase() || 'G'}
              </span>
            </div>
            <span
              className="hidden md:block truncate"
              style={{ fontSize: '13px', color: '#94a3b8', maxWidth: '130px', fontWeight: 500 }}
            >
              {user?.email || 'Guest'}
            </span>
          </button>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}