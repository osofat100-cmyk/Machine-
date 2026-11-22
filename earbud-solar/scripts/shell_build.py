"""Build the printable, waterproof two-half paddle shell (cover + base) and the flexible hook.

Input: the flat-face solar bud (make_solar_bud.py), data/shell_frame.json + shell_anchors.json
(shell_frame.py), data/shell_params.json, data/components.json.  Everything is done in the seat frame S
(Z = out of the face, seat at Z = 0) on a voxel grid whose faces fall on multiples of the pitch, so the
seat plane and the parting plane are exact.
Steps: solid -> paddle / hook split (stadium outline) -> exact flat seat -> re-distance -> hollow
(0.8 under cell, 1.0 floor, 1.1 sides) -> parting plane (auto) -> lands, groove, tongue -> screws ->
openings (charging pins, window port, LED, mics, pod socket, cell wire pass-throughs + potting cups,
charger pocket) -> hook peg/socket + magnet pocket -> meshes (STL + 3MF) + report.
Usage: python3 shell_build.py <solar bud glb> <data dir> <out dir> [pitch override]
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
from scipy import ndimage
import sdf

glb, data, out = sys.argv[1:4]
PR = json.load(open(os.path.join(data, "shell_params.json")))
A = json.load(open(os.path.join(data, "shell_anchors.json")))
FR = json.load(open(os.path.join(data, "shell_frame.json")))
p = float(sys.argv[4]) if len(sys.argv) > 4 else PR["pitch"]
os.makedirs(out, exist_ok=True)
o, R = np.array(FR["origin_measured_frame"]), np.array(FR["R_rows_XYZ"])
W, SE, FE, HK, SC = PR["walls"], PR["seal"], PR["features"], PR["hook"], PR["screws"]
rep = dict(pitch=p)
log = lambda *a: print(*a, flush=True)

# ---------------- 1. closed solid of the whole bud in S ----------------
scene = trimesh.load(glb, force="scene")
tris, pod_tris = [], []
for nd in scene.graph.nodes_geometry:
    if nd.startswith("SM400"):
        continue
    T, gk = scene.graph[nd]; m = scene.geometry[gk].copy(); m.apply_transform(T)
    t = ((m.triangles.reshape(-1, 3) - o) @ R.T).reshape(-1, 3, 3)
    tris.append(t)
    if nd in ("Earphone_Rubber", "Earphone_Fabric"):
        pod_tris.append(t)
skin = np.vstack(tris)
lo = np.floor((skin.reshape(-1, 3).min(0) - 1.5) / p) * p
hi = skin.reshape(-1, 3).max(0) + 1.5
G0 = sdf.Grid(lo, hi, p)
phi_all = sdf.skin_sdf(skin, G0, seal_mm=PR["paddle"].get("seal_mm", 1.0), sigma_vox=1.0)   # seal model slits (underside plate gap)
kz = int(round((-16.5 - G0.lo[2]) / p))
sl = (slice(None), slice(None), slice(max(kz, 0), None))
phi = np.ascontiguousarray(phi_all[sl]); g = G0.sub(sl); del phi_all
ax = g.axes(); X, Y, Z = g.xyz()
log("grid", g.shape, "lo", g.lo.round(3))
solid = phi <= 0


def kslice(z):
    return int(np.clip(round((z - g.lo[2]) / p - 0.5), 0, g.shape[2] - 1))


# ---------------- 2. paddle outline (stadium) & regions ----------------
s3 = solid[:, :, kslice(PR["paddle"]["outline_slice_z"])]
cols = np.where(np.abs(ax[0]) < 8)[0]
ymins = [ax[1][s3[i]].min() for i in cols if s3[i].any()]
ymaxs = [ax[1][s3[i]].max() for i in cols if s3[i].any()]
yc = float(np.mean((np.array(ymins) + np.array(ymaxs)) / 2)); r = float(np.mean((np.array(ymaxs) - np.array(ymins)) / 2))
s15 = solid[:, :, kslice(PR["paddle"]["ends_slice_z"])]
rows = np.abs(ax[1] - yc) < 1.0
xs = ax[0][s15[:, rows].any(1)]
xa, xb = float(xs.min() + r), float(xs.max() - r)
rst = r + PR["paddle"]["outline_margin"]
XX, YY = np.meshgrid(ax[0], ax[1], indexing="ij")
tt = np.clip((XX - xa) / (xb - xa), 0, 1)
d2 = (np.hypot(XX - (xa + tt * (xb - xa)), YY - yc) - rst).astype(np.float32)     # 2-D stadium SDF
rep["paddle_outline"] = dict(centre_y=round(yc, 3), half_width=round(r, 3), centres_x=[round(xa, 3), round(xb, 3)])
log("paddle stadium: y", round(yc, 2), "r", round(r, 2), "x", round(xa, 2), round(xb, 2))
zc = PR["paddle"]["z_cut_bottom"]
phi_pad = np.maximum(np.maximum(phi, d2[:, :, None]), (zc - Z).astype(np.float32))

hook = solid & (d2[:, :, None] > 0) & (Z >= -15.5)
lab, nl = ndimage.label(hook)
hook = lab == (np.argmax(ndimage.sum(hook, lab, range(1, nl + 1))) + 1)
neck2d = solid[:, :, kslice(zc - 0.3)] & (d2 < 0)                                # pod neck section under the cut
lab2, n2 = ndimage.label(neck2d)
if n2:
    neck2d = lab2 == (np.argmax(ndimage.sum(neck2d, lab2, range(1, n2 + 1))) + 1)
del solid

# ---------------- 3. exact flat seat over the cell footprint ----------------
union_prism = sdf.box(g, np.array([0.0, 0.0, -2.0]), np.eye(3), [16.5 - 0.3, 7.5 - 0.3, 2.0])
sdf.union(phi_pad, union_prism)
win = (np.abs(XX) <= 17.0) & (np.abs(YY) <= 8.0)
phi_pad = np.where(win[:, :, None], np.maximum(phi_pad, Z.astype(np.float32)), phi_pad)

# ---------------- 4. re-distance + hollow ----------------
phi2 = sdf.smooth(sdf.redistance(phi_pad, p), 1.0); del phi_pad
inside = phi2 <= 0
gz = np.gradient(phi2, p, axis=2)
tw = np.where(gz > 0.7, W["cover_top"], np.where(gz < -0.7, W["floor"], W["side"])).astype(np.float32); del gz
tw = ndimage.gaussian_filter(tw, 0.5 / p)
cavity = phi2 < -tw; del tw
rb = max(1, int(round(0.4 / p))); ball = (np.indices((2 * rb + 1,) * 3) - rb); ball = (ball ** 2).sum(0) <= rb * rb
cavity = ndimage.binary_opening(cavity, structure=ball)
shell = inside & ~cavity
zgrid = np.broadcast_to(Z, phi2.shape)
cav_top = np.where(cavity.any(2), ax[2][g.shape[2] - 1 - np.argmax(cavity[:, :, ::-1], 2)], np.nan)
cav_bot = np.where(cavity.any(2), ax[2][np.argmax(cavity, 2)], np.nan)
clear = (cav_top - cav_bot + p)[(np.abs(XX) < 12) & (np.abs(YY - yc) < 4)]
rep["clear_height_mm"] = dict(median=round(float(np.nanmedian(clear)), 2), p10=round(float(np.nanpercentile(clear, 10)), 2),
                              p90=round(float(np.nanpercentile(clear, 90)), 2))
log("inside clear height (centre of paddle):", rep["clear_height_mm"])

# ---------------- 5. hook = rigid stub (joins the paddle, outside the seal) + flexible arm ----------------
# root = hook voxels face-touching the paddle body; stub = hook within `stub_len` of the paddle outline that is
# connected to the root (the free tip, 0.75 mm away, is not connected); arm = the rest (flexible part).
touch = hook & ndimage.binary_dilation(inside, structure=ndimage.generate_binary_structure(3, 1))
near = hook & (d2[:, :, None] <= HK["stub_len"])
labn, _ = ndimage.label(near)
ids, cnt = np.unique(labn[touch], return_counts=True); cnt = cnt[ids > 0]; ids = ids[ids > 0]
stub = labn == ids[np.argmax(cnt)]                     # the real root = the largest contact (the free tip can look
                                                       # "touching" on a coarse grid because its gap is only 0.75 mm)
arm = hook & ~stub
la_, na_ = ndimage.label(arm)
arm = la_ == (np.argmax(ndimage.sum(arm, la_, range(1, na_ + 1))) + 1)
iface = arm & ndimage.binary_dilation(stub, iterations=2)
ri = np.argwhere(iface); ic = g.lo + (ri.mean(0) + 0.5) * p
gx2, gy2 = np.gradient(d2, p)
ii, jj = g.index(ic)[:2]
nrm = np.array([gx2[ii, jj], gy2[ii, jj], 0.0]); nrm /= np.linalg.norm(nrm)
peg_axis = -nrm                                                    # from the arm into the stub (towards the paddle)
rep["hook_joint"] = dict(centre=ic.round(3).tolist(), axis_into_stub=peg_axis.round(4).tolist(),
                         stub_volume_mm3=round(float(stub.sum() * p ** 3), 1), arm_volume_mm3=round(float(arm.sum() * p ** 3), 1))
log("hook joint at", ic.round(2), "axis", peg_axis.round(2))

# ---------------- 6. parting plane ----------------
side_z = [A["led"]["centre"][2]] + [m_["centre"][2] for m_ in A["mic_ports"]]
cands = []
for zp in np.arange(PR["parting"]["scan"][0], PR["parting"]["scan"][1] + 1e-6, p):
    zp = round(zp / p) * p
    if min(abs(zp - z) for z in side_z) < PR["parting"]["keep_clear_of_side_features"]:
        continue
    k = kslice(zp)
    opening = cavity[:, :, k] & ((ndimage.distance_transform_edt(inside[:, :, k]) - 0.5) * p >= SE["land_t"])
    cands.append((int(opening.sum()), zp))
zp = float(max(cands)[1]) if PR["parting"]["z"] == "auto" else float(PR["parting"]["z"])
rep["parting_z"] = round(zp, 3)
log("parting plane Z =", round(zp, 3), "(", len(cands), "valid candidates)")

# ---------------- 7. halves, lands, groove, tongue ----------------
below = zgrid < zp
# in-slice (horizontal) distance from the outer skin: lands, groove, tongue and tab follow the side walls only,
# never the floor/top (a 3-D distance would spread the land across the shallow floor)
D2 = np.full(inside.shape, np.float32(1e3))
k0, k1 = kslice(zp - PR["tab"]["depth"] - 1.0), kslice(zp + SE["land_h_cover"] + 0.5) + 1
for kk in range(k0, k1):
    D2[:, :, kk] = (ndimage.distance_transform_edt(inside[:, :, kk]) - 0.5) * p
land = inside & (D2 < SE["land_t"])
base = ((shell | (land & (zgrid >= zp - SE["land_h_base"]))) & below)
cover = ((shell | (land & (zgrid < zp + SE["land_h_cover"]))) & ~below)
w_out, gw = SE["groove_wall_out"], SE["groove_w"]
groove = (D2 >= w_out) & (D2 < w_out + gw) & (zgrid >= zp - SE["groove_d"]) & below
c_ = (gw - SE["tongue_w"]) / 2
tongue = (D2 >= w_out + c_) & (D2 < w_out + c_ + SE["tongue_w"]) & (zgrid >= zp - SE["tongue_h"]) & below
base &= ~groove
cover |= tongue
seam_len = float((ndimage.binary_dilation(groove[:, :, kslice(zp - 0.5)]) ^ groove[:, :, kslice(zp - 0.5)]).sum() * p / 2)
rep["seal"] = dict(seam_length_mm=round(seam_len, 1), groove=[gw, SE["groove_d"]], tongue=[SE["tongue_w"], SE["tongue_h"]],
                   gasket_gap_mm=round(SE["groove_d"] - SE["tongue_h"], 2))
del land, shell, tongue                     # keep `groove`: re-cut at the end so nothing can block it


def add(mask, prim):
    s_, v = prim; mask[s_] |= v <= 0


def cut(mask, prim):
    s_, v = prim; mask[s_] &= ~(v <= 0)


def cyl(c, axis, d, length):
    return sdf.cylinder(g, np.asarray(c, float), axis, d / 2, length / 2)


def floor_outer_z(x, y):
    i, j = g.index([x, y, 0])[:2]
    col = inside[i, j]
    return float(ax[2][np.argmax(col)]) if col.any() else zc


# ---------------- 8. openings & fittings ----------------
for pin in A["pins"]:                                               # charging contacts (case pins line up)
    cut(base, cyl([pin["centre"][0], pin["centre"][1], pin["centre"][2] - 0.5], [0, 0, 1], FE["pin_hole_d"], 5.0))
wd = A["window"]; slot = FE["window"]["slot"]; rec = FE["window"]["recess"]
wb = FE["window"].get("boss_h", 0.6)
add(base, sdf.box(g, np.array([wd["centre"][0], wd["centre"][1], wd["centre"][2] + W["floor"] + wb / 2 - 0.05]), np.eye(3),
                  [rec[0] / 2 + 0.8, rec[1] / 2 + 0.8, wb / 2 + 0.05]))
cut(base, sdf.box(g, np.array(wd["centre"]) + [0, 0, 0.0], np.eye(3), [slot[0] / 2, slot[1] / 2, 2.0 + wb]))
cut(base, sdf.box(g, np.array([wd["centre"][0], wd["centre"][1], wd["centre"][2] + W["floor"] + wb - rec[2] / 2]), np.eye(3),
                  [rec[0] / 2, rec[1] / 2, rec[2] / 2 + 0.05]))
L = FE["led"]; ld = np.array(A["led"]["dir"]); lc = np.array(A["led"]["centre"])
add(cover, cyl(lc - ld * (W["side"] + L["sleeve_len"] / 2), ld, L["sleeve_od"], L["sleeve_len"]))
cut(cover, cyl(lc - ld * (W["side"] + L["sleeve_len"]) / 2, ld, L["hole_d"], W["side"] + L["sleeve_len"] + 2.0))
Mi = FE["mic"]
for mp in A["mic_ports"]:
    md, mc = np.array(mp["dir"]), np.array(mp["centre"])
    add(cover, cyl(mc - md * (W["side"] + Mi["boss_h"] / 2), md, Mi["boss_od"], Mi["boss_h"]))
    cut(cover, cyl(mc, md, Mi["hole_d"], 2 * (W["side"] + Mi["boss_h"]) + 2.0))
    cut(cover, cyl(mc - md * (W["side"] + Mi["boss_h"] - Mi["recess_h"] / 2), md, Mi["recess_d"], Mi["recess_h"] + 0.1))
# pod socket: opening = neck section + clearance, collar with an inner O-ring groove
PS = FE["pod_socket"]
dn = ndimage.distance_transform_edt(~neck2d) * p
open2d = dn <= PS["clearance"]
collar2d = (dn > PS["clearance"]) & (dn <= PS["clearance"] + PS["collar_w"])
oring2d = (dn > PS["clearance"]) & (dn <= PS["clearance"] + PS["oring_groove_d"])
zf_in = zc + W["floor"]
zz = ax[2][None, None, :]
base |= collar2d[:, :, None] & (zz >= zc) & (zz <= zf_in + PS["collar_h"]) & inside
base &= ~(open2d[:, :, None] & (zz <= zf_in + PS["collar_h"] + 0.5))
zm = zf_in + PS["collar_h"] / 2
base &= ~(oring2d[:, :, None] & (np.abs(zz - zm) <= PS["oring_groove_w"] / 2))
rep["pod_socket"] = dict(opening_area_mm2=round(float(open2d.sum() * p * p), 1), oring_groove_z=round(zm, 2))
CP = FE["cell_passthrough"]; CH = FE["charger_pocket"]; LID = PR.get("cell_as_lid", {"enabled": False})
if LID["enabled"]:
    # the solar cell IS the lid: open the top wall inside a lip of `lip` mm; the cell is bonded + sealed on the lip,
    # its back pads face straight into the cavity (no pass-through holes), the charger board sits on the cell back
    lip = LID["lip"]
    cut(cover, sdf.box(g, np.array([0.0, 0.0, -1.0]), np.eye(3), [16.5 - lip, 7.5 - lip, 1.05]))
    ch_c = np.array([A["cell"]["pads"][1]["centre"][0] - 4.0, 0.0, -0.7])
    rep["cell_as_lid"] = dict(lip_mm=lip, opening_mm=[33.0 - 2 * lip, 15.0 - 2 * lip], charger="on the cell back, next to the + pad")
else:
    for pad in A["cell"]["pads"]:                                  # wire pass-throughs + solder relief + potting cups
        pc = np.array(pad["centre"], float)
        add(cover, cyl([pc[0], pc[1], -W["cover_top"] - CP["cup_h"] / 2], [0, 0, 1], CP["cup_id"] + 2 * CP["cup_wall"], CP["cup_h"]))
        cut(cover, cyl([pc[0], pc[1], -W["cover_top"] - CP["cup_h"] / 2 - 0.05], [0, 0, 1], CP["cup_id"], CP["cup_h"] + 0.1))
        cut(cover, cyl([pc[0], pc[1], -1.0], [0, 0, 1], CP["hole_d"], 3.0))
        cut(cover, cyl([pc[0], pc[1], -CP["relief_h"] / 2 + 0.05], [0, 0, 1], CP["relief_d"], CP["relief_h"] + 0.1))
    cx0 = A["cell"]["pads"][1]["centre"][0] - 1.5; cy0 = CP["cup_id"] / 2 + CP["cup_wall"] + 0.4 + CH["inner"][1] / 2
    ch_c = np.array([cx0, cy0, -W["cover_top"] - CH["h"] / 2])          # charger pocket under the cover
    add(cover, sdf.box(g, ch_c, np.eye(3), [CH["inner"][0] / 2 + CH["wall"], CH["inner"][1] / 2 + CH["wall"], CH["h"] / 2]))
    cut(cover, sdf.box(g, ch_c - [0, 0, 0.05], np.eye(3), [CH["inner"][0] / 2, CH["inner"][1] / 2, CH["h"] / 2 + 0.05]))
cover &= inside                                                      # nothing may poke out of the skin
rep["charger_centre"] = ch_c.round(2).tolist()
top_eff = np.zeros_like(cav_top) if LID["enabled"] else cav_top + p / 2      # cell back (Z = 0) or cover inner face
clear2 = (top_eff - (cav_bot - p / 2))[(np.abs(XX) < 12) & (np.abs(YY - yc) < 4)]
rep["clear_height_final_mm"] = dict(median=round(float(np.nanmedian(clear2)), 2), p10=round(float(np.nanpercentile(clear2, 10)), 2))
log("final inside clear height (cell back or cover to floor):", rep["clear_height_final_mm"])

# ---------------- 9. hook arm: peg into the stub, magnet pocket at the free tip ----------------
add(arm, cyl(ic + peg_axis * (HK["peg_len"] - 0.2 - 0.8) / 2, peg_axis, HK["peg_d"], HK["peg_len"] - 0.2 + 0.8))  # 0.8 mm into the arm
hv = np.argwhere(arm); hp = g.lo + (hv + 0.5) * p
far = np.linalg.norm(hp - ic, axis=1) > 15.0
dpad = ndimage.distance_transform_edt(~inside) * p
dh = dpad[tuple(hv[far].T)]
tip = hp[far][np.argmin(dh)]
gi_ = g.index(tip); gdx = np.array([np.gradient(dpad, axis=a_)[tuple(gi_)] for a_ in range(3)])
to_pad = -gdx / (np.linalg.norm(gdx) + 1e-9)
mag_d, mag_h = HK["magnet"]
mag_c = tip - to_pad * (HK["magnet_skin"] + mag_h / 2)
cut(arm, cyl(mag_c - to_pad * 1.5, to_pad, mag_d + 0.2, mag_h + 3.0))
rep["hook"] = dict(mode=HK["mode"], tip=tip.round(2).tolist(), tip_gap_to_paddle_mm=round(float(dh.min()), 2),
                   magnet_centre=mag_c.round(2).tolist(), magnet_axis=to_pad.round(3).tolist())
del dpad

# ---------------- 10. screws ----------------
k = kslice(zp)
# a screw hole must stay inboard of the gasket line: skin -> 0.6 wall -> 1.1 groove -> 0.3 -> hole radius
seal_safe = SE["groove_wall_out"] + SE["groove_w"] + 0.3 + SC["clear_hole"] / 2
inner_ok = ndimage.distance_transform_edt(inside[:, :, k]) * p >= seal_safe
excl = np.zeros_like(inner_ok)
def ex_circle(x, y, rr):
    excl[(XX - x) ** 2 + (YY - y) ** 2 <= rr * rr] = True
pcb, bat = json.load(open(os.path.join(data, "components.json")))["pcb"]["size"], None
rb_ = SC["boss_od"] / 2 + 0.3
excl[(np.abs(XX) <= pcb[0] / 2 + 0.6 + rb_) & (np.abs(YY - yc) <= 4.9 + rb_)] = True   # PCB / battery keep-out (+boss)
if LID["enabled"]:                                                                   # pillars need the top wall
    excl[(np.abs(XX) <= 16.5 - LID["lip"] + rb_) & (np.abs(YY) <= 7.5 - LID["lip"] + rb_)] = True
for pad in A["cell"]["pads"]: ex_circle(pad["centre"][0], pad["centre"][1], CP["cup_id"] / 2 + CP["cup_wall"] + SC["boss_od"] / 2 + 0.3)
for pin in A["pins"]: ex_circle(pin["centre"][0], pin["centre"][1], 3.5)
ex_circle(wd["centre"][0], wd["centre"][1], 3.5)
for mp in A["mic_ports"] + [A["led"]]: ex_circle(mp["centre"][0], mp["centre"][1], 4.0)
excl |= ndimage.binary_dilation(neck2d, iterations=int((PS["clearance"] + PS["collar_w"] + SC["boss_od"] / 2 + 0.3) / p))
ex_circle(tip[0], tip[1], SC["min_dist_to_hall_area"])
ex_circle(ch_c[0], ch_c[1], max(CH["inner"]) / 2 + CH["wall"] + SC["boss_od"] / 2 + 0.3)
ok2 = inner_ok & ~excl
pts = np.c_[XX[ok2], YY[ok2]]
screws = []
if len(pts):
    screws.append(pts[np.argmin(pts[:, 0])]); screws.append(pts[np.argmax(pts[:, 0])])
    while len(screws) < SC["max_count"]:
        dmin = np.min([np.linalg.norm(pts - s_, axis=1) for s_ in screws], axis=0)
        if dmin.max() < 8.0: break
        screws.append(pts[np.argmax(dmin)])
for sx, sy in screws:
    ztop_in = -W["cover_top"]; zfo = floor_outer_z(sx, sy)
    add(cover, cyl([sx, sy, (zp + ztop_in) / 2], [0, 0, 1], SC["boss_od"], ztop_in - zp))
    cut(cover, cyl([sx, sy, zp + SC["insert_hole_h"] / 2 - 0.05], [0, 0, 1], SC["insert_hole_d"], SC["insert_hole_h"] + 0.1))
    add(base, cyl([sx, sy, (zfo + zp) / 2], [0, 0, 1], SC["boss_od"], zp - zfo))
    cut(base, cyl([sx, sy, (zfo + zp) / 2], [0, 0, 1], SC["clear_hole"], zp - zfo + 2.0))
    cut(base, cyl([sx, sy, zfo + SC["head_cbore_h"] / 2 - 0.5], [0, 0, 1], SC["head_cbore_d"], SC["head_cbore_h"] + 1.0))
base &= inside
rep["screws"] = [[round(float(a), 2), round(float(b), 2)] for a, b in screws]
log("screws at", rep["screws"])

# ---------------- 10a. hook-in tab at the end without screws (cover tab hooks under a base ledge) ----------------
TB = PR["tab"]
end_x = xb if np.mean([s_[0] for s_ in screws]) < 0 else xa                 # the end opposite the screws
sgn = 1.0 if end_x == xb else -1.0
zone = (sgn * (X - end_x) > 0) & (np.abs(Y - yc) <= TB["width"] / 2 + 1.4)
rin = SE["land_t"]                                                          # inner face of the land, from the skin
base |= inside & zone & (D2 < rin) & (zgrid >= zp - TB["depth"] - 0.6) & below          # deeper land here
slot = zone & (np.abs(Y - yc) <= TB["width"] / 2 + 0.15) & (D2 < rin + 0.01) & (D2 >= rin - TB["hook"] - 0.1) \
       & (zgrid >= zp - TB["depth"]) & (zgrid < zp - TB["depth"] + TB["hook_h"] + 0.15)
base &= ~slot
tz = (zgrid >= zp - TB["depth"] + 0.05) & (zgrid < zp)
tab = zone & (np.abs(Y - yc) <= TB["width"] / 2) & (D2 >= rin + 0.15) & (D2 < rin + 0.15 + TB["t"]) & tz
foot = zone & (np.abs(Y - yc) <= TB["width"] / 2) & (D2 >= rin - TB["hook"]) & (D2 < rin + 0.15) \
       & (zgrid >= zp - TB["depth"] + 0.05) & (zgrid < zp - TB["depth"] + TB["hook_h"])
bridge = zone & (np.abs(Y - yc) <= TB["width"] / 2) & (D2 >= rin - 0.4) & (D2 < rin + 0.15 + TB["t"]) \
         & (zgrid >= zp) & (zgrid < zp + SE["land_h_cover"])                  # ties the tab to the cover land
cover |= (tab | foot | bridge) & inside & ~ndimage.binary_dilation(base)   # keep one voxel of play to the base
rep["tab"] = dict(end_x=round(float(end_x), 2), width=TB["width"], hook=TB["hook"], depth_below_seam=TB["depth"])
del slot, tab, foot, zone

# ---------------- 10b. rigid hook stub joins the halves (outside the seal) + peg socket ----------------
stub_f = stub | (ndimage.binary_dilation(stub, iterations=3) & inside & ~cavity)    # fuse into the wall, not the cavity
cover |= stub_f & ~below
base |= stub_f & below
sock = cyl(ic + peg_axis * (HK["peg_len"] + 0.1) / 2, peg_axis, HK["peg_d"] + 2 * HK["socket_clearance"], HK["peg_len"] + 0.1)
s_, v_ = sock
assert not (cavity[s_] & (v_ <= 0)).any(), "hook peg socket would break into the sealed cavity - shorten peg_len"
cut(cover, sock); cut(base, sock)
rep["hook_joint"]["socket_in"] = "cover" if ic[2] >= zp else "base"

# ---------------- 10c. final guards: the gasket groove stays open, the halves never overlap ----------------
base &= ~groove
ov = cover & base
rep["overlap_voxels_resolved"] = int(ov.sum())
base &= ~ov

# ---------------- 11. meshes & report ----------------
def to_mesh(mask, name):
    ph = sdf.smooth(sdf.sdf_from_solid(mask, p), 0.6)
    m = sdf.mesh(ph, g)
    parts = sorted(m.split(only_watertight=False), key=lambda q: -abs(q.volume))
    dropped = [round(abs(q.volume), 2) for q in parts[1:]]
    if dropped: log(f"{name}: kept main body, dropped {len(dropped)} loose fragments (mm3):", dropped[:12])
    m = parts[0]
    m.export(os.path.join(out, f"EP3_shell_{name}.stl"))
    m.export(os.path.join(out, f"EP3_shell_{name}.3mf"))
    thin = sdf.thin_regions(mask, W["min_check"], p)
    info = dict(watertight=bool(m.is_watertight), bodies_before_cleanup=len(parts), volume_cm3=round(abs(m.volume) / 1000, 3),
                mass_g=round(abs(m.volume) / 1000 * PR["print"]["density_g_cm3"], 2), triangles=len(m.faces),
                extents_mm=np.round(m.extents, 2).tolist(), thinner_than_min_share=round(float(thin.sum() / max(mask.sum(), 1)), 4))
    log(name, info)
    return m, info


meshes = {}
for name, mask in (("cover", cover), ("base", base), ("hook_arm", arm)):
    meshes[name], rep[name] = to_mesh(mask, name)
np.savez_compressed(os.path.join(out, "shell_masks.npz"), cover=cover, base=base, arm=arm, inside=inside, cavity=cavity, lo=g.lo, p=p, zp=zp)
asm = trimesh.Scene()
cols = {"cover": [70, 70, 75, 255], "base": [45, 45, 50, 255], "hook_arm": [200, 90, 30, 255]}
for k_, m in meshes.items():
    mm = m.copy(); mm.visual.face_colors = cols[k_]; asm.add_geometry(mm, node_name=k_)
for t in pod_tris:
    pm = trimesh.Trimesh(t.reshape(-1, 3), np.arange(len(t) * 3).reshape(-1, 3), process=True); pm.visual.face_colors = [25, 25, 25, 255]
    asm.add_geometry(pm, node_name="original_pod")
cellm = trimesh.creation.box(extents=[33.0, 15.0, 1.5]); cellm.apply_translation([0, 0, 0.75]); cellm.visual.face_colors = [30, 50, 130, 255]
asm.add_geometry(cellm, node_name="solar_cell")
asm.export(os.path.join(out, "EP3_shell_assembly_S.glb"))
json.dump(rep, open(os.path.join(data, "shell_report.json"), "w"), indent=1)
log(json.dumps({k_: rep[k_] for k_ in ("parting_z", "clear_height_mm", "screws", "seal", "hook")}, indent=1))
