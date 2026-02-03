'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface Customer {
    id: string;
    card_id: string;
    customer_name: string;
    email: string;
    risk_score: number;
    risk_level: string;
    total_transactions: number;
    total_spent: number;
    total_alerts: number;
    last_transaction_at: string;
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

export default function CustomersPage() {
    const [customers, setCustomers] = useState<Customer[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchCustomers();
    }, []);

    const fetchCustomers = async () => {
        try {
            const res = await fetch('http://localhost:8002/customers/risky?limit=50');
            if (res.ok) {
                const data = await res.json();
                setCustomers(data);
            }
        } catch (error) {
            console.error('Failed to fetch customers:', error);
        } finally {
            setLoading(false);
        }
    };

    const getRiskColor = (level: string) => {
        switch (level?.toUpperCase()) {
            case 'CRITICAL': return 'var(--risk-critical)';
            case 'HIGH': return 'var(--risk-high)';
            case 'MEDIUM': return 'var(--risk-medium)';
            default: return 'var(--risk-low)';
        }
    };

    return (
        <div className="app-layout">
            <Sidebar />

            <main className="main-content">
                <header className="topbar">
                    <div className="topbar-left">
                        <h1 className="page-title">Customer 360°</h1>
                    </div>
                    <div className="topbar-right">
                        <input
                            type="search"
                            placeholder="Search customers..."
                            style={{
                                background: 'var(--bg-tertiary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '8px',
                                padding: '8px 16px',
                                color: 'var(--text-primary)',
                                width: '250px'
                            }}
                        />
                    </div>
                </header>

                <div className="content-area">
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <div className="card-title">High-Risk Customers</div>
                                <div className="card-subtitle">Customers with elevated risk scores or past fraud alerts</div>
                            </div>
                        </div>

                        {loading ? (
                            <div className="loading">
                                <div className="loading-spinner"></div>
                            </div>
                        ) : customers.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-icon">👥</div>
                                <div className="empty-state-text">No high-risk customers found</div>
                            </div>
                        ) : (
                            <div className="table-container">
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th>Customer</th>
                                            <th>Card ID</th>
                                            <th>Risk Score</th>
                                            <th>Risk Level</th>
                                            <th>Transactions</th>
                                            <th>Total Spent</th>
                                            <th>Alerts</th>
                                            <th>Last Activity</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {customers.map((customer) => (
                                            <tr key={customer.id}>
                                                <td>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                        <div style={{
                                                            width: '36px',
                                                            height: '36px',
                                                            borderRadius: '50%',
                                                            background: 'var(--accent-gradient)',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            color: 'white',
                                                            fontWeight: 600,
                                                            fontSize: '14px'
                                                        }}>
                                                            {customer.customer_name?.charAt(0) || 'U'}
                                                        </div>
                                                        <div>
                                                            <div style={{ fontWeight: 500 }}>{customer.customer_name || 'Unknown'}</div>
                                                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{customer.email || 'No email'}</div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td style={{ fontFamily: 'monospace' }}>{customer.card_id.slice(-8)}</td>
                                                <td>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                        <div style={{
                                                            width: '60px',
                                                            height: '6px',
                                                            background: 'var(--bg-tertiary)',
                                                            borderRadius: '3px',
                                                            overflow: 'hidden'
                                                        }}>
                                                            <div style={{
                                                                width: `${Math.min(customer.risk_score * 100, 100)}%`,
                                                                height: '100%',
                                                                background: getRiskColor(customer.risk_level),
                                                                borderRadius: '3px'
                                                            }}></div>
                                                        </div>
                                                        <span style={{ fontWeight: 600 }}>{(customer.risk_score * 100).toFixed(0)}%</span>
                                                    </div>
                                                </td>
                                                <td>
                                                    <span className={`risk-badge ${customer.risk_level?.toLowerCase() || 'low'}`}>
                                                        {customer.risk_level || 'LOW'}
                                                    </span>
                                                </td>
                                                <td>{customer.total_transactions.toLocaleString()}</td>
                                                <td style={{ fontWeight: 600 }}>${customer.total_spent.toLocaleString()}</td>
                                                <td>
                                                    <span style={{
                                                        color: customer.total_alerts > 0 ? 'var(--color-danger)' : 'var(--text-muted)',
                                                        fontWeight: customer.total_alerts > 0 ? 600 : 400
                                                    }}>
                                                        {customer.total_alerts}
                                                    </span>
                                                </td>
                                                <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                                                    {customer.last_transaction_at
                                                        ? new Date(customer.last_transaction_at).toLocaleDateString()
                                                        : 'Never'}
                                                </td>
                                                <td>
                                                    <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '12px' }}>
                                                        View Profile
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
