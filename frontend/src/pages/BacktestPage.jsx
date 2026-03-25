import { useState } from 'react'
import BacktestList from '../components/BacktestList'
import BacktestForm from '../components/BacktestForm'
import { Plus, Search, SlidersHorizontal } from 'lucide-react'

export default function BacktestPage() {
  const [showForm, setShowForm]       = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 28px' }}>

      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', marginBottom: '28px' }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: 700, color: 'white', letterSpacing: '-0.02em', lineHeight: 1 }}>
            Backtest Results
          </h1>
          <p style={{ fontSize: '13px', color: '#64748b', marginTop: '6px' }}>
            Manage and analyze your strategy simulations.
          </p>
        </div>

        <button
          onClick={() => setShowForm(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 20px', borderRadius: '12px',
            background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)',
            border: 'none', color: 'white',
            fontSize: '13px', fontWeight: 600, cursor: 'pointer',
            boxShadow: '0 4px 18px rgba(99,102,241,0.4)',
            transition: 'opacity 0.2s', whiteSpace: 'nowrap',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.88' }}
          onMouseLeave={(e) => { e.currentTarget.style.opacity = '1' }}
        >
          <Plus size={16} strokeWidth={2.5} />
          New Simulation
        </button>
      </div>

      {/* Search + Filter bar */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        {/* Search */}
        <div style={{ position: 'relative', flex: 1, minWidth: '240px', maxWidth: '420px' }}>
          <Search
            size={15}
            style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: '#475569', pointerEvents: 'none' }}
          />
          <input
            type="text"
            placeholder="Search by name, symbol, or strategy…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              paddingLeft: '40px', paddingRight: '16px',
              paddingTop: '11px', paddingBottom: '11px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
              borderRadius: '12px',
              fontSize: '13px', color: 'white',
              outline: 'none', transition: 'all 0.2s',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = 'rgba(129,140,248,0.4)'
              e.target.style.background = 'rgba(129,140,248,0.04)'
              e.target.style.boxShadow = '0 0 0 3px rgba(129,140,248,0.07)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'rgba(255,255,255,0.07)'
              e.target.style.background = 'rgba(255,255,255,0.03)'
              e.target.style.boxShadow = 'none'
            }}
          />
        </div>

        {/* Filter button */}
        <button
          style={{
            display: 'flex', alignItems: 'center', gap: '7px',
            padding: '11px 18px', borderRadius: '12px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.07)',
            color: '#94a3b8', fontSize: '13px', fontWeight: 500,
            cursor: 'pointer', transition: 'all 0.2s', whiteSpace: 'nowrap',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'white'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)' }}
        >
          <SlidersHorizontal size={15} strokeWidth={2} />
          Filters
        </button>
      </div>

      {/* Grid */}
      <BacktestList searchQuery={searchQuery} />

      {/* Modal */}
      {showForm && <BacktestForm onClose={() => setShowForm(false)} />}
    </div>
  )
}