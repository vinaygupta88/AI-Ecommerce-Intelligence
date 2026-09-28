'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { ProductListItem } from '@/types/api';
import { Search } from 'lucide-react';

const CATEGORIES = ['All', 'Electronics', 'Apparel', 'Home & Kitchen', 'Beauty & Health', 'Fitness & Outdoors'];

export default function ProductsPage() {
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    setLoading(true);
    const catParam = selectedCategory === 'All' ? undefined : selectedCategory;
    api.getProducts(catParam)
      .then(setProducts)
      .finally(() => setLoading(false));
  }, [selectedCategory]);

  const filteredProducts = products.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.sku.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Product Catalog & Inventory Matrix</h1>
        <p className="text-sm text-slate-400 mt-1">
          Monitor stock balances and trigger on-demand ML predictions for individual SKUs.
        </p>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-center">
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                selectedCategory === cat
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search SKU or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Catalog Table */}
      <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 text-sm">Loading product catalog...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/60 text-xs uppercase text-slate-400 border-b border-slate-700/60">
                <tr>
                  <th className="py-3 px-4">SKU / Name</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Base Price</th>
                  <th className="py-3 px-4">Stock Level</th>
                  <th className="py-3 px-4">Reorder Point</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Inference</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredProducts.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/50 transition">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-white">{p.sku}</div>
                      <div className="text-xs text-slate-400">{p.name}</div>
                    </td>
                    <td className="py-3 px-4">{p.category}</td>
                    <td className="py-3 px-4 font-mono">${p.base_price.toFixed(2)}</td>
                    <td className="py-3 px-4 font-mono font-medium text-white">{p.current_stock}</td>
                    <td className="py-3 px-4 font-mono text-slate-400">{p.reorder_point}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${
                          p.stock_status === 'CRITICAL'
                            ? 'bg-red-950/60 text-red-300 border-red-800'
                            : p.stock_status === 'LOW'
                            ? 'bg-amber-950/60 text-amber-300 border-amber-800'
                            : 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                        }`}
                      >
                        {p.stock_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/products/${p.id}`}
                        className="px-3 py-1 bg-slate-700 hover:bg-blue-600 text-slate-200 hover:text-white rounded-md text-xs font-medium transition"
                      >
                        Analyze &rarr;
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}