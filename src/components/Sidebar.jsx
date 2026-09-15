import React from 'react'

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="logo">SupplyPulse</div>
      <nav className="nav">
        <a href="#">Overview</a>
        <a href="#">Inventory</a>
        <a href="#">Replenishment</a>
        <a href="#">Risk Analysis</a>
        <a href="#">Suppliers</a>
      </nav>
    </aside>
  )
}
