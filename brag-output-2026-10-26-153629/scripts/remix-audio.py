from pathlib import Path
from html.parser import HTMLParser
import subprocess,json
ROOT=Path(__file__).resolve().parents[1]
class AudioTags(HTMLParser):
 def __init__(self):super().__init__();self.tracks=[]
 def handle_starttag(self,tag,attrs):
  if tag=='audio':self.tracks.append(dict(attrs))
p=AudioTags();p.feed((ROOT/'composition/index.html').read_text())
assert sum(t['id']=='female-narration' for t in p.tracks)==1
cmd=['ffmpeg','-y','-i',str(ROOT/'brag-45s-voiceover.mp4')]
filters=[];labels=[]
for i,t in enumerate(p.tracks,1):
 cmd+=['-i',str(ROOT/'composition'/t['src'])]
 duration=float(t['data-duration']);start=float(t['data-start'])
 chain=f'[{i}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={t.get("data-volume","1")}'
 if 'data-fade-in' in t:chain+=f',afade=t=in:st=0:d={t["data-fade-in"]}'
 if 'data-fade-out' in t:
  fade=float(t['data-fade-out']);chain+=f',afade=t=out:st={duration-fade}:d={fade}'
 chain+=f',adelay={round(start*1000)}:all=1[a{i}]'
 filters.append(chain);labels.append(f'[a{i}]')
filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0:duration=longest,atrim=duration=45[mix]')
cmd+=['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[mix]','-c:v','copy','-c:a','aac','-b:a','192k','-t','45','-movflags','+faststart',str(ROOT/'brag-45s-voiceover-fixed.mp4')]
subprocess.run(cmd,check=True)
report=json.loads((ROOT/'narration.json').read_text())
assert all(s['rate']==1 and s['speech_seconds']<=s['duration']-.4 for s in report)
print('All speech uses natural speed. Single narration track. Visual stream copied unchanged.')
