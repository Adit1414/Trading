import { useEffect, useState } from 'react'
import { useBots, useUpdateBotState } from '../api/bots'
import { useStrategies } from '../api/strategies'
import { useAuthStore } from '../stores/authStore'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Bot, Play, Pause, Square, Activity, AlertTriangle, Plus } from 'lucide-react'

export default function BotDashboardPage() {
  const navigate = useNavigate()
  const { data: bots = [], isLoading: isLoadingBots, isError } = useBots()
  const { data: strategies = [], isLoading: isLoadingStrategies } = useStrategies()
  const { mutate: updateState } = useUpdateBotState()
  const session = useAuthStore((s) => s.session)

  // Real-time SSE integration
  useEffect(() => {
    const token = session?.access_token
    if (!token) return  // Don't open SSE if not authenticated

    const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    // EventSource cannot send custom headers — pass the JWT as a query param
    const eventSource = new EventSource(`${baseURL}/bots/events?token=${token}`)

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'ALERT' || payload.type === 'CIRCUIT_BREAKER') {
          toast.custom((t) => (
            <div style={{
              background: '#1e293b', border: '1px solid #f59e0b', borderRadius: '12px',
              padding: '16px', display: 'flex', gap: '12px', alignItems: 'flex-start',
              boxShadow: '0 4px 24px rgba(0,0,0,0.4)', color: 'white'
            }}>
              <AlertTriangle size={20} style={{ color: '#f59e0b', flexShrink: 0 }} />
              <div>
                <p style={{ fontSize: '14px', fontWeight: 700, marginBottom: '4px' }}>System Alert</p>
                <p style={{ fontSize: '13px', color: '#cbd5e1' }}>{payload.message}</p>
              </div>
            </div>
          ), { duration: 6000 })
        } else if (payload.type === 'SUCCESS') {
          toast.success(payload.message)
        } else if (payload.type === 'ERROR') {
          console.warn('[SSE] Server error event:', payload.message)
        }
      } catch (err) {
        console.error('Failed to parse SSE data', err)
      }
    }

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err)
      // Browser automatically retries the connection
    }

    return () => {
      eventSource.close()
    }
  }, [session])  // Re-open SSE whenever the session changes (login / token refresh)

  const handleToggleState = (bot) => {
    const targetState = bot.status === 'RUNNING' ? 'PAUSED' : 'RUNNING'
    const idempotencyKey = crypto.randomUUID()
    
    updateState(
      { botId: bot.id, targetState, idempotencyKey },
      {
        onSuccess: () => toast.success(`Bot ${targetState === 'RUNNING' ? 'started' : 'paused'}.`),
        onError: () => toast.error('Failed to update bot state.')
      }
    )
  }

  const handleStopBot = (bot) => {
    if (!window.confirm(`Are you sure you want to stop bot ${bot.id.slice(0, 8)}? It cannot be restarted.`)) return
    
    const idempotencyKey = crypto.randomUUID()
    updateState(
      { botId: bot.id, targetState: 'STOPPED', idempotencyKey },
      {
        onSuccess: () => toast.success('Bot stopped permanently.'),
        onError: () => toast.error('Failed to stop bot.')
      }
    )
  }

  if (isLoadingBots || isLoadingStrategies) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', flexDirection: 'column', gap: '12px' }}>
        <div style={{ width: '32px', height: '32px', border: '2px solid rgba(129,140,248,0.2)', borderTopColor: '#818cf8', borderRadius: '50%', animation: 'spin-cw 0.8s linear infinite' }} />
        <p style={{ fontSize: '13px', color: '#475569' }}>Loading active bots…</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div style={{ maxWidth: '1400px', margin: '40px auto', padding: '0 28px', textAlign: 'center' }}>
        <div style={{ background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', borderRadius: '16px', padding: '32px' }}>
          <p style={{ color: '#f43f5e', fontWeight: 600 }}>Failed to load bots.</p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 28px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#10b981' }}>
            <Bot size={24} strokeWidth={2} />
          </div>
          <div>
            <h1 style={{ fontSize: '26px', fontWeight: 700, color: 'white', letterSpacing: '-0.02em', lineHeight: 1.2 }}>
              Live Bots
            </h1>
            <p style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>
              Monitor and manage your active trading algorithms.
            </p>
          </div>
        </div>
        <button
          onClick={() => navigate('/bots/create')}
          style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '12px 24px', borderRadius: '12px',
            background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)',
            border: 'none', color: 'white', fontSize: '14px', fontWeight: 700,
            cursor: 'pointer', transition: 'all 0.2s',
            boxShadow: '0 4px 24px rgba(99,102,241,0.4)',
          }}
        >
          <Plus size={16} />
          Create Bot
        </button>
      </div>

      {bots.length === 0 ? (
        <div style={{ background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '80px', textAlign: 'center' }}>
          <Bot size={48} style={{ color: '#334155', margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'white', marginBottom: '8px' }}>No Active Bots</h3>
          <p style={{ fontSize: '14px', color: '#64748b', marginBottom: '24px' }}>Deploy your first live trading bot.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
          {bots.map(bot => {
            const isRunning = bot.status === 'RUNNING'
            const isPaused = bot.status === 'PAUSED'
            const isStopped = bot.status === 'STOPPED'
            
            const pnl = bot.pnl || 0
            const pnlColor = pnl > 0 ? '#10b981' : pnl < 0 ? '#f43f5e' : 'white'
            const pnlPrefix = pnl > 0 ? '+' : ''

            return (
              <div key={bot.id} style={{
                background: 'linear-gradient(145deg,#131b2f,#0f1729)', border: '1px solid rgba(255,255,255,0.06)', 
                borderRadius: '20px', overflow: 'hidden', boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
                opacity: isStopped ? 0.6 : 1, transition: 'opacity 0.2s',
                display: 'flex', flexDirection: 'column'
              }}>
                {/* Card Header */}
                <div style={{ padding: '20px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1, minWidth: 0, paddingRight: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span style={{ fontSize: '16px', fontWeight: 700, color: 'white', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }} title={bot.name || `${bot.symbol} Bot`}>
                        {bot.name || `${bot.symbol} Bot`}
                      </span>
                      <span style={{
                        flexShrink: 0,
                        padding: '3px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 800, letterSpacing: '0.05em',
                        background: bot.is_testnet ? 'rgba(129,140,248,0.1)' : 'rgba(244,63,94,0.1)',
                        color: bot.is_testnet ? '#818cf8' : '#f43f5e',
                        border: bot.is_testnet ? '1px solid rgba(129,140,248,0.2)' : '1px solid rgba(244,63,94,0.2)'
                      }}>
                        {bot.is_testnet ? 'TESTNET' : 'MAINNET'}
                      </span>
                    </div>
                    <p style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      <span style={{ fontWeight: 700, color: '#94a3b8' }}>{bot.symbol}</span> • ID: {bot.id.slice(0,8)}
                    </p>
                  </div>

                  <span style={{
                    flexShrink: 0,
                    display: 'flex', alignItems: 'center', gap: '4px',
                    padding: '4px 8px', borderRadius: '8px', fontSize: '11px', fontWeight: 700,
                    background: isRunning ? 'rgba(16,185,129,0.1)' : isPaused ? 'rgba(244,163,94,0.1)' : 'rgba(100,116,139,0.1)',
                    color: isRunning ? '#10b981' : isPaused ? '#f59e0b' : '#94a3b8',
                    border: `1px solid ${isRunning ? 'rgba(16,185,129,0.2)' : isPaused ? 'rgba(244,163,94,0.2)' : 'rgba(100,116,139,0.2)'}`
                  }}>
                    {isRunning ? <Activity size={12} /> : null}
                    {bot.status}
                  </span>
                </div>

                {/* Card Body */}
                <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                      <p style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, marginBottom: '4px' }}>STRATEGY</p>
                      <p style={{ fontSize: '13px', color: 'white', fontWeight: 500 }}>
                        {strategies.find(s => s.id === bot.strategy_id)?.name || bot.strategy_id.slice(0, 8)}
                      </p>
                    </div>
                    <div>
                      <p style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, marginBottom: '4px' }}>RUNNING PNL</p>
                      <p style={{ fontSize: '15px', color: pnlColor, fontWeight: 700 }}>
                        {pnlPrefix}{pnl.toFixed(2)} USDT
                      </p>
                    </div>
                  </div>
                  
                  {bot.parameters && Object.keys(bot.parameters).length > 0 && (
                    <div style={{ paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                      <p style={{ fontSize: '11px', color: '#64748b', fontWeight: 600, marginBottom: '8px' }}>PARAMETERS</p>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {Object.entries(bot.parameters).map(([k, v]) => (
                          <span key={k} style={{ 
                            fontSize: '11px', 
                            background: 'rgba(255,255,255,0.03)', 
                            border: '1px solid rgba(255,255,255,0.05)',
                            padding: '4px 8px', 
                            borderRadius: '6px', 
                            color: '#cbd5e1',
                            fontFamily: 'monospace'
                          }}>
                            <span style={{ color: '#94a3b8' }}>{k}:</span> {String(v)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Footer Actions */}
                <div style={{ padding: '16px 20px', background: 'rgba(0,0,0,0.15)', borderTop: '1px solid rgba(255,255,255,0.03)', display: 'flex', gap: '12px' }}>
                  <button
                    onClick={() => handleToggleState(bot)}
                    disabled={isStopped}
                    style={{
                      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                      padding: '10px', borderRadius: '10px', fontSize: '12px', fontWeight: 600,
                      background: isRunning ? 'rgba(244,163,94,0.1)' : 'rgba(16,185,129,0.1)',
                      color: isRunning ? '#f59e0b' : '#10b981',
                      border: `1px solid ${isRunning ? 'rgba(244,163,94,0.2)' : 'rgba(16,185,129,0.2)'}`,
                      cursor: isStopped ? 'not-allowed' : 'pointer',
                      opacity: isStopped ? 0.4 : 1, transition: 'all 0.2s'
                    }}
                  >
                    {isRunning ? <Pause size={14} /> : <Play size={14} />}
                    {isRunning ? 'Pause Bot' : 'Start Bot'}
                  </button>
                  
                  <button
                    onClick={() => handleStopBot(bot)}
                    disabled={isStopped}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      padding: '10px', borderRadius: '10px',
                      background: 'rgba(244,63,94,0.1)', color: '#f43f5e',
                      border: '1px solid rgba(244,63,94,0.2)',
                      cursor: isStopped ? 'not-allowed' : 'pointer',
                      opacity: isStopped ? 0.4 : 1, transition: 'all 0.2s'
                    }}
                    title="Stop & Delete Bot"
                  >
                    <Square size={14} fill="currentColor" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
