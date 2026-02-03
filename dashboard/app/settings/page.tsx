'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

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

export default function SettingsPage() {
    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                <header className="topbar">
                    <div className="topbar-left"><h1 className="page-title">Settings</h1></div>
                </header>
                <div className="content-area">
                    <div className="grid-2">
                        <div className="card">
                            <div className="card-header"><div className="card-title">Fraud Detection</div></div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>Fraud Score Threshold</label>
                                    <input type="range" min="0" max="100" defaultValue="70" style={{ width: '100%' }} />
                                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Current: 0.70</div>
                                </div>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>Velocity Threshold</label>
                                    <input type="number" defaultValue="5" style={{ width: '100%', padding: '8px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', borderRadius: '8px', color: 'var(--text-primary)' }} />
                                </div>
                            </div>
                        </div>
                        <div className="card">
                            <div className="card-header"><div className="card-title">Notifications</div></div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                {['Email alerts for critical fraud', 'Slack notifications', 'SMS for high-value fraud'].map((item, i) => (
                                    <label key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
                                        <input type="checkbox" defaultChecked={i === 0} />
                                        <span style={{ fontSize: '14px' }}>{item}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
