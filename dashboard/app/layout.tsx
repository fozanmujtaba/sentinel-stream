import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Sentinel Stream | Enterprise Fraud Detection',
    description: 'Real-time fraud detection and case management platform',
    keywords: ['fraud detection', 'machine learning', 'real-time analytics', 'security'],
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body className={inter.className}>
                {children}
            </body>
        </html>
    )
}
