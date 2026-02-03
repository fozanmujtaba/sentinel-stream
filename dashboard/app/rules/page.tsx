'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface Rule {
    rule_id: string;
    rule_name: string;
    rule_type: string;
    total_triggers: number;
    true_positives: number;
    false_positives: number;
    precision: number;
    is_active: boolean;
}

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
                        <Link key={item.href} href={item.href} className={`nav-link ${pathname === item.href ? 'active' : ''}`}>
                            <span className="nav-link-icon">{item.icon}</span>
                            <span>{item.label}</span>
                        </Link>
                    ))}
                </div>
            </nav>
        </aside>
    );
}

export default function RulesPage() {
    const [rules, setRules] = useState<Rule[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://localhost:8002/rules/performance')
            .then(res => res.ok ? res.json() : [])
            .then(setRules)
            .finally(() => setLoading(false));
    }, []);

    const icons: Record<string, string> = { velocity: '⚡', amount: '💰', location: '📍', time: '🕐', pattern: '🔄', ml_threshold: '🤖' };

    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <header className="topbar">
                    <div className="topbar-left"><h1 className="page-title">Fraud Rules Engine</h1></div>
                    <div className="topbar-right"><button className="btn btn-primary">+ Create Rule</button></div>
                </header>
                <div className="content-area">
                    <div className="kpi-grid" style={{ marginBottom: 'var(--spacing-xl)' }}>
                        <div className="kpi-card"><div className="kpi-icon blue">📋</div><div className="kpi-content"><div className="kpi-value">{rules.length}</div><div className="kpi-label">Total Rules</div></div></div>
                        <div className="kpi-card"><div className="kpi-icon green">✅</div><div className="kpi-content"><div className="kpi-value">{rules.filter(r => r.is_active).length}</div><div className="kpi-label">Active</div></div></div>
                        <div className="kpi-card"><div className="kpi-icon purple">🎯</div><div className="kpi-content"><div className="kpi-value">{rules.length ? (rules.reduce((a, r) => a + (r.precision || 0), 0) / rules.length).toFixed(1) : 0}%</div><div className="kpi-label">Avg Precision</div></div></div>
                        <div className="kpi-card"><div className="kpi-icon yellow">⚡</div><div className="kpi-content"><div className="kpi-value">{rules.reduce((a, r) => a + r.total_triggers, 0)}</div><div className="kpi-label">Total Triggers</div></div></div>
                    </div>
                    <div className="card">
                        <div className="card-header"><div className="card-title">Detection Rules</div></div>
                        {loading ? <div className="loading"><div className="loading-spinner"></div></div> : (
                            <div className="table-container">
                                <table className="data-table">
                                    <thead><tr><th>Rule</th><th>Type</th><th>Status</th><th>Triggers</th><th>Precision</th><th>Actions</th></tr></thead>
                                    <tbody>
                                        {rules.map(r => (
                                            <tr key={r.rule_id}>
                                                <td><div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}><span style={{ fontSize: '20px' }}>{icons[r.rule_type] || '📋'}</span><div><div style={{ fontWeight: 600 }}>{r.rule_name}</div></div></div></td>
                                                <td><span style={{ padding: '4px 10px', background: 'var(--bg-tertiary)', borderRadius: '12px', fontSize: '12px' }}>{r.rule_type}</span></td>
                                                <td><span style={{ color: r.is_active ? 'var(--color-success)' : 'var(--text-muted)' }}>{r.is_active ? 'Active' : 'Inactive'}</span></td>
                                                <td style={{ fontWeight: 600 }}>{r.total_triggers}</td>
                                                <td><span style={{ color: r.precision >= 80 ? 'var(--color-success)' : r.precision >= 50 ? 'var(--color-warning)' : 'var(--color-danger)', fontWeight: 600 }}>{r.precision?.toFixed(1) || 0}%</span></td>
                                                <td><button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }}>Edit</button></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
