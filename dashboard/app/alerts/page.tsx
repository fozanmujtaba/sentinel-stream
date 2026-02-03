'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface Alert {
    id: string;
    transaction_id: string;
    card_id: string;
    amount: number;
    timestamp: string;
    location: string;
    merchant_category: string;
    fraud_score: number;
    fraud_reason: string;
    risk_level: string;
    detected_at: string;
    status: string;
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

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState({ risk_level: '', status: '' });

    useEffect(() => {
        fetchAlerts();
    }, []);

    const fetchAlerts = async () => {
        try {
            const res = await fetch('http://localhost:8000/alerts/recent?limit=100');
            if (res.ok) {
                const data = await res.json();
                setAlerts(data);
            }
        } catch (error) {
            console.error('Failed to fetch alerts:', error);
        } finally {
            setLoading(false);
        }
    };

    const filteredAlerts = alerts.filter(alert => {
        if (filter.risk_level && alert.risk_level !== filter.risk_level) return false;
        if (filter.status && alert.status !== filter.status) return false;
        return true;
    });

    return (
        <div className="app-layout">
            <Sidebar />

            <main className="main-content">
                <header className="topbar">
                    <div className="topbar-left">
                        <h1 className="page-title">Fraud Alerts</h1>
                    </div>
                    <div className="topbar-right">
                        <select
                            value={filter.risk_level}
                            onChange={(e) => setFilter(prev => ({ ...prev, risk_level: e.target.value }))}
                            style={{
                                background: 'var(--bg-tertiary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '8px',
                                padding: '8px 12px',
                                color: 'var(--text-primary)',
                                fontSize: '13px'
                            }}
                        >
                            <option value="">All Risk Levels</option>
                            <option value="CRITICAL">Critical</option>
                            <option value="HIGH">High</option>
                            <option value="MEDIUM">Medium</option>
                            <option value="LOW">Low</option>
                        </select>
                        <button className="btn btn-primary" onClick={fetchAlerts}>
                            🔄 Refresh
                        </button>
                    </div>
                </header>

                <div className="content-area">
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <div className="card-title">All Fraud Alerts</div>
                                <div className="card-subtitle">Showing {filteredAlerts.length} alerts</div>
                            </div>
                        </div>

                        {loading ? (
                            <div className="loading">
                                <div className="loading-spinner"></div>
                            </div>
                        ) : (
                            <div className="table-container">
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th>Time</th>
                                            <th>Transaction ID</th>
                                            <th>Card</th>
                                            <th>Amount</th>
                                            <th>Location</th>
                                            <th>Category</th>
                                            <th>Score</th>
                                            <th>Risk Level</th>
                                            <th>Reason</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {filteredAlerts.map((alert, index) => (
                                            <tr key={alert.id || index}>
                                                <td style={{ whiteSpace: 'nowrap' }}>
                                                    {new Date(alert.detected_at).toLocaleString()}
                                                </td>
                                                <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                                                    {alert.transaction_id.slice(0, 8)}...
                                                </td>
                                                <td style={{ fontFamily: 'monospace' }}>
                                                    {alert.card_id.slice(-8)}
                                                </td>
                                                <td style={{ fontWeight: 600 }}>
                                                    ${alert.amount.toFixed(2)}
                                                </td>
                                                <td>{alert.location?.slice(0, 20) || 'Unknown'}</td>
                                                <td>{alert.merchant_category}</td>
                                                <td>
                                                    <span style={{
                                                        color: alert.fraud_score > 0.8 ? 'var(--risk-critical)' :
                                                            alert.fraud_score > 0.6 ? 'var(--risk-high)' : 'var(--risk-medium)'
                                                    }}>
                                                        {(alert.fraud_score * 100).toFixed(0)}%
                                                    </span>
                                                </td>
                                                <td>
                                                    <span className={`risk-badge ${alert.risk_level.toLowerCase()}`}>
                                                        {alert.risk_level}
                                                    </span>
                                                </td>
                                                <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                    {alert.fraud_reason}
                                                </td>
                                                <td>
                                                    <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }}>
                                                        Create Case
                                                    </button>
                                                </td>
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
