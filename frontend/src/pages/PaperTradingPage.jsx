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
  Pause,
  Square
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
import { useCreateBot, useUpdateBotState } from '../api/bots';
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
  const [botName, setBotName] = useState('');
  const [parameters, setParameters] = useState({});
  const [activeTimeframe, setActiveTimeframe] = useState('1D');
  const chartRef = useRef(null);
  const [chartData, setChartData] = useState([]);

  const { data: activeBots = [], isLoading: loadingBots } = usePaperBots();
  const { data: ledgerTrades = [], isLoading: loadingLedger } = usePaperLedger();
  const { data: portfolioData = [], isLoading: loadingPortfolio, isError: portfolioError } = usePaperPortfolio(activeTimeframe);
  
  const { data: strategiesData = [] } = useStrategies();
  const { mutate: createBot, isPending: isDeploying } = useCreateBot();
  const { mutate: updateState } = useUpdateBotState();
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
      name: botName.trim() || `Paper Bot - ${assetMode} - ${selectedStrategy?.name}`
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

  const handleToggleState = (bot) => {
    const targetState = bot.status === 'RUNNING' ? 'PAUSED' : 'RUNNING';
    const idempotencyKey = crypto.randomUUID();
    updateState(
      { botId: bot.id, targetState, idempotencyKey },
      {
        onSuccess: () => toast.success(`Bot ${targetState === 'RUNNING' ? 'started' : 'paused'}.`),
        onError: () => toast.error('Failed to update bot state.')
      }
    );
  };

  const handleStopBot = (bot) => {
    if (!window.confirm(`Are you sure you want to stop bot ${bot.id.slice(0, 8)}? It cannot be restarted.`)) return;
    const idempotencyKey = crypto.randomUUID();
    updateState(
      { botId: bot.id, targetState: 'STOPPED', idempotencyKey },
      {
        onSuccess: () => toast.success('Bot stopped permanently.'),
        onError: () => toast.error('Failed to stop bot.')
      }
    );
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 28px' }}>
      <div className="flex flex-col gap-[32px]">

        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-[24px]">
          <div className="flex flex-col gap-[12px]">
            <div className="flex flex-wrap items-center gap-[16px]">
              <h1 className="text-[32px] font-bold text-white tracking-tight leading-none">
                Paper Trading Lab
              </h1>
              <div className="flex items-center gap-[6px] px-[10px] py-[4px] rounded-md border border-amber-500/30 bg-amber-500/10 mb-[2px]">
                <AlertTriangle className="w-[14px] h-[14px] text-amber-500" />
                <span className="text-[11px] font-bold text-amber-500 tracking-widest uppercase mt-[1px]">
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
                className="flex items-center justify-center gap-[6px] px-[12px] py-[8px] rounded-lg border border-rose-500/20 bg-rose-500/10 hover:bg-rose-500/20 transition-all font-medium text-[13px] text-rose-400 whitespace-nowrap"
              >
                <Key className="w-[14px] h-[14px] text-rose-400" />
                {isRevokingKeys ? 'Disconnecting...' : 'Disconnect Keys'}
              </button>
            ) : (
               <a 
                href="/settings"
                className="flex items-center justify-center gap-[6px] px-[12px] py-[8px] rounded-lg border border-blue-500/20 bg-blue-500/10 hover:bg-blue-500/20 transition-all font-medium text-[13px] text-blue-400 whitespace-nowrap"
              >
                <Key className="w-[14px] h-[14px] text-blue-400" />
                Configure Keys in Settings
              </a>
            )}

            <button className="flex items-center justify-center gap-[6px] px-[12px] py-[8px] rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-all font-medium text-[13px] text-slate-300 whitespace-nowrap">
              <RotateCcw className="w-[14px] h-[14px] text-slate-400" />
              Reset Virtual Balance
            </button>
          </div>
        </div>

        {/* KPI METRICS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[24px]">
          
          <div className="flex flex-col gap-[24px] justify-between" style={{ background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
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

          <div className="flex flex-col gap-[24px] justify-between" style={{ background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
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

          <div className="flex flex-col gap-[24px] justify-between" style={{ background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
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

          <div className="flex flex-col gap-[24px] justify-between" style={{ background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
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

        <div className="w-full" style={{ background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
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
            <div className="flex flex-col gap-[32px]" style={{ background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
              <h3 className="text-[18px] font-bold text-white flex items-center gap-[8px] leading-none">
                 <Play className="w-[20px] h-[20px] text-blue-400" />
                 Deploy Virtual Bot
              </h3>

              <form className="grid grid-cols-1 sm:grid-cols-2 gap-[24px]" onSubmit={handleDeploy}>
                <div className="flex flex-col gap-[8px] sm:col-span-2">
                  <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest leading-none ml-1" style={{ marginLeft: '4px' }}>
                    Bot Name
                  </label>
                  <input
                    type="text"
                    value={botName}
                    onChange={(e) => setBotName(e.target.value)}
                    placeholder="e.g. My Paper Bot"
                    className="w-full h-14 bg-[#0a0f1c] border border-white/5 rounded-xl px-4 text-white text-[14px] focus:outline-none focus:border-blue-500"
                    style={{ paddingLeft: '16px', paddingRight: '16px', height: '52px' }}
                  />
                </div>

                <div className="flex flex-col gap-[8px] sm:col-span-2">
                  <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest leading-none ml-1" style={{ marginLeft: '4px' }}>
                    Asset Pair
                  </label>
                  <select
                    value={assetMode}
                    onChange={(e) => setAssetMode(e.target.value)}
                    className="w-full h-14 bg-[#0a0f1c] border border-white/5 rounded-xl px-4 text-white text-[14px] focus:outline-none focus:border-blue-500 appearance-none cursor-pointer"
                    style={{ paddingLeft: '16px', paddingRight: '16px', height: '52px' }}
                  >
                    <option value="BTCUSDT">BTC/USDT</option>
                    <option value="ETHUSDT">ETH/USDT</option>
                    <option value="SOLUSDT">SOL/USDT</option>
                  </select>
                </div>

                <div className="flex flex-col gap-[8px]">
                  <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest leading-none ml-1" style={{ marginLeft: '4px' }}>
                    Select Strategy
                  </label>
                  <select
                    value={strategyId}
                    onChange={(e) => setStrategyId(e.target.value)}
                    className="w-full h-14 bg-[#0a0f1c] border border-white/5 rounded-xl px-4 text-white text-[14px] focus:outline-none focus:border-blue-500 appearance-none cursor-pointer"
                    style={{
                        paddingLeft: '16px',
                        paddingRight: '16px',
                        height: '52px',
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

                <div className="flex flex-col gap-[8px]">
                  <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest leading-none ml-1" style={{ marginLeft: '4px' }}>
                    Virtual Allocation ($)
                  </label>
                  <div className="relative h-14" style={{ height: '52px' }}>
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none" style={{ paddingLeft: '16px' }}>
                      <span className="text-slate-500 text-[14px] font-bold">$</span>
                    </div>
                    <input
                      type="number"
                      value={allocation}
                      onChange={(e) => setAllocation(e.target.value)}
                      className="w-full h-full bg-[#0a0f1c] border border-white/5 rounded-xl pl-10 pr-4 text-white text-[14px] focus:outline-none focus:border-blue-500"
                      style={{ paddingLeft: '36px', paddingRight: '16px' }}
                    />
                  </div>
                </div>

                {/* Dynamic Parameters */}
                {Object.keys(parameters).length > 0 && (
                  <div className="sm:col-span-2 pt-6 border-t border-white/5 mt-2" style={{ paddingTop: '24px', marginTop: '8px' }}>
                    <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest leading-none mb-4 block ml-1" style={{ marginBottom: '16px', marginLeft: '4px' }}>
                      Strategy Parameters
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" style={{ gap: '16px' }}>
                      {Object.entries(parameters).map(([key, val]) => {
                        const schema = strategiesData.find(s => s.id === strategyId)?.parameter_schema?.properties?.[key];
                        const isEnum = schema?.enum;
                        
                        return (
                          <div key={key} className="flex flex-col gap-2" style={{ gap: '8px' }}>
                            <span className="text-[11px] text-slate-500 uppercase tracking-widest leading-none ml-1" style={{ marginLeft: '4px' }}>
                              {key.replace(/_/g, ' ')}
                            </span>
                            {isEnum ? (
                              <select
                                value={val}
                                onChange={(e) => handleParamChange(key, e.target.value, schema.type)}
                                className="w-full h-12 bg-[#0a0f1c] border border-white/5 rounded-xl px-4 text-white text-[14px] focus:outline-none focus:border-blue-500 appearance-none cursor-pointer"
                                style={{
                                    paddingLeft: '16px',
                                    paddingRight: '16px',
                                    height: '48px',
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
                                className="w-full h-12 bg-[#0a0f1c] border border-white/5 rounded-xl px-4 text-white text-[14px] focus:outline-none focus:border-blue-500"
                                style={{ paddingLeft: '16px', paddingRight: '16px', height: '48px' }}
                                required
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              <button type="submit" onClick={handleDeploy} disabled={isDeploying} className="w-full h-14 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-[14px] transition-colors flex items-center justify-center gap-2 mt-2" style={{ height: '56px', marginTop: '8px', gap: '8px' }}>
                <Play className="w-[16px] h-[16px] fill-current" />
                {isDeploying ? 'Deploying...' : 'Launch Paper Bot'}
              </button>
            </form>
            </div>
          </div>

          {/* RIGHT AREA: Active Simulations */}
          <div className="flex flex-col gap-[24px]" style={{ background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '24px', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
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
                <div key={bot.id} style={{
                  background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', 
                  borderRadius: '16px', overflow: 'hidden', opacity: bot.status === 'STOPPED' ? 0.5 : 1
                }}>
                  {/* Card Header */}
                  <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{ fontSize: '15px', fontWeight: 700, color: 'white', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={bot.name || bot.pair}>
                          {bot.name || bot.pair}
                        </span>
                        <span style={{
                          padding: '2px 6px', borderRadius: '4px', fontSize: '9px', fontWeight: 800, letterSpacing: '0.05em',
                          background: 'rgba(129,140,248,0.1)', color: '#818cf8', border: '1px solid rgba(129,140,248,0.2)', flexShrink: 0
                        }}>
                          TESTNET
                        </span>
                      </div>
                      <p style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        <span style={{ fontWeight: 700, color: '#94a3b8' }}>{bot.pair}</span> • {bot.strategy}
                      </p>
                    </div>
                  </div>

                  {/* Card Body */}
                  <div style={{ padding: '16px', display: 'flex', alignItems: 'center', justifyItems: 'flex-start', gap: '24px' }}>
                    <div>
                      <p style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Uptime</p>
                      <p style={{ fontSize: '13px', color: 'white', fontWeight: 500 }}>{bot.uptime}</p>
                    </div>
                    <div>
                      <p style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sim PNL</p>
                      <p style={{ fontSize: '14px', color: bot.pnl >= 0 ? '#10b981' : '#f43f5e', fontWeight: 700 }}>
                        {bot.pnl >= 0 ? '+' : ''}${Math.abs(bot.pnl).toLocaleString(undefined, {minimumFractionDigits: 2})}
                      </p>
                    </div>
                  </div>

                  {/* Card Footer Actions */}
                  <div style={{ padding: '12px 16px', background: 'rgba(0,0,0,0.2)', borderTop: '1px solid rgba(255,255,255,0.03)', display: 'flex', gap: '8px' }}>
                     <button
                      onClick={() => handleToggleState(bot)}
                      disabled={bot.status === 'STOPPED'}
                      style={{
                        flex: 1, display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center', gap: '6px',
                        padding: '8px', borderRadius: '8px', fontSize: '11px', fontWeight: 600,
                        background: bot.status === 'RUNNING' ? 'rgba(244,163,94,0.1)' : 'rgba(16,185,129,0.1)',
                        color: bot.status === 'RUNNING' ? '#f59e0b' : '#10b981',
                        border: `1px solid ${bot.status === 'RUNNING' ? 'rgba(244,163,94,0.2)' : 'rgba(16,185,129,0.2)'}`,
                        cursor: bot.status === 'STOPPED' ? 'not-allowed' : 'pointer', transition: 'all 0.2s'
                      }}
                    >
                      {bot.status === 'RUNNING' ? <Pause className="w-[12px] h-[12px] shrink-0" /> : <Play className="w-[12px] h-[12px] shrink-0" />}
                      {bot.status === 'RUNNING' ? 'Pause' : 'Start'}
                    </button>
                    <button
                      onClick={() => handleStopBot(bot)}
                      disabled={bot.status === 'STOPPED'}
                      style={{
                        display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center',
                        padding: '8px', borderRadius: '8px',
                        background: 'rgba(244,63,94,0.1)', color: '#f43f5e',
                        border: '1px solid rgba(244,63,94,0.2)',
                        cursor: bot.status === 'STOPPED' ? 'not-allowed' : 'pointer', transition: 'all 0.2s'
                      }}
                      title="Stop Bot"
                    >
                      <Square className="w-[12px] h-[12px] shrink-0" fill="currentColor" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RECENT SIMULATED TRADES */}
        <div className="flex flex-col overflow-hidden" style={{ background: 'linear-gradient(145deg, #131b2f 0%, #0f1729 100%)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', boxShadow: '0 4px 24px rgba(0,0,0,0.25)' }}>
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
                  <th className="pl-6 pr-4 py-4 text-[11px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/5" style={{ padding: '16px', paddingLeft: '24px' }}>Asset Pair</th>
                  <th className="px-4 py-4 text-[11px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/5" style={{ padding: '16px' }}>Bot Name</th>
                  <th className="px-4 py-4 text-[11px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/5 text-center" style={{ padding: '16px' }}>Side</th>
                  <th className="px-4 py-4 text-[11px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/5 text-right" style={{ padding: '16px' }}>Fill Price</th>
                  <th className="px-4 py-4 text-[11px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/5" style={{ padding: '16px' }}>Time</th>
                  <th className="pl-4 pr-6 py-4 text-[11px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/5 text-right" style={{ padding: '16px', paddingRight: '24px' }}>Virtual PnL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {ledgerTrades.map((trade, i) => (
                  <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                    <td className="pl-6 pr-4 py-4 text-[13px] font-bold text-white whitespace-nowrap" style={{ padding: '16px', paddingLeft: '24px' }}>
                      {trade.pair}
                    </td>
                    <td className="px-4 py-4 text-[13px] text-slate-300 font-medium max-w-[200px] truncate" title={trade.bot_name || "Manual Trade"} style={{ padding: '16px' }}>
                      {trade.bot_name || "Manual Trade"}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-center" style={{ padding: '16px' }}>
                      <span
                        className={`inline-flex items-center justify-center px-3 py-1 rounded-full text-[11px] font-bold uppercase border ${
                          trade.side === 'BUY'
                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                        }`}
                        style={{ padding: '3px 10px' }}
                      >
                        {trade.side}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-[13px] text-slate-300 whitespace-nowrap text-right font-medium" style={{ padding: '16px' }}>
                      ${trade.price?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 6})}
                    </td>
                    <td className="px-4 py-4 text-[13px] text-slate-500 whitespace-nowrap" style={{ padding: '16px' }}>
                      {new Date(trade.time).toLocaleString()}
                    </td>
                    <td
                      className={`pl-4 pr-6 py-4 text-[13px] font-bold text-right whitespace-nowrap ${
                        trade.isWin ? 'text-emerald-500' : 'text-rose-500'
                      }`}
                      style={{ padding: '16px', paddingRight: '24px' }}
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
