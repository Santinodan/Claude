import sys, json, numpy as np
from PIL import Image
S='/tmp/claude-0/-home-user-lore/7d508246-2704-5e00-8a78-fcf8e8181527/scratchpad/'
sys.path.insert(0,S+'scripts'); import lutlib as L
B=dict(L.DEFAULT); B.update(dict(exposure=1, contrast=0.55, pivot=0.45, black=-0.07,
  shadow_hue=185, shadow_amt=0.030, high_hue=75, high_amt=0.030, sat=1.18,
  blue_center=240, blue_width=40, blue_shift=-35, blue_sat=1.25,
  green_center=138, green_width=25, green_shift=-8, green_sat=0.8, green_dark=0.03,
  warm_center=60, warm_width=25, warm_sat=1.12))
if len(sys.argv)>1: B.update(json.loads(sys.argv[1]))
def boost(v): return L.encode_709(L.grade(np.clip(v,0,1)**2.4, B))
if __name__=='__main__':
    a=np.asarray(Image.open(S+'work/user_frame.png').convert('RGB')).astype(float)/255; a=a[:a.shape[0]//2]
    o=boost(a)
    lab=L.lin_to_oklab(o**2.4).reshape(-1,3); Lm=lab[:,0]
    s=f'L={np.round(np.percentile(Lm,[2,50,98]),3)} C={np.hypot(lab[:,1],lab[:,2]).mean():.3f} |'
    for lo,hi in [(0,.3),(.3,.45),(.45,.6),(.6,.75),(.75,1.01)]:
        m=(Lm>=lo)&(Lm<hi); A=lab[m,1].mean(); Bb=lab[m,2].mean(); s+=f' {np.hypot(A,Bb):.3f}@{np.degrees(np.arctan2(Bb,A))%360:.0f}'
    print(s)
    k=np.asarray(Image.open(S+'work/kitchen.png').convert('RGB')).astype(float)/255
    k=np.asarray(Image.fromarray((k*255).astype(np.uint8)).resize((a.shape[1], int(k.shape[0]*a.shape[1]/k.shape[1])))).astype(float)/255
    img=np.concatenate([a,o,k],0)
    Image.fromarray((np.clip(img,0,1)*255).astype(np.uint8)).resize((img.shape[1]//2,img.shape[0]//2)).save(S+'work/boost.png')
