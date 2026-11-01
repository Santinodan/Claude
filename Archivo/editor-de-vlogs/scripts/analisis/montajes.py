import sys,json,os,numpy as np,librosa
n=sys.argv[1]; O=os.path.dirname(os.path.abspath(__file__))+"/out/"
y,sr=librosa.load(O+n+".wav",sr=22050); dur=len(y)/sr; H=512
tx=json.load(open(O+n+"_tx.json"))
sp=[]
for s in tx["segs"]:
    for a,b,_ in s["w"]:
        if sp and a-sp[-1][1]<1.0: sp[-1][1]=b
        else: sp.append([a,b])
habla=sum(b-a for a,b in sp)
# silencios entre palabras dentro del habla (ritmo de jump cut)
gaps=[]
for s in tx["segs"]:
    w=s["w"]
    for i in range(1,len(w)): gaps.append(w[i][0]-w[i-1][1])
# tramos sin voz >= 8 s
nv=[];prev=0
for a,b in sp+[[dur,dur]]:
    if a-prev>=8: nv.append((prev,a))
    prev=b
cuts=np.load(O+n+"_cuts5.npy")
env_all=librosa.onset.onset_strength(y=librosa.effects.percussive(y,margin=3.0),sr=sr,hop_length=H)
et=librosa.frames_to_time(np.arange(len(env_all)),sr=sr,hop_length=H)
rows=[]
for a,b in nv:
    i0,i1=np.searchsorted(et,[a,b]); env=env_all[i0:i1]
    if len(env)<50: continue
    tempo,bf=librosa.beat.beat_track(onset_envelope=env,sr=sr,hop_length=H)
    bts=et[i0:i1][bf]
    cs=cuts[(cuts>a+0.5)&(cuts<b-0.5)]
    if len(bts)<4: continue
    bi=np.median(np.diff(bts))
    d=np.array([np.min(np.abs(bts-c)) for c in cs]) if len(cs) else np.array([])
    # largo de plano en beats
    shot_beats=np.diff(cs)/bi if len(cs)>1 else []
    rows.append(dict(desde=f"{int(a//60)}:{int(a%60):02d}",dur=round(b-a),bpm=int(round(60/bi)),cortes=len(cs),
        en_beat=f"{int(round(100*np.mean(d<0.07)))}%" if len(d) else "-",
        azar=f"{int(round(100*min(1,0.14/bi)))}%",
        plano_en_beats=np.round(np.percentile(shot_beats,[25,50,75]),1).tolist() if len(shot_beats)>2 else None))
print(f"### {n} | idioma {tx['lang']} | habla {100*habla/dur:.0f}% del video | pausas entre palabras p50={np.median(gaps):.2f}s p95={np.percentile(gaps,95):.2f}s | pausas>0.5s: {np.mean(np.array(gaps)>0.5)*100:.1f}%")
for r in rows: print(r)
