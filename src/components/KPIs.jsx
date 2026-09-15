import React from 'react'

function Card({ title, value, subtitle }) {
  return (
    <div className="card">
      <div className="muted">{title}</div>
      <div style={{ fontSize: 20, fontWeight: 700 }}>{value}</div>
      {subtitle && <div className="muted">{subtitle}</div>}
    </div>
  )
}

export default function KPIs({ data, loading }) {
  if (loading) return <div className="kpis"><div className="card loader">Loading KPIs…</div></div>
  return (
    <div className="kpis">
      <Card title="Total SKUs" value={data.total_skus} />
      <Card title="Inventory Value" value={`$${Number(data.inventory_value).toLocaleString()}`} />
      <Card title="Average Coverage" value={`${Number(data.average_days_of_coverage).toFixed(1)} days`} />
      <Card title="Critical SKUs" value={data.number_critical_skus} />
      <Card title="High Risk SKUs" value={data.number_high_risk_skus} />
    </div>
  )
}
