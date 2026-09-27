import os,time,re,subprocess,requests,json,hashlib
SPACE="https://cbensimon-wan2-2-fp8da-aoti-preview2.hf.space"
FLOOT="https://75fc1d9a-19b3-4bff-ac0a-280ed4cc1636.sandbox.floot.app"
SOURCE=FLOOT+"/_cdn/static/976b79ec-b0af-475d-8706-d46377c4fd27-file_0000000047408246bbbd81d5c888ce7d.png"
KNOWN=[FLOOT+"/_cdn/static/2cb10cec-c83d-4c7c-9272-6933648c430a-jafar-wan22-seg01.mp4",FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-01.mp4",FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-02.mp4",FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-04.mp4"]
POS="Natural cinematic motion. Keep the exact same adult man and woman, faces, clothing and proportions. Calm neutral expressions, closed mouths, subtle head and eye movement, hair moving in sea breeze, natural ocean waves and sunset reflections. Mostly steady selfie camera. No identity change, no morphing, no laughing, no grin."
NEG="face distortion, identity change, morphing, laughing, open mouth, exaggerated smile, grin, extra limbs, warped hands, duplicated people, flicker, sudden camera motion, text, watermark"
os.makedirs("output/segments",exist_ok=True)
def dur(p):
 try:return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p],text=True).strip())
 except:return 0
def dl(u,p):
 r=requests.get(u,timeout=120);r.raise_for_status();open(p,"wb").write(r.content);return p
def upload(p):
 with open(p,"rb") as f:r=requests.post(SPACE+"/gradio_api/upload",files={"files":("source.png",f,"image/png")},timeout=120)
 r.raise_for_status();x=r.json();return x[0] if isinstance(x,list) else x.get("path") or x.get("name")
def gen(src,n):
 remote=upload(src); obj={"path":remote,"meta":{"_type":"gradio.FileData"}}
 data=[obj,None,POS,6,NEG,3.5,1,1,1000+n*101,True,6,"UniPCMultistep",3.0,16,False,True]
 r=requests.post(SPACE+"/gradio_api/call/generate_video",json={"data":data},timeout=120);r.raise_for_status();eid=r.json()["event_id"];print("EVENT",eid,flush=True)
 r=requests.get(SPACE+"/gradio_api/call/generate_video/"+eid,stream=True,timeout=1200);r.raise_for_status()
 for line in r.iter_lines(decode_unicode=True):
  if not line:continue
  print(line[:300],flush=True)
  if line.startswith("event: error"):raise RuntimeError("wan event error")
  if line.startswith("data:"):
   m=re.search(r'(/tmp/gradio/[^"\\]+?\.mp4)',line)
   if m:
    p=f"output/segments/gen-{n:02d}.mp4";dl(SPACE+"/gradio_api/file="+m.group(1),p)
    if dur(p)>1:return p
 raise RuntimeError("no mp4")
src="source.png";dl(SOURCE,src);clips=[];seen=set()
for i,u in enumerate(KNOWN,1):
 try:
  p=f"output/segments/known-{i:02d}.mp4";dl(u,p);h=hashlib.sha256(open(p,"rb").read()).hexdigest()
  if dur(p)>1 and h not in seen:seen.add(h);clips.append(p)
 except Exception as e:print("KNOWN_FAIL",e,flush=True)
attempt=0
while sum(dur(x) for x in clips)<60 and attempt<50:
 attempt+=1
 try:
  p=gen(src,attempt);h=hashlib.sha256(open(p,"rb").read()).hexdigest()
  if h not in seen:seen.add(h);clips.append(p)
  print("PROGRESS",len(clips),sum(dur(x) for x in clips),flush=True);time.sleep(10)
 except Exception as e:print("GEN_FAIL",attempt,repr(e),flush=True);time.sleep(min(90,20+attempt*5))
total=sum(dur(x) for x in clips)
json.dump({"clips":len(clips),"seconds":total,"attempts":attempt},open("output/report.json","w"),indent=2)
if total<60:raise SystemExit("Not enough real AI video: "+str(total))
norm=[]
for i,p in enumerate(clips):
 q=f"output/segments/norm-{i:02d}.mp4";subprocess.check_call(["ffmpeg","-y","-i",p,"-vf","scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2:black,fps=24,setsar=1","-an","-c:v","libx264","-pix_fmt","yuv420p",q]);norm.append(q)
with open("concat.txt","w") as f:
 for p in norm:f.write("file '"+os.path.abspath(p)+"'\n")
subprocess.check_call(["ffmpeg","-y","-f","concat","-safe","0","-i","concat.txt","-c","copy","-movflags","+faststart","output/final.mp4"])
final=dur("output/final.mp4");print("FINAL_DURATION",final,flush=True)
if final<60:raise SystemExit("Final under 60")
