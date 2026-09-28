export interface HealthStatus {
  status: string;
  database: string;
  ml_models: string;
  timestamp: string;
}

export interface ProductListItem {
  id: number;
  sku: string;
  name: string;
  category: string;
  base_price: number;
  current_stock: number;
  reorder_point: number;
  stock_status: 'NORMAL' | 'LOW' | 'CRITICAL';
}

export interface ProductDetail {
  id: number;
  sku: string;
  name: string;
  category: string;
  base_price: number;
  lead_time_days: number;
  reorder_point: number;
  target_stock: number;
  current_stock: number;
  safety_stock: number;
  created_at: string;
}

export interface ReorderAdvice {
  reorder_needed: boolean;
  suggested_reorder_qty: number;
  safety_stock: number;
  reorder_point: number;
  lead_time_demand: number;
}

export interface ForecastResponse {
  product_id: number;
  sku: string;
  name: string;
  current_stock: number;
  predicted_demand_next_7d: number;
  stockout_probability: number;
  is_anomaly: boolean;
  reorder_advice: ReorderAdvice;
  business_explanation: string;
  model_version: string;
}

export interface AlertItem {
  id: number;
  product_id: number;
  sku: string;
  product_name: string;
  alert_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  message: string;
  is_resolved: boolean;
  created_at: string;
}

export interface DashboardSummary {
  total_skus: number;
  total_inventory_units: number;
  critical_stockout_skus: number;
  active_alerts_count: number;
  fleet_7d_forecasted_demand: number;
  top_risk_products: ProductListItem[];
}