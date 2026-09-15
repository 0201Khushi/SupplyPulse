import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

const COLORS = ['#ef4444','#f59e0b','#fbbf24','#10b981','#3b82f6']

export function RiskPie({ data }){
  const counts = [
    { name: 'Critical', value: data.filter(d=>d.stockout_risk_category==='Critical').length },
    { name: 'High', value: data.filter(d=>d.stockout_risk_category==='High').length },
    { name: 'Medium', value: data.filter(d=>d.stockout_risk_category==='Medium').length },
    { name: 'Low', value: data.filter(d=>d.stockout_risk_category==='Low').length },
  ]
  return (
    <div className="card" style={{ height:260 }}>
      <div className="muted">Risk distribution</div>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={counts} dataKey="value" nameKey="name" innerRadius={40} outerRadius={70}>
            {counts.map((entry, i) => (
              <Cell key={`cell-${i}`} fill={COLORS[i%COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export function CategoryBar({ data }){
  const byCat = {}
  data.forEach(d=>{
    const c = d.category || 'Unknown'
    byCat[c] = (byCat[c]||0) + (d.on_hand||0)
  })
  const arr = Object.keys(byCat).map(k=>({ category:k, units:byCat[k]})).sort((a,b)=>b.units-a.units).slice(0,8)
  return (
    <div className="card" style={{ padding:12 }}>
      <div className="muted">Inventory by category</div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={arr} layout="vertical">
          <XAxis type="number" />
          <YAxis dataKey="category" type="category" width={120} />
          <Tooltip />
          <Bar dataKey="units" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
