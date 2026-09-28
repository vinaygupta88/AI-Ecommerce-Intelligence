'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { DashboardSummary } from '@/types/api';
import { AlertTriangle, TrendingUp, PackageCheck, Layers, ArrowUpRight, ShieldAlert } from 'lucide-react';

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDashboardSummary()
      .then(setSummary)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin"></div>
        <p className="text-zinc-400 text-sm font-medium">Crunching real-time telemetry...</p>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="p-6 bg-rose-950/30 border border-rose-800/50 rounded-2xl text-rose-200 max-w-2xl mx-auto my-12">
        <div className="flex items-center space-x-3 mb-2">
          <ShieldAlert className="w-6 h-6 text-rose-400" />
          <h3 className="font-semibold text-lg text-white">Backend Connection Error</h3>
        </div>
        <p className="text-sm font-mono text-rose-300/90">{error}</p>
        <p className="text-xs mt-3 text-zinc-400">
          Make sure your FastAPI server is running on <code>http://localhost:8000</code>.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/60 pb-6">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Operations & Demand Intelligence
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Real-time multi-horizon demand forecasting and supply risk telemetry across active SKUs.
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs text-zinc-400 bg-zinc-900/90 border border-zinc-800 px-3.5 py-1.5 rounded-xl">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Pipeline: Automated 24h Sync</span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        
        {/* SKUs */}
        <div className="p-6 bg-zinc-900/60 border border-zinc-800/80 rounded-2xl relative overflow-hidden group hover:border-zinc-700 transition">
          <div className="flex justify-between items-center text-zinc-400 mb-3">
            <span className="text-xs uppercase font-semibold tracking-wider text-zinc-400">Total Active SKUs</span>
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-black text-white">{summary.total_skus}</div>
          <div className="text-xs text-zinc-400 mt-2">Monitored across 5 product categories</div>
        </div>

        {/* Warehouse Inventory */}
        <div className="p-6 bg-zinc-900/60 border border-zinc-800/80 rounded-2xl relative overflow-hidden group hover:border-zinc-700 transition">
          <div className="flex justify-between items-center text-zinc-400 mb-3">
            <span className="text-xs uppercase font-semibold tracking-wider text-zinc-400">Current Stock</span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <PackageCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-black text-white">{summary.total_inventory_units.toLocaleString()}</div>
          <div className="text-xs text-zinc-400 mt-2">Available warehouse units</div>
        </div>

        {/* Forecasted Demand */}
        <div className="p-6 bg-zinc-900/60 border border-zinc-800/80 rounded-2xl relative overflow-hidden group hover:border-zinc-700 transition">
          <div className="flex justify-between items-center text-zinc-400 mb-3">
            <span className="text-xs uppercase font-semibold tracking-wider text-zinc-400">7-Day Fleet Forecast</span>
            <div className="p-2 bg-violet-500/10 text-violet-400 rounded-lg">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-black text-white">{summary.fleet_7d_forecasted_demand.toLocaleString()}</div>
          <div className="text-xs text-zinc-400 mt-2">LightGBM predicted units</div>
        </div>

        {/* Critical Stockout Risk */}
        <div className="p-6 bg-gradient-to-br from-rose-950/30 to-zinc-900/80 border border-rose-900/50 rounded-2xl relative overflow-hidden group hover:border-rose-700/60 transition">
          <div className="flex justify-between items-center text-rose-300 mb-3">
            <span className="text-xs uppercase font-semibold tracking-wider">Critical Stockouts</span>
            <div className="p-2 bg-rose-500/20 text-rose-400 rounded-lg">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-black text-rose-400">{summary.critical_stockout_skus}</div>
          <div className="text-xs text-rose-300/80 mt-2">SKUs at or below Reorder Point</div>
        </div>
      </div>

      {/* Priority Stockout Table */}
      <div className="bg-zinc-900/50 border border-zinc-800/80 rounded-2xl overflow-hidden shadow-xl">
        <div className="p-6 flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-zinc-800/60">
          <div>
            <h2 className="text-lg font-bold text-white">Top Replenishment Priorities</h2>
            <p className="text-xs text-zinc-400 mt-0.5">Products with critical stock-out probability requiring purchase orders</p>
          </div>
          <Link
            href="/products"
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition"
          >
            <span>View Complete Catalog</span>
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="bg-zinc-950/60 text-xs uppercase font-semibold text-zinc-400 border-b border-zinc-800/60">
              <tr>
                <th className="py-3.5 px-6">Product & SKU</th>
                <th className="py-3.5 px-6">Category</th>
                <th className="py-3.5 px-6">Current Stock</th>
                <th className="py-3.5 px-6">Reorder Trigger</th>
                <th className="py-3.5 px-6">Risk Status</th>
                <th className="py-3.5 px-6 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {summary.top_risk_products.map((p) => (
                <tr key={p.id} className="hover:bg-zinc-800/30 transition">
                  <td className="py-4 px-6">
                    <div className="font-semibold text-white">{p.name}</div>
                    <div className="text-xs font-mono text-zinc-400">{p.sku}</div>
                  </td>
                  <td className="py-4 px-6 text-zinc-300">{p.category}</td>
                  <td className="py-4 px-6 font-mono font-bold text-white">{p.current_stock}</td>
                  <td className="py-4 px-6 font-mono text-zinc-400">{p.reorder_point}</td>
                  <td className="py-4 px-6">
                    <span
                      className={`px-2.5 py-1 text-xs font-bold rounded-md border ${
                        p.stock_status === 'CRITICAL'
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                      }`}
                    >
                      {p.stock_status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-right">
                    <Link
                      href={`/products/${p.id}`}
                      className="px-3.5 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-semibold transition"
                    >
                      Analyze &rarr;
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}