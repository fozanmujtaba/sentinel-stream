'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface Case {
    id: string;
    case_number: string;
    title: string;
    description: string;
    priority: string;
    status: string;
    category: string;
    card_id: string;
    total_amount: number;
    assigned_name: string;
    sla_breached: boolean;
    created_at: string;
    updated_at: string;
}

interface CaseStats {
    total_cases: number;
    open_cases: number;
    investigating: number;
    resolved: number;
    sla_breached: number;
    avg_resolution_hours: number;
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

export default function CasesPage() {
    const [cases, setCases] = useState<Case[]>([]);
    const [stats, setStats] = useState<CaseStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState('');

    useEffect(() => {
        fetchCases();
        fetchStats();
    }, [statusFilter]);

    const fetchCases = async () => {
        try {
            const url = statusFilter
                ? `http://localhost:8001/cases?status=${statusFilter}`
                : 'http://localhost:8001/cases';
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                setCases(data);
            }
        } catch (error) {
            console.error('Failed to fetch cases:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchStats = async () => {
        try {
            const res = await fetch('http://localhost:8001/cases/stats');
            if (res.ok) {
                const data = await res.json();
                setStats(data);
            }
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
    };

    const priorityColors: Record<string, string> = {
        critical: 'var(--risk-critical)',
        high: 'var(--risk-high)',
        medium: 'var(--risk-medium)',
        low: 'var(--risk-low)'
    };

    return (
        <div className="app-layout">
            <Sidebar />

            <main className="main-content">
                <header className="topbar">
                    <div className="topbar-left">
                        <h1 className="page-title">Case Management</h1>
                    </div>
                    <div className="topbar-right">
                        <button className="btn btn-primary">
                            + New Case
                        </button>
                    </div>
                </header>

                <div className="content-area">
                    {/* Stats */}
                    {stats && (
                        <div className="kpi-grid" style={{ marginBottom: 'var(--spacing-xl)' }}>
                            <div className="kpi-card">
                                <div className="kpi-icon blue"><span style={{ fontSize: '24px' }}>📁</span></div>
                                <div className="kpi-content">
                                    <div className="kpi-value">{stats.total_cases}</div>
                                    <div className="kpi-label">Total Cases</div>
                                </div>
                            </div>
                            <div className="kpi-card">
                                <div className="kpi-icon yellow"><span style={{ fontSize: '24px' }}>🔍</span></div>
                                <div className="kpi-content">
                                    <div className="kpi-value">{stats.open_cases + stats.investigating}</div>
                                    <div className="kpi-label">Active Cases</div>
                                </div>
                            </div>
                            <div className="kpi-card">
                                <div className="kpi-icon green"><span style={{ fontSize: '24px' }}>✅</span></div>
                                <div className="kpi-content">
                                    <div className="kpi-value">{stats.resolved}</div>
                                    <div className="kpi-label">Resolved</div>
                                </div>
                            </div>
                            <div className="kpi-card">
                                <div className="kpi-icon red"><span style={{ fontSize: '24px' }}>⚠️</span></div>
                                <div className="kpi-content">
                                    <div className="kpi-value">{stats.sla_breached}</div>
                                    <div className="kpi-label">SLA Breached</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Filter Tabs */}
                    <div style={{
                        display: 'flex',
                        gap: 'var(--spacing-sm)',
                        marginBottom: 'var(--spacing-lg)',
                        borderBottom: '1px solid var(--border-color)',
                        paddingBottom: 'var(--spacing-md)'
                    }}>
                        {['', 'open', 'investigating', 'resolved', 'closed'].map(status => (
                            <button
                                key={status}
                                onClick={() => setStatusFilter(status)}
                                style={{
                                    padding: '8px 16px',
                                    background: statusFilter === status ? 'var(--accent-primary)' : 'transparent',
                                    border: 'none',
                                    borderRadius: '8px',
                                    color: statusFilter === status ? 'white' : 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    fontSize: '14px',
                                    fontWeight: 500
                                }}
                            >
                                {status === '' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)}
                            </button>
                        ))}
                    </div>

                    {/* Cases List */}
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <div className="card-title">Cases</div>
                                <div className="card-subtitle">{cases.length} cases found</div>
                            </div>
                        </div>

                        {loading ? (
                            <div className="loading">
                                <div className="loading-spinner"></div>
                            </div>
                        ) : cases.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-icon">📁</div>
                                <div className="empty-state-text">No cases found</div>
                            </div>
                        ) : (
                            <div className="table-container">
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th>Case #</th>
                                            <th>Title</th>
                                            <th>Priority</th>
                                            <th>Status</th>
                                            <th>Category</th>
                                            <th>Amount</th>
                                            <th>Assigned To</th>
                                            <th>Created</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {cases.map((c) => (
                                            <tr key={c.id}>
                                                <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>
                                                    {c.case_number}
                                                </td>
                                                <td style={{ maxWidth: '250px' }}>
                                                    <div style={{ fontWeight: 500 }}>{c.title}</div>
                                                    {c.card_id && (
                                                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                                            Card: {c.card_id.slice(-8)}
                                                        </div>
                                                    )}
                                                </td>
                                                <td>
                                                    <span style={{
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        gap: '4px',
                                                        color: priorityColors[c.priority] || 'var(--text-secondary)'
                                                    }}>
                                                        <span style={{
                                                            width: '8px',
                                                            height: '8px',
                                                            borderRadius: '50%',
                                                            background: priorityColors[c.priority]
                                                        }}></span>
                                                        {c.priority.toUpperCase()}
                                                    </span>
                                                </td>
                                                <td>
                                                    <span className={`status-badge ${c.status}`}>
                                                        {c.status}
                                                    </span>
                                                </td>
                                                <td>{c.category || '-'}</td>
                                                <td style={{ fontWeight: 600 }}>${c.total_amount.toFixed(2)}</td>
                                                <td>{c.assigned_name || 'Unassigned'}</td>
                                                <td style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                                    {new Date(c.created_at).toLocaleDateString()}
                                                </td>
                                                <td>
                                                    <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }}>
                                                        View
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
