import os, subprocess, tempfile, requests
from flask import Flask, jsonify, request
app=Flask(__name__)
FLOOT="https://75fc1d9a-19b3-4bff-ac0a-280ed4cc1636.sandbox.floot.app"
KNOWN=[
FLOOT+"/_cdn/static/2cb10cec-c83d-4c7c-9272-6933648c430a-jafar-wan22-seg01.mp4",
FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-01.mp4",
FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-02.mp4",
FLOOT+"/_cdn/video-jobs/jafar60-worker-02/segment-04.mp4"]
@app.get("/")
def home(): return jsonify(ok=True,service="jafar-video-worker",known_clips=len(KNOWN))
@app.get("/probe")
def probe():
 out=[]
 for u in KNOWN:
  try:
   r=requests.get(u,timeout=30); out.append({"url":u,"status":r.status_code,"bytes":len(r.content)})
  except Exception as e: out.append({"url":u,"error":str(e)})
 return jsonify(out)
@app.get("/ffmpeg")
def ffmpeg():
 try:
  v=subprocess.check_output(["ffmpeg","-version"],text=True,timeout=10).splitlines()[0]
  return jsonify(ok=True,version=v)
 except Exception as e:return jsonify(ok=False,error=str(e)),500

def startup_probe():
 print("STARTUP_PROBE_BEGIN", flush=True)
 try:
  v=subprocess.check_output(["ffmpeg","-version"],text=True,timeout=10).splitlines()[0]
  print("FFMPEG_OK "+v, flush=True)
 except Exception as e: print("FFMPEG_FAIL "+str(e), flush=True)
 for i,u in enumerate(KNOWN,1):
  try:
   r=requests.get(u,timeout=30)
   print(f"CLIP_{i} status={r.status_code} bytes={len(r.content)}", flush=True)
  except Exception as e: print(f"CLIP_{i}_FAIL {e}", flush=True)
 print("STARTUP_PROBE_END", flush=True)
startup_probe()
