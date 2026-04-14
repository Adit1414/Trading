import React, { useState } from 'react';
import {
  AlertTriangle,
  RotateCcw,
  TrendingUp,
  Bot,
  Crosshair,
  Play,
  Activity,
  History,
  DollarSign,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const MOCK_ACTIVE_PAPER_BOTS = [
  { id: 1, pair: 'BTC/USDT', strategy: 'EMA CROSSOVER', pnl: '+$450.20', isWin: true, uptime: '14h 22m' },
  { id: 2, pair: 'ETH/USDT', strategy: 'RSI DIVERGENCE', pnl: '-$120.50', isWin: false, uptime: '4h 10m' },
  { id: 3, pair: 'SOL/USDT', strategy: 'MACD TREND', pnl: '+$89.00', isWin: true, uptime: '2d 4h' },
];

const MOCK_PAPER_LEDGER = [
  { id: 101, pair: 'BTC/USDT', side: 'BUY', price: '$64,230.00', time: '10 mins ago', pnl: '+$12.50', isWin: true },
  { id: 102, pair: 'ETH/USDT', side: 'SELL', price: '$3,450.00', time: '1 hour ago', pnl: '-$5.20', isWin: false },
  { id: 103, pair: 'SOL/USDT', side: 'BUY', price: '$145.20', time: '3 hours ago', pnl: '+$45.00', isWin: true },
  { id: 104, pair: 'AVAX/USDT', side: 'SELL', price: '$24.50', time: '5 hours ago', pnl: '+$8.40', isWin: true },
  { id: 105, pair: 'BTC/USDT', side: 'SELL', price: '$64,100.00', time: '12 hours ago', pnl: '-$15.20', isWin: false },
];

const CHART_DATA = [
  { time: '00:00', price: 64100 },
  { time: '04:00', price: 64800 },
  { time: '08:00', price: 64000 },
  { time: '12:00', price: 65400 },
  { time: '16:00', price: 65200 },
  { time: '20:00', price: 66200 },
  { time: '24:00', price: 66800 },
];

export default function PaperTradingPage() {
  const [allocation, setAllocation] = useState('1000');
  const [strategy, setStrategy] = useState('EMA Crossover');
  const [activeTimeframe, setActiveTimeframe] = useState('1D');

  return (
    <div className="min-h-screen bg-[#0f1729] text-white font-sans selection:bg-blue-500/30">
      <div className="max-w-[1400px] mx-auto px-[24px] py-[32px] md:px-[32px] md:py-[40px] flex flex-col gap-[32px]">

        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-[24px]">
          <div className="flex flex-col gap-[12px]">
            <div className="flex flex-wrap items-center gap-[16px]">
              <h1 className="text-[32px] font-bold text-white tracking-tight leading-none">
                Paper Trading Lab
              </h1>
              <div className="flex items-center gap-[8px] px-[12px] py-[6px] rounded-full border border-amber-500/30 bg-[#0f1729]">
                <AlertTriangle className="w-[16px] h-[16px] text-amber-500" />
                <span className="text-[12px] font-bold text-amber-500 tracking-wider uppercase leading-none">
                  Simulation Mode Active
                </span>
              </div>
            </div>
            <p className="text-slate-400 text-[14px]">
              Risk-free algorithmic strategy simulation. Test your edge without risking real capital.
            </p>
          </div>

          <button className="flex items-center justify-center gap-[8px] px-[16px] py-[10px] rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-all font-medium text-[14px] text-slate-300 shrink-0">
            <RotateCcw className="w-[16px] h-[16px] text-slate-400" />
            Reset Virtual Balance
          </button>
        </div>

        {/* KPI METRICS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[24px]">
          
          <div className="p-[24px] rounded-2xl bg-[#131b2f] border border-white/5 flex flex-col gap-[24px] justify-between">
            <div className="flex items-center justify-between">
              <span className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                Virtual Balance
              </span>
              <div className="w-[32px] h-[32px] rounded-full bg-blue-500/20 flex items-center justify-center">
                <DollarSign className="w-[16px] h-[16px] text-blue-400" />
              </div>
            </div>
            <div className="flex flex-col gap-[4px]">
              <div className="text-[32px] font-bold text-white tracking-tight leading-none">
                $100,000.00
              </div>
              <div className="text-[12px] text-slate-500 leading-none">
                Initial balance: $100,000.00
              </div>
            </div>
          </div>

          <div className="p-[24px] rounded-2xl bg-[#131b2f] border border-white/5 flex flex-col gap-[24px] justify-between">
             <div className="flex items-center justify-between">
              <span className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                Simulated PnL (24h)
              </span>
              <div className="w-[32px] h-[32px] rounded-full bg-emerald-500/20 flex items-center justify-center">
                <TrendingUp className="w-[16px] h-[16px] text-emerald-400" />
              </div>
            </div>
            <div className="flex items-baseline gap-[8px]">
              <div className="text-[32px] font-bold text-emerald-500 tracking-tight leading-none">
                +$1,450.20
              </div>
              <div className="text-[14px] text-emerald-500/80 font-bold leading-none">
                +1.45%
              </div>
            </div>
          </div>

          <div className="p-[24px] rounded-2xl bg-[#131b2f] border border-white/5 flex flex-col gap-[24px] justify-between">
            <div className="flex items-center justify-between">
              <span className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                Active Paper Bots
              </span>
              <div className="w-[32px] h-[32px] rounded-full bg-blue-500/20 flex items-center justify-center">
                <Bot className="w-[16px] h-[16px] text-blue-400" />
              </div>
            </div>
            <div className="flex flex-col gap-[4px]">
              <div className="text-[32px] font-bold text-white tracking-tight leading-none">
                3
              </div>
              <div className="text-[12px] text-slate-500 leading-none">
                Across 3 different pairs
              </div>
            </div>
          </div>

          <div className="p-[24px] rounded-2xl bg-[#131b2f] border border-white/5 flex flex-col gap-[24px] justify-between">
            <div className="flex items-center justify-between">
              <span className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                Global Win Rate
              </span>
              <div className="w-[32px] h-[32px] rounded-full bg-teal-500/20 flex items-center justify-center">
                <Crosshair className="w-[16px] h-[16px] text-teal-400" />
              </div>
            </div>
            <div className="flex flex-col gap-[12px]">
              <div className="flex items-end justify-between leading-none">
                <div className="text-[32px] font-bold text-white tracking-tight leading-none">
                  68.5%
                </div>
                <div className="text-[12px] text-slate-400 font-bold leading-none">
                  31.5%
                </div>
              </div>
              <div className="flex w-full h-[10px] rounded-full overflow-hidden bg-slate-800">
                <div className="h-full bg-emerald-500" style={{ width: '68.5%' }} />
                <div className="h-full bg-rose-500" style={{ width: '31.5%' }} />
              </div>
            </div>
          </div>

        </div>

        {/* MAIN SPLIT */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-[24px]">

          {/* LEFT AREA: Chart + Deploy Setup */}
          <div className="lg:col-span-2 flex flex-col gap-[24px]">
            
            {/* Chart Container */}
            <div className="bg-[#131b2f] border border-white/5 rounded-2xl p-[24px] flex flex-col gap-[24px]">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-[16px]">
                <h2 className="text-[18px] font-bold text-white flex items-center gap-[12px] leading-none">
                  <Activity className="w-[20px] h-[20px] text-blue-400" />
                  Simulated Strategy Performance
                </h2>
                <div className="flex items-center gap-[4px] bg-[#0a0f1c] p-[4px] rounded-lg border border-white/5 w-fit">
                  {['1H', '4H', '1D', '1W'].map((tf) => (
                    <button
                      key={tf}
                      onClick={() => setActiveTimeframe(tf)}
                      className={`px-[12px] py-[6px] rounded-md text-[12px] font-bold transition-all ${
                        activeTimeframe === tf
                          ? 'bg-blue-600 text-white'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>

              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={CHART_DATA} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis
                      dataKey="time"
                      stroke="#475569"
                      fontSize={11}
                      tickMargin={12}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      domain={['dataMin - 100', 'dataMax + 200']}
                      stroke="#475569"
                      fontSize={11}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                      axisLine={false}
                      tickLine={false}
                      tickMargin={10}
                      width={80}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f1729',
                        borderColor: '#1e293b',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                      itemStyle={{ color: '#3b82f6', fontWeight: 'bold' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="price"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorPrice)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Deploy Bot Form */}
            <div className="bg-[#131b2f] border border-white/5 rounded-2xl p-[24px] flex flex-col gap-[32px]">
              <h3 className="text-[18px] font-bold text-white flex items-center gap-[8px] leading-none">
                 <Play className="w-[20px] h-[20px] text-blue-400" />
                 Deploy Virtual Bot
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-[24px]">
                <div className="flex flex-col gap-[12px]">
                  <label className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                    Select Strategy
                  </label>
                  <select
                    value={strategy}
                    onChange={(e) => setStrategy(e.target.value)}
                    className="w-full h-[52px] bg-[#0a0f1c] border border-white/5 rounded-xl px-[16px] text-white text-[14px] focus:outline-none focus:border-blue-500 appearance-none cursor-pointer"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%23475569' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                        backgroundPosition: 'right 16px center',
                        backgroundRepeat: 'no-repeat',
                        backgroundSize: '24px 24px',
                      }}
                  >
                    <option>EMA Crossover</option>
                    <option>RSI Divergence</option>
                    <option>MACD Trend</option>
                    <option>Bollinger Bands Reversion</option>
                  </select>
                </div>

                <div className="flex flex-col gap-[12px]">
                  <label className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                    Virtual Allocation ($)
                  </label>
                  <div className="relative h-[52px]">
                    <div className="absolute inset-y-0 left-0 pl-[16px] flex items-center pointer-events-none">
                      <span className="text-slate-500 text-[14px] font-bold">$</span>
                    </div>
                    <input
                      type="number"
                      value={allocation}
                      onChange={(e) => setAllocation(e.target.value)}
                      className="w-full h-full bg-[#0a0f1c] border border-white/5 rounded-xl pl-[32px] pr-[16px] text-white text-[14px] focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
              </div>

              <button className="w-full h-[56px] rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-[14px] transition-colors flex items-center justify-center gap-[8px]">
                <Play className="w-[16px] h-[16px] fill-current" />
                Launch Paper Bot
              </button>
            </div>
          </div>

          {/* RIGHT AREA: Active Simulations */}
          <div className="bg-[#131b2f] border border-white/5 rounded-2xl p-[24px] flex flex-col gap-[24px]">
            <div className="flex items-center justify-between">
              <h3 className="text-[18px] font-bold text-white flex items-center gap-[8px] leading-none">
                <Bot className="w-[20px] h-[20px] text-cyan-400" />
                Active Simulations
              </h3>
              <span className="flex items-center justify-center px-[8px] py-[2px] rounded-md bg-blue-600 text-[12px] font-bold text-white leading-none tracking-wide">
                {MOCK_ACTIVE_PAPER_BOTS.length}
              </span>
            </div>

            <div className="flex flex-col gap-[16px]">
              {MOCK_ACTIVE_PAPER_BOTS.map((bot) => (
                <div
                  key={bot.id}
                  className="p-[16px] rounded-xl bg-white/[0.02] border border-white/5 flex flex-col gap-[16px]"
                >
                  <div className="flex items-start justify-between gap-[16px]">
                    <div className="flex flex-col gap-[4px]">
                      <div className="font-bold text-white text-[16px] leading-none">
                        {bot.pair}
                      </div>
                      <div className="text-[12px] text-slate-500 font-bold uppercase tracking-wider leading-none">
                        {bot.strategy}
                      </div>
                    </div>
                    <button className="w-[24px] h-[24px] rounded-md bg-[#1e293b] hover:bg-slate-700 flex items-center justify-center transition-colors shrink-0">
                      <div className="w-[10px] h-[10px] bg-slate-400 rounded-sm" />
                    </button>
                  </div>
                  
                  <div className="flex items-center justify-between border-t border-white/5 pt-[16px]">
                    <div className="flex items-center gap-[8px]">
                      <span className="text-[12px] text-slate-500 font-bold uppercase tracking-wider leading-none">Uptime</span>
                      <span className="text-[14px] text-white font-medium leading-none">{bot.uptime}</span>
                    </div>
                    <span className={`text-[14px] font-bold leading-none ${bot.isWin ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {bot.pnl}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RECENT SIMULATED TRADES */}
        <div className="bg-[#131b2f] border border-white/5 rounded-2xl flex flex-col overflow-hidden">
          <div className="flex items-center gap-[12px] px-[24px] py-[20px] border-b border-white/5">
            <div className="w-[32px] h-[32px] rounded-full bg-teal-500/20 flex items-center justify-center">
               <History className="w-[16px] h-[16px] text-teal-400" />
            </div>
            <h3 className="text-[18px] font-bold text-white leading-none">Recent Simulated Trades</h3>
          </div>

          <div className="overflow-x-auto w-full">
            <table className="w-full text-left whitespace-nowrap">
              <thead>
                <tr>
                  <th className="px-[24px] py-[16px] text-[12px] font-bold text-slate-500 uppercase tracking-wider border-b border-white/5">Asset Pair</th>
                  <th className="px-[24px] py-[16px] text-[12px] font-bold text-slate-500 uppercase tracking-wider border-b border-white/5">Side</th>
                  <th className="px-[24px] py-[16px] text-[12px] font-bold text-slate-500 uppercase tracking-wider border-b border-white/5">Fill Price</th>
                  <th className="px-[24px] py-[16px] text-[12px] font-bold text-slate-500 uppercase tracking-wider border-b border-white/5">Time</th>
                  <th className="px-[24px] py-[16px] text-[12px] font-bold text-slate-500 uppercase tracking-wider border-b border-white/5 text-right">Virtual PnL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {MOCK_PAPER_LEDGER.map((trade) => (
                  <tr key={trade.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-[24px] py-[16px] text-[14px] font-bold text-white">
                      {trade.pair}
                    </td>
                    <td className="px-[24px] py-[16px]">
                      <span
                        className={`inline-flex items-center justify-center px-[12px] py-[4px] rounded-full text-[12px] font-bold uppercase border ${
                          trade.side === 'BUY'
                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                        }`}
                      >
                        {trade.side}
                      </span>
                    </td>
                    <td className="px-[24px] py-[16px] text-[14px] text-slate-300">
                      {trade.price}
                    </td>
                    <td className="px-[24px] py-[16px] text-[14px] text-slate-500">
                      {trade.time}
                    </td>
                    <td
                      className={`px-[24px] py-[16px] text-[14px] font-bold text-right ${
                        trade.isWin ? 'text-emerald-500' : 'text-rose-500'
                      }`}
                    >
                      {trade.pnl}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
