"""Download JBL's own Endurance Peak 3 3D model into ../models/ (not committed).

The file is the one the 3D/AR viewer on JBL Canada's product page loads for every visitor:
  page:   https://ca.jbl.com/en_CA/ENDURANCE-PEAK-3.html   (viewer SKU gfsk7ti2mdasfl0b6d1p)
  model:  served by the viewer's CDN (URL below, found in the viewer's product record)
The model is JBL's property. It is kept out of git (see .gitignore) because this repo is public.
Use it for personal measurement only.
"""
import os
import urllib.request

URL = ("https://ar.huemenar.com/media/assets/jbl/endurance-peak-3/black/"
       "endurance-peak-3-black-android-ar-asset.glb")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "JBL_Endurance_Peak_3_original.glb")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with urllib.request.urlopen(URL, timeout=120) as r, open(OUT, "wb") as f:
    f.write(r.read())
print("saved", os.path.abspath(OUT), os.path.getsize(OUT), "bytes (expected 5,955,176)")
