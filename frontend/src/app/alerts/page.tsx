'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AlertItem } from '@/types/api';
import { AlertTriangle, Check, RotateCw, CheckCircle2 } from 'lucide-react';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const loadAlerts = () => {
    setLoading(true);
    api.getAlerts()
      .then(setAlerts)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleResolve = async (id: number) => {
    try {
      setResolvingId(id);
      await api.resolveAlert(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      setToastMessage(`Alert #${id} successfully resolved!`);
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err: any) {
      alert(`Error: ${err.message || err}`);
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 py-4">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-emerald-600 text-white px-4 py-3 rounded-lg shadow-xl flex items-center space-x-2">
          <CheckCircle2 className="w-5 h-5" />
          <span className="text-sm font-medium">{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Active Operational Alerts</h1>
          <p className="text-sm text-slate-400 mt-1">Real-time stockout warnings and inventory anomalies</p>
        </div>
        <button
          onClick={loadAlerts}
          className="inline-flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-lg text-xs font-semibold border border-slate-700 transition"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Alerts List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">Loading telemetry alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/40">
            <Check className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <p className="text-base font-semibold text-white">All Clear</p>
            <p className="text-xs text-slate-400 mt-1">No active stock-out warnings detected.</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 transition shadow-sm"
            >
              <div className="flex items-start space-x-3.5">
                <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 mt-0.5">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-white text-sm">{alert.sku}</span>
                    <span className="text-xs text-slate-400">• {alert.product_name}</span>
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300 mt-1.5">{alert.message}</p>
                  <p className="text-xs text-slate-500 mt-1 font-mono">
                    Logged: {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2.5 self-end sm:self-center">
                <Link
                  href={`/products/${alert.product_id}`}
                  className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold border border-slate-700 transition"
                >
                  Inspect SKU →
                </Link>
                <button
                  onClick={() => handleResolve(alert.id)}
                  disabled={resolvingId === alert.id}
                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50 flex items-center space-x-1"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>{resolvingId === alert.id ? 'Resolving...' : 'Resolve'}</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}