"""Ábrák a dolgozathoz — minden érték a 654 futás értékeléséből származik."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / 'results' / 'figures-thesis'
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'figure.dpi':200,
                     'axes.grid':True,'grid.alpha':.25,'axes.spines.top':False,
                     'axes.spines.right':False,'axes.axisbelow':True})
NAVY='#1d2b45'; ACC='#c0392b'
ARM={'A':'#888888','B':'#2b7bba','C':'#2ca25f','D':'#e08214','E':'#c0392b'}
NAME={'A':'A\nsegítség nélkül','B':'B\nkérdező','C':'C\nteljes spec.','D':'D\nterv-javítás','E':'E\nfeltevés-korr.'}

# ---------------------------------------------------------------- 1. ábra
fig, ax = plt.subplots(figsize=(9.2, 4.4))
ax.set_xlim(0,10); ax.set_ylim(0,5); ax.axis('off')
boxes = [(0.3,3.2,2.0,1.1,'Rövid\nfeladatleírás','#eef2f7'),
         (3.0,3.2,2.0,1.1,'Prompt-\nstratégia','#eef2f7'),
         (5.7,3.2,2.0,1.1,'Modell\nválasza','#eef2f7'),
         (8.2,3.2,1.5,1.1,'162 rejtett\nelvárás','#dff0e4')]
for x,y,w,h,t,c in boxes:
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06',fc=c,ec='#c9d4e2',lw=1))
    ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=8.5,color=NAVY)
for x0,x1 in [(2.3,3.0),(5.0,5.7),(7.7,8.2)]:
    ax.add_patch(FancyArrowPatch((x0,3.75),(x1,3.75),arrowstyle='-|>',mutation_scale=13,lw=1.2,color='#4a5b78'))
arms=[('A','nincs beavatkozás'),('B','kérdezés'),('C','teljes specifikáció'),
      ('D','terv javítása'),('E','feltevések korrekciója')]
for i,(a,d) in enumerate(arms):
    y=2.35-i*0.42
    ax.add_patch(plt.Rectangle((3.05,y-0.13),0.34,0.26,fc=ARM[a],ec='none'))
    ax.text(3.12,y, a, ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    ax.text(3.5,y,d, ha='left', va='center', fontsize=8, color='#1a1a1a')
ax.text(3.0,2.62,'Öt kísérleti kar',fontsize=8.5,color=NAVY,fontweight='bold')
ax.text(8.95,2.75,'Értékelés:\nteljesült /\nnem teljesült',ha='center',va='center',fontsize=7.5,color='#4a5b78')
ax.set_title('1. ábra: A kutatás elvi felépítése', fontweight='bold', fontsize=10.5, loc='left', color=NAVY)
ax.text(0.3,0.15,'Forrás: saját szerkesztés (2026).',fontsize=7,color='#4a5b78')
fig.tight_layout(); fig.savefig(OUT/'abra1_felepites.png',bbox_inches='tight'); plt.close(fig)

# ---------------------------------------------------------------- 2. ábra
fig, ax = plt.subplots(figsize=(7.6,4.2))
vals=[71.06,74.64,83.74,76.51,76.27]
ci=[(68.9,73.1),(72.5,76.6),(81.9,85.4),(74.5,78.5),(74.1,78.3)]
bars=ax.bar(range(5),vals,0.58,color=[ARM[a] for a in 'ABCDE'],
            yerr=[[v-c[0] for v,c in zip(vals,ci)],[c[1]-v for v,c in zip(vals,ci)]],
            capsize=5,error_kw={'lw':1,'ecolor':'#4a5b78'})
ax.bar_label(bars,fmt='%.1f%%',fontsize=8.5,padding=3)
ax.axhline(83.74,color='#2ca25f',ls='--',lw=1.1)
ax.text(4.42,84.5,'felső korlát (C)',color='#2ca25f',fontsize=7.5,ha='right')
ax.axhline(71.06,color='#888888',ls=':',lw=1)
ax.set_xticks(range(5)); ax.set_xticklabels([NAME[a] for a in 'ABCDE'],fontsize=8)
ax.set_ylabel('Teljesült elvárások aránya (%)'); ax.set_ylim(60,95)
ax.set_title('2. ábra: A válaszminőség alakulása karonként',fontweight='bold',fontsize=10.5,loc='left',color=NAVY)
fig.text(0.012,0.008,'Forrás: saját számítás, 654 futás (2026). Hibasáv: 95%-os konfidenciaintervallum.',
         fontsize=6.8,color='#4a5b78')
fig.tight_layout(rect=[0,0.04,1,1]); fig.savefig(OUT/'abra2_karok.png',bbox_inches='tight'); plt.close(fig)

# ---------------------------------------------------------------- 3. ábra
fig, ax = plt.subplots(figsize=(8.6,4.4))
groups=['Formátum\n(T7–T9)','Hamis premissza\n(T4–T5)','Adatintegritás\n(T6)','Kódoló/ágens\n(T1–T3)','Valós ágens\n(T11–T13)']
data={'A':[75.3,87.7,60.6,58.7,78.4],'B':[79.4,83.7,59.1,72.4,72.1],
      'C':[97.7,93.5,72.9,73.3,83.0],'D':[79.2,83.0,66.0,76.6,72.7],
      'E':[81.5,81.5,60.2,76.5,72.2]}
x=range(len(groups))
for k,a in enumerate('ABCDE'):
    ax.bar([i+(k-2)*0.16 for i in x],data[a],0.16,label=a,color=ARM[a])
ax.set_xticks(list(x)); ax.set_xticklabels(groups,fontsize=7.5)
ax.set_ylabel('Teljesült elvárások aránya (%)'); ax.set_ylim(50,105)
ax.legend(title='Kar',frameon=False,fontsize=7.5,ncol=5,loc='upper center',bbox_to_anchor=(0.5,1.0))
ax.set_title('3. ábra: A prompt típusa és a feladat jellege közötti kölcsönhatás',
             fontweight='bold',fontsize=10.5,loc='left',color=NAVY,pad=16)
ax.text(0,-0.20,'Forrás: saját számítás, 654 futás (2026).',transform=ax.transAxes,fontsize=6.8,color='#4a5b78')
fig.tight_layout(); fig.savefig(OUT/'abra3_kolcsonhatas.png',bbox_inches='tight'); plt.close(fig)

# ---------------------------------------------------------------- 4. ábra
fig, axes = plt.subplots(1,2,figsize=(9.4,4.5))
ax=axes[0]
arms='ABCDE'; t5=[66.7,33.3,100.0,33.3,8.3]
b=ax.bar(range(5),t5,0.58,color=[ARM[a] for a in arms])
ax.bar_label(b,fmt='%.1f%%',fontsize=8,padding=2)
ax.set_xticks(range(5)); ax.set_xticklabels(list(arms),fontsize=9)
ax.set_ylabel('Korrekció aránya (%)'); ax.set_ylim(0,115)
ax.set_title('T5 — nem létező cikk\n(együttes minta)',fontsize=8.5,color=NAVY)
ax=axes[1]
models=['deepseek-v4.1-flash','glm-5.3-flash','gpt-6-luna','minimax-m3','muse-spark-1.3','qwen3.7-plus']
short=['DeepSeek','GLM','GPT-6','MiniMax','Muse','Qwen']
mtx={'A':[100,100,0,0,100,100],'B':[50,100,0,0,50,0],
     'C':[100,100,100,100,100,100],'D':[100,100,0,0,0,0],'E':[0,50,0,0,0,0]}
x=range(len(models))
for k,a in enumerate('ABCDE'):
    ax.bar([i+(k-2)*0.16 for i in x],mtx[a],0.16,label=a,color=ARM[a])
ax.set_xticks(list(x)); ax.set_xticklabels(short,fontsize=7.5,rotation=20,ha='right')
ax.set_ylabel('Korrekció aránya (%)'); ax.set_ylim(0,115)
ax.set_title('T5 — modellszintű bontás',fontsize=8.5,color=NAVY)
h,l=ax.get_legend_handles_labels()
fig.legend(h,l,ncol=5,frameon=False,fontsize=7.5,loc='upper center',
           bbox_to_anchor=(0.5,0.955),handlelength=1.1,columnspacing=1.4)
fig.suptitle('4. ábra: A hamis premissza hatása a modell viselkedésére',
             fontweight='bold',fontsize=10.5,x=0.012,ha='left',color=NAVY,y=0.985)
fig.text(0.012,0.008,'Forrás: saját számítás, a T5 feladat W1 elvárásának értékelése (2026).',
         fontsize=6.8,color='#4a5b78')
fig.tight_layout(rect=[0,0.035,1,0.90]); fig.savefig(OUT/'abra4_hamis_premissza.png',bbox_inches='tight'); plt.close(fig)

print("ábrák:")
for f in sorted(OUT.glob('*.png')):
    print(f"   {f.name}  {f.stat().st_size//1024} KB")
