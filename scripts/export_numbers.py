"""Export pipeline results as LaTeX macros and tables for paper/ (no hand-copied numbers).

    uv run python scripts/export_numbers.py

Writes paper/generated/numbers.tex and paper/generated/tab_*.tex. Missing result
files produce \\todo{...} placeholders so the draft always compiles.
"""

import json

import pandas as pd

from orpaper.config import ROOT, load_config

RES, GEN = ROOT / "results", ROOT / "paper/generated"
CASE = load_config()["case"]


def macro(name, value):
    return f"\\newcommand{{\\{name}}}{{{value}}}\n"


def todo(what):
    return f"\\todo{{{what}}}"


def fmt(x, nd=1):
    return f"{x:,.{nd}f}"


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    out = []
    summ = json.loads((RES / "instance_summary.json").read_text())
    audit = json.loads((RES / "data_audit_kaggle.json").read_text())
    out += [macro("AreaKm", fmt(summ["bbmp_area_km2"], 0)),
            macro("NDemandCells", f"{summ['demand_cells']:,}"),
            macro("NOsmSites", f"{summ['osm_sites_in_bbmp']:,}"),
            macro("NCandidates", f"{summ['candidate_sites']:,}"),
            macro("PopWorldPop", fmt(summ["population_worldpop_in_bbmp"] / 1e6, 2)),
            macro("Detour", fmt(summ["detour"]["detour_median"], 2)),
            macro("DetourLo", fmt(summ["detour"]["detour_p25"], 2)),
            macro("DetourHi", fmt(summ["detour"]["detour_p75"], 2)),
            macro("KaggleOffsetPct", fmt(100 * audit["food_delivery"]["share_identical_lat_lon_offset"], 1)),
            macro("CurrentStores", f"{CASE['current_dark_stores_bengaluru']}"),
            macro("BaseV", "15"), macro("BaseT", "15")]

    e1 = pd.read_csv(RES / "e1_design.csv").set_index(["promise_min", "speed_kmh"])
    g = lambda T, v, c: e1.loc[(T, v), c]
    names = {10: "Ten", 15: "Fifteen", 20: "Twenty", 30: "Thirty"}
    for T, nm in names.items():
        out += [macro(f"StoresT{nm}", int(g(T, 15, "stores"))),
                macro(f"CostPerOrder{nm}", fmt(g(T, 15, "cost_per_order_inr"), 1)),
                macro(f"Served{nm}Pct", fmt(100 * g(T, 15, "served_share"), 1)),
                macro(f"Riders{nm}", f"{int(g(T, 15, 'riders_peak')):,}")]
    out += [macro("UnreachTenPct", fmt(100 * (1 - g(10, 15, "served_share")), 1)),
            macro("CostPerOrderVTwelve", fmt(g(15, 12, "cost_per_order_inr"), 1)),
            macro("CostPerOrderVTwenty", fmt(g(15, 20, "cost_per_order_inr"), 1)),
            macro("SpeedCapPremiumPct", fmt(100 * (g(15, 15, "cost_per_order_inr") / g(15, 20, "cost_per_order_inr") - 1), 0)),
            macro("StoreRange", f"{int(e1['stores'].min())}--{int(e1['stores'].max())}")]

    pert = pd.read_csv(RES / "pert_reliability.csv").set_index(["promise_min", "speed_kmh"])
    out += [macro("PertTenP", fmt(100 * pert.loc[(10, 15), "p_on_time"], 1)),
            macro("PertTenSpeed", fmt(pert.loc[(10, 15), "speed_for_95pct_kmh"], 1))]

    asg = pd.read_csv(RES / "assignment_peak.csv")
    st = asg[(asg.store_type == "p90_ride_distance") & (asg.staffing == 1.0)].set_index("promise_min")
    out += [macro("AssignStressTenOnTime", fmt(100 * st.loc[10, "on_time_opt"], 0)),
            macro("AssignStressSpeed", fmt(st.loc[10, "speed_to_recover_late_kmh_median"], 0)),
            macro("AssignStressRide", fmt(st.loc[10, "mean_ride_km"], 1))]

    tr = json.loads((RES / "transport_replenishment.json").read_text())
    out += [macro("TransLP", fmt(tr["lp_order_km"] / 1e6, 2)), macro("TransVAM", fmt(tr["vogel_order_km"] / 1e6, 2)),
            macro("TransNW", fmt(tr["nw_order_km"] / 1e6, 2)), macro("TransNearest", fmt(tr["nearest_hub_order_km"] / 1e6, 2)),
            macro("TransVAMGapPct", fmt(100 * (tr["vogel_order_km"] / tr["lp_order_km"] - 1), 1)),
            macro("TransNWRatio", fmt(tr["nw_order_km"] / tr["lp_order_km"], 1)),
            macro("TransCapPremiumPct", fmt(100 * (tr["lp_order_km"] / tr["nearest_hub_order_km"] - 1), 1))]

    grid_f = RES / "grid_robustness.csv"
    if grid_f.exists():
        gr = pd.read_csv(grid_f).set_index("promise_min")
        out += [macro("GridTenStores", int(gr.loc[10, "stores"])),
                macro("GridTenServedPct", fmt(100 * gr.loc[10, "served_share"], 1)),
                macro("GridTenCost", fmt(gr.loc[10, "cost_per_order_inr"], 1))]
        if 15 in gr.index:
            out += [macro("GridFifteenStores", int(gr.loc[15, "stores"])),
                    macro("GridFifteenCost", fmt(gr.loc[15, "cost_per_order_inr"], 1)),
                    macro("GridStorePremiumPct", fmt(100 * (gr.loc[10, "stores"] / gr.loc[15, "stores"] - 1), 0)),
                    macro("GridCostPremiumPct", fmt(100 * (gr.loc[10, "cost_per_order_inr"] / gr.loc[15, "cost_per_order_inr"] - 1), 1)),
                    macro("GridPricePerMinute", fmt((gr.loc[10, "cost_per_order_inr"] - gr.loc[15, "cost_per_order_inr"]) / 5, 2)),
                    macro("GridCandidates", gr.loc[10, "candidates"].split("(")[1].split()[0])]
        else:
            out += [macro(n, todo("grid run")) for n in ("GridFifteenStores", "GridFifteenCost")]
    else:
        out += [macro(n, todo("grid run")) for n in ("GridTenStores", "GridTenServedPct", "GridTenCost",
                                                     "GridFifteenStores", "GridFifteenCost")]

    tor_f = RES / "tornado.csv"
    if tor_f.exists():
        tor = pd.read_csv(tor_f).sort_values("span", ascending=False)
        out += [macro("TornadoTop", tor.iloc[0]["param"].split(" (")[0].lower()),
                macro("TornadoSecond", tor.iloc[1]["param"].split(" (")[0].lower()),
                macro("TornadoTopSpan", fmt(tor.iloc[0]["span"], 1)),
                macro("TornadoSecondSpan", fmt(tor.iloc[1]["span"], 1))]
    else:
        out += [macro("TornadoTop", todo("tornado")), macro("TornadoSecond", todo("tornado"))]
    (GEN / "numbers.tex").write_text("% Generated by scripts/export_numbers.py -- do not edit\n" + "".join(out))

    # Table: E1 design results
    t = pd.read_csv(RES / "e1_design.csv")
    lines = ["\\begin{tabular}{rrrrrrrr}", "\\toprule",
             "$T$ & $v$ & Radius & Stores & Reachable & Riders & Orders/ & Cost/order \\\\",
             "(min) & (km/h) & (km) & & pop.\\ (\\%) & (peak) & store/day & (INR) \\\\", "\\midrule"]
    for r in t.itertuples():
        lines.append(f"{r.promise_min} & {r.speed_kmh} & {r.radius_km:.2f} & {r.stores} & "
                     f"{100 * r.served_share:.1f} & {r.riders_peak:,} & {r.orders_per_store_day:,} & "
                     f"{r.cost_per_order_inr:.1f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (GEN / "tab_e1.tex").write_text("\n".join(lines) + "\n")

    # Table: PERT
    p = pd.read_csv(RES / "pert_reliability.csv")
    p = p[p.speed_kmh == 15]
    lines = ["\\begin{tabular}{rrrrr}", "\\toprule",
             "$T$ (min) & Mean (min) & SD (min) & $P$(on time) & Speed for 95\\% (km/h) \\\\", "\\midrule"]
    for r in p.itertuples():
        lines.append(f"{r.promise_min} & {r.mean_min:.2f} & {r.sd_min:.2f} & {r.p_on_time:.3f} & {r.speed_for_95pct_kmh:.1f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (GEN / "tab_pert.tex").write_text("\n".join(lines) + "\n")

    # Table: assignment (stressed store)
    a = asg[asg.store_type == "p90_ride_distance"]
    lines = ["\\begin{tabular}{rrrrrr}", "\\toprule",
             "Staffing & Riders & $T$ (min) & On time, optimal & On time, FIFO & Mean lateness opt./FIFO (min) \\\\",
             "\\midrule"]
    for r in a.itertuples():
        lines.append(f"{int(100 * r.staffing)}\\% & {r.riders} & {r.promise_min} & {100 * r.on_time_opt:.0f}\\% & "
                     f"{100 * r.on_time_fifo:.0f}\\% & {r.mean_late_min_opt:.2f} / {r.mean_late_min_fifo:.2f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    (GEN / "tab_assign.tex").write_text("\n".join(lines) + "\n")
    print(f"Wrote {GEN}/numbers.tex and tables")


if __name__ == "__main__":
    main()
