import sys,numpy as np,librosa
d=sys.argv[1]
v,sr=librosa.load(d+"/vocals.wav",sr=22050); m,_=librosa.load(d+"/no_vocals.wav",sr=22050)
hop=sr//2
db=lambda x: 20*np.log10(np.sqrt(np.mean(x**2))+1e-9)
V=np.array([db(v[i:i+hop]) for i in range(0,len(v)-hop,hop)]); M=np.array([db(m[i:i+hop]) for i in range(0,len(m)-hop,hop)])
voz=V>-35
print("seg a seg (voz/musica dB):"," ".join(f"{i/2:.0f}s:{a:.0f}/{b:.0f}" for i,(a,b) in enumerate(zip(V,M)) if i%2==0))
print(f"musica con voz: {np.median(M[voz]):.1f} dB | musica sin voz: {np.median(M[~voz]):.1f} dB | voz: {np.median(V[voz]):.1f} dB")
print(f"ducking ~ {np.median(M[~voz])-np.median(M[voz]):.1f} dB | voz por encima de musica ~ {np.median(V[voz])-np.median(M[voz]):.1f} dB")
