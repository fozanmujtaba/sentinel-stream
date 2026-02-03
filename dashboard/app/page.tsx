'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LineChart, Line, AreaChart, Area, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

// Types
interface Alert {
    transaction_id: string;
    card_id: string;
    amount: number;
    timestamp: string;
    location: string;
    merchant_category: string;
    fraud_score: number;
    fraud_reason: string;
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    detected_at: string;
    latency_ms: number;
}

interface Metrics {
    transactions_processed: number;
    alerts_generated: number;
    tps: number;
    avg_latency_ms: number;
    velocity_violations: number;
    timestamp: string;
}

interface KPIs {
    transactions_24h: number;
    transactions_1h: number;
    volume_24h: number;
    alerts_24h: number;
    critical_alerts_24h: number;
    velocity_violations_24h: number;
    open_cases: number;
    sla_breached: number;
    avg_latency_ms: number;
    fraud_rate_24h: number;
}

// Navigation Items
const navItems = [
    { href: '/', label: 'Dashboard', icon: '📊' },
    { href: '/alerts', label: 'Fraud Alerts', icon: '🚨', badge: true },
    { href: '/cases', label: 'Cases', icon: '📁' },
    { href: '/customers', label: 'Customers', icon: '👥' },
    { href: '/analytics', label: 'Analytics', icon: '📈' },
    { href: '/rules', label: 'Rules', icon: '⚙️' },
    { href: '/settings', label: 'Settings', icon: '🔧' },
];

// Sidebar Component
function Sidebar({ alertCount }: { alertCount: number }) {
    const pathname = usePathname();

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="logo">
                    <div className="logo-icon">🛡️</div>
                    <span className="logo-text">Sentinel Stream</span>
                </div>
            </div>

            <nav className="sidebar-nav">
                <div className="nav-section">
                    <div className="nav-section-title">Main Menu</div>
                    {navItems.slice(0, 5).map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`nav-link ${pathname === item.href ? 'active' : ''}`}
                        >
                            <span className="nav-link-icon">{item.icon}</span>
                            <span>{item.label}</span>
                            {item.badge && alertCount > 0 && (
                                <span className="nav-link-badge">{alertCount}</span>
                            )}
                        </Link>
                    ))}
                </div>

                <div className="nav-section">
                    <div className="nav-section-title">Configuration</div>
                    {navItems.slice(5).map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`nav-link ${pathname === item.href ? 'active' : ''}`}
                        >
                            <span className="nav-link-icon">{item.icon}</span>
                            <span>{item.label}</span>
                        </Link>
                    ))}
                </div>
            </nav>

            <div style={{ padding: 'var(--spacing-md)', borderTop: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Sentinel Stream v2.0
                </div>
            </div>
        </aside>
    );
}

// Topbar Component
function Topbar({ metrics, isConnected }: { metrics: Metrics | null; isConnected: boolean }) {
    return (
        <header className="topbar">
            <div className="topbar-left">
                <h1 className="page-title">Real-time Fraud Monitoring</h1>
            </div>
            <div className="topbar-right">
                <div className={`status-indicator ${isConnected ? '' : 'disconnected'}`} style={{
                    background: isConnected ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    borderColor: isConnected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)',
                    color: isConnected ? 'var(--color-success)' : 'var(--color-danger)'
                }}>
                    <span className="status-dot" style={{
                        background: isConnected ? 'var(--color-success)' : 'var(--color-danger)'
                    }}></span>
                    {isConnected ? 'Live' : 'Disconnected'}
                </div>
                {metrics && (
                    <>
                        <div style={{
                            padding: '8px 16px',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '8px',
                            fontSize: '13px'
                        }}>
                            <span style={{ color: 'var(--text-muted)' }}>TPS: </span>
                            <span style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>{metrics.tps}</span>
                        </div>
                        <div style={{
                            padding: '8px 16px',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '8px',
                            fontSize: '13px'
                        }}>
                            <span style={{ color: 'var(--text-muted)' }}>Latency: </span>
                            <span style={{ fontWeight: 600, color: 'var(--color-success)' }}>{metrics.avg_latency_ms.toFixed(1)}ms</span>
                        </div>
                    </>
                )}
            </div>
        </header>
    );
}

// KPI Card Component
function KPICard({ icon, value, label, trend, color }: {
    icon: string;
    value: string | number;
    label: string;
    trend?: { value: number; direction: 'up' | 'down' };
    color: 'blue' | 'green' | 'red' | 'yellow' | 'purple';
}) {
    return (
        <div className="kpi-card">
            <div className={`kpi-icon ${color}`}>
                <span style={{ fontSize: '24px' }}>{icon}</span>
            </div>
            <div className="kpi-content">
                <div className="kpi-value">{typeof value === 'number' ? value.toLocaleString() : value}</div>
                <div className="kpi-label">{label}</div>
                {trend && (
                    <div className={`kpi-trend ${trend.direction}`}>
                        {trend.direction === 'up' ? '↑' : '↓'} {trend.value}%
                    </div>
                )}
            </div>
        </div>
    );
}

// Alert Item Component
function AlertItem({ alert }: { alert: Alert }) {
    const riskColors = {
        CRITICAL: 'var(--risk-critical)',
        HIGH: 'var(--risk-high)',
        MEDIUM: 'var(--risk-medium)',
        LOW: 'var(--risk-low)'
    };

    return (
        <div className={`alert-item ${alert.risk_level.toLowerCase()}`}>
            <div className="alert-icon" style={{ background: `${riskColors[alert.risk_level]}20`, color: riskColors[alert.risk_level] }}>
                {alert.risk_level === 'CRITICAL' ? '🔴' : alert.risk_level === 'HIGH' ? '🟠' : alert.risk_level === 'MEDIUM' ? '🟡' : '🟢'}
            </div>
            <div className="alert-content">
                <div className="alert-title">
                    ${alert.amount.toFixed(2)} - {alert.merchant_category}
                </div>
                <div className="alert-details">
                    {alert.fraud_reason}
                </div>
                <div className="alert-time">
                    Card: {alert.card_id.slice(-8)} • {alert.location} • {new Date(alert.detected_at).toLocaleTimeString()}
                </div>
            </div>
            <span className={`risk-badge ${alert.risk_level.toLowerCase()}`}>{alert.risk_level}</span>
        </div>
    );
}

// Main Dashboard Page
export default function Dashboard() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [kpis, setKpis] = useState<KPIs | null>(null);
    const [hourlyTrends, setHourlyTrends] = useState<any[]>([]);
    const [alertsByRisk, setAlertsByRisk] = useState<any[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [tpsHistory, setTpsHistory] = useState<{ time: string; tps: number }[]>([]);

    // Fetch KPIs
    const fetchKPIs = useCallback(async () => {
        try {
            const res = await fetch('http://localhost:8002/kpis');
            if (res.ok) {
                const data = await res.json();
                setKpis(data);
            }
        } catch (error) {
            console.error('Failed to fetch KPIs:', error);
        }
    }, []);

    // Fetch trends
    const fetchTrends = useCallback(async () => {
        try {
            const [hourlyRes, riskRes] = await Promise.all([
                fetch('http://localhost:8002/trends/hourly?hours=12'),
                fetch('http://localhost:8002/alerts/by-risk?hours=24')
            ]);

            if (hourlyRes.ok) {
                const hourlyData = await hourlyRes.json();
                setHourlyTrends(hourlyData);
            }

            if (riskRes.ok) {
                const riskData = await riskRes.json();
                setAlertsByRisk(riskData);
            }
        } catch (error) {
            console.error('Failed to fetch trends:', error);
        }
    }, []);

    // WebSocket connections
    useEffect(() => {
        // Fetch initial data
        fetchKPIs();
        fetchTrends();

        // Refresh KPIs periodically
        const kpiInterval = setInterval(fetchKPIs, 30000);
        const trendInterval = setInterval(fetchTrends, 60000);

        // Alert WebSocket
        const alertWs = new WebSocket('ws://localhost:8000/ws/alerts');

        alertWs.onopen = () => {
            setIsConnected(true);
            console.log('Alert WebSocket connected');
        };

        alertWs.onmessage = (event) => {
            const alert = JSON.parse(event.data);
            setAlerts(prev => [alert, ...prev.slice(0, 49)]);
        };

        alertWs.onclose = () => {
            setIsConnected(false);
            console.log('Alert WebSocket disconnected');
        };

        alertWs.onerror = () => {
            setIsConnected(false);
        };

        // Metrics WebSocket
        const metricsWs = new WebSocket('ws://localhost:8000/ws/metrics');

        metricsWs.onmessage = (event) => {
            const metricsData = JSON.parse(event.data);
            setMetrics(metricsData);
            setTpsHistory(prev => {
                const newEntry = { time: new Date().toLocaleTimeString(), tps: metricsData.tps };
                return [...prev.slice(-59), newEntry];
            });
        };

        return () => {
            alertWs.close();
            metricsWs.close();
            clearInterval(kpiInterval);
            clearInterval(trendInterval);
        };
    }, [fetchKPIs, fetchTrends]);

    const RISK_COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e'];

    return (
        <div className="app-layout">
            <Sidebar alertCount={alerts.filter(a => a.risk_level === 'CRITICAL').length} />

            <main className="main-content">
                <Topbar metrics={metrics} isConnected={isConnected} />

                <div className="content-area">
                    {/* KPI Cards */}
                    <div className="kpi-grid">
                        <KPICard
                            icon="📊"
                            value={kpis?.transactions_24h || metrics?.transactions_processed || 0}
                            label="Transactions (24h)"
                            color="blue"
                        />
                        <KPICard
                            icon="🚨"
                            value={kpis?.alerts_24h || metrics?.alerts_generated || 0}
                            label="Fraud Alerts"
                            color="red"
                        />
                        <KPICard
                            icon="⚡"
                            value={kpis?.velocity_violations_24h || metrics?.velocity_violations || 0}
                            label="Velocity Violations"
                            color="yellow"
                        />
                        <KPICard
                            icon="📁"
                            value={kpis?.open_cases || 0}
                            label="Open Cases"
                            color="purple"
                        />
                        <KPICard
                            icon="💰"
                            value={`$${((kpis?.volume_24h || 0) / 1000).toFixed(1)}K`}
                            label="Volume (24h)"
                            color="green"
                        />
                        <KPICard
                            icon="⏱️"
                            value={`${(kpis?.avg_latency_ms || metrics?.avg_latency_ms || 0).toFixed(1)}ms`}
                            label="Avg Latency"
                            color="blue"
                        />
                        <KPICard
                            icon="📈"
                            value={`${(kpis?.fraud_rate_24h || 0).toFixed(2)}%`}
                            label="Fraud Rate"
                            color="red"
                        />
                        <KPICard
                            icon="⚠️"
                            value={kpis?.sla_breached || 0}
                            label="SLA Breached"
                            color="yellow"
                        />
                    </div>

                    {/* Charts Row */}
                    <div className="grid-2" style={{ marginBottom: 'var(--spacing-xl)' }}>
                        {/* Throughput Chart */}
                        <div className="card">
                            <div className="card-header">
                                <div>
                                    <div className="card-title">Real-time Throughput</div>
                                    <div className="card-subtitle">Transactions per second</div>
                                </div>
                            </div>
                            <div className="chart-container">
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={tpsHistory}>
                                        <defs>
                                            <linearGradient id="colorTps" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                        <XAxis dataKey="time" stroke="#6b7280" tick={{ fontSize: 10 }} />
                                        <YAxis stroke="#6b7280" tick={{ fontSize: 10 }} />
                                        <Tooltip
                                            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                            labelStyle={{ color: '#9ca3af' }}
                                        />
                                        <Area type="monotone" dataKey="tps" stroke="#6366f1" fillOpacity={1} fill="url(#colorTps)" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* Alerts by Risk */}
                        <div className="card">
                            <div className="card-header">
                                <div>
                                    <div className="card-title">Alerts by Risk Level</div>
                                    <div className="card-subtitle">Last 24 hours distribution</div>
                                </div>
                            </div>
                            <div className="chart-container">
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={alertsByRisk}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={60}
                                            outerRadius={100}
                                            paddingAngle={5}
                                            dataKey="count"
                                            nameKey="risk_level"
                                            label={({ risk_level, count }) => `${risk_level}: ${count}`}
                                        >
                                            {alertsByRisk.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={RISK_COLORS[index % RISK_COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>

                    {/* Hourly Trends */}
                    <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
                        <div className="card-header">
                            <div>
                                <div className="card-title">Transaction & Alert Trends</div>
                                <div className="card-subtitle">Last 12 hours</div>
                            </div>
                        </div>
                        <div className="chart-container">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={hourlyTrends}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis
                                        dataKey="timestamp"
                                        stroke="#6b7280"
                                        tick={{ fontSize: 10 }}
                                        tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    />
                                    <YAxis stroke="#6b7280" tick={{ fontSize: 10 }} />
                                    <Tooltip
                                        contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        labelFormatter={(value) => new Date(value).toLocaleString()}
                                    />
                                    <Line type="monotone" dataKey="transactions" stroke="#6366f1" strokeWidth={2} dot={false} name="Transactions" />
                                    <Line type="monotone" dataKey="alerts" stroke="#ef4444" strokeWidth={2} dot={false} name="Alerts" />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Live Alerts Feed */}
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <div className="card-title">Live Fraud Alerts</div>
                                <div className="card-subtitle">Real-time feed • {alerts.length} alerts</div>
                            </div>
                            <Link href="/alerts" className="btn btn-secondary">
                                View All
                            </Link>
                        </div>
                        <div className="alerts-feed">
                            {alerts.length === 0 ? (
                                <div className="empty-state">
                                    <div className="empty-state-icon">🔍</div>
                                    <div className="empty-state-text">
                                        Waiting for alerts... The system is monitoring transactions in real-time.
                                    </div>
                                </div>
                            ) : (
                                alerts.slice(0, 10).map((alert, index) => (
                                    <AlertItem key={`${alert.transaction_id}-${index}`} alert={alert} />
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
