# Familia final "MA_Vivo": el look aprobado (v2 sobre clip D-Log) con variantes de exposicion.
import sys, json, numpy as np
S='/tmp/claude-0/-home-user-lore/7d508246-2704-5e00-8a78-fcf8e8181527/scratchpad/'
sys.path.insert(0,S+'scripts'); import lutlib as L, boost as Bm
Bm.B.update(json.load(open(S+'work/boost_params.json')))
P=dict(L.DEFAULT); P.update(json.load(open(S+'work/final_params.json')))
# grey of D-Log (0.40) decoded with the D-Log2 curve lands ~1.58 stops over grey
DLOG_GREY_COMP = 0.18 / L.dlog2_to_lin(np.array(0.3996))
def vivo(codes, mult=1.0):
    lin = L.dlog2_to_lin(codes) @ L.DG2_TO_709.T * mult
    return Bm.boost(L.encode_709(L.grade(L.tonemap(lin, P['exposure']), P)))
FAMILY = {
  # nombre: (multiplicador de exposicion, titulo)
  'MA_Vivo_DLog_NOCHE.cube': (1.0, 'MA Vivo - D-Log - Noche'),            # = el look aprobado
  'MA_Vivo_DLog_DIA.cube':   (float(DLOG_GREY_COMP), 'MA Vivo - D-Log - Dia'),
  'MA_Vivo_DLog2_DIA.cube':  (1.0/2.0, 'MA Vivo - D-Log2 - Dia'),
  'MA_Vivo_DLog2_NOCHE.cube':(1.0*1.5, 'MA Vivo - D-Log2 - Noche'),
}
