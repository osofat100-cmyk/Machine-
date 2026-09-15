# `sim/` — driving the model and drawing it

Renders the arm running a pick-and-place cycle to video. Entry point is
[`../simulate.py`](../simulate.py).

```bash
cd cad
python3 simulate.py                  # build/machine.mp4
python3 simulate.py --check-only     # solve and check, render nothing
```

## What is actually on screen

The arm is the CAD model. Not a stand-in, not a re-model: the same
eleven solids `robot_arm/parts.py` exports to STEP, placed by
`robot_arm/assembly.py`'s own `build_assembly`, at poses
`robot_arm/assembly.py`'s own `joint_frames` resolves. If the STEP file
is wrong, the video is wrong in the same way and at the same joint.

The floor, the two fixtures and the orange block are scenery. They are
boxes generated here, and they are the only things in frame that are not
CAD.

## Modules

| file | what it does |
|---|---|
| `kinematics.py` | tool-centre point, damped-least-squares IK, quintic blending |
| `program.py` | the motion program, expanded to one solved state per frame |
| `scene.py` | tessellates the eleven prototypes once; re-places them per frame |
| `raster.py` | z-buffered software rasteriser, and camera fitting |
| `render.py` | shading, ground shadow, static/dynamic compositing |
| `hud.py` | the telemetry overlay |

## Three decisions worth explaining

**The placements are read out of the assembly, not copied.** `assembly.py`
says driving the pose "is a matter of changing `ArmParams.joints` — no
geometry is rebuilt, only re-placed", so that is what happens.
`scene.placements` calls the real `build_assembly` with the eleven solids
swapped for unit cubes, purely to read back each instance's `Location`,
then moves cached triangles by those transforms. Rebuilding the solids
 per frame would cost 1.3 s each; more to the point, a re-implementation of
the chain could drift from the one that makes the STEP file, and this one
cannot. `test_simulate.py` compares all fifteen transforms against the
real assembly exactly.

**Z-buffer, not depth sort.** A painter's algorithm gets self-overlap
wrong, and an arm folding back over itself is nothing but self-overlap.
Backfaces are *not* culled: a tessellation that has been through boolean
cuts can carry inconsistently wound faces, so the shading normal is
turned toward the camera instead, which cannot punch holes in a part.

**The camera is fitted, not placed.** Every vertex the arm visits across
the whole program is collected and the camera distance bisected until all
of it lands inside the frame. Framing a robot by eye works right up until
the one pose you were not looking at.

## Speed

A frame is about 44,000 triangles at 2560×1440, and the expensive part is
not the arm — it is the ground plane, a few triangles each covering a
quarter of the screen. So the floor and fixtures are shaded once into a
cached layer with its own depth buffer, and each frame rasterises only
what moves, compositing against that depth. That, rectangular
bounding-box buckets for scan conversion, and a sort-based depth resolve
in place of `np.maximum.at`, together take a frame from 9.4 s to 0.8 s.

No GPU, no OpenGL, no display: numpy and Pillow.
