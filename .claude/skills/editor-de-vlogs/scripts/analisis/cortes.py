import re,sys,numpy as np
f=sys.argv[1]; t=[];s=[]
cur=None
for line in open(f):
    m=re.search(r'pts_time:([\d.]+)',line)
    if m: cur=float(m.group(1)); continue
    m=re.search(r'scd.score=([\d.]+)',line)
    if m: t.append(cur); s.append(float(m.group(1)))
t=np.array(t); s=np.array(s)
print("p50,p90,p99,p99.9 score:",np.percentile(s,[50,90,99,99.9]).round(2))
for th in (3,5,8):
    # local peaks above th, min 0.3s apart
    idx=[i for i in range(1,len(s)-1) if s[i]>=th and s[i]>=s[i-1] and s[i]>=s[i+1]]
    cuts=[];
    for i in idx:
        if not cuts or t[i]-cuts[-1]>0.3: cuts.append(t[i])
    cuts=np.array(cuts); d=np.diff(np.r_[0,cuts,t[-1]])
    print(f"th={th}: cortes={len(cuts)} plano_medio={d.mean():.2f}s mediana={np.median(d):.2f}s")
    np.save(f.replace('_scdet.txt',f'_cuts{th}.npy'),cuts)
