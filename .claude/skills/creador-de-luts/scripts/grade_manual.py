# Grade manual (sin LUT) para fotos/fotogramas Rec709: curva, color por zonas, mascara sobre el sujeto, vineta y grano.
# Uso: python3 grade_manual.py foto.jpg ../looks/manual_pegada.json salida.jpg
# Parametros: ver el JSON de ejemplo. "subj" = [centro x, centro y, radio x, radio y] en proporcion del cuadro.
import sys, json, numpy as np
from PIL import Image

def s2l(x): return np.where(x <= 0.04045, x/12.92, ((x+0.055)/1.055)**2.4)
def l2s(x): x=np.clip(x,0,1); return np.where(x <= 0.0031308, x*12.92, 1.055*x**(1/2.4)-0.055)
M1=np.array([[0.4122214708,0.5363325363,0.0514459929],[0.2119034982,0.6806995451,0.1073969566],[0.0883024619,0.2817188376,0.6299787005]])
M2=np.array([[0.2104542553,0.7936177850,-0.0040720468],[1.9779984951,-2.4285922050,0.4505937099],[0.0259040371,0.7827717662,-0.8086757660]])
def to_ok(rgb): lms=np.cbrt(rgb@M1.T); return lms@M2.T
def from_ok(lab):
    lms=(lab@np.linalg.inv(M2).T)**3; return lms@np.linalg.inv(M1).T

def smooth(x,a,b): t=np.clip((x-a)/(b-a),0,1); return t*t*(3-2*t)
def hue_w(h, c, width):  # peso gaussiano por tono (grados)
    d=np.angle(np.exp(1j*np.radians(h-c)),deg=True); return np.exp(-(d/width)**2)

def pchip(xs, ys, x):
    h=np.diff(xs); d=np.diff(ys)/h; n=len(xs); m=np.zeros(n)
    m[0],m[-1]=d[0],d[-1]
    for i in range(1,n-1):
        m[i]=0 if d[i-1]*d[i]<=0 else 3*(h[i-1]+h[i])/((2*h[i]+h[i-1])/d[i-1]+(h[i]+2*h[i-1])/d[i])
    i=np.clip(np.searchsorted(xs,x)-1,0,n-2); t=(x-xs[i])/h[i]
    return (ys[i]*(2*t**3-3*t**2+1)+h[i]*m[i]*(t**3-2*t**2+t)+ys[i+1]*(-2*t**3+3*t**2)+h[i]*m[i+1]*(t**3-t**2))

def grade(img, p):
    H,W,_=img.shape
    lin=s2l(img)
    # balance de blancos / exposicion en lineal
    lin=lin*np.array(p.get('wb',[1,1,1]))*2**p.get('expo',0)
    lab=to_ok(lin); L,a,b=lab[...,0],lab[...,1],lab[...,2]
    C=np.hypot(a,b); h=np.degrees(np.arctan2(b,a))%360
    if 'curve' in p:  # curva tipo Lightroom en valores de gris sRGB (entrada->salida), monotona
        pts=np.array(p['curve'],float); xs,ys=pts[:,0],pts[:,1]
        v=l2s(np.clip(L,0,1)**3); v2=pchip(xs,ys,v); L2=np.cbrt(s2l(np.clip(v2,0,1)))
    else:
        L2=None
    # curva de luminancia: negros, S, techo
    bp,wp=p.get('in_black',0.08),p.get('in_white',0.97)
    x=np.clip((L-bp)/(wp-bp),0,1.2)
    k=p.get('s',1.6); piv=p.get('pivot',0.45)
    x=np.where(x<piv, piv*(x/piv)**k, 1-(1-piv)*((1-np.minimum(x,1))/(1-piv))**(k*0.8))
    if L2 is None: L2=p.get('out_black',0.03)+x*(p.get('out_white',0.97)-p.get('out_black',0.03))
    C=C*(1+p.get('sat_follow',0)*(L2/np.maximum(L,1e-3)-1))  # croma acompana el cambio de luz (evita sombras sucias)
    # mascaras de zona
    sh=1-smooth(L2,0.1,0.5); hi=smooth(L2,0.55,0.95)
    # saturacion general + piel + verdes + magenta
    skin=hue_w(h,55,25)*smooth(C,0.02,0.05)
    green=hue_w(h,150,35); mag=hue_w(h,350,35)
    sat=p.get('sat',1.0)*(1+skin*(p.get('skin_sat',1.0)-1))*(1+green*(p.get('green_sat',1.0)-1))*(1+mag*(p.get('mag_sat',1.0)-1))
    C2=C*sat
    # corrimiento de tono de piel y verdes
    h2=h+skin*p.get('skin_hue',0)+green*p.get('green_hue',0)
    a2=C2*np.cos(np.radians(h2)); b2=C2*np.sin(np.radians(h2))
    # split toning
    def tint(hue,amt): return amt*np.cos(np.radians(hue)), amt*np.sin(np.radians(hue))
    ta,tb=tint(p.get('sh_hue',210),p.get('sh_amt',0.02)); a2+=ta*sh; b2+=tb*sh
    ta,tb=tint(p.get('hi_hue',75),p.get('hi_amt',0.01)); a2+=ta*hi; b2+=tb*hi
    # mascara radial sobre el sujeto: un poco mas de luz
    yy,xx=np.mgrid[0:H,0:W]
    cx,cy,rx,ry=[v*s for v,s in zip(p.get('subj',[0.46,0.5,0.28,0.55]),[W,H,W,H])]
    r=np.sqrt(((xx-cx)/rx)**2+((yy-cy)/ry)**2)
    subj=1-smooth(r,0.6,1.2)
    L2=L2+subj*p.get('subj_lift',0.03)*(1-L2)
    # vineta
    vr=np.sqrt(((xx-W/2)/(W*0.62))**2+((yy-H/2)/(H*0.62))**2)
    L2=L2*(1-p.get('vig',0.25)*smooth(vr,0.55,1.15))
    out=from_ok(np.stack([L2,a2,b2],-1))
    out=l2s(np.clip(out,0,1))
    # grano
    g=p.get('grain',0)
    if g:
        rng=np.random.default_rng(1); n=rng.normal(0,1,(H,W,1)); out=out+g*n*(0.6+0.4*np.sin(np.pi*np.clip(out,0,1)))
    return np.clip(out,0,1)

src,params,out=sys.argv[1:4]
img=np.asarray(Image.open(src).convert('RGB')).astype(np.float64)/255
p=json.load(open(params))
res=grade(img,p)
Image.fromarray((res*255+0.5).astype(np.uint8)).save(out,quality=95)
print('ok',out)
