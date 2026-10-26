import sys,json
from faster_whisper import WhisperModel
m=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4)
for n in sys.argv[1:]:
    segs,info=m.transcribe(__import__("librosa").load(f"{n}.wav",sr=16000)[0],vad_filter=True,word_timestamps=True)
    out=[{"s":s.start,"e":s.end,"t":s.text,"w":[(w.start,w.end,w.word) for w in s.words]} for s in segs]
    json.dump({"lang":info.language,"segs":out},open(f"{n}_tx.json","w"),ensure_ascii=False)
    print(n,info.language,len(out),flush=True)
