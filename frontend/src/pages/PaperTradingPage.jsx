import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios'; // <-- Add this
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
  Key,
  X,
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

import { usePaperBots, usePaperLedger, usePaperPortfolio, useSubmitPaperKeys, useRevokePaperKeys } from '../api/paper';
import { useStrategies } from '../api/strategies';
import { useCreateBot } from '../api/bots';
import { useAuthStore } from '../stores/authStore';
import { useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import PortfolioPerformanceCard from '../components/PortfolioPerformanceCard';
import LiveChart from '../components/LiveChart';

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
  const [assetMode, setAssetMode] = useState('BTCUSDT');
  const [strategyId, setStrategyId] = useState('');
  const [allocation, setAllocation] = useState('1000');
  const [parameters, setParameters] = useState({});
  const [activeTimeframe, setActiveTimeframe] = useState('1D');
  const chartRef = useRef(null);
  const [chartData, setChartData] = useState([]);

  const { data: activeBots = [], isLoading: loadingBots } = usePaperBots();
  const { data: ledgerTrades = [], isLoading: loadingLedger } = usePaperLedger();
  const { data: portfolioData = [], isLoading: loadingPortfolio, isError: portfolioError } = usePaperPortfolio(activeTimeframe);
  
  const { data: strategiesData = [] } = useStrategies();
  const { mutate: createBot, isPending: isDeploying } = useCreateBot();
  const { mutate: revokeKeys, isPending: isRevokingKeys } = useRevokePaperKeys();

  const session = useAuthStore((s) => s.session);
  const queryClient = useQueryClient();

  useEffect(() => {
    // Select first strategy initially if none selected
    if (strategiesData.length > 0 && !strategyId) {
      setStrategyId(strategiesData[0].id);
    }
  }, [strategiesData, strategyId]);

  useEffect(() => {
    if (strategiesData.length > 0 && strategyId) {
      const selected = strategiesData.find(s => s.id === strategyId);
      if (selected && selected.parameter_schema?.properties) {
        let p = {};
        Object.entries(selected.parameter_schema.properties).forEach(([k, v]) => {
          p[k] = v.default || 0;
        });
        setParameters(p);
      } else {
        setParameters({});
      }
    }
  }, [strategyId, strategiesData]);

  const handleParamChange = (key, value, type) => {
    const val = type === 'integer' || type === 'number' ? Number(value) : value;
    setParameters((prev) => ({ ...prev, [key]: val }));
  };

  const navigate = window.location.assign; // We will just use standard anchor/link or useNavigate. Wait, I should import useNavigate from react-router-dom!

  // We infer lack of keys if portfolio returns an error (404)
  const hasKeys = !portfolioError && portfolioData && !loadingPortfolio;

  // Real-time SSE integration for testnet metrics
  React.useEffect(() => {
    const token = session?.access_token;
    if (!token) return;

    const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    const eventSource = new EventSource(`${baseURL}/bots/events?token=${token}`);

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'SUCCESS') {
          // Immediately refresh the simulated charts and tables if an order was filled
          queryClient.invalidateQueries({ queryKey: ['paperLedger'] });
          queryClient.invalidateQueries({ queryKey: ['paperPortfolio'] });
          queryClient.invalidateQueries({ queryKey: ['paperBots'] });
        }
      } catch (err) {
        console.error('Failed to parse SSE data', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
    };

    return () => {
      eventSource.close();
    };
  }, [session, queryClient]);

  // Set default strategy when strategies load
  React.useEffect(() => {
    if (strategiesData.length > 0 && !strategyId) {
      setStrategyId(strategiesData[0].id);
    }
  }, [strategiesData, strategyId]);

  // Fetch live market data for the chart
  useEffect(() => {
    let ws = null;
    const symbolClean = assetMode.replace('/', '');
    const symbolLower = symbolClean.toLowerCase();

    // 1. Fetch historical data to populate the chart initially
    axios.get(`https://api.binance.com/api/v3/klines?symbol=${symbolClean}&interval=1m&limit=100`)
      .then(res => {
        const formattedData = res.data.map(d => ({
          time: d[0] / 1000,
          open: parseFloat(d[1]),
          high: parseFloat(d[2]),
          low: parseFloat(d[3]),
          close: parseFloat(d[4])
        }));
        setChartData(formattedData);

        // 2. Open Binance WebSocket for real-time tick updates
        ws = new WebSocket(`wss://stream.binance.com:9443/ws/${symbolLower}@kline_1m`);
        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          const kline = message.k;
          const candle = {
            time: kline.t / 1000,
            open: parseFloat(kline.o),
            high: parseFloat(kline.h),
            low: parseFloat(kline.l),
            close: parseFloat(kline.c)
          };
          
          // Push the live tick directly to the chart component
          if (chartRef.current) {
            chartRef.current.updateCandle(candle);
          }
        };
      })
      .catch(err => console.error("Failed to fetch klines", err));

    // Cleanup websocket if the user changes coins or leaves the page
    return () => {
      if (ws) ws.close();
    };
  }, [assetMode]);

  const currentBalance = portfolioData?.length > 0 ? portfolioData[portfolioData.length - 1].equity : 0.0;
  const rawPnl = portfolioData?.length > 0 && portfolioData[0].equity > 0 
    ? (currentBalance - portfolioData[0].equity) 
    : 0.0;
  const pnlPercent = portfolioData?.length > 0 && portfolioData[0].equity > 0
    ? ((rawPnl / portfolioData[0].equity) * 100).toFixed(2)
    : '0.00';
  const pnlPrefix = rawPnl >= 0 ? '+' : '';
  const pnlColorClass = rawPnl >= 0 ? 'text-emerald-500' : 'text-rose-500';
  const pnlIconClass = rawPnl >= 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400';

  const globalWins = ledgerTrades.filter(t => t.isWin).length;
  const globalWinRate = ledgerTrades.length > 0 
    ? ((globalWins / ledgerTrades.length) * 100).toFixed(1) 
    : 0;
  const globalLossRate = ledgerTrades.length > 0 
    ? (100 - parseFloat(globalWinRate)).toFixed(1) 
    : 0;

  const handleDeploy = (e) => {
    e.preventDefault();
    if (!strategyId) return toast.error('Please select a strategy');

    const selectedStrategy = strategiesData.find(s => s.id === strategyId);


    const payload = {
      symbol: assetMode,
      is_testnet: true,
      strategy_id: strategyId,
      parameters: parameters,
      take_profit: null,
      stop_loss: null,
      name: `Paper Bot - ${assetMode} - ${selectedStrategy?.name}`
    };

    const idempotencyKey = crypto.randomUUID();

    createBot({ payload, idempotencyKey }, {
      onSuccess: () => {
        toast.success(`Virtual bot for ${assetMode} deployed to Testnet!`);
      },
      onError: (err) => {
        toast.error(err.response?.data?.detail || 'Failed to deploy virtual bot');
      }
    });
  };



  const handleKeyRevoke = () => {
    if (window.confirm("Are you sure you want to disconnect your Binance Testnet keys?")) {
      revokeKeys(undefined, {
        onSuccess: () => {
          toast.success('Keys revoked successfully');
        }
      });
    }
  };

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

          <div className="flex flex-wrap items-center gap-[12px] shrink-0">
            {hasKeys ? (
              <button 
                onClick={handleKeyRevoke}
                disabled={isRevokingKeys}
                className="flex items-center justify-center gap-[8px] px-[16px] py-[10px] rounded-xl border border-rose-500/20 bg-rose-500/10 hover:bg-rose-500/20 transition-all font-medium text-[14px] text-rose-400"
              >
                <Key className="w-[16px] h-[16px] text-rose-400" />
                {isRevokingKeys ? 'Disconnecting...' : 'Disconnect Keys'}
              </button>
            ) : (
               <a 
                href="/settings"
                className="flex items-center justify-center gap-[8px] px-[16px] py-[10px] rounded-xl border border-blue-500/20 bg-blue-500/10 hover:bg-blue-500/20 transition-all font-medium text-[14px] text-blue-400"
              >
                <Key className="w-[16px] h-[16px] text-blue-400" />
                Configure Keys in Settings
              </a>
            )}

            <button className="flex items-center justify-center gap-[8px] px-[16px] py-[10px] rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-all font-medium text-[14px] text-slate-300">
              <RotateCcw className="w-[16px] h-[16px] text-slate-400" />
              Reset Virtual Balance
            </button>
          </div>
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
                ${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className={"text-[12px] leading-none " + (portfolioError ? "text-rose-500" : "text-slate-500")}>
                {portfolioError ? "Live API Error or No Keys" : "Synced via CCXT"}
              </div>
            </div>
          </div>

          <div className="p-[24px] rounded-2xl bg-[#131b2f] border border-white/5 flex flex-col gap-[24px] justify-between">
             <div className="flex items-center justify-between">
              <span className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                Simulated PnL (24h)
              </span>
              <div className={`w-[32px] h-[32px] rounded-full flex items-center justify-center ${pnlIconClass}`}>
                <TrendingUp className="w-[16px] h-[16px] currentColor" />
              </div>
            </div>
            <div className="flex items-baseline gap-[8px]">
              <div className={`text-[32px] font-bold tracking-tight leading-none ${pnlColorClass}`}>
                {pnlPrefix}${Math.abs(rawPnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className={`text-[14px] font-bold leading-none ${pnlColorClass} opacity-80`}>
                {pnlPrefix}{pnlPercent}%
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
                {activeBots.length}
              </div>
              <div className="text-[12px] text-slate-500 leading-none">
                Across {new Set(activeBots.map(b => b.pair)).size} different pairs
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
                  {globalWinRate}%
                </div>
                <div className="text-[12px] text-slate-400 font-bold leading-none">
                  {globalLossRate}%
                </div>
              </div>
              <div className="flex w-full h-[10px] rounded-full overflow-hidden bg-slate-800">
                <div className="h-full bg-emerald-500 transition-all duration-500" style={{ width: `${globalWinRate}%` }} />
                <div className="h-full bg-rose-500 transition-all duration-500" style={{ width: `${globalLossRate}%` }} />
              </div>
            </div>
          </div>

        </div>

        <div className="w-full bg-[#131b2f] border border-white/5 rounded-2xl p-[24px]">
          <h2 className="text-[16px] font-bold text-slate-300 tracking-wide mb-[16px]">
            Live Market View ({assetMode})
          </h2>
          <div className="h-[450px] w-full rounded-xl overflow-hidden">
             <LiveChart 
               ref={chartRef} 
               initialData={chartData} 
               symbol={assetMode.replace('/', '')} 
             /> 
          </div>
        </div>

        {/* MAIN SPLIT */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-[24px]">

          {/* LEFT AREA: Chart + Deploy Setup */}
          <div className="lg:col-span-2 flex flex-col gap-[24px]">
            
            {/* Chart Container */}
            <PortfolioPerformanceCard
              data={portfolioData}
              title="Simulated Strategy Performance"
              currentBalance={currentBalance}
              pnlPercent={pnlPercent}
              rawPnl={rawPnl}
              activeTimeframe={activeTimeframe}
              setActiveTimeframe={setActiveTimeframe}
              isError={portfolioError}
              mode="PAPER"
              compact={true}
            />

            {/* Deploy Bot Form */}
            <div className="bg-[#131b2f] border border-white/5 rounded-2xl p-[24px] flex flex-col gap-[32px]">
              <h3 className="text-[18px] font-bold text-white flex items-center gap-[8px] leading-none">
                 <Play className="w-[20px] h-[20px] text-blue-400" />
                 Deploy Virtual Bot
              </h3>

              <form className="grid grid-cols-1 sm:grid-cols-2 gap-[24px]" onSubmit={handleDeploy}>
                <div className="flex flex-col gap-[12px] sm:col-span-2">
                  <label className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                    Asset Pair
                  </label>
                  <select
                    value={assetMode}
                    onChange={(e) => setAssetMode(e.target.value)}
                    className="w-full h-[52px] bg-[#0a0f1c] border border-white/5 rounded-xl px-[16px] text-white text-[14px] focus:outline-none focus:border-blue-500 appearance-none cursor-pointer"
                  >
                    <option value="BTCUSDT">BTC/USDT</option>
                    <option value="ETHUSDT">ETH/USDT</option>
                    <option value="SOLUSDT">SOL/USDT</option>
                  </select>
                </div>

                <div className="flex flex-col gap-[12px]">
                  <label className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none">
                    Select Strategy
                  </label>
                  <select
                    value={strategyId}
                    onChange={(e) => setStrategyId(e.target.value)}
                    className="w-full h-[52px] bg-[#0a0f1c] border border-white/5 rounded-xl px-[16px] text-white text-[14px] focus:outline-none focus:border-blue-500 appearance-none cursor-pointer"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%23475569' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                        backgroundPosition: 'right 16px center',
                        backgroundRepeat: 'no-repeat',
                        backgroundSize: '24px 24px',
                      }}
                  >
                    {strategiesData.map(st => (
                      <option key={st.id} value={st.id}>{st.name}</option>
                    ))}
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

                {/* Dynamic Parameters */}
                {Object.keys(parameters).length > 0 && (
                  <div className="sm:col-span-2 pt-[24px] border-t border-white/5 mt-[8px]">
                    <label className="text-[12px] font-bold text-slate-500 uppercase tracking-widest leading-none mb-[16px] block">
                      Strategy Parameters
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[16px]">
                      {Object.entries(parameters).map(([key, val]) => {
                        const schema = strategiesData.find(s => s.id === strategyId)?.parameter_schema?.properties?.[key];
                        const isEnum = schema?.enum;
                        
                        return (
                          <div key={key} className="flex flex-col gap-[8px]">
                            <span className="text-[11px] text-slate-500 uppercase tracking-widest leading-none">
                              {key.replace(/_/g, ' ')}
                            </span>
                            {isEnum ? (
                              <select
                                value={val}
                                onChange={(e) => handleParamChange(key, e.target.value, schema.type)}
                                className="w-full h-[48px] bg-[#0a0f1c] border border-white/5 rounded-xl px-[16px] text-white text-[14px] focus:outline-none focus:border-blue-500 appearance-none cursor-pointer"
                                style={{
                                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%23475569' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                                    backgroundPosition: 'right 16px center',
                                    backgroundRepeat: 'no-repeat',
                                    backgroundSize: '24px 24px',
                                  }}
                              >
                                {schema.enum.map(opt => (
                                  <option key={opt} value={opt}>{opt}</option>
                                ))}
                              </select>
                            ) : (
                              <input
                                type="number"
                                value={val}
                                onChange={(e) => handleParamChange(key, e.target.value, schema?.type || 'number')}
                                className="w-full h-[48px] bg-[#0a0f1c] border border-white/5 rounded-xl px-[16px] text-white text-[14px] focus:outline-none focus:border-blue-500"
                                required
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              <button type="submit" onClick={handleDeploy} disabled={isDeploying} className="w-full h-[56px] rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-[14px] transition-colors flex items-center justify-center gap-[8px] mt-[8px]">
                <Play className="w-[16px] h-[16px] fill-current" />
                {isDeploying ? 'Deploying...' : 'Launch Paper Bot'}
              </button>
            </form>
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
                {activeBots.length}
              </span>
            </div>

            <div className="flex flex-col gap-[16px]">
              {activeBots.map((bot) => (
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
                      {bot.pnl >= 0 ? '+' : ''}${Math.abs(bot.pnl).toLocaleString(undefined, {minimumFractionDigits: 2})}
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
                {ledgerTrades.map((trade, i) => (
                  <tr key={i} className="hover:bg-white/[0.02] transition-colors">
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
                      ${trade.price?.toLocaleString()}
                    </td>
                    <td className="px-[24px] py-[16px] text-[14px] text-slate-500">
                      {new Date(trade.time).toLocaleString()}
                    </td>
                    <td
                      className={`px-[24px] py-[16px] text-[14px] font-bold text-right ${
                        trade.isWin ? 'text-emerald-500' : 'text-rose-500'
                      }`}
                    >
                      {trade.pnl >= 0 ? '+' : ''}${Math.abs(trade.pnl).toLocaleString(undefined, {minimumFractionDigits: 2})}
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
