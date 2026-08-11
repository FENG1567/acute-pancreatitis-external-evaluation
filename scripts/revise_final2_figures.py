#!/usr/bin/env python3
"""Rebuild Final-2 publication figures from aggregate tables and frozen SOT only.

No patient-level or controlled artifact is read. All plotted model estimates
are selected by result_id from the frozen source-of-truth registry.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd


PKG = Path(__file__).resolve().parents[1]
SOT_PATH = PKG / "final" / "source_of_truth_metrics.csv"
SOURCE_DATA = PKG / "source_data"
MAIN_FIGURES = PKG / "figures"
SUPPLEMENTARY_FIGURES = PKG / "supplementary" / "figures"

COL = {"A": "#4477AA", "B": "#CC6677", "primary": "#228833",
       "sensitive": "#CCBB44", "internal": "#6F7782", "neutral": "#6F7782",
       "light": "#EDF1F5", "dark": "#222222"}
MARK = {"MIMIC_keyed_OOF": "o", "eICU_primary_locked_359": "s",
        "eICU_sensitive_landmark_1106": "^"}
LABEL = {"MIMIC_keyed_OOF": "MIMIC corrected keyed OOF\nn=347; events=31",
         "eICU_primary_locked_359": "eICU primary locked\nn=359; events=21",
         "eICU_sensitive_landmark_1106": "eICU sensitivity\nn=1,106; events=96"}

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "font.size": 7, "axes.titlesize": 8, "axes.labelsize": 7,
    "xtick.labelsize": 6.3, "ytick.labelsize": 6.3, "legend.fontsize": 6.2,
    "axes.spines.right": False, "axes.spines.top": False, "axes.linewidth": 0.75,
    "axes.unicode_minus": False, "svg.fonttype": "none", "pdf.fonttype": 42,
    "savefig.facecolor": "white", "svg.hashsalt": "final2-figures-v1",
})


def ensure_dirs() -> None:
    for p in (MAIN_FIGURES, SUPPLEMENTARY_FIGURES):
        p.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if "controlled_artifacts" in str(path):
        raise RuntimeError("Controlled patient-level inputs are prohibited")
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


_SOT: pd.DataFrame | None = None
def sot() -> pd.DataFrame:
    global _SOT
    if _SOT is None:
        _SOT = read_csv(SOT_PATH)
        if not _SOT.result_id.is_unique:
            raise RuntimeError("SOT result_id is not unique")
    return _SOT.copy()


def write_source(df: pd.DataFrame, name: str) -> None:
    """Assert that each declared aggregate source is already packaged.

    The public repository treats ``source_data/`` as an immutable input. This
    preserves the result-id/SOT constraints while ensuring that figure builds
    write only to repository-local figure directories.
    """
    del df
    read_csv(SOURCE_DATA / name)


def save_pub(fig: plt.Figure, stem: str, supplementary: bool = False) -> None:
    out = SUPPLEMENTARY_FIGURES if supplementary else MAIN_FIGURES
    fixed = dt.datetime(2026, 8, 10, tzinfo=dt.timezone.utc)
    # The public script writes PDF/PNG previews only inside this repository.
    fig.savefig(out / f"{stem}.pdf", bbox_inches="tight",
                metadata={"CreationDate": fixed, "ModDate": fixed, "Creator": "matplotlib"})
    fig.savefig(out / f"{stem}.png", dpi=300, bbox_inches="tight", metadata={"Date": "2026-08-10"})
    plt.close(fig)


def panel(ax, label: str) -> None:
    ax.text(-0.13, 1.08, label, transform=ax.transAxes, fontweight="bold", fontsize=8, va="top")


def parse_ci(text: object) -> tuple[float, float]:
    vals = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", str(text))
    return (float(vals[0]), float(vals[1])) if len(vals) >= 2 else (np.nan, np.nan)


def rows_for(cohorts: list[str], metrics: list[str]) -> pd.DataFrame:
    d = sot()
    x = d[d.cohort.isin(cohorts) & d.model.isin(["Model A", "Model B"]) & d.metric_name.isin(metrics)].copy()
    x = x[~x.metric_name.str.contains("hospital_cluster", case=False, na=False)]
    x = x[~x.result_id.str.contains("HOSPITAL_CLUSTER", case=False, na=False)]
    if x.duplicated(["cohort", "model", "metric_name"]).any():
        raise RuntimeError("Ambiguous primary metric rows")
    return x


def forest(ax, frame: pd.DataFrame, metric: str, xlim: tuple[float, float], title: str) -> None:
    cohorts = ["MIMIC_keyed_OOF", "eICU_primary_locked_359", "eICU_sensitive_landmark_1106"]
    ypos, labels = [], []
    y = 5
    for cohort in cohorts:
        for model in ("Model A", "Model B"):
            r = frame[(frame.cohort == cohort) & (frame.model == model) & (frame.metric_name == metric)].iloc[0]
            short = model[-1]
            ax.errorbar(float(r.estimate), y,
                        xerr=[[float(r.estimate)-float(r.ci_low)], [float(r.ci_high)-float(r.estimate)]],
                        fmt=MARK[cohort], color=COL[short], mfc="white" if cohort == "eICU_sensitive_landmark_1106" else COL[short],
                        mec=COL[short], ms=4.2, capsize=2, lw=1.0)
            ypos.append(y); labels.append(f"{LABEL[cohort]} | {short}"); y -= 1
        if y >= 0:
            ax.axhline(y + 0.5, color="#E8E8E8", lw=0.6)
    ax.set_yticks(ypos, labels)
    ax.set_xlim(*xlim); ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="x", color="#ECECEC", lw=0.5)


def fig1() -> None:
    d = read_csv(SOURCE_DATA / "fig1_design_and_cohort_flow.csv")
    strict_sot = sot().loc[sot().result_id.eq("R8_PHENOTYPE_STRICT_TIME_WINDOW_PHENOTYPE")]
    if len(strict_sot) != 1 or str(strict_sot.iloc[0].result_role) != "NE/not executable":
        raise RuntimeError("Strict phenotype must occur once with role NE/not executable")
    strict_metric = strict_sot.iloc[0]
    # Table 1 contains executable cohorts. Add the single registered strict
    # phenotype row explicitly, while preventing duplicate display on reruns.
    d = d.loc[~d.cohort_or_role.astype(str).str.contains("strict", case=False, na=False)].copy()
    strict_row = pd.DataFrame([{
        "database": "eICU",
        "cohort_or_role": "strict time-window phenotype",
        "total_n": "NE",
        "landmark_n": "NE",
        "events": "NE",
        "result_role": "NE/not executable",
        "interpretation_limit": str(strict_metric.interpretation),
        "result_ids": str(strict_metric.result_id),
    }])
    d = pd.concat([d, strict_row], ignore_index=True)
    if d.cohort_or_role.astype(str).str.contains("strict", case=False, na=False).sum() != 1:
        raise RuntimeError("Figure 1 source must contain exactly one strict phenotype row")
    write_source(d, "fig1_design_and_cohort_flow.csv")
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 5.25), gridspec_kw={"height_ratios": [2.55, 1.0]})
    ax = axes[0]; ax.axis("off"); panel(ax, "a")
    flow_specs = [
        ("MIMIC-IV", "aligned primary internal development", "Aligned primary development", COL["A"], 0.78, False),
        ("eICU", "aligned diagnosis-priority-only primary locked", "Aligned primary locked", COL["B"], 0.55, False),
        ("eICU", "broad database-specific primary", "Broad database-specific", "#AA4499", 0.32, False),
        ("eICU", "sensitive any-AP", "Sensitive any-AP", "#999933", 0.09, False),
        ("eICU", "strict time-window phenotype", "Strict time-window phenotype", COL["neutral"], -0.14, True),
    ]
    for db, cohort_name, label, color, y, strict in flow_specs:
        match = d.loc[(d.database == db) & (d.cohort_or_role == cohort_name)]
        if len(match) != 1:
            raise RuntimeError(f"Figure 1 cohort row not unique: {db}/{cohort_name}")
        source_row = match.iloc[0]
        total, lm, events = source_row.total_n, source_row.landmark_n, source_row.events
        xs = [0.04, 0.38, 0.72]
        texts = ([("Strict time-window phenotype", "NE/not executable"), ("Reached 24-h landmark", lm), ("In-hospital deaths", events)]
                 if strict else [(f"{label}\nBefore landmark", total), ("Reached 24-h landmark", lm), ("In-hospital deaths", events)])
        for i, (txt, n) in enumerate(texts):
            box = FancyBboxPatch((xs[i], y), 0.23, 0.125, boxstyle="round,pad=0.012", ec=color, fc="#F7F9FC", lw=1.0, linestyle="--" if strict else "-")
            ax.add_patch(box); ax.text(xs[i]+0.115, y+0.078, txt, ha="center", va="center", fontsize=5.9)
            if strict and i == 0:
                n_label = str(n)
            else:
                n_text = "NE" if pd.isna(n) or str(n).upper() == "NE" else f"{int(float(n)):,}"
                n_label = f"n={n_text}"
            ax.text(xs[i]+0.115, y+0.022, n_label, ha="center", va="center", fontweight="bold", color=color)
            if i < 2 and not strict:
                ax.add_patch(FancyArrowPatch((xs[i]+0.235, y+0.062), (xs[i+1]-0.008, y+0.062), arrowstyle="-|>", mutation_scale=8, color=COL["neutral"], lw=0.8))
        ax.text(0.005, y+0.062, db, ha="right", va="center", fontweight="bold", color=color)
    ax.set_xlim(-0.08, 1); ax.set_ylim(-0.21, 0.98)
    ax.set_title("Cohort definitions and the 24-h landmark are explicit", loc="left", fontweight="bold", pad=10)

    ax = axes[1]; ax.axis("off"); panel(ax, "b")
    support = d[d.database.isin(["NWICU", "SICdb", "HiRID"])]
    for i, (_, r) in enumerate(support.iterrows()):
        x = 0.02 + i*0.33
        ax.add_patch(FancyBboxPatch((x, 0.23), 0.29, 0.52, boxstyle="round,pad=0.015", ec=COL["neutral"], fc="#F3F3F3", lw=0.8))
        landmark = "NE" if pd.isna(r.landmark_n) or str(r.landmark_n) == "NE" else f"{int(float(r.landmark_n)):,} at 24 h"
        events = "events=NA" if str(r.events) == "NE" else f"events={int(float(r.events))}"
        ax.text(x+0.145, 0.64, f"{r.database}: n={int(float(r.total_n)):,}", ha="center", fontweight="bold")
        ax.text(x+0.145, 0.50, f"{landmark}; {events}", ha="center", fontsize=6.1)
        ax.text(x+0.145, 0.35, str(r.cohort_or_role), ha="center", fontsize=6.0, wrap=True)
    ax.text(0.02, 0.90, "Supporting databases retain prespecified non-primary roles", fontweight="bold", fontsize=8)
    fig.suptitle("Frozen cohort construction and honest database roles", fontsize=10, fontweight="bold", y=0.995)
    fig.text(0.5, 0.01, "Counts are aggregate first eligible ICU stays/patients; phenotype sensitivities do not replace the locked primary cohort.", ha="center", fontsize=6, color=COL["neutral"])
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    save_pub(fig, "fig1_design_and_cohort_flow")


def fig2() -> None:
    d = read_csv(SOURCE_DATA / "fig2_measurement_process_shift.csv")
    # Stage-4 measurement-profile scalars are not registered in the revised R8
    # SOT. Remove stale R7 prefixes and use the audited aggregate table mapping.
    if "result_id_prefix" in d.columns:
        d=d.drop(columns=["result_id_prefix"])
    d["source_mapping"]="Aggregate audited Stage-4 measurement-profile table; no patient rows; not registered in revised R8 SOT"
    write_source(d, "fig2_measurement_process_shift.csv")
    labels = {"heart_rate":"Heart rate","map":"MAP","respiratory_rate":"Respiratory rate","spo2":"SpO2","temperature":"Temperature","wbc":"WBC","platelet":"Platelets","hematocrit":"Haematocrit","bun":"BUN","creatinine":"Creatinine","glucose":"Glucose","bilirubin":"Bilirubin","lactate":"Lactate","gcs_total":"GCS","urine_output":"Urine output"}
    order = list(labels)
    pres = d.pivot(index="variable", columns="database", values="presence_percent").reindex(order).apply(pd.to_numeric, errors="coerce")
    rate = d.pivot(index="variable", columns="database", values="median_rate_per_hour_among_observed").reindex(order).apply(pd.to_numeric, errors="coerce")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 4.6), gridspec_kw={"width_ratios":[1.15,1.05,1.25]})
    cmap = LinearSegmentedColormap.from_list("coverage", ["#F5F5F5", "#C6DBEF", COL["A"]])
    for ax, mat, title, vmax, fmt in [(axes[0], pres, "Presence in 0-24 h (%)",100,".0f"),(axes[1],np.log1p(rate),"Measurement rate among observed",np.nanmax(np.log1p(rate.to_numpy())),".2g")]:
        im=ax.imshow(mat[["MIMIC-IV","eICU"]],aspect="auto",vmin=0,vmax=vmax,cmap=cmap)
        ax.set_xticks([0,1],["MIMIC-IV","eICU"])
        ax.text(.5,-.105,"MIMIC-IV n=347; eICU n=359; events=NA",
                transform=ax.transAxes,ha="center",va="top",fontsize=5.5,color=COL["neutral"])
        ax.set_yticks(range(len(order)),[labels[v] for v in order] if ax is axes[0] else [])
        ax.set_title(title,loc="left",fontweight="bold")
        raw = pres if ax is axes[0] else rate
        for i in range(len(order)):
            for j in range(2):
                v=raw.iloc[i,j]; ax.text(j,i,"NE" if pd.isna(v) else format(v,fmt),ha="center",va="center",fontsize=5.4,color="white" if (pd.notna(v) and ((ax is axes[0] and v>65) or (ax is axes[1] and np.log1p(v)>0.65*vmax))) else COL["dark"])
        fig.colorbar(im,ax=ax,fraction=0.045,pad=0.035)
    diff=pres["eICU"]-pres["MIMIC-IV"]; y=np.arange(len(order)); axes[2].axvline(0,color=COL["dark"],lw=0.8)
    axes[2].barh(y,diff,color=COL["A"],alpha=.82); axes[2].set_yticks(y,[labels[v] for v in order]); axes[2].invert_yaxis()
    axes[2].set_xlabel("eICU - MIMIC-IV (percentage points)"); axes[2].set_title("Presence difference",loc="left",fontweight="bold"); axes[2].grid(axis="x",color="#E8E8E8",lw=.5)
    for ax,lab in zip(axes,"abc"): panel(ax,lab)
    fig.suptitle("Measurement coverage and frequency differ descriptively across databases",fontsize=10,fontweight="bold",y=.995)
    fig.text(.5,.01,"Descriptive EHR observation patterns are not evidence of clinician intent or a causal measurement-process effect; NE is not zero.",ha="center",fontsize=6,color=COL["neutral"])
    fig.tight_layout(rect=[0,.04,1,.96]); save_pub(fig,"fig2_measurement_process_shift")


def fig3() -> None:
    cohorts=["MIMIC_keyed_OOF","eICU_primary_locked_359","eICU_sensitive_landmark_1106"]
    metrics=["auroc","auprc","brier","log_loss"]; d=rows_for(cohorts,metrics)
    write_source(d,"fig3_primary_corrected_performance.csv"); write_source(d,"fig3_internal_external_performance.csv")
    specs=[("auroc","AUROC",(.68,.98)),("auprc","AUPRC",(.08,.68)),("brier","Brier score",(.03,.12)),("log_loss","Log loss",(.12,.42))]
    fig,axes=plt.subplots(2,2,figsize=(7.2,5.0))
    for ax,(m,t,xlim),lab in zip(axes.ravel(),specs,"abcd"):
        forest(ax,d,m,xlim,t); panel(ax,lab)
    fig.suptitle("Corrected internal, locked external and phenotype-sensitivity performance",fontsize=10,fontweight="bold",y=.995)
    fig.text(.5,.01,"Whiskers are patient-bootstrap 95% CIs. Corrected keyed OOF and post-audit sensitivity estimates are not blind external-degradation contrasts.",ha="center",fontsize=6,color=COL["neutral"])
    fig.tight_layout(rect=[0,.04,1,.96]); save_pub(fig,"fig3_internal_external_performance")


def fig4() -> None:
    perf=rows_for(["eICU_primary_locked_359","eICU_sensitive_landmark_1106"],["calibration_intercept","calibration_slope"])
    bins=read_csv(SOURCE_DATA/"fig4_calibration_bins.csv"); curves=read_csv(SOURCE_DATA/"fig4_logistic_calibration_curves.csv"); dist=read_csv(SOURCE_DATA/"fig4_prediction_distribution_summary.csv")
    id_map={
        "A": ("R8_EICU_PRIMARY_LOCKED_359_A_CALIBRATION_INTERCEPT", "R8_EICU_PRIMARY_LOCKED_359_A_CALIBRATION_SLOPE"),
        "B": ("R8_EICU_PRIMARY_LOCKED_359_B_CALIBRATION_INTERCEPT", "R8_EICU_PRIMARY_LOCKED_359_B_CALIBRATION_SLOPE"),
    }
    bins["intercept_result_id"]=bins["model"].map(lambda x: id_map[str(x)][0])
    bins["slope_result_id"]=bins["model"].map(lambda x: id_map[str(x)][1])
    curves["intercept_result_id"]=curves["model"].map(lambda x: id_map[str(x)][0])
    curves["slope_result_id"]=curves["model"].map(lambda x: id_map[str(x)][1])
    curves["source_mapping"]="Aggregate primary-eICU logistic calibration curve; no patient rows"
    dist["source_mapping"]="Aggregate primary-eICU prediction-distribution summary; no patient rows"
    for x,name in [(perf,"fig4_calibration_parameters.csv"),(bins,"fig4_calibration_bins.csv"),(curves,"fig4_logistic_calibration_curves.csv"),(dist,"fig4_prediction_distribution_summary.csv")]: write_source(x,name)
    fig,axes=plt.subplots(2,2,figsize=(7.2,5.0))
    for ax,metric,title,xlim,ideal,lab in [(axes[0,0],"calibration_intercept","Calibration intercept",(-2.5,-.4),0,"a"),(axes[0,1],"calibration_slope","Calibration slope",(0,.9),1,"b")]:
        y=3
        for cohort in ["eICU_primary_locked_359","eICU_sensitive_landmark_1106"]:
            for model in ["Model A","Model B"]:
                r=perf[(perf.cohort==cohort)&(perf.model==model)&(perf.metric_name==metric)].iloc[0]; short=model[-1]
                ax.errorbar(r.estimate,y,xerr=[[r.estimate-r.ci_low],[r.ci_high-r.estimate]],fmt=MARK[cohort],color=COL[short],mfc="white" if cohort.endswith("1106") else COL[short],capsize=2,ms=4)
                y-=1
        ax.axvline(ideal,color="#999999",ls="--",lw=.8); ax.set_yticks([3,2,1,0],["Primary A\nn=359/21","Primary B","Sensitivity A\nn=1,106/96","Sensitivity B"]); ax.set_xlim(*xlim); ax.set_title(title,loc="left",fontweight="bold"); ax.grid(axis="x",color="#ECECEC",lw=.5); panel(ax,lab)
    ax=axes[1,0]; ax.plot([0,.55],[0,.55],ls="--",color="#999999",lw=.8,label="Ideal")
    for short in ["A","B"]:
        c=curves[curves.model==short]; q=bins[bins.model==short]; color=COL[short]; ls="-" if short=="A" else "--"; marker="o" if short=="A" else "s"
        ax.fill_between(c.predicted,c.ci_low,c.ci_high,color=color,alpha=.13); ax.plot(c.predicted,c.calibrated_observed,color=color,ls=ls,lw=1.4,label=f"Model {short}")
        # Numerical bootstrap endpoints can differ from an exact zero by machine
        # epsilon.  Clamp display-only error lengths at zero; source values remain
        # unchanged in the exported source-data CSV.
        yerr_low=np.maximum(q.observed.to_numpy(dtype=float)-q.ci_low.to_numpy(dtype=float),0.0)
        yerr_high=np.maximum(q.ci_high.to_numpy(dtype=float)-q.observed.to_numpy(dtype=float),0.0)
        ax.errorbar(q.mean_predicted,q.observed,yerr=[yerr_low,yerr_high],fmt=marker,color=color,ms=2.8,capsize=1)
    ax.set(xlim=(0,.55),ylim=(0,.62),xlabel="Predicted mortality risk",ylabel="Observed mortality"); ax.set_title("Primary eICU logistic calibration",loc="left",fontweight="bold"); ax.legend(); ax.grid(color="#ECECEC",lw=.5); panel(ax,"c")
    ax=axes[1,1]
    for i,(_,r) in enumerate(dist.iterrows(),1):
        color=COL[str(r.model)]; ax.plot([r.p05,r.p95],[i,i],color=COL["neutral"],lw=.9); ax.add_patch(Rectangle((r.p25,i-.22),r.p75-r.p25,.44,fc=color,ec=color,alpha=.24)); ax.plot([r["median"],r["median"]],[i-.22,i+.22],color=color,lw=1.5)
    ax.set_xscale("log"); ax.set_yticks(range(1,5),[f"{r.model}: {'death' if int(r.outcome)==1 else 'survived'} (n={int(r.n)})" for _,r in dist.iterrows()]); ax.set_xlabel("Predicted risk (log scale)"); ax.set_title("Aggregate primary eICU prediction summaries",loc="left",fontweight="bold"); ax.grid(axis="x",color="#ECECEC",lw=.5); panel(ax,"d")
    fig.suptitle("Absolute-risk calibration remains uncertain and phenotype-dependent",fontsize=10,fontweight="bold",y=.995)
    fig.text(.5,.01,"Primary calibration curves and distributions use aggregate locked eICU summaries (n=359; events=21); shaded bands are 95% bootstrap CIs.",ha="center",fontsize=6,color=COL["neutral"])
    fig.tight_layout(rect=[0,.04,1,.96]); save_pub(fig,"fig4_external_calibration_and_distribution")


def fig5() -> None:
    d=sot(); cohorts=["eICU_primary_locked_359","eICU_sensitive_landmark_1106"]
    point=rows_for(cohorts,["auroc","auprc"])
    cluster=d[d.cohort.isin(cohorts)&d.model.isin(["Model A","Model B"])&d.metric_name.isin(["auroc_hospital_cluster_CI","auprc_hospital_cluster_CI"])].copy()
    paired=d[d.cohort.isin(cohorts)&d.model.eq("A minus B")&d.metric_name.isin(["paired_A_minus_B_auroc","paired_A_minus_B_auprc"])].copy()
    src=pd.concat([point.assign(display_component="patient_CI"),cluster.assign(display_component="hospital_cluster_CI"),paired.assign(display_component="paired_A_minus_B")],ignore_index=True)
    write_source(src,"fig5_phenotype_cluster_paired_robustness.csv")
    fig,axes=plt.subplots(2,2,figsize=(7.2,4.7))
    for ax,metric,title,xlim,lab in [(axes[0,0],"auroc","AUROC by phenotype and CI unit",(.72,.94),"a"),(axes[0,1],"auprc","AUPRC by phenotype and CI unit",(.12,.52),"b")]:
        y=3
        for cohort in cohorts:
            for model in ["Model A","Model B"]:
                p=point[(point.cohort==cohort)&(point.model==model)&(point.metric_name==metric)].iloc[0]
                c=cluster[(cluster.cohort==cohort)&(cluster.model==model)&(cluster.metric_name==metric+"_hospital_cluster_CI")].iloc[0]; short=model[-1]
                ax.plot([c.ci_low,c.ci_high],[y,y],color=COL[short],lw=3,alpha=.22,label="Hospital-cluster CI" if y==3 else None)
                ax.errorbar(p.estimate,y,xerr=[[p.estimate-p.ci_low],[p.ci_high-p.estimate]],fmt="o" if cohort==cohorts[0] else "^",color=COL[short],mfc=COL[short],capsize=2,ms=4,label="Patient CI" if y==3 else None)
                y-=1
        ax.set_yticks([3,2,1,0],["Primary A\n359/21","Primary B","Sensitivity A\n1,106/96","Sensitivity B"]); ax.set_xlim(*xlim); ax.set_title(title,loc="left",fontweight="bold"); ax.grid(axis="x",color="#ECECEC",lw=.5); panel(ax,lab)
        if metric=="auroc": ax.legend(loc="lower left")
    for ax,metric,title,xlim,lab in [(axes[1,0],"paired_A_minus_B_auroc","Paired A - B AUROC",(-.045,.045),"c"),(axes[1,1],"paired_A_minus_B_auprc","Paired A - B AUPRC",(-.065,.045),"d")]:
        ax.axvline(0,color="#777777",ls="--",lw=.8)
        for y,cohort in [(1,cohorts[0]),(0,cohorts[1])]:
            r=paired[(paired.cohort==cohort)&(paired.metric_name==metric)].iloc[0]; color=COL["primary"] if y==1 else COL["sensitive"]
            ax.errorbar(r.estimate,y,xerr=[[r.estimate-r.ci_low],[r.ci_high-r.estimate]],fmt="D",color=color,capsize=2,ms=4)
        ax.set_yticks([1,0],["Primary locked\n359/21","Sensitivity\n1,106/96"]); ax.set_xlim(*xlim); ax.set_title(title,loc="left",fontweight="bold"); ax.grid(axis="x",color="#ECECEC",lw=.5); panel(ax,lab)
    fig.suptitle("Phenotype and clustering sensitivity: paired A-vs-B robustness",fontsize=10,fontweight="bold",y=.995)
    fig.text(.5,.01,"Phenotype choice changes estimates; patient and hospital-cluster intervals are both shown. Paired A-vs-B differences are small and unstable.",ha="center",fontsize=6,color=COL["neutral"])
    fig.tight_layout(rect=[0,.04,1,.96]); save_pub(fig,"fig5_phenotype_cluster_paired_robustness")


def supplementary_s3() -> None:
    """Corrected keyed-OOF fold heterogeneity, isolated for fast QA reruns."""
    s=sot(); d=s[s.result_id.str.match(r"R8_MIMIC_[AB]_OUTER_FOLD_[012]_(AUROC|AUPRC|BRIER|LOG_LOSS)$")].copy()
    d["outer_fold"]=d.result_id.str.extract(r"OUTER_FOLD_(\d+)").astype(int); d["model_short"]=d.model.str[-1]
    write_source(d,"figS3_corrected_outer_fold_performance.csv")
    specs=[("outer_fold_auroc","AUROC",(.75,1)),("outer_fold_auprc","AUPRC",(.25,.75)),("outer_fold_brier","Brier score",(.035,.11)),("outer_fold_log_loss","Log loss",(.12,.36))]
    fig,axes=plt.subplots(2,2,figsize=(6.8,4.7)); xt=["Fold 0\n116/10","Fold 1\n116/11","Fold 2\n115/10"]
    for ax,(m,title,ylim),lab in zip(axes.ravel(),specs,"abcd"):
        for short,marker in [("A","o"),("B","s")]:
            g=d[(d.model_short==short)&(d.metric_name==m)].sort_values("outer_fold"); ax.plot(g.outer_fold,g.estimate,marker=marker,color=COL[short],lw=1.1,label=f"Model {short}")
        ax.set_xticks([0,1,2],xt); ax.set_ylim(*ylim); ax.set_title(title,loc="left",fontweight="bold"); ax.grid(color="#ECECEC",lw=.5); panel(ax,lab)
    axes[0,0].legend(); fig.suptitle("Corrected keyed OOF fold heterogeneity (total n=347; events=31)",fontsize=9,fontweight="bold")
    fig.text(.5,.01,"Fold labels give validation n/events. Pooled keyed OOF has been reconstructed; these panels show fold heterogeneity only.",ha="center",fontsize=6,color=COL["neutral"])
    fig.tight_layout(rect=[0,.04,1,.96]); save_pub(fig,"figS3_corrected_outer_fold_performance",True)


def supplementary() -> None:
    # S1: explicitly exploratory.
    d=read_csv(SOURCE_DATA/"figS1_exploratory_models.csv")
    # These legacy exploratory estimates were not promoted into the revised R8
    # registry.  Remove stale R7 identifiers and retain an explicit aggregate
    # source-table mapping instead of claiming false SOT registration.
    if "result_id" in d.columns:
        d=d.drop(columns=["result_id"])
    d["source_mapping"]="Aggregate Stage-7 exploratory-metrics table; no patient rows; not registered in revised R8 SOT"
    write_source(d,"figS1_exploratory_models.csv")
    metrics=["auroc","auprc","brier","log_loss","calibration_slope"]; fig,axes=plt.subplots(1,5,figsize=(7.2,2.7))
    for ax,m in zip(axes,metrics):
        g=d[d.metric_name==m]
        for y,model,color,marker in [(1,"Logistic C","#AA4499","o"),(0,"paper-guided reconstruction","#999933","s")]:
            r=g[g.model==model].iloc[0]; ax.errorbar(r.estimate,y,xerr=[[r.estimate-r.ci_low],[r.ci_high-r.estimate]],fmt=marker,color=color,capsize=2,ms=4)
        ax.set_yticks([1,0],["Model C","Paper-guided"] if ax is axes[0] else []); ax.set_title(m.replace("_","\n"),fontweight="bold"); ax.grid(axis="x",color="#ECECEC",lw=.5)
    fig.suptitle("Exploratory only: additional models in eICU (n=359; events=21)",fontsize=9,fontweight="bold"); fig.tight_layout(); save_pub(fig,"figS1_exploratory_model_metrics",True)

    # S2: supportive DCA.
    d=sot(); d=d[(d.database=="eICU")&(d.cohort=="eICU_primary_locked_359")&(d.metric_name=="decision_curve_net_benefit")&d.model.isin(["A","B","treat_all","treat_none"])].copy()
    d["threshold"]=pd.to_numeric(d.source_locator.str.extract(r"threshold=([0-9.]+)")[0],errors="coerce")
    d["net_benefit"]=pd.to_numeric(d.estimate,errors="coerce")
    d["model"]=d.model.replace({"A":"model_A","B":"model_B"})
    d["denominator"]=359; d["events"]=21
    d=d[["result_id","model","threshold","net_benefit","denominator","events","result_role"]].sort_values(["model","threshold"])
    write_source(d,"figS2_decision_curve.csv")
    fig,ax=plt.subplots(figsize=(5.8,3.6)); styles={"model_A":(COL["A"],"-"),"model_B":(COL["B"],"-."),"treat_all":("#222222","--"),"treat_none":("#888888",":")}
    for name,g in d.groupby("model"):
        color,ls=styles[name]; ax.plot(g.threshold,g.net_benefit,color=color,ls=ls,lw=1.2,label=name.replace("model_","Model ").replace("treat_","Treat "))
    ax.axhline(0,color="#AAAAAA",lw=.6); ax.set(xlabel="Risk threshold",ylabel="Net benefit",xlim=(0,.30)); ax.set_title("Supportive/exploratory DCA: eICU n=359; events=21; thresholds 0-0.30",loc="left",fontweight="bold"); ax.legend(ncol=2); ax.grid(color="#ECECEC",lw=.5); save_pub(fig,"figS2_decision_curve_A_B",True)

    supplementary_s3()


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--figure",choices=["1","2","3","4","5","supp","s3","all"],default="all"); args=parser.parse_args(); ensure_dirs()
    funcs={"1":fig1,"2":fig2,"3":fig3,"4":fig4,"5":fig5,"supp":supplementary,"s3":supplementary_s3}; todo=["1","2","3","4","5","supp"] if args.figure=="all" else [args.figure]
    for key in todo: funcs[key]()
    print(json.dumps({"status":"PASS","rendered":todo,"backend":"python/matplotlib","controlled_patient_files_read":0}))


if __name__ == "__main__":
    main()
