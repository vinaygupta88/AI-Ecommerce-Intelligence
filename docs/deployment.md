# Production Cloud Deployment Guide

This guide details two deployment paths for the **AI E-Commerce Intelligence & Demand Forecasting Platform**:
1. **Low-Cost / Free-Tier Portfolio Deployment** (For hosting a live demo on a resume for $0/month).
2. **Enterprise AWS Architecture** (For enterprise production with autoscaling, high availability, and isolated VPC subnets).

---

## Path 1: Low-Cost / Free-Tier Portfolio Deployment

To host this project online for recruiters without paying AWS cloud bills:

### 1. Database Tier: Managed PostgreSQL (Neon or Supabase)
1. Create a free account at [Neon.tech](https://neon.tech) or [Supabase.com](https://supabase.com).
2. Provision a free PostgreSQL database.
3. Copy your connection URI:
   ```text
   postgresql+psycopg2://user:password@ep-sample-123.us-east-2.aws.neon.tech/ecommerce_intelligence?sslmode=require