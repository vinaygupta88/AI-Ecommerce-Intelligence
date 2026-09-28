'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { ProductDetail, ForecastResponse } from '@/types/api';
import {
  ArrowLeft,
  AlertTriangle,
  BrainCircuit,
  Calendar,
  CheckCircle2,
  Clock,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

export default function ProductDetailPage() {
  const params = useParams();
  const productId = Number(params.id);

  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    Promise.all([api.getProductDetail(productId), api.getForecast(productId)])
      .then(([prodData, forecastData]) => {
        setProduct(prodData);
        setForecast(forecastData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !product || !forecast) {
    return (
      <div className="p-6 bg-red-950/40 border border-red-800 rounded-xl text-red-200">
        <h3 className="font-semibold text-lg mb-2">Error Loading Product Intelligence</h3>
        <p className="text-sm font-mono">{error}</p>
        <Link href="/products" className="inline-block mt-4 text-xs font-semibold text-blue-400 underline">
          &larr; Return to catalog
        </Link>
      </div>
    );
  }

  const stockoutRiskPct = Math.round(forecast.stockout_probability * 100);

  return (
    <div className="space-y-8">
      {/* Navigation Breadcrumb */}
      <div>
        <Link
          href="/products"
          className="inline-flex items-center space-x-1 text-xs font-medium text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Product Catalog</span>
        </Link>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mt-2 gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-white">{product.name}</h1>
              <span className="px-2.5 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700/50 text-xs font-mono">
                {product.sku}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Category: <span className="text-slate-200">{product.category}</span> &bull; Base Price:{' '}
              <span className="text-slate-200 font-mono">${product.base_price.toFixed(2)}</span>
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">
            <Clock className="w-4 h-4 text-blue-400" />
            <span>Supplier Lead Time: <strong>{product.lead_time_days} days</strong></span>
          </div>
        </div>
      </div>

      {/* Core Intelligence Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: 7-Day Demand Forecast */}
        <div className="p-6 bg-slate-800/40 border border-slate-700/60 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs uppercase font-semibold tracking-wider">Predicted 7-Day Demand</span>
            <TrendingUp className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">
            {forecast.predicted_demand_next_7d} <span className="text-sm font-normal text-slate-400">units</span>
          </div>
          <div className="text-xs text-slate-400 mt-2 flex items-center space-x-1">
            <BrainCircuit className="w-3.5 h-3.5 text-blue-400" />
            <span>Model: {forecast.model_version}</span>
          </div>
        </div>

        {/* Card 2: Stock-Out Risk Assessment */}
        <div
          className={`p-6 border rounded-xl ${
            stockoutRiskPct >= 70
              ? 'bg-red-950/20 border-red-800/80 text-red-200'
              : stockoutRiskPct >= 35
              ? 'bg-amber-950/20 border-amber-800/80 text-amber-200'
              : 'bg-emerald-950/20 border-emerald-800/80 text-emerald-200'
          }`}
        >
          <div className="flex items-center justify-between mb-3 opacity-90">
            <span className="text-xs uppercase font-semibold tracking-wider">Stock-Out Probability</span>
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="text-3xl font-bold font-mono">
            {stockoutRiskPct}%
          </div>
          <div className="text-xs mt-2 opacity-80">
            Risk window: next {product.lead_time_days} days (Supplier replenishment cycle)
          </div>
        </div>

        {/* Card 3: Inventory Position */}
        <div className="p-6 bg-slate-800/40 border border-slate-700/60 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs uppercase font-semibold tracking-wider">Current Stock Position</span>
            <Calendar className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">
            {product.current_stock} <span className="text-sm font-normal text-slate-400">units</span>
          </div>
          <div className="text-xs text-slate-400 mt-2">
            Reorder Point (ROP): <strong className="text-slate-200">{product.reorder_point}</strong> &bull; Safety Stock:{' '}
            <strong className="text-slate-200">{product.safety_stock}</strong>
          </div>
        </div>
      </div>

      {/* Prescriptive Reorder Recommendation Box */}
      <div className="p-6 bg-gradient-to-r from-blue-950/30 to-indigo-950/30 border border-blue-800/50 rounded-xl">
        <div className="flex items-center space-x-2 mb-3">
          <Sparkles className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold text-white">Prescriptive Replenishment Recommendation</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div className="space-y-2">
            <div className="text-sm text-slate-300">
              Order Status:{' '}
              {forecast.reorder_advice.reorder_needed ? (
                <span className="px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 text-xs font-semibold">
                  REORDER REQUIRED IMMEDIATELY
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-xs font-semibold">
                  STOCK ADEQUATE
                </span>
              )}
            </div>
            <div className="text-2xl font-bold text-white font-mono">
              Suggested Order:{' '}
              <span className="text-blue-400">{forecast.reorder_advice.suggested_reorder_qty} units</span>
            </div>
            <p className="text-xs text-slate-400">
              Target Warehouse Capacity: {product.target_stock} units
            </p>
          </div>

          <div className="p-4 bg-slate-900/80 border border-slate-700/60 rounded-lg text-xs font-mono text-slate-300 space-y-1.5">
            <div className="text-slate-400 font-semibold mb-1">Supply Chain Math Breakdown:</div>
            <div>&bull; Lead-Time Demand = {forecast.reorder_advice.lead_time_demand} units</div>
            <div>&bull; Safety Stock (Z=1.65, 95% service level) = {forecast.reorder_advice.safety_stock} units</div>
            <div>&bull; Reorder Trigger Point = {forecast.reorder_advice.reorder_point} units</div>
            <div className="text-blue-300 pt-1 border-t border-slate-800">
              Formula: Target Stock ({product.target_stock}) - Current Stock ({product.current_stock})
            </div>
          </div>
        </div>
      </div>

      {/* AI Business Explanation */}
      <div className="p-6 bg-slate-800/40 border border-slate-700/60 rounded-xl space-y-3">
        <h3 className="text-sm uppercase font-semibold tracking-wider text-slate-400 flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Operational Rationale</span>
        </h3>
        <p className="text-sm leading-relaxed text-slate-200 bg-slate-900/50 p-4 rounded-lg border border-slate-800 font-sans">
          &ldquo;{forecast.business_explanation}&rdquo;
        </p>
      </div>
    </div>
  );
}