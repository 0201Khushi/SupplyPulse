import React, { useEffect, useState } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import KPIs from './components/KPIs'
import { RiskPie, CategoryBar } from './components/QuickCharts'
import CriticalTable from './components/CriticalTable'
import { fetchInventory, fetchDemandTrends } from './services/api'

function App(){
  const [kpis, setKpis] = useState(null)
  const [inventory, setInventory] = useState([])
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(()=>{
    async function load(){
      setLoading(true)
      try{
        const [inv, trends] = await Promise.all([fetchInventory(), fetchDemandTrends()])

        // Map trends by sku for quick lookup
        const trendMap = new Map(trends.map(t=>[t.sku, t]))

        // Enrich inventory rows with computed fields used by the UI
        const enriched = inv.map(row=>{
          const tr = trendMap.get(row.sku) || {}
          const demand30 = Number(tr.demand_30d || tr.historical_demand_30d || 0)
          const daily_demand = demand30 > 0 ? demand30 / 30 : 0
          const on_hand = Number(row.on_hand || 0)
          const unit_cost = Number(row.unit_cost || 0)
          const days_of_coverage = daily_demand > 0 ? on_hand / daily_demand : Infinity

          // simple risk classification so UI shows non-zero counts while backend risk is unavailable
          let stockout_risk_category = 'Low'
          if (days_of_coverage === Infinity) stockout_risk_category = 'Medium'
          else if (days_of_coverage < 7) stockout_risk_category = 'Critical'
          else if (days_of_coverage < 30) stockout_risk_category = 'High'

          // minimal recommendation: order up to 30 days of coverage when critical/high
          const recommended_order_qty = (stockout_risk_category==='Critical' || stockout_risk_category==='High')
            ? Math.max(0, Math.round((30 * daily_demand) - on_hand))
            : 0
          const recommended_action = recommended_order_qty>0 ? 'Reorder' : 'OK'

          return {
            ...row,
            days_of_coverage,
            stockout_risk_category,
            stockout_risk_score: stockout_risk_category==='Critical' ? 1 : stockout_risk_category==='High' ? 0.7 : stockout_risk_category==='Medium' ? 0.4 : 0.1,
            recommended_order_qty,
            recommended_action,
            inventory_value: on_hand * unit_cost
          }
        })

        // Compute KPIs from enriched inventory
        const total_skus = enriched.length
        const inventory_value = enriched.reduce((s,r)=>s + (r.inventory_value||0), 0)
        const total_units = enriched.reduce((s,r)=>s + Number(r.on_hand||0), 0)
        const avg_cov = enriched.filter(e=>isFinite(e.days_of_coverage)).reduce((s,r)=>s + r.days_of_coverage,0) / Math.max(1, enriched.filter(e=>isFinite(e.days_of_coverage)).length)
        const number_critical_skus = enriched.filter(e=>e.stockout_risk_category==='Critical').length
        const number_high_risk_skus = enriched.filter(e=>e.stockout_risk_category==='High').length

        setKpis({ total_skus, inventory_value, total_units, average_days_of_coverage: avg_cov, number_critical_skus, number_high_risk_skus })
        setInventory(enriched)
        setRecs(enriched.map(e=>({ sku: e.sku, recommended_order_qty: e.recommended_order_qty, recommended_action: e.recommended_action })))
      }catch(err){
        console.error(err)
      }finally{ setLoading(false) }
    }
    load()
  },[])

  const topCritical = inventory.filter(i=>i.stockout_risk_category==='Critical')

  return (
    <div id="dashboard">
      <Sidebar />
      <div className="main">
        <Header lastUpdated={null} />
        <KPIs data={kpis||{}} loading={loading} />

        <div className="charts">
          <div>
            <div className="card" style={{ marginBottom:12 }}>
              <div className="muted">Demand trends (recent)</div>
              <div className="muted">(Use API endpoint /api/demand-trends for time series)</div>
            </div>
            <CriticalTable rows={topCritical} loading={loading} />
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            <RiskPie data={inventory} />
            <CategoryBar data={inventory} />
          </div>
        </div>

        <div style={{ marginTop:18 }}>
          <div className="muted">Replenishment recommendations</div>
          <div className="table card">
            <table>
              <thead><tr><th>SKU</th><th>Recommended Qty</th><th>Action</th></tr></thead>
              <tbody>
                {recs.slice(0,10).map(r=> (
                  <tr key={r.sku}><td>{r.sku}</td><td>{r.recommended_order_qty}</td><td>{r.recommended_action}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
