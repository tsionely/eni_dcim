import sys, time, os, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pyautogui
pyautogui.FAILSAFE=False
import sim_window_utils as R
import numpy as np
label=sys.argv[1]
out=os.path.join(os.environ.get('TEMP','.'),'phase5b_r2_shots',label); os.makedirs(out,exist_ok=True)
status_dir=Path(os.environ.get('TEMP','.'))/'phase5b_r2_status'; status_dir.mkdir(exist_ok=True)
status_path=status_dir/f'{label}_race.json'
def cyan_score(img):
    arr=np.array(img.convert('RGB')); r,g,b=arr[:,:,0],arr[:,:,1],arr[:,:,2]
    return int(((b>130)&(g>100)&(r<100)&((b.astype(int)-r.astype(int))>60)).sum())
def write(**kw): status_path.write_text(json.dumps(kw,indent=2),encoding='utf-8')
ai=R.sim_window(ensure_visible=True)
ai=R._sim_click(ai,1650,866); time.sleep(0.2)
ai=R._sim_click(ai,1650,866); time.sleep(0.5)
verify=pyautogui.screenshot(); vpath=os.path.join(out,f'{label}_verify_after_race.png'); verify.save(vpath)
cyan=cyan_score(verify); r2_ok=cyan>2000
write(race_clicked=True,cyan_pixels=cyan,r2_ok=r2_ok,verify_path=vpath)
print(f'RACE_CLICKED cyan={cyan} r2_ok={r2_ok}',flush=True)
for i in range(160):
    try:
        img=pyautogui.screenshot(); p=os.path.join(out,f'{label}_{i:03d}_{time.strftime("%H%M%S")}.png'); img.save(p); print(p,flush=True)
    except Exception as e: print('shot err',e,flush=True)
    time.sleep(3)
