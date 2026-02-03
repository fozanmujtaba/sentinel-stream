'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

const navItems = [
    { href: '/', label: 'Dashboard', icon: '📊' },
    { href: '/alerts', label: 'Fraud Alerts', icon: '🚨' },
    { href: '/cases', label: 'Cases', icon: '📁' },
    { href: '/customers', label: 'Customers', icon: '👥' },
    { href: '/analytics', label: 'Analytics', icon: '📈' },
    { href: '/rules', label: 'Rules', icon: '⚙️' },
    { href: '/settings', label: 'Settings', icon: '🔧' },
];

function Sidebar() {
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
                    {navItems.map((item) => (
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
        </aside>
    );
}

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e', '#14b8a6'];

export default function AnalyticsPage() {
    const [dailyTrends, setDailyTrends] = useState<any[]>([]);
    const [categoryData, setCategoryData] = useState<any[]>([]);
    const [reasonsData, setReasonsData] = useState<any[]>([]);
    const [latencyData, setLatencyData] = useState<any>(null);
    const [summary, setSummary] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAnalytics();
    }, []);

    const fetchAnalytics = async () => {
        try {
            const [dailyRes, categoryRes, reasonsRes, latencyRes, summaryRes] = await Promise.all([
                fetch('http://localhost:8002/trends/daily?days=14'),
                fetch('http://localhost:8002/alerts/by-category?hours=168'),
                fetch('http://localhost:8002/alerts/reasons?hours=168'),
                fetch('http://localhost:8002/performance/latency?hours=24'),
                fetch('http://localhost:8002/summary')
            ]);

            if (dailyRes.ok) setDailyTrends(await dailyRes.json());
            if (categoryRes.ok) setCategoryData(await categoryRes.json());
            if (reasonsRes.ok) setReasonsData(await reasonsRes.json());
            if (latencyRes.ok) setLatencyData(await latencyRes.json());
            if (summaryRes.ok) setSummary(await summaryRes.json());
        } catch (error) {
            console.error('Failed to fetch analytics:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="app-layout">
            <Sidebar />

            <main className="main-content">
                <header className="topbar">
                    <div className="topbar-left">
                        <h1 className="page-title">Analytics & Reports</h1>
                    </div>
                    <div className="topbar-right">
                        <button className="btn btn-secondary">
                            📥 Export Report
                        </button>
                    </div>
                </header>

                <div className="content-area">
                    {loading ? (
                        <div className="loading">
                            <div className="loading-spinner"></div>
                        </div>
                    ) : (
                        <>
                            {/* Summary Cards */}
                            {summary && (
                                <div className="kpi-grid" style={{ marginBottom: 'var(--spacing-xl)' }}>
                                    <div className="kpi-card">
                                        <div className="kpi-icon blue"><span style={{ fontSize: '24px' }}>📊</span></div>
                                        <div className="kpi-content">
                                            <div className="kpi-value">{summary.today_transactions?.toLocaleString() || 0}</div>
                                            <div className="kpi-label">Today's Transactions</div>
                                        </div>
                                    </div>
                                    <div className="kpi-card">
                                        <div className="kpi-icon green"><span style={{ fontSize: '24px' }}>💰</span></div>
                                        <div className="kpi-content">
                                            <div className="kpi-value">${((summary.today_volume || 0) / 1000).toFixed(1)}K</div>
                                            <div className="kpi-label">Today's Volume</div>
                                        </div>
                                    </div>
                                    <div className="kpi-card">
                                        <div className="kpi-icon red"><span style={{ fontSize: '24px' }}>🚨</span></div>
                                        <div className="kpi-content">
                                            <div className="kpi-value">{summary.today_alerts || 0}</div>
                                            <div className="kpi-label">Today's Alerts</div>
                                        </div>
                                    </div>
                                    <div className="kpi-card">
                                        <div className="kpi-icon yellow"><span style={{ fontSize: '24px' }}>💸</span></div>
                                        <div className="kpi-content">
                                            <div className="kpi-value">${((summary.today_fraud_amount || 0) / 1000).toFixed(1)}K</div>
                                            <div className="kpi-label">Fraud Amount</div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Daily Trends */}
                            <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
                                <div className="card-header">
                                    <div>
                                        <div className="card-title">14-Day Trend Analysis</div>
                                        <div className="card-subtitle">Transactions, alerts, and fraud amounts over time</div>
                                    </div>
                                </div>
                                <div className="chart-container" style={{ height: '350px' }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={dailyTrends}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                            <XAxis
                                                dataKey="date"
                                                stroke="#6b7280"
                                                tickFormatter={(value) => new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                                            />
                                            <YAxis yAxisId="left" stroke="#6b7280" />
                                            <YAxis yAxisId="right" orientation="right" stroke="#6b7280" />
                                            <Tooltip
                                                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                                labelFormatter={(value) => new Date(value).toLocaleDateString()}
                                            />
                                            <Legend />
                                            <Line yAxisId="left" type="monotone" dataKey="transactions" stroke="#6366f1" strokeWidth={2} name="Transactions" />
                                            <Line yAxisId="left" type="monotone" dataKey="alerts" stroke="#ef4444" strokeWidth={2} name="Alerts" />
                                            <Line yAxisId="right" type="monotone" dataKey="fraud_amount" stroke="#f59e0b" strokeWidth={2} name="Fraud Amount ($)" />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            <div className="grid-2" style={{ marginBottom: 'var(--spacing-xl)' }}>
                                {/* Fraud by Category */}
                                <div className="card">
                                    <div className="card-header">
                                        <div>
                                            <div className="card-title">Fraud by Merchant Category</div>
                                            <div className="card-subtitle">Last 7 days</div>
                                        </div>
                                    </div>
                                    <div className="chart-container">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart data={categoryData} layout="vertical">
                                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                                <XAxis type="number" stroke="#6b7280" />
                                                <YAxis dataKey="category" type="category" stroke="#6b7280" width={100} />
                                                <Tooltip
                                                    contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                                />
                                                <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>

                                {/* Top Fraud Reasons */}
                                <div className="card">
                                    <div className="card-header">
                                        <div>
                                            <div className="card-title">Top Detection Reasons</div>
                                            <div className="card-subtitle">Last 7 days</div>
                                        </div>
                                    </div>
                                    <div className="chart-container">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <PieChart>
                                                <Pie
                                                    data={reasonsData.slice(0, 6)}
                                                    cx="50%"
                                                    cy="50%"
                                                    outerRadius={100}
                                                    dataKey="count"
                                                    nameKey="fraud_reason"
                                                    label={({ fraud_reason, percent }) =>
                                                        `${(fraud_reason as string).slice(0, 15)}... (${(percent * 100).toFixed(0)}%)`
                                                    }
                                                >
                                                    {reasonsData.map((_, index) => (
                                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
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

                            {/* Latency Stats */}
                            {latencyData && (
                                <div className="card">
                                    <div className="card-header">
                                        <div>
                                            <div className="card-title">Performance Metrics</div>
                                            <div className="card-subtitle">Detection latency (last 24 hours)</div>
                                        </div>
                                    </div>
                                    <div className="grid-4" style={{ padding: 'var(--spacing-lg)' }}>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--accent-primary)' }}>
                                                {latencyData.avg_latency?.toFixed(2) || 0}ms
                                            </div>
                                            <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Average Latency</div>
                                        </div>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--color-success)' }}>
                                                {latencyData.p50?.toFixed(2) || 0}ms
                                            </div>
                                            <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>P50 Latency</div>
                                        </div>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--color-warning)' }}>
                                                {latencyData.p95?.toFixed(2) || 0}ms
                                            </div>
                                            <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>P95 Latency</div>
                                        </div>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--color-danger)' }}>
                                                {latencyData.p99?.toFixed(2) || 0}ms
                                            </div>
                                            <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>P99 Latency</div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </main>
        </div>
    );
}
