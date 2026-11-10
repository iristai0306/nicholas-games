"""
PTD menu hero — 3D replacement for the flat SVG poster.

Design brief: two plebs mid-fight, still (a poster, not an action shot),
concentrated in the centre of frame, with the sides and background falling
off into soft blur.

How the "blurry sides" is done (layered, so it survives any crop):
  1. real depth of field from the camera (fast aperture, long-ish lens)
  2. the arena only exists near the middle — pillars and bokeh sit wide/back
  3. a compositor pass that blurs the whole frame and blends that blur back in
     only at the edges, driven by a soft radial mask

Run:
  blender -b -P menu_hero.py                 # final
  PREVIEW=1 blender -b -P menu_hero.py       # fast low-res check
  ONLY=wide blender -b -P menu_hero.py
  COMP=0 blender -b -P menu_hero.py          # no post, for debugging
"""
import bpy, os, math, random
from mathutils import Vector

ROOT = "/root/.openclaw/workspace-wayne/nicholas-games/pleb-td"
ART = os.path.join(ROOT, "art")
os.makedirs(ART, exist_ok=True)

G = {"__name__": "plebs_lib"}
exec(open(os.path.join(ROOT, "blender", "plebs.py")).read(), G)
clear_scene = G["clear_scene"]
build_pleb  = G["build_pleb"]
mat         = G["mat"]
sphere      = G["sphere"]
stick       = G["stick"]
cyl         = G["cyl"]

PREVIEW  = os.environ.get("PREVIEW") == "1"
ONLY     = os.environ.get("ONLY", "").strip()
USE_COMP = os.environ.get("COMP", "1") == "1"
_S       = int(os.environ.get("SAMPLES", "0") or 0)
SAMPLES  = _S or (16 if PREVIEW else 160)
BODY_Z   = 0.98

# ------------------------------------------------------------------ materials
def emat(name, color, strength=6.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*color, 1.0)
    em.inputs[1].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m

WOOD = ROCK = FLOOR = GLOW_C = GLOW_W = None
MATS = {}

def build_materials():
    """Must run AFTER clear_scene() — read_factory_settings invalidates datablocks."""
    global WOOD, ROCK, FLOOR, GLOW_C, GLOW_W
    WOOD   = mat("wood",    (0.26, 0.17, 0.10), rough=0.82)
    ROCK   = mat("rock",    (0.028, 0.038, 0.055), rough=0.94)
    FLOOR  = mat("floor3d", (0.016, 0.024, 0.037), rough=0.34)
    GLOW_C = emat("glow_cyan", (0.30, 0.72, 1.00), 9.0)
    GLOW_W = emat("glow_warm", (1.00, 0.70, 0.28), 8.0)
    for i in range(12):
        MATS[i] = emat(f"spark{i}", (1.0, 0.86, 0.48), 22.0)

def setmat(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)
    return o

# ------------------------------------------------------------------ lights
def area(name, loc, energy, size, color=(1, 1, 1), target=(0, 0, 1.2)):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = energy; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o

def point(name, loc, energy, color=(1, 1, 1), radius=0.3):
    d = bpy.data.lights.new(name, 'POINT')
    d.energy = energy; d.color = color; d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    return o

# ------------------------------------------------------------------ the arena
def build_arena():
    bpy.ops.mesh.primitive_plane_add(size=90, location=(0, 10, 0))
    setmat(bpy.context.object, FLOOR)

    # arena floor glow strips receding into the dark
    for y, xr in ((3.2, 2.8), (4.9, 3.4), (7.2, 4.2)):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, y, 0.004))
        p = bpy.context.object
        p.scale = (xr, 0.009, 1)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        setmat(p, GLOW_C)

    random.seed(11)
    # flanking monoliths — pushed WIDE so they only ever clip the frame edges
    for t in range(4):
        for side in (-1, 1):
            x = side * (2.9 + t * 1.45) + random.uniform(-0.15, 0.15)
            y = 3.0 + t * 2.4 + random.uniform(-0.3, 0.3)
            h = random.uniform(2.0, 4.2)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2))
            c = bpy.context.object
            c.scale = (random.uniform(0.45, 0.9), random.uniform(0.45, 0.9), h)
            c.rotation_euler = (0, 0, random.uniform(-0.4, 0.4))
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            setmat(c, ROCK)

    # near side walls, close enough to the lens that they land in frame at the
    # extreme left/right — this is the detail the edge-blur pass works on
    for side in (-1, 1):
        x = side * 2.30
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 1.15, 1.15))
        w = bpy.context.object
        w.scale = (0.55, 1.55, 2.30)
        w.rotation_euler = (0, 0, side * math.radians(6))
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        setmat(w, mat("wall_side", (0.020, 0.028, 0.045), rough=0.9))
        # glowing seam on the inner face so it is not a black silhouette
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x - side * 0.28, 1.15, 1.30))
        gs = bpy.context.object
        gs.scale = (0.020, 1.35, 1.9)
        gs.rotation_euler = (math.radians(90), 0, side * math.radians(6))
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        setmat(gs, emat(f"seam{side}", (0.30, 0.72, 1.0) if side < 0 else (1.0, 0.52, 0.34), 2.0))

    # distant emissive motes → soft bokeh discs once DOF bites
    for i in range(44):
        x = random.uniform(-8.5, 8.5)
        y = random.uniform(6.5, 16.0)
        z = random.uniform(0.4, 4.4)
        r = random.uniform(0.05, 0.13)
        m = GLOW_W if random.random() < 0.26 else GLOW_C
        s = sphere(f"bokeh{i}", (x, y, z), r, m, segs=12)
        setmat(s, m)

    # two dim shapes hugging the very bottom corners — frame the shot without
    # ever reading as objects
    for i, (x, z, r) in enumerate(((-1.34, -0.16, 0.30), (1.38, -0.20, 0.32))):
        b = sphere(f"fg{i}", (x, -2.7, z), r, ROCK, segs=16)
        b.scale = (1.35, 1.0, 0.9)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        setmat(b, ROCK)

# ------------------------------------------------------------------ the plebs
MAGE_POS  = Vector((-0.92, -0.18, 0))
BRAWL_POS = Vector(( 0.92,  0.06, 0))
MAGE_ROT  = math.radians(20)
BRAWL_ROT = math.radians(-20)

def build_mage():
    """Cone hat, no auto gear — the staff is placed explicitly so it reads
    as being held rather than growing out of his shoulder."""
    p = build_pleb("hero_mage", (0.20, 0.46, 0.92), hat="cone")
    p.location = MAGE_POS
    p.rotation_euler = (math.radians(-2), 0, MAGE_ROT)
    bpy.context.view_layer.update()

    # staff: from low in front of him up to a crystal near the middle of frame
    grip = Vector((MAGE_POS.x + 0.34, -0.30, 0.56))
    tip  = Vector((-0.30, -0.40, 1.52))
    stick("mage_staff", grip, tip, 0.030, mat("staff_w", (0.21, 0.13, 0.075), rough=0.85))

    # fist on the shaft so the grip is unambiguous
    grip2 = grip + (tip - grip) * 0.16
    stick("mage_fist", (MAGE_POS.x + 0.62, -0.14, 0.90), grip2, 0.042,
          mat("ink_fa", (0.055, 0.055, 0.062), rough=0.75))

    orb = sphere("mage_orb", tip, 0.062, GLOW_C, segs=24)
    setmat(orb, emat("orb_hot", (0.62, 0.88, 1.00), 6.0))
    point("mage_orb_light", tip, 26, (0.40, 0.76, 1.00), 0.26)
    return p, tip

def build_brawler(meet):
    """Club raised on a clear diagonal, head stopping just short of the crystal."""
    p = build_pleb("hero_brawler", (0.95, 0.34, 0.22))
    p.location = BRAWL_POS
    p.rotation_euler = (math.radians(-2), 0, BRAWL_ROT)
    bpy.context.view_layer.update()

    grip   = Vector((BRAWL_POS.x - 0.34, -0.30, 0.54))
    head_c = Vector(( 0.26,            -0.44, 1.60))

    stick("club_shaft", grip, head_c, 0.046, WOOD)
    knob = sphere("club_head", head_c, 0.120, WOOD, segs=20)
    knob.scale = (1.0, 1.0, 1.25)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    setmat(knob, WOOD)

    # forearm up to the grip, so it reads as held
    grip2 = grip + (head_c - grip) * 0.13
    stick("brawler_fist",
          (BRAWL_POS.x - 0.62, -0.14, 0.90), grip2, 0.042,
          mat("ink_fb", (0.055, 0.055, 0.062), rough=0.75))
    return p

def build_impact(meet):
    halo = sphere("impact_halo", meet, 0.085, GLOW_W, segs=24)
    setmat(halo, emat("impact_soft", (1.0, 0.66, 0.30), 4.5))
    core = sphere("impact_core", meet, 0.030, GLOW_W, segs=20)
    setmat(core, emat("impact_hot", (1.0, 0.95, 0.82), 30.0))
    point("impact_light", meet, 30, (1.0, 0.82, 0.52), 0.20)

    random.seed(5)
    for i in range(15):
        a = random.uniform(0, math.tau)
        d = random.uniform(0.16, 0.50)
        s = sphere(f"spark{i}",
                   (meet.x + math.cos(a) * d * 1.15,
                    meet.y + random.uniform(-0.07, 0.07),
                    meet.z + math.sin(a) * d),
                   random.uniform(0.009, 0.020), GLOW_W, segs=8)
        setmat(s, MATS[i % 12])

# ------------------------------------------------------------------ scene
def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = SAMPLES
    # this Blender build ships without OpenImageDenoiser, so control noise
    # with clamped indirect + slightly higher samples instead
    sc.cycles.use_denoising = False
    sc.cycles.sample_clamp_indirect = 2.5
    sc.cycles.blur_glossy = 1.4
    sc.cycles.max_bounces = 4
    sc.cycles.transmission_bounces = 2
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Filmic'
    sc.view_settings.look = 'Medium High Contrast'
    sc.view_settings.exposure = 0.10

    w = bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.013, 0.022, 0.041, 1)
    bg.inputs[1].default_value = 1.0

    area("key",   (-2.5, -3.1, 4.4), 540, 3.0, (1.00, 0.94, 0.86), (0, 0, 1.34))
    area("fill",  ( 3.0, -2.2, 2.1), 190, 4.5, (0.60, 0.80, 1.00), (0, 0, 1.15))
    area("rim",   ( 0.5,  3.3, 3.5), 700, 3.0, (0.40, 0.70, 1.00), (0, 0.2, 1.32))
    area("sideL", (-3.2,  0.9, 2.0), 150, 2.2, (0.34, 0.60, 1.00), (-0.9, 0, 1.10))
    area("sideR", ( 3.0,  1.0, 1.9), 170, 2.2, (1.00, 0.46, 0.32), ( 0.9, 0, 1.00))
    return sc

def setup_compositor(sc):
    """
    Glare, then an edge-blur pass:
      blurred copy of the frame + soft radial mask -> mix at the edges only
    """
    sc.use_nodes = True
    t = sc.node_tree
    t.nodes.clear()
    N = t.nodes.new

    rl = N("CompositorNodeRLayers")
    gl = N("CompositorNodeGlare")
    gl.glare_type = 'FOG_GLOW'; gl.quality = 'HIGH'
    gl.threshold = 1.05; gl.size = 8; gl.mix = 0.0
    t.links.new(rl.outputs["Image"], gl.inputs["Image"])

    # --- full-frame blur
    bl = N("CompositorNodeBlur")
    bl.filter_type = 'GAUSS'
    bl.use_relative = False
    bl.factor_x = 62.0; bl.factor_y = 62.0
    t.links.new(gl.outputs["Image"], bl.inputs["Image"])

    # --- soft radial mask: white in the centre, black outside.
    # Wide ellipse + heavy blur ramp = the falloff never resolves into a ring.
    ell = N("CompositorNodeEllipseMask")
    ell.mask_type = 'ADD'
    ell.x, ell.y = 0.5, 0.5
    ell.width, ell.height = 0.78, 0.72
    mb = N("CompositorNodeBlur")
    mb.filter_type = 'GAUSS'
    mb.use_relative = True
    mb.factor_x = 0.30; mb.factor_y = 0.30
    t.links.new(ell.outputs["Mask"], mb.inputs["Image"])

    # --- edge mask = 1 - centre
    inv = N("CompositorNodeInvert")
    inv.inputs["Fac"].default_value = 1.0
    t.links.new(mb.outputs[0], inv.inputs["Color"])

    # --- blend sharp centre over blurred frame, weighted by edge mask
    mix = N("CompositorNodeMixRGB")
    mix.blend_type = 'MIX'
    mix.inputs["Fac"].default_value = 1.0
    t.links.new(inv.outputs["Color"], mix.inputs[0])
    t.links.new(gl.outputs["Image"], mix.inputs[1])   # sharp
    t.links.new(bl.outputs["Image"], mix.inputs[2])   # blurred

    comp = N("CompositorNodeComposite")
    t.links.new(mix.outputs["Image"], comp.inputs["Image"])

def camera(name, loc, target, lens, fstop):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = 36.0
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 9
    cd.dof.aperture_rotation = math.radians(12)
    cd.dof.focus_distance = (Vector(target) - Vector(loc)).length
    cam = bpy.data.objects.new(name, cd)
    bpy.context.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return cam

def render(key, res, cam, sc):
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.camera = cam
    out = os.path.join(ART, f"menu-hero-3d-{key}{'-preview' if PREVIEW else ''}.png")
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("RENDERED", out)

# ------------------------------------------------------------------ main
def main():
    clear_scene()
    build_materials()
    sc = setup_scene()
    build_arena()
    _, orb_tip = build_mage()
    build_brawler(orb_tip)
    build_impact(Vector((-0.005, -0.44, 1.575)))
    if USE_COMP:
        setup_compositor(sc)
    bpy.context.view_layer.update()

    focus = (0.0, 0.0, 1.05)

    # poster is concentrated: subject fills the frame, edges fall away
    camP = camera("camP", (0.00, -6.60, 1.36), focus, 76, 1.25)
    camW = camera("camW", (0.00, -6.30, 1.36), focus, 54, 1.5)

    if ONLY in ("", "portrait", "tall"):
        render("tall", (880, 1280), camP, sc)
    if ONLY in ("", "wide"):
        render("wide", (1600, 768), camW, sc)

if __name__ == "__main__":
    main()
