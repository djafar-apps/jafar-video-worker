import os, subprocess, tempfile, requests, threading, time, json, re, shutil
from flask import Flask, jsonify, send_file
app=Flask(__name__)
FLOOT="https://75fc1d9a-19b3-4bff-ac0a-280ed4cc1636.sandbox.floot.app"
SPACE="https://cbensimon-wan2-2-fp8da-aoti-preview2.hf.space"
SOURCE=FLOOT+"/_cdn/static/976b79ec-b0af-475d-8706-d46377c4fd27-file_0000000047408246bbbd81d5c888ce7d.png"
KNOWN=[
FLOOT+"/_cdn/static/2cb10cec-c83d-4c7c-9272-6933648c430a-jafar-wan22-seg01.mp4",
FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-01.mp4",
FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-02.mp4",
FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-04.mp4"]
WORK="/tmp/jafar60"; os.makedirs(WORK,exist_ok=True)
STATE={"running":False,"done":False,"clips":0,"seconds":0.0,"attempts":0,"last":"boot","final":None}
POS="Natural cinematic motion. Keep the exact same adult man and woman, faces, clothing and proportions. Calm neutral expressions, closed mouths, subtle head and eye movement, hair moving in sea breeze, natural ocean waves and sunset reflections. Mostly steady selfie camera. No identity change, no morphing, no laughing, no grin."
NEG="face distortion, identity change, morphing, laughing, open mouth, exaggerated smile, grin, extra limbs, warped hands, duplicated people, flicker, sudden camera motion, text, watermark"

def duration(p):
 try:return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",p],text=True,timeout=20).strip())
 except:return 0.0

def get(url,path):
 r=requests.get(url,timeout=90); r.raise_for_status(); open(path,"wb").write(r.content); return path

def upload_source():
 p=os.path.join(WORK,"source.png")
 if not os.path.exists(p): get(SOURCE,p)
 with open(p,"rb") as h:
  r=requests.post(SPACE+"/gradio_api/upload",files={"files":("source.png",h,"image/png")},timeout=120)
 r.raise_for_status(); x=r.json()
 if isinstance(x,list): return x[0]
 if isinstance(x,dict):
  for k in ("path","name"):
   if k in x:return x[k]
 raise RuntimeError("upload response "+str(x)[:300])

def generate_one(n):
 remote=upload_source()
 image_obj={"path":remote,"meta":{"_type":"gradio.FileData"}}
 data=[image_obj,None,POS,6,NEG,3.5,1,1,42+n*97,True,6,"UniPCMultistep",3.0,16,False,True]
 r=requests.post(SPACE+"/gradio_api/call/generate_video",json={"data":data},timeout=120)
 r.raise_for_status(); eid=r.json()["event_id"]
 s=requests.get(SPACE+"/gradio_api/call/generate_video/"+eid,stream=True,timeout=900)
 s.raise_for_status(); blob=""
 for raw in s.iter_lines(decode_unicode=True):
  if not raw:continue
  blob+=raw+"\n"
  if raw.startswith("event: error"): raise RuntimeError("wan event error")
  if raw.startswith("data:"):
   m=re.search(r'(/tmp/gradio/[^"\\]+?\.mp4)',raw)
   if m:
    url=SPACE+"/gradio_api/file="+m.group(1)
    out=os.path.join(WORK,f"gen-{n:02d}.mp4"); get(url,out)
    if duration(out)>1:return out
 raise RuntimeError("no mp4 "+blob[-500:])

def stitch(clips):
 lst=os.path.join(WORK,"list.txt")
 with open(lst,"w") as h:
  for p in clips:h.write("file '"+p.replace("'","'\\''")+"'\n")
 out=os.path.join(WORK,"final.mp4")
 subprocess.check_call(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",out],timeout=600)
 return out

def run():
 if STATE["running"] or STATE["done"]:return
 STATE["running"]=True; clips=[]
 try:
  for i,u in enumerate(KNOWN,1):
   p=os.path.join(WORK,f"known-{i:02d}.mp4")
   try:
    get(u,p)
    if duration(p)>1:clips.append(p)
   except Exception as e: print("KNOWN_FAIL",i,e,flush=True)
  STATE["clips"]=len(clips); STATE["seconds"]=sum(duration(x) for x in clips)
  n=1
  while STATE["seconds"]<60 and STATE["attempts"]<40:
   STATE["attempts"]+=1; STATE["last"]=f"generating attempt {STATE['attempts']}"
   try:
    p=generate_one(n); n+=1; clips.append(p)
    STATE["clips"]=len(clips); STATE["seconds"]=sum(duration(x) for x in clips)
    print("GEN_OK",STATE["clips"],STATE["seconds"],flush=True)
    time.sleep(8)
   except Exception as e:
    STATE["last"]="retry: "+str(e)[:160]; print("GEN_FAIL",STATE["attempts"],e,flush=True); time.sleep(45)
  if STATE["seconds"]>=60:
   out=stitch(clips); d=duration(out)
   if d>=60:
    STATE.update(done=True,final=out,seconds=d,last="FINAL_READY")
    print("FINAL_READY duration=",d,flush=True)
   else: STATE["last"]=f"stitch too short {d}"
  else: STATE["last"]="attempt limit before 60s"
 except Exception as e:
  STATE["last"]="fatal: "+repr(e); print("WORKER_FATAL",repr(e),flush=True)
 finally: STATE["running"]=False

@app.get("/")
def home():return jsonify(STATE)
@app.get("/start")
def start():
 threading.Thread(target=run,daemon=True).start(); return jsonify(STATE)
@app.get("/final.mp4")
def final():
 if STATE["done"] and STATE["final"] and os.path.exists(STATE["final"]):return send_file(STATE["final"],mimetype="video/mp4",as_attachment=True,download_name="jafar-ai-60s.mp4")
 return jsonify(STATE),404

print("FFMPEG",subprocess.getoutput("ffmpeg -version | head -1"),flush=True)
threading.Thread(target=run,daemon=True).start()
