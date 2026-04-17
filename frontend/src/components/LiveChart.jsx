import { useEffect, useImperativeHandle, useRef, forwardRef } from 'react'
import { createChart, CrosshairMode, LineStyle, ColorType } from 'lightweight-charts'

/**
 * LiveChart — a dark-themed candlestick chart powered by TradingView's
 * lightweight-charts library.
 *
 * Props
 * ─────
 *   initialData  array of { time, open, high, low, close } objects
 *                where `time` is a Unix timestamp in SECONDS (integer).
 *
 * Ref API (via forwardRef + useImperativeHandle)
 * ─────────────────────────────────────────────
 *   chartRef.current.updateCandle(ohlc)
 *     ohlc: { time, open, high, low, close }
 *     Updates or appends the candle in real-time.
 */
const LiveChart = forwardRef(function LiveChart({ initialData = [], symbol = 'BTCUSDT' }, ref) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)

  // Expose updateCandle() to parent via ref
  useImperativeHandle(ref, () => ({
    updateCandle(ohlc) {
      if (seriesRef.current && ohlc?.time) {
        seriesRef.current.update(ohlc)
      }
    },
  }))

  // Mount chart once
  useEffect(() => {
    if (!containerRef.current) return
    let chartInstance = null

    try {
      const width = containerRef.current.clientWidth || 300
      const height = 340

      const chart = createChart(containerRef.current, {
        width,
        height,
        layout: {
          background: { type: ColorType.Solid, color: '#0f172a' },
          textColor: '#94a3b8',
          fontSize: 12,
          fontFamily: "'Inter', 'Roboto', sans-serif",
        },
        grid: {
          vertLines: { color: 'rgba(255,255,255,0.04)', style: LineStyle.Dotted },
          horzLines: { color: 'rgba(255,255,255,0.04)', style: LineStyle.Dotted },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
          vertLine: { color: '#475569', labelBackgroundColor: '#1e293b' },
          horzLine: { color: '#475569', labelBackgroundColor: '#1e293b' },
        },
        rightPriceScale: {
          borderColor: 'rgba(255,255,255,0.08)',
          textColor: '#64748b',
        },
        timeScale: {
          borderColor: 'rgba(255,255,255,0.08)',
          timeVisible: true,
          secondsVisible: false,
          tickMarkFormatter: (time) => {
            try {
              const d = new Date(time * 1000)
              return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
            } catch (e) {
              return ''
            }
          },
        },
        handleScroll: { mouseWheel: true, pressedMouseMove: true },
        handleScale: { mouseWheel: true, pinch: true },
      })

      chartRef.current = chart
      chartInstance = chart

      const series = chart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#f43f5e',
        borderUpColor: '#10b981',
        borderDownColor: '#f43f5e',
        wickUpColor: '#10b981',
        wickDownColor: '#f43f5e',
      })
      seriesRef.current = series

      if (initialData && initialData.length > 0) {
        series.setData(initialData)
        chart.timeScale().fitContent()
      }
    } catch (err) {
      console.error('[LiveChart] Chart initialization failed:', err)
    }

    // Responsive resize
    const ro = new ResizeObserver(() => {
      try {
        if (containerRef.current && chartRef.current) {
          chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
        }
      } catch (e) { /* ignore resize errors */ }
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      if (chartInstance) {
        try {
          chartInstance.remove()
        } catch (e) { /* ignore */ }
      }
      chartRef.current = null
      seriesRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Update data when initialData prop changes (e.g., symbol switch)
  useEffect(() => {
    try {
      if (seriesRef.current && initialData) {
        seriesRef.current.setData(initialData)
        chartRef.current?.timeScale().fitContent()
      }
    } catch (err) {
      console.error('[LiveChart] Data update failed:', err)
    }
  }, [initialData])

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      {/* Symbol badge */}
      <div style={{
        position: 'absolute', top: 10, left: 12, zIndex: 10,
        display: 'flex', alignItems: 'center', gap: '8px',
      }}>
        <span style={{
          fontSize: '12px', fontWeight: 700, color: '#a5b4fc',
          background: 'rgba(129,140,248,0.12)',
          border: '1px solid rgba(129,140,248,0.2)',
          borderRadius: '6px', padding: '2px 8px', letterSpacing: '0.05em',
        }}>
          {symbol}
        </span>
        <span style={{ fontSize: '10px', color: '#475569', letterSpacing: '0.08em' }}>
          1m · Candlestick
        </span>
      </div>
      <div ref={containerRef} style={{ width: '100%', borderRadius: '12px', overflow: 'hidden' }} />
    </div>
  )
})

export default LiveChart
