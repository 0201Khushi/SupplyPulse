import React from 'react'

export default function CriticalTable({ rows, loading }){
  if(loading) return <div className="table card">Loading table…</div>
  if(!rows || !rows.length) return <div className="table card">No critical SKUs</div>
  return (
    <div className="table">
      <table>
        <thead>
          <tr><th>SKU</th><th>Product</th><th>Category</th><th>Current Stock</th><th>Days Coverage</th><th>Lead Time</th><th>Risk</th><th>Recommended</th><th>Action</th></tr>
        </thead>
        <tbody>
          {rows.map(r=> (
            <tr key={r.sku}>
              <td>{r.sku}</td>
              <td>{r.product_name}</td>
              <td>{r.category}</td>
              <td>{r.on_hand}</td>
              <td>{Number(r.days_of_coverage).toFixed(1)}</td>
              <td>{r.lead_time_days}</td>
              <td>{r.stockout_risk_score}</td>
              <td>{r.recommended_order_qty}</td>
              <td>{r.recommended_action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
