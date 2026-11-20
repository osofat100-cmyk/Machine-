#!/usr/bin/env python3
"""Graph the 1-120 minute re-pick results from data/machine_speed.csv (run machine_speed.py first)."""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
d=pd.read_csv("data/machine_speed.csv").set_index("repick_every_minutes")["final_$"].loc[1:120]
surface, ink, ink2, muted, gridc, blue = "#fcfcfb","#0b0b0b","#52514e","#898781","#e1e0d9","#2a78d6"
plt.rcParams.update({"font.size":12,"text.color":ink,"axes.labelcolor":ink2,"xtick.color":muted,"ytick.color":muted,"axes.edgecolor":"#c3c2b7"})
fig,ax=plt.subplots(figsize=(12,6),facecolor=surface); ax.set_facecolor(surface)
ax.axvspan(19.5,39.5,color="#cde2fb",zorder=0)
ax.text(29.5,5050,"safest stretch: every 20-39 min\n20 in a row, all $4,734",ha="center",va="bottom",fontsize=11,color=ink)
ax.plot(d.index,d.values,color=blue,lw=1,alpha=0.5,zorder=2)
ax.plot(d.index,d.values,"o",ms=5,color=blue,mec=surface,mew=0.8,zorder=3)
ax.axhline(2830,color=ink2,lw=1.4,ls=(0,(5,3)))
ax.text(120,2830,"just holding $2,830 ",ha="right",va="bottom",fontsize=10.5,color=ink2)
ax.plot([30],[d[30]],"o",ms=11,color="#eb6834",mec=surface,mew=2,zorder=4)
ax.annotate("every 30 min: $4,734",(30,d[30]),xytext=(0,-26),textcoords="offset points",ha="center",fontsize=11,color=ink)
ax.set_xlim(0,121); ax.set_ylim(2500,5500)
ax.set_xticks([1,10,20,30,40,50,60,70,80,90,100,110,120])
ax.set_xlabel("how often the machine re-picks its buy/sell % (minutes)")
ax.set_ylabel("money on Nov 20 ($)")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v,_:f"${v:,.0f}"))
ax.grid(axis="y",color=gridc,lw=0.8)
for s in ("top","right"): ax.spines[s].set_visible(False)
ax.set_title("Re-picking every 1 to 120 minutes: each dot is one machine (Jun 25 - Nov 20, $1,000 start)",loc="left",fontsize=12.5,pad=10)
fig.savefig("machine_1to120.png",dpi=110,facecolor=surface,bbox_inches="tight"); print("ok")
