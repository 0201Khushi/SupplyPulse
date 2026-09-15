import React from 'react'

export default function Header({ lastUpdated }) {
  return (
    <div className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 18 }}>SupplyPulse</div>
        <div className="muted">Inventory & Replenishment Intelligence</div>
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <input placeholder="Search SKU or product" style={{ padding: 8, borderRadius:8, border:'1px solid #e6edf3' }} />
        <div className="muted">Last updated: {lastUpdated || '—'}</div>
      </div>
    </div>
  )
}
