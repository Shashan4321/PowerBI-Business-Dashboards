"""Render the dashboard designs (1600x900, Power BI canvas size) from the CSVs in ``data/``.

Each page is laid out like a Power BI report page (nav rail, header with slicers, KPI cards,
visual grid) using the colours from ``theme/portfolio-theme.json``. Output:
``screenshots/<nn>-<page>.png``. Every number shown is computed from ``data/``.

    python design/hr_data.py && python design/build.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "screenshots"
THEME = json.loads((ROOT / "theme" / "portfolio-theme.json").read_text())
C = THEME["dataColors"]
NAVY, TEAL, AMBER, CORAL, VIOLET, SKY = C[0], C[1], C[2], C[3], C[4], C[5]
INK, MUTED, GRID = "#252423", "#605E5C", "#EDEBE9"
FONT = "Segoe UI, Inter, Arial, sans-serif"


# ----------------------------------------------------------------- helpers
def inr(v: float) -> str:
    if abs(v) >= 1e7:
        return f"₹{v / 1e7:,.2f} Cr"
    if abs(v) >= 1e5:
        return f"₹{v / 1e5:,.1f} L"
    return f"₹{v:,.0f}"


def pct(v: float, signed: bool = False) -> str:
    return f"{v * 100:+.1f}%" if signed else f"{v * 100:.1f}%"


def style(fig: go.Figure, h: int, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=h, margin=dict(l=8, r=12, t=6, b=6), paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family=FONT, size=12, color=MUTED), showlegend=legend,
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)), hoverlabel=dict(font_family=FONT),
        treemapcolorway=[NAVY, TEAL, AMBER, CORAL, VIOLET], extendtreemapcolors=True,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="", tickfont=dict(size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(size=11))
    return fig


def kpi(label: str, value: str, delta: str | None = None, good: bool | None = None, sub: str = "") -> str:
    good = None if good is None else bool(good)
    color = "#107C10" if good else ("#C50F1F" if good is False else MUTED)
    arrow = "▲" if good else ("▼" if good is False else "")
    d = f'<div class="delta" style="color:{color}">{arrow} {delta}</div>' if delta else ""
    return (f'<div class="card kpi"><div class="label">{label}</div><div class="value">{value}</div>'
            f'{d}<div class="sub">{sub}</div></div>')


def visual(title: str, fig: go.Figure | str, span: str = "") -> str:
    body = fig if isinstance(fig, str) else fig.to_html(full_html=False, include_plotlyjs=False,
                                                         config={"staticPlot": True})
    return f'<div class="card vis" style="{span}"><div class="vtitle">{title}</div>{body}</div>'


def page(n: int, title: str, subtitle: str, slicers: list[str], kpis: list[str], grid: str,
         cols: str, active: int, insight: str) -> str:
    nav = "".join(f'<div class="nav {"on" if i == active else ""}">{ic}</div>'
                  for i, ic in enumerate(["◧", "▦", "◉", "⬡", "◈"]))
    chips = "".join(f'<span class="chip">{s}</span>' for s in slicers)
    return f"""
<div class="page">
  <div class="rail"><div class="logo">SS</div>{nav}</div>
  <div class="main">
    <div class="head">
      <div><div class="title">{title}</div><div class="subtitle">{subtitle}</div></div>
      <div class="chips">{chips}</div>
    </div>
    <div class="kpis" style="grid-template-columns:repeat({len(kpis)},1fr)">{"".join(kpis)}</div>
    <div class="grid" style="grid-template-columns:{cols}">{grid}</div>
    <div class="foot"><span class="insight">💡 {insight}</span>
      <span>Page {n}/5 · Synthetic data · Design prototype, Shashank Singh</span></div>
  </div>
</div>"""


CSS = f"""
*{{box-sizing:border-box}} body{{margin:0;font-family:{FONT};background:#F3F2F1;color:{INK}}}
.page{{width:1600px;height:900px;display:flex;background:#F3F2F1;overflow:hidden}}
.rail{{width:64px;background:{NAVY};display:flex;flex-direction:column;align-items:center;padding-top:14px;gap:10px}}
.logo{{width:38px;height:38px;border-radius:10px;background:{AMBER};color:{NAVY};font-weight:800;
  display:flex;align-items:center;justify-content:center;margin-bottom:12px}}
.nav{{width:40px;height:40px;border-radius:8px;color:#9FB3C8;display:flex;align-items:center;justify-content:center;font-size:20px}}
.nav.on{{background:rgba(255,255,255,.14);color:white}}
.main{{flex:1;padding:18px 22px 10px 22px;display:flex;flex-direction:column;gap:12px}}
.head{{display:flex;justify-content:space-between;align-items:flex-end}}
.title{{font-size:26px;font-weight:700;color:{NAVY}}} .subtitle{{font-size:13px;color:{MUTED};margin-top:2px}}
.chips{{display:flex;gap:8px}} .chip{{background:white;border:1px solid #E1DFDD;border-radius:16px;padding:6px 14px;font-size:12px;color:{INK}}}
.card{{background:white;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.kpis{{display:grid;gap:12px}} .kpi{{padding:12px 16px;border-top:4px solid {NAVY}}}
.kpi:nth-child(2){{border-top-color:{TEAL}}} .kpi:nth-child(3){{border-top-color:{AMBER}}}
.kpi:nth-child(4){{border-top-color:{CORAL}}} .kpi:nth-child(5){{border-top-color:{VIOLET}}}
.label{{font-size:12px;color:{MUTED};text-transform:uppercase;letter-spacing:.05em}}
.value{{font-size:28px;font-weight:700;color:{INK};margin-top:2px}}
.delta{{font-size:12.5px;font-weight:600;margin-top:2px}} .sub{{font-size:11.5px;color:{MUTED}}}
.grid{{display:grid;gap:12px;flex:1;min-height:0}}
.vis{{padding:10px 12px;overflow:hidden}} .vtitle{{font-size:14px;font-weight:600;color:{INK};margin-bottom:2px}}
.foot{{display:flex;justify-content:space-between;font-size:11.5px;color:{MUTED}}}
.insight{{color:{NAVY};font-weight:600}}
table.t{{width:100%;border-collapse:collapse;font-size:12.5px}} .t th{{text-align:left;color:{MUTED};font-weight:600;
  border-bottom:1px solid {GRID};padding:6px 4px}} .t td{{padding:6px 4px;border-bottom:1px solid #F3F2F1}}
.t td.n{{text-align:right}} .bar{{height:8px;border-radius:4px;background:{TEAL}}}
"""


# ----------------------------------------------------------------- pages
def exec_sales() -> str:
    m = pd.read_csv(DATA / "sales_monthly.csv")
    yr = pd.read_csv(DATA / "sales_yearly.csv").set_index("year")
    y25, y24 = m[m.year == 2025], m[m.year == 2024]
    rev, rev_py = y25.revenue.sum(), y24.revenue.sum()
    orders, orders_py = y25.orders.sum(), y24.orders.sum()
    gm = 1 - y25.cost_amt.sum() / rev
    gm_py = 1 - y24.cost_amt.sum() / rev_py
    aov, aov_py = rev / orders, rev_py / orders_py
    months = pd.date_range("2025-01-01", periods=12, freq="MS").strftime("%b")
    f1 = go.Figure()
    f1.add_bar(x=months, y=y25.revenue / 1e7, name="2025", marker_color=NAVY)
    f1.add_scatter(x=months, y=y24.revenue.values / 1e7, name="2024", mode="lines+markers",
                   line=dict(color=AMBER, width=3))
    f1.update_yaxes(ticksuffix=" Cr")
    p = pd.read_csv(DATA / "sales_by_product.csv")
    cat = p[p.year == 2025].groupby("category").revenue.sum().sort_values()
    cat_py = p[p.year == 2024].groupby("category").revenue.sum()
    yoy = (cat / cat_py - 1)
    f2 = go.Figure(go.Bar(x=cat / 1e7, y=cat.index, orientation="h", marker_color=TEAL,
                          text=[f"{inr(v)} · {g:+.0%}" for v, g in zip(cat, yoy[cat.index], strict=True)],
                          textposition="outside", cliponaxis=False))
    f2.update_xaxes(visible=False, range=[0, cat.max() / 1e7 * 1.75])
    g = pd.read_csv(DATA / "sales_by_geo.csv")
    st = g[(g.year == 2025)].groupby(["country", "state"]).revenue.sum().reset_index()
    ctry = st.groupby("country").revenue.sum()
    f3 = go.Figure(go.Treemap(
        ids=list(ctry.index) + [f"{c}/{s_}" for c, s_ in zip(st.country, st.state, strict=True)],
        labels=list(ctry.index) + list(st.state), parents=[""] * len(ctry) + list(st.country),
        values=list(ctry.values) + list(st.revenue), branchvalues="total",
        customdata=[inr(v) for v in list(ctry.values) + list(st.revenue)],
        texttemplate="<b>%{label}</b><br>%{customdata}<br>%{percentRoot:.1%}",
        textfont=dict(family=FONT, size=13)))
    ch = pd.read_csv(DATA / "sales_by_channel_segment.csv")
    chn = ch[ch.year == 2025].groupby("channel").revenue.sum()
    f4 = go.Figure(go.Pie(labels=chn.index, values=chn.values, hole=0.62, sort=False,
                          marker=dict(colors=[NAVY, AMBER]), textinfo="label+percent", textfont=dict(size=12)))
    f4.add_annotation(text=f"<b>{inr(chn.sum())}</b><br>2025", showarrow=False, font=dict(size=13, color=INK))
    kpis = [
        kpi("Revenue", inr(rev), f"{rev / rev_py - 1:+.1%} vs PY", rev > rev_py, f"PY {inr(rev_py)}"),
        kpi("Orders", f"{orders:,}", f"{orders / orders_py - 1:+.1%} vs PY", orders > orders_py),
        kpi("Avg order value", inr(aov), f"{aov / aov_py - 1:+.1%} vs PY", aov > aov_py),
        kpi("Gross margin", pct(gm), f"{(gm - gm_py) * 100:+.1f} pts vs PY", gm > gm_py),
        kpi("Active customers", f"{yr.loc[2025, 'customers']:,}",
            f"{yr.loc[2025, 'customers'] / yr.loc[2024, 'customers'] - 1:+.1%} vs PY",
            yr.loc[2025, "customers"] > yr.loc[2024, "customers"], "bought at least once in 2025"),
    ]
    oct_share = y25[y25.month.isin([10, 11])].revenue.sum() / rev
    grid = (visual("Monthly revenue 2025 vs 2024 (₹ Cr)", style(f1, 300, True), "grid-column:span 2")
            + visual("Revenue by category · YoY", style(f2, 300))
            + visual("Revenue by country → state (drill-down)", style(f3, 250), "grid-column:span 2")
            + visual("Channel mix", style(f4, 250)))
    return page(1, "Executive Sales Overview", "Retail · FY view with YoY · all amounts in INR",
                ["Year: 2025", "Country: All", "Channel: All", "Category: All"], kpis, grid,
                "1.2fr 1.2fr 1fr", 0,
                f"October-November festive season = {oct_share:.0%} of 2025 revenue. Plan stock and staff from September.")


def product_scorecard() -> str:
    p = pd.read_csv(DATA / "sales_by_product.csv")
    s = pd.read_csv(DATA / "sales_by_sku.csv")
    p25 = p[p.year == 2025]
    rev = p25.revenue.sum()
    gm = 1 - p25.cost_amt.sum() / rev
    units = p25.units.sum()
    rr = (p25.return_rate * p25.units).sum() / units
    sub = p25.assign(margin=1 - p25.cost_amt / p25.revenue).sort_values("revenue", ascending=False)
    f1 = go.Figure(go.Treemap(labels=list(p25.category.unique()) + list(sub.subcategory),
                              parents=[""] * p25.category.nunique() + list(sub.category),
                              values=list(p25.groupby("category").revenue.sum()[p25.category.unique()]) + list(sub.revenue),
                              branchvalues="total", texttemplate="<b>%{label}</b><br>%{percentRoot:.1%}",
                              ))
    top = s[s.year == 2025].sort_values("revenue", ascending=False).head(10)
    mx = top.revenue.max()
    rows = "".join(
        f'<tr><td>{i + 1}</td><td>{r.product_name}</td><td>{r.category}</td>'
        f'<td class="n">{inr(r.revenue)}</td><td class="n">{1 - r.cost_amt / r.revenue:.1%}</td>'
        f'<td style="width:22%"><div class="bar" style="width:{r.revenue / mx * 100:.0f}%"></div></td></tr>'
        for i, r in enumerate(top.itertuples()))
    table = (f'<table class="t"><tr><th>#</th><th>Product</th><th>Category</th><th class="n">Revenue</th>'
             f'<th class="n">Margin</th><th></th></tr>{rows}</table>')
    pos = ["top center", "bottom center", "middle right", "middle left"]
    f3 = go.Figure(go.Scatter(x=sub.revenue / 1e7, y=sub.margin * 100, mode="markers+text", text=sub.subcategory,
                              textposition=[pos[i % 4] for i in range(len(sub))], textfont=dict(size=10),
                              marker=dict(size=np.sqrt(sub.units) / 4 + 6, color=TEAL, opacity=.75,
                                          line=dict(color="white", width=1))))
    f3.update_xaxes(title_text="Revenue (₹ Cr)", title_font=dict(size=11), type="log")
    f3.update_yaxes(title_text="Gross margin %", title_font=dict(size=11))
    rrc = p25.groupby("category").apply(lambda d: (d.return_rate * d.units).sum() / d.units.sum(),
                                        include_groups=False).sort_values()
    f4 = go.Figure(go.Bar(x=rrc.index, y=rrc.values * 100, marker_color=[CORAL if v == rrc.max() else "#C8C6C4" for v in rrc],
                          text=[f"{v:.2%}" for v in rrc], textposition="outside", cliponaxis=False))
    f4.update_yaxes(visible=False, range=[0, rrc.max() * 100 * 1.3])
    elec = p25[p25.category == "Electronics"].revenue.sum() / rev
    kpis = [kpi("Revenue", inr(rev)), kpi("Units sold", f"{units:,.0f}"), kpi("Gross margin", pct(gm)),
            kpi("Return rate", f"{rr:.2%}"), kpi("SKUs sold", f"{s[s.year == 2025].product_name.nunique()}")]
    grid = (visual("Category → subcategory mix (share of revenue)", style(f1, 300))
            + visual("Top 10 products by revenue", table)
            + visual("Revenue vs margin by subcategory (bubble = units)", style(f3, 240))
            + visual("Return rate by category (all within 1.9-2.1%)", style(f4, 240)))
    return page(2, "Product Scorecard", "Mix, margin and returns · 2025", ["Year: 2025", "Category: All", "Brand: All"],
                kpis, grid, "1fr 1fr", 1,
                f"Electronics drives {elec:.0%} of revenue. Use the margin-vs-revenue view to decide where to push premium mix.")


def hr_analytics() -> str:
    d = pd.read_csv(DATA / "hr_employees.csv", parse_dates=["hire_date", "exit_date"])

    def hc(t):
        return int(((d.hire_date <= t) & (d.exit_date.isna() | (d.exit_date > t))).sum())

    s, e = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
    head, head_py = hc(e), hc(pd.Timestamp("2024-12-31"))
    exits = d[d.exit_date.between(s, e)]
    hires = d[d.hire_date.between(s, e)]
    avg_hc = (hc(s - pd.Timedelta(days=1)) + head) / 2
    attr = len(exits) / avg_hc
    vol = (exits.exit_type == "Voluntary").mean()
    active = d[d.hire_date.le(e) & (d.exit_date.isna() | d.exit_date.gt(e))]
    female = (active.gender == "Female").mean()
    tenure = ((e - active.hire_date).dt.days / 365).mean()
    months = pd.date_range("2025-01-01", periods=12, freq="MS")
    h_m = [((d.hire_date >= m) & (d.hire_date < m + pd.offsets.MonthBegin())).sum() for m in months]
    x_m = [((d.exit_date >= m) & (d.exit_date < m + pd.offsets.MonthBegin())).sum() for m in months]
    f1 = go.Figure()
    f1.add_bar(x=months.strftime("%b"), y=h_m, name="Hires", marker_color=TEAL)
    f1.add_bar(x=months.strftime("%b"), y=[-v for v in x_m], name="Exits", marker_color=CORAL)
    f1.add_scatter(x=months.strftime("%b"), y=[hc(m + pd.offsets.MonthEnd()) for m in months], name="Headcount",
                   yaxis="y2", line=dict(color=NAVY, width=3))
    f1.update_layout(barmode="relative", yaxis2=dict(overlaying="y", side="right", showgrid=False, tickformat=",d"))
    dep = []
    for name, g in d.groupby("department"):
        ex = g.exit_date.between(s, e).sum()
        base = ((g.hire_date <= e) & (g.exit_date.isna() | (g.exit_date > s))).sum()
        dep.append((name, ex / base))
    dep = pd.DataFrame(dep, columns=["dept", "rate"]).sort_values("rate")
    f2 = go.Figure(go.Bar(x=dep.rate * 100, y=dep.dept, orientation="h",
                          marker_color=[CORAL if r == dep.rate.max() else NAVY for r in dep.rate],
                          text=[f"{r:.1%}" for r in dep.rate], textposition="outside", cliponaxis=False))
    f2.update_xaxes(visible=False, range=[0, dep.rate.max() * 130])
    drv = []
    base_set = d[(d.hire_date <= e) & (d.exit_date.isna() | (d.exit_date > s))]
    for lab, mask in [("Overtime", base_set.overtime), ("No overtime", ~base_set.overtime),
                      ("Rating 1-2", base_set.rating <= 2), ("Rating 3-5", base_set.rating >= 3),
                      ("Grade L1", base_set.grade == "L1"), ("Grades L4-L5", base_set.grade.isin(["L4", "L5"])),
                      ("Contract", base_set.employment_type == "Contract"), ("Permanent", base_set.employment_type == "Permanent")]:
        g = base_set[mask]
        drv.append((lab, g.exit_date.between(s, e).mean()))
    drv = pd.DataFrame(drv, columns=["driver", "rate"])
    f3 = go.Figure(go.Bar(x=drv.driver, y=drv.rate * 100,
                          marker_color=[CORAL, "#C8C6C4"] * 4, text=[f"{r:.0%}" for r in drv.rate],
                          textposition="outside", cliponaxis=False))
    f3.update_yaxes(visible=False, range=[0, drv.rate.max() * 130])
    rsn = exits.exit_reason.value_counts()
    f4 = go.Figure(go.Pie(labels=rsn.index, values=rsn.values, hole=.6, sort=True,
                          marker=dict(colors=[NAVY, TEAL, AMBER, CORAL, VIOLET]), textinfo="percent", textfont=dict(size=11)))
    f4.update_layout(showlegend=True, legend=dict(orientation="v", x=1, y=.5, font=dict(size=10)))
    kpis = [kpi("Headcount", f"{head:,}", f"{head - head_py:+,} vs Dec-24", head > head_py),
            kpi("Hires 2025", f"{len(hires):,}"), kpi("Exits 2025", f"{len(exits):,}", f"{vol:.0%} voluntary", None),
            kpi("Attrition rate", pct(attr), "exits / avg headcount", None),
            kpi("Women in workforce", pct(female), f"avg tenure {tenure:.1f} yrs", None)]
    ot = drv.set_index("driver").rate
    grid = (visual("Hires, exits and headcount by month · 2025", style(f1, 300, True), "grid-column:span 2")
            + visual("Attrition rate by department", style(f2, 300))
            + visual("Attrition drivers (exit rate by group)", style(f3, 250), "grid-column:span 2")
            + visual("Exit reasons", style(f4, 250, True)))
    return page(3, "HR Analytics: Headcount & Attrition", "Workforce movement and attrition drivers · 2025",
                ["Year: 2025", "Department: All", "Location: All", "Grade: All"], kpis, grid, "1.2fr 1.2fr 1fr", 2,
                f"Employees on overtime leave at {ot['Overtime']:.0%} vs {ot['No overtime']:.0%}. Workload balancing is the first retention lever.")


def supply_chain() -> str:
    sc = pd.read_csv(DATA / "supplier_scorecard.csv")
    om = pd.read_csv(DATA / "otif_monthly.csv")
    lt = pd.read_csv(DATA / "lead_times.csv")
    sp = pd.read_csv(DATA / "stock_position.csv")
    w = sc.lines
    otif, ont, inf = (sc.otif * w).sum() / w.sum(), (sc.on_time * w).sum() / w.sum(), (sc.in_full * w).sum() / w.sum()
    om["m"] = pd.to_datetime(om.ym.astype(str), format="%Y%m")
    f1 = go.Figure()
    for col, name, color in [("otif", "OTIF", NAVY), ("on_time", "On-time", TEAL), ("in_full", "In-full", AMBER)]:
        f1.add_scatter(x=om.m, y=om[col] * 100, name=name, line=dict(color=color, width=3 if col == "otif" else 2))
    f1.add_hline(y=85, line_dash="dot", line_color=CORAL, annotation_text="Target 85%", annotation_font_size=10)
    f1.update_yaxes(ticksuffix="%", range=[50, 100])
    worst = sc.sort_values("otif").head(8)
    rows = "".join(f'<tr><td>{r.supplier_code}</td><td>{r.country}</td><td class="n">{r.lines}</td>'
                   f'<td class="n" style="color:{"#C50F1F" if r.otif < .6 else INK};font-weight:600">{r.otif:.1%}</td>'
                   f'<td class="n">{r.on_time:.0%}</td><td class="n">{r.in_full:.0%}</td><td class="n">{r.lead_days:.0f} d</td></tr>'
                   for r in worst.itertuples())
    table = (f'<table class="t"><tr><th>Supplier</th><th>Country</th><th class="n">Lines</th><th class="n">OTIF</th>'
             f'<th class="n">On-time</th><th class="n">In-full</th><th class="n">Lead</th></tr>{rows}</table>')
    f3 = go.Figure(go.Histogram(x=lt.lead_time_days, nbinsx=30, marker_color=TEAL))
    f3.update_xaxes(title_text="Days from order to first receipt", title_font=dict(size=11))
    stk = sp.pivot_table(index="warehouse_name", columns="category", values="closing_value", aggfunc="sum").fillna(0)
    stk = stk.loc[stk.sum(axis=1).sort_values().index]
    f4 = go.Figure()
    for i, c in enumerate(stk.columns):
        f4.add_bar(y=stk.index, x=stk[c] / 1e7, name=c, orientation="h", marker_color=[NAVY, TEAL, AMBER, CORAL][i % 4])
    f4.update_layout(barmode="stack", legend=dict(y=1.2))
    f4.update_xaxes(ticksuffix=" Cr")
    kpis = [kpi("Supplier OTIF", pct(otif), "target 85%", otif >= .85), kpi("On-time", pct(ont)),
            kpi("In-full", pct(inf)), kpi("Median lead time", f"{lt.lead_time_days.median():.0f} days"),
            kpi("Closing stock value", inr(sp.closing_value.sum()), None, None, "5 DCs · latest month")]
    grid = (visual("OTIF, on-time and in-full by order month", style(f1, 290, True), "grid-column:span 2")
            + visual("Lowest-OTIF suppliers (call list)", table)
            + visual("Lead-time distribution", style(f3, 250))
            + visual("Stock value by DC and category (₹ Cr)", style(f4, 250, True).update_layout(margin=dict(t=36)), "grid-column:span 2"))
    n_bad = (sc.otif < .5).sum()
    return page(4, "Supply Chain & Inventory", "Supplier delivery performance and stock position · 2024-2025",
                ["Period: 2024-25", "DC: All", "Supplier: All", "Category: All"], kpis, grid, "1.1fr 1.1fr 1.2fr", 3,
                f"On-time ({ont:.0%}) is the gap, not in-full ({inf:.0%}). {n_bad} suppliers below 50% OTIF: fix promised dates first.")


def customer_retention() -> str:
    ca = json.loads((DATA / "customer_analytics.json").read_text())
    coh = pd.read_csv(DATA / "cohort_retention.csv", index_col=0)
    rfm = pd.read_csv(DATA / "rfm_segments.csv").set_index("segment")
    z = coh.values
    f1 = go.Figure(go.Heatmap(z=z, x=[f"M{c}" for c in coh.columns], y=coh.index,
                              colorscale=[[0, "#F3F2F1"], [.5, SKY], [1, NAVY]], zmin=0, zmax=100,
                              text=np.where(np.isnan(z), "", np.round(z).astype("Int64").astype(str)) if False else
                              [[("" if np.isnan(v) else f"{v:.0f}") for v in row] for row in z],
                              texttemplate="%{text}", textfont=dict(size=10), showscale=False))
    f1.update_yaxes(autorange="reversed")
    order = ["Champions", "Promising", "Needs attention", "At risk", "Hibernating"]
    r = rfm.loc[order]
    f2 = go.Figure()
    f2.add_bar(x=r.index, y=r.customers, name="Customers", marker_color="#BFD4EA")
    f2.add_scatter(x=r.index, y=r.churn_rate * 100, name="Churn % (next 6 m)", yaxis="y2", mode="lines+markers+text",
                   text=[f"{v:.0%}" for v in r.churn_rate], textposition="top center", textfont=dict(color=INK, size=12), line=dict(color=CORAL, width=3))
    f2.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%", range=[0, 100], dtick=20))
    drivers = pd.DataFrame(ca["top_drivers"], columns=["feature", "impact"]).iloc[::-1]
    labels = {"recency_days": "Days since last order", "avg_discount": "Avg discount taken",
              "orders_last_90d": "Orders in last 90 days", "orders_per_month": "Orders per month",
              "avg_order_value": "Avg order value"}
    f3 = go.Figure(go.Bar(x=drivers.impact, y=[labels.get(f, f) for f in drivers.feature], orientation="h",
                          marker_color=VIOLET, text=[f"{v:.2f}" for v in drivers.impact], textposition="outside",
                          cliponaxis=False))
    f3.update_xaxes(visible=False, range=[0, drivers.impact.max() * 1.25])
    gb = ca["gradient_boosting"]
    at_risk_rev = rfm.loc["At risk", "revenue"]
    kpis = [kpi("Active customers", f"{ca['n_customers']:,}", None, None, "bought in last 12 months"),
            kpi("Churn rate (6 m)", f"{ca['churn_rate_pct']:.1f}%", None, None, "snapshot 30-Jun-2025"),
            kpi("Month-3 retention", f"{np.mean(list(ca['month3_retention_pct'].values())):.0f}%", None, None, "avg of cohorts"),
            kpi("Model ROC-AUC", f"{gb['roc_auc']:.2f}", f"top-20% lift {gb['top20_lift']:.1f}×", True),
            kpi("'At risk' lifetime value", inr(at_risk_rev), None, None, f"{int(rfm.loc['At risk','customers'])} customers")]
    grid = (visual("Retention by first-purchase quarter (% still buying)", style(f1, 300), "grid-column:span 2")
            + visual("What drives churn (mean |SHAP|)", style(f3, 300))
            + visual("RFM segments: size and churn in the next 6 months", style(f2, 250, True), "grid-column:span 3"))
    return page(5, "Customer Retention & Churn Risk", "Cohorts, RFM and churn model · snapshot 30-Jun-2025",
                ["Snapshot: Jun-2025", "Segment: All", "Country: All"], kpis, grid, "1.1fr 1.1fr 1fr", 4,
                "'At risk' customers still hold high lifetime value. Target them with service offers, not deeper discounts (discount is a churn driver).")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    import plotly

    js = (Path(plotly.__file__).parent / "package_data" / "plotly.min.js").read_text()
    pages = {"01-executive-sales-overview": exec_sales(), "02-product-scorecard": product_scorecard(),
             "03-hr-analytics": hr_analytics(), "04-supply-chain-inventory": supply_chain(),
             "05-customer-retention-churn": customer_retention()}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1.25)
        for name, body in pages.items():
            html = f"<html><head><meta charset='utf-8'><style>{CSS}</style><script>{js}</script></head><body>{body}</body></html>"
            (ROOT / "design" / ".render.html").write_text(html, encoding="utf-8")
            pg.goto((ROOT / "design" / ".render.html").as_uri())
            pg.wait_for_timeout(600)
            pg.screenshot(path=str(OUT / f"{name}.png"), clip=dict(x=0, y=0, width=1600, height=900))
            print("rendered", name)
        b.close()
    (ROOT / "design" / ".render.html").unlink()


if __name__ == "__main__":
    main()
