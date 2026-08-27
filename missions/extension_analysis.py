"""extension_analysis.py — Implementation and quantitative analysis of the 5 'Your Turn' Extensions.

Author: Trương Đình Khoa
Student ID: 2A202601297
Dossier: Day 25 Track 2 - GPU FinOps Optimization
"""
from __future__ import annotations
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from finops import pricing, metrics, sustainability
from missions._common import load_csv, catalog_by_type


def run_extension_1() -> dict:
    """Extension 1 — Improved Tier Recommendation with Duration & Interruption Risk."""
    workloads = load_csv("workloads.csv")
    recs = []
    for row in workloads:
        # Pass job duration and gpu_type to enhanced recommend_tier
        h = float(row["hours_per_day"])
        interruptible = bool(int(row["interruptible"]))
        days = int(row["days"])
        gpu_type = row["gpu_type"]
        tier = pricing.recommend_tier(h, interruptible, gpu_type=gpu_type, job_days=days)
        recs.append({"job_id": row["job_id"], "gpu_type": gpu_type, "tier": tier, "days": days})
    return {"status": "PASS", "recommendations": recs}


def run_extension_2() -> dict:
    """Extension 2 — Right-sizing memory-bound workloads by MBU & $/GB-VRAM."""
    from missions import m1_efficiency_audit
    m1_res = m1_efficiency_audit.run(verbose=False)
    catalog = load_csv("price_catalog.csv")
    
    stats = {}
    for r in catalog:
        gpu_type = r["gpu_type"]
        price = float(r["on_demand_hr"])
        vram = float(r["hbm_gb"])
        bw = float(r["peak_bw_tbs"])
        stats[gpu_type] = {
            "vram_gb": vram,
            "peak_bw_tbs": bw,
            "on_demand_hr": price,
            "cost_per_gb_vram_hr": round(price / vram if vram > 0 else 0.0, 4),
        }

    mem_bound_suggestions = []
    for s in m1_res["summary"]:
        mfu = s["mfu"]
        mbu = s["mbu"]
        cur_type = s["gpu_type"]
        # Memory bound: MBU is significantly higher than MFU, or GPU-util lie detected
        if (mbu > mfu or mfu < 0.30) and cur_type in ("H100", "A100"):
            target = "A100" if cur_type == "H100" else "A10G"
            orig_cost = stats[cur_type]["on_demand_hr"]
            new_cost = stats[target]["on_demand_hr"]
            savings_hr = orig_cost - new_cost
            mem_bound_suggestions.append({
                "gpu_id": s["gpu_id"],
                "current_type": cur_type,
                "mfu": mfu,
                "mbu": mbu,
                "suggested_type": target,
                "monthly_savings": round(savings_hr * 24 * 30, 2),
            })
            
    return {"status": "PASS", "gpu_catalog_stats": stats, "rightsize_suggestions": mem_bound_suggestions[:5]}


def run_extension_3() -> dict:
    """Extension 3 — Cache Break-even Economics (cache_is_worth_it)."""
    usage = load_csv("token_usage.csv")
    total_reqs = len(usage)
    cached_reqs = sum(1 for r in usage if int(r.get("cached_input_tokens", 0)) > 0)
    
    # Assume average cache reads per prefix across the dataset is 2.5
    avg_reads = 2.5
    sample_write_cost = 3.00  # $3/1M write cost
    worth_it = pricing.cache_is_worth_it(avg_reads, sample_write_cost)
    
    return {
        "status": "PASS",
        "avg_cache_reads": avg_reads,
        "is_cache_worth_it": worth_it,
        "cached_request_ratio": round(cached_reqs / total_reqs, 3) if total_reqs > 0 else 0,
    }


def run_extension_4() -> dict:
    """Extension 4 — Reasoning Traffic Budget & Energy Audit."""
    usage = load_csv("token_usage.csv")
    reasoning_reqs = [r for r in usage if int(r.get("is_reasoning", 0)) == 1]
    normal_reqs = [r for r in usage if int(r.get("is_reasoning", 0)) == 0]
    
    reasoning_count = len(reasoning_reqs)
    normal_count = len(normal_reqs)
    
    reasoning_wh = sum(sustainability.wh_per_query(int(r["input_tokens"]) + int(r["output_tokens"]), is_reasoning=True) for r in reasoning_reqs)
    normal_wh = sum(sustainability.wh_per_query(int(r["input_tokens"]) + int(r["output_tokens"]), is_reasoning=False) for r in normal_reqs)
    
    total_wh = reasoning_wh + normal_wh
    reasoning_wh_pct = (reasoning_wh / total_wh * 100.0) if total_wh > 0 else 0.0
    
    return {
        "status": "PASS",
        "reasoning_req_count": reasoning_count,
        "normal_req_count": normal_count,
        "reasoning_wh": round(reasoning_wh, 2),
        "normal_wh": round(normal_wh, 2),
        "reasoning_energy_share_pct": round(reasoning_wh_pct, 1),
    }


def run_extension_5() -> dict:
    """Extension 5 — Carbon-Aware Workload Scheduling."""
    workloads = load_csv("workloads.csv")
    interruptible_jobs = [w for w in workloads if int(w["interruptible"]) == 1]
    
    cat = catalog_by_type()
    dirty_region = "us-east-1"      # 380 gCO2/kWh
    clean_region = "europe-north1"   # 30 gCO2/kWh
    
    total_wh = 0.0
    for j in interruptible_jobs:
        gtype = j["gpu_type"]
        gcount = float(j["num_gpus"])
        h = float(j["hours_per_day"])
        watts = float(cat[gtype]["watts"]) if gtype in cat else 400.0
        daily_wh = (watts * gcount * h)
        total_wh += daily_wh * 30  # Monthly Wh
        
    dirty_carbon = sustainability.carbon_g(total_wh, dirty_region) / 1000.0  # kgCO2
    clean_carbon = sustainability.carbon_g(total_wh, clean_region) / 1000.0  # kgCO2
    saved_kg_co2 = dirty_carbon - clean_carbon
    
    return {
        "status": "PASS",
        "monthly_dirty_carbon_kg": round(dirty_carbon, 1),
        "monthly_clean_carbon_kg": round(clean_carbon, 1),
        "monthly_saved_carbon_kg": round(saved_kg_co2, 1),
        "reduction_pct": round((saved_kg_co2 / dirty_carbon * 100.0), 1) if dirty_carbon > 0 else 0.0,
    }


def run_all_extensions() -> dict:
    ext1 = run_extension_1()
    ext2 = run_extension_2()
    ext3 = run_extension_3()
    ext4 = run_extension_4()
    ext5 = run_extension_5()
    
    print("\n============================================================")
    print("  LAB 25 YOUR TURN EXTENSIONS RESULTS")
    print("  Student: Trương Đình Khoa (MSSV: 2A202601297)")
    print("============================================================")
    print(f"  [Ext 1] Enhanced Tiering Recommendations: {len(ext1['recommendations'])} jobs analyzed")
    print(f"  [Ext 2] Right-sizing MBU suggestions: {len(ext2['rightsize_suggestions'])} recommendations generated")
    print(f"  [Ext 3] Cache Economics: avg_reads={ext3['avg_cache_reads']} -> Cache Worth It = {ext3['is_cache_worth_it']}")
    print(f"  [Ext 4] Reasoning Energy Audit: Reasoning share = {ext4['reasoning_energy_share_pct']}% total energy")
    print(f"  [Ext 5] Carbon-Aware Scheduling: Savings = {ext5['monthly_saved_carbon_kg']} kgCO2/month (-{ext5['reduction_pct']}%)")
    print("============================================================\n")
    
    return {
        "ext1": ext1,
        "ext2": ext2,
        "ext3": ext3,
        "ext4": ext4,
        "ext5": ext5,
    }


if __name__ == "__main__":
    run_all_extensions()
