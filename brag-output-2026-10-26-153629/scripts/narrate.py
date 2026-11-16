import asyncio, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VOICEBOX=Path('/Users/saurabh/Desktop/codex-projects/ai-clip-gen')
os.environ['HF_HOME']=str(VOICEBOX/'.cache/huggingface')
sys.path.insert(0,str(VOICEBOX/'vendor/voicebox'))
import numpy as np
import soundfile as sf
from backend.backends.kokoro_backend import KokoroTTSBackend
SCENES=[
('intro',0,3.75,'Meet Job Hunter. Your job search, organized.'),
('discover',3.75,6,'Discover openings across public feeds and company job boards. Shortlist promising roles.'),
('evidence',9.75,6,'Understand each match with clear evidence. See your strongest skills and gaps to review.'),
('resumes',15.75,5.25,'Compare your resumes using shared keywords and job similarity.'),
('studio',21,7.5,'Prepare resumes, letters, outreach, and application answers together. Review every draft before applying.'),
('trends',28.5,5.25,'Find recurring skills across your saved jobs, and decide what to learn next.'),
('interview',33.75,5.25,'Practice role-based interview questions, then get feedback to strengthen your answers.'),
('outro',39,6,'Your career. Your data. Keep documents local. Focus your search. Make your move.'),
('visit',45,10,'Visit job hunter live six dot vercel dot app today, and start finding jobs of your dreams.')]
async def main():
 backend=KokoroTTSBackend()
 dest=ROOT/'composition/assets/voice'
 full=np.zeros(55*24000,dtype=np.float32)
 report=[]
 for name,start,duration,text in SCENES:
  raw=dest/f'{name}-raw.wav'
  if raw.exists(): audio,sr=sf.read(raw,dtype='float32')
  else:
   audio,sr=await backend.generate(text,{'kokoro_voice':str(dest/'af_heart.pt')},language='en',seed=42)
   sf.write(raw,audio,sr)
  assert sr==24000 and np.max(np.abs(audio))>.01
  original=len(audio)/sr
  available=duration-.4
  rate=max(1,original/available)
  if rate>1: raise RuntimeError(f'{name} exceeds its scene; shorten the script instead of stretching speech')
  # Consistent narration level, with headroom for quiet background music.
  audio=audio/max(np.max(np.abs(audio)),.01)*.82
  offset=round((start+.2)*sr)
  full[offset:offset+len(audio)]=audio
  sf.write(dest/f'{name}.wav',audio,sr)
  report.append(dict(scene=name,start=start,duration=duration,text=text,raw_seconds=original,speech_seconds=len(audio)/sr,rate=rate))
  print(name,round(original,2),'seconds; rate',round(rate,3),flush=True)
 sf.write(dest/'narration.wav',full,24000)
 (ROOT/'narration.json').write_text(json.dumps(report,indent=2))
 (ROOT/'narration.md').write_text('# Female voiceover · Voicebox\n\nVoicebox Kokoro backend, Heart (af_heart), English. Scene-aligned narration for the 55-second edit.\n\n'+'\n\n'.join(f'## {n} · {s:g}s\n{t}' for n,s,d,t in SCENES))
asyncio.run(main())
