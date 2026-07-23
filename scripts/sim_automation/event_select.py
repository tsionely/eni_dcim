"""Deterministic AI-GP event selection + verification/capture (with nav prelude)."""
import sys, time, os, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pyautogui
pyautogui.FAILSAFE=False
import sim_window_utils as R
import cv2, numpy as np

event_key=sys.argv[1]; label=sys.argv[2]; mode=sys.argv[3] if len(sys.argv)>3 else 'dialog'
TMP=Path(os.environ.get('TEMP','.'))
out=TMP/'phase5b_r2_shots'/label; out.mkdir(parents=True,exist_ok=True)
status_dir=TMP/'phase5b_r2_status'; status_dir.mkdir(exist_ok=True)
status_path=status_dir/f'{label}_select.json'
TEMPLATES={
 'r1': HERE/'templates'/'r1_label_template.png',
 'r2submission': HERE/'templates'/'r2submission_label_template.png',
 'r2training': HERE/'templates'/'r2training_label_template.png',
}
def write(**kw): status_path.write_text(json.dumps(kw,indent=2),encoding='utf-8')
def cyan_score(img):
    arr=np.array(img.convert('RGB')); r,g,b=arr[:,:,0],arr[:,:,1],arr[:,:,2]
    return int(((b>130)&(g>100)&(r<100)&((b.astype(int)-r.astype(int))>60)).sum())
def match(gray, templ_path):
    templ=cv2.imread(str(templ_path),cv2.IMREAD_GRAYSCALE)
    if templ is None: return None,-1.0
    best=(None,-1.0)
    for s in (0.9,0.95,1.0,1.05,1.1):
        t=cv2.resize(templ,(int(templ.shape[1]*s),int(templ.shape[0]*s)),interpolation=cv2.INTER_AREA)
        if gray.shape[0]<t.shape[0] or gray.shape[1]<t.shape[1]: continue
        res=cv2.matchTemplate(gray,t,cv2.TM_CCOEFF_NORMED); _,mv,_,ml=cv2.minMaxLoc(res)
        if mv>best[1]: best=((ml[0],ml[1],t.shape[1],t.shape[0]),float(mv))
    return best
def match_all(shot):
    gray=cv2.cvtColor(np.array(shot),cv2.COLOR_RGB2GRAY)
    sc={}; bx={}
    for k,p in TEMPLATES.items():
        b,s=match(gray,p); sc[k]=s; bx[k]=b
    return sc,bx

ai=R.sim_window(ensure_visible=True)
if ai is None:
    write(ok=False,reason='sim_window_not_found'); print('NO_SIM_WINDOW',flush=True); sys.exit(3)
ai=R._sim_focus(ai); time.sleep(0.5)
# Navigation prelude: pass title/login screens to reach the event list.
# Retry until all three event rows are visible (each template matches well).
reached=False; scores={}; boxes={}
for attempt in range(8):
    ai=R._sim_click(ai,1465,713); pyautogui.press('enter'); time.sleep(1.0)
    shot=pyautogui.screenshot()
    scores,boxes=match_all(shot)
    if min(scores.values())>=0.80:
        reached=True; break
elp=out/f'{label}_eventlist.png'; shot.save(elp)
print('SCORES',json.dumps({k:round(v,3) for k,v in scores.items()}),'reached',reached,flush=True)
if not reached:
    write(ok=False,reason='eventlist_not_reached',scores=scores,boxes=boxes,eventlist=str(elp))
    print('EVENTLIST_NOT_REACHED',flush=True); sys.exit(2)
chosen=boxes.get(event_key); chosen_sc=scores.get(event_key,-1.0)
uniq = chosen_sc>=0.80
if not chosen or not uniq:
    write(ok=False,reason='row_not_uniquely_matched',scores=scores,boxes=boxes,eventlist=str(elp))
    print('ROW_NOT_UNIQUE',flush=True); sys.exit(2)
x,y,w,h=chosen; cx=x+w//2; cy=y+h//2
pyautogui.moveTo(cx,cy); time.sleep(0.6)
hov=pyautogui.screenshot(); hovp=out/f'{label}_row_highlight.png'; hov.save(hovp)
hsc,_=match_all(hov)
ai=R._sim_click(ai,cx,cy); time.sleep(2.0)
dlg=pyautogui.screenshot(); dlgp=out/f'{label}_race_dialog.png'; dlg.save(dlgp)
res=dict(ok=True,event_key=event_key,scores=scores,boxes=boxes,click=[cx,cy],
         highlight_scores=hsc,eventlist=str(elp),highlight=str(hovp),dialog=str(dlgp),mode=mode)
if mode=='scene':
    ai=R._sim_click(ai,1650,866); time.sleep(0.25)
    ai=R._sim_click(ai,1650,866); time.sleep(2.5)
    sc1=pyautogui.screenshot(); s1=out/f'{label}_scene_01.png'; sc1.save(s1); time.sleep(1.5)
    sc2=pyautogui.screenshot(); s2=out/f'{label}_scene_02.png'; sc2.save(s2); time.sleep(1.5)
    sc3=pyautogui.screenshot(); s3=out/f'{label}_scene_03.png'; sc3.save(s3)
    res['scene_paths']=[str(s1),str(s2),str(s3)]; res['scene_cyan']=cyan_score(sc2)
    pyautogui.press('esc'); time.sleep(1.5)
    ai=R._sim_click(ai,472,800); time.sleep(2.0)
    ai=R._sim_click(ai,1360,840); time.sleep(2.0)
write(**res)
print('SELECT_OK',event_key,'mode',mode,flush=True)
