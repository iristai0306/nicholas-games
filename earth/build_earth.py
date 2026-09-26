"""
build_earth.py — hyper-realistic Earth in Blender (Cycles CPU)

Usage:
  blender -b -P build_earth.py -- stills          # hero stills @1080p
  blender -b -P build_earth.py -- test            # fast low-res preview
  blender -b -P build_earth.py -- anim            # rotating Earth clip

Textures (blender-assets/textures/):
  8k_earth_daymap.jpg, 8k_earth_nightmap.jpg, 8k_earth_clouds.jpg,
  8k_earth_normal_map.tif, earth_spec.jpg, stars.png
"""
import bpy, sys, math, os
from mathutils import Vector

ROOT = "/root/.openclaw/workspace-wayne/blender-assets"
TEX  = os.path.join(ROOT, "textures")
OUT  = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["stills"]
MODE = argv[0] if argv else "stills"

# ------------------------------------------------------------------
# scene reset
# ------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 128
sc.cycles.use_denoising = False          # not compiled in this build
sc.cycles.max_bounces = 12
sc.cycles.transparent_max_bounces = 16
sc.cycles.glare_compensate = False
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGB'
try:
    sc.view_settings.view_transform = 'AgX'
except Exception:
    sc.view_settings.view_transform = 'Filmic'
sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.42


def img(path, non_color=False):
    im = bpy.data.images.load(path)
    im.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    return im


# ------------------------------------------------------------------
# world — starfield environment
# ------------------------------------------------------------------
world = bpy.data.worlds.new("Space")
sc.world = world
world.use_nodes = True
wnt = world.node_tree
wnt.nodes.clear()
wout = wnt.nodes.new("ShaderNodeOutputWorld")
wbg  = wnt.nodes.new("ShaderNodeBackground")
wtex = wnt.nodes.new("ShaderNodeTexEnvironment")
wtex.image = img(os.path.join(TEX, "stars.png"))
wbg.inputs["Strength"].default_value = 1.0
wnt.links.new(wtex.outputs["Color"], wbg.inputs["Color"])
wnt.links.new(wbg.outputs["Background"], wout.inputs["Surface"])


# ------------------------------------------------------------------
# Earth
# ------------------------------------------------------------------
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=180, ring_count=90)
earth = bpy.context.active_object
earth.name = "Earth"
bpy.ops.object.shade_smooth()

day_tex    = cmd = None
emat = bpy.data.materials.new("EarthMat")
emat.use_nodes = True
nt = emat.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Roughness"].default_value = 0.62

# day colour
t_day = nt.nodes.new("ShaderNodeTexImage"); t_day.image = img(os.path.join(TEX, "8k_earth_daymap.jpg"))
nt.links.new(t_day.outputs["Color"], bsdf.inputs["Base Color"])

# normal relief
t_nrm = nt.nodes.new("ShaderNodeTexImage")
try:
    t_nrm.image = img(os.path.join(TEX, "8k_earth_normal_map.tif"), non_color=True)
    print("using 8k tif normal map")
except Exception as e:
    t_nrm.image = img(os.path.join(TEX, "earth_normal.jpg"), non_color=True)
    print("fallback normal map:", e)
nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = 0.85
nt.links.new(t_nrm.outputs["Color"], nmap.inputs["Color"])
nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

# ocean specular -> roughness (specmap: ocean bright)
t_spec = nt.nodes.new("ShaderNodeTexImage"); t_spec.image = img(os.path.join(TEX, "earth_spec.jpg"), non_color=True)
sp_ramp = nt.nodes.new("ShaderNodeValToRGB")
sp_ramp.color_ramp.elements[0].position = 0.20; sp_ramp.color_ramp.elements[0].color = (0.90, 0.90, 0.90, 1)  # land = rough
sp_ramp.color_ramp.elements[1].position = 0.85; sp_ramp.color_ramp.elements[1].color = (0.42, 0.42, 0.42, 1)  # ocean = glossy
nt.links.new(t_spec.outputs["Color"], sp_ramp.inputs["Fac"])
nt.links.new(sp_ramp.outputs["Color"], bsdf.inputs["Roughness"])

# night lights on the dark side
t_night = nt.nodes.new("ShaderNodeTexImage"); t_night.image = img(os.path.join(TEX, "8k_earth_nightmap.jpg"))
geo = nt.nodes.new("ShaderNodeNewGeometry")
SUN_DIR = Vector((0.60, 0.40, -0.69)).normalized()
sun_vec = nt.nodes.new("ShaderNodeCombineXYZ")
sun_vec.inputs[0].default_value = SUN_DIR.x
sun_vec.inputs[1].default_value = SUN_DIR.y
sun_vec.inputs[2].default_value = SUN_DIR.z
dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'
nt.links.new(geo.outputs["Normal"], dot.inputs[0])
nt.links.new(sun_vec.outputs["Vector"], dot.inputs[1])
lit = nt.nodes.new("ShaderNodeMapRange")
lit.inputs["From Min"].default_value = -0.12
lit.inputs["From Max"].default_value = 0.22
lit.inputs["To Min"].default_value = 1.0     # full night
lit.inputs["To Max"].default_value = 0.0     # full day
nt.links.new(dot.outputs["Value"], lit.inputs["Value"])
night_mix = nt.nodes.new("ShaderNodeMix"); night_mix.data_type = 'RGBA'; night_mix.blend_type = 'MULTIPLY'
night_mix.inputs["Factor"].default_value = 1.0
nt.links.new(t_night.outputs["Color"], night_mix.inputs[6])
nt.links.new(lit.outputs["Result"], night_mix.inputs[7])
nt.links.new(night_mix.outputs[2], bsdf.inputs["Emission Color"])
bsdf.inputs["Emission Strength"].default_value = 2.6

nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
earth.data.materials.append(emat)


# ------------------------------------------------------------------
# Clouds shell
# ------------------------------------------------------------------
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.008, segments=180, ring_count=90)
clouds = bpy.context.active_object
clouds.name = "Clouds"
bpy.ops.object.shade_smooth()

cmat = bpy.data.materials.new("CloudMat")
cmat.use_nodes = True
cmat.blend_method = 'BLEND'
cnt = cmat.node_tree; cnt.nodes.clear()
cout = cnt.nodes.new("ShaderNodeOutputMaterial")
cbsdf = cnt.nodes.new("ShaderNodeBsdfPrincipled")
cbsdf.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1)
cbsdf.inputs["Roughness"].default_value = 0.95
t_cl = cnt.nodes.new("ShaderNodeTexImage"); t_cl.image = img(os.path.join(TEX, "8k_earth_clouds.jpg"), non_color=True)
cl_ramp = cnt.nodes.new("ShaderNodeValToRGB")
cl_ramp.color_ramp.elements[0].position = 0.30; cl_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
cl_ramp.color_ramp.elements[1].position = 0.66; cl_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
cnt.links.new(t_cl.outputs["Color"], cl_ramp.inputs["Fac"])
cnt.links.new(cl_ramp.outputs["Color"], cbsdf.inputs["Alpha"])
cnt.links.new(cbsdf.outputs["BSDF"], cout.inputs["Surface"])
clouds.data.materials.append(cmat)
clouds.visible_shadow = False


# ------------------------------------------------------------------
# Atmosphere rim shell
# ------------------------------------------------------------------
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.035, segments=140, ring_count=70)
atmo = bpy.context.active_object
atmo.name = "Atmosphere"
bpy.ops.object.shade_smooth()

amat = bpy.data.materials.new("AtmoMat")
amat.use_nodes = True
amat.blend_method = 'BLEND'
amat.use_backface_culling = False
ant = amat.node_tree; ant.nodes.clear()
aout = ant.nodes.new("ShaderNodeOutputMaterial")
mix = ant.nodes.new("ShaderNodeMixShader")
trans = ant.nodes.new("ShaderNodeBsdfTransparent")
emis = ant.nodes.new("ShaderNodeEmission")
lw = ant.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.55
aram = ant.nodes.new("ShaderNodeValToRGB")
aram.color_ramp.elements[0].position = 0.80; aram.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1)
aram.color_ramp.elements[1].position = 0.99; aram.color_ramp.elements[1].color = (0.20, 0.52, 1.0, 1)
emis.inputs["Strength"].default_value = 2.4
ant.links.new(lw.outputs["Facing"], aram.inputs["Fac"])
ant.links.new(aram.outputs["Color"], emis.inputs["Color"])
ant.links.new(aram.outputs["Color"], mix.inputs["Fac"])
ant.links.new(trans.outputs["BSDF"], mix.inputs[1])
ant.links.new(emis.outputs["Emission"], mix.inputs[2])
ant.links.new(mix.outputs["Shader"], aout.inputs["Surface"])
atmo.data.materials.append(amat)


# ------------------------------------------------------------------
# Sun — light + visible warm disk (glare source)
# ------------------------------------------------------------------
bpy.ops.object.light_add(type='SUN', location=(SUN_DIR * 60.0))
sun = bpy.context.active_object
sun.data.energy = 4.2
sun.data.angle = math.radians(0.6)
sun.rotation_euler = (0, 0, 0)
# aim at origin
d = -SUN_DIR
sun.rotation_euler = Vector((0, 0, -1)).rotation_difference(d).to_euler()

# disk
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.9, location=(SUN_DIR * 26.0), segments=48, ring_count=24)
disk = bpy.context.active_object
disk.name = "SunDisk"
dmat = bpy.data.materials.new("SunMat"); dmat.use_nodes = True
dnt = dmat.node_tree; dnt.nodes.clear()
dout = dnt.nodes.new("ShaderNodeOutputMaterial")
dem = dnt.nodes.new("ShaderNodeEmission")
dem.inputs["Color"].default_value = (1.0, 0.96, 0.90, 1)
dem.inputs["Strength"].default_value = 60.0
dnt.links.new(dem.outputs["Emission"], dout.inputs["Surface"])
disk.data.materials.append(dmat)
disk.visible_shadow = False
# halo sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.7, location=(SUN_DIR * 26.0), segments=48, ring_count=24)
halo = bpy.context.active_object
halo.name = "SunHalo"
hmat = bpy.data.materials.new("HaloMat"); hmat.use_nodes = True; hmat.blend_method = 'BLEND'
hnt = hmat.node_tree; hnt.nodes.clear()
hout = hnt.nodes.new("ShaderNodeOutputMaterial")
hlw = hnt.nodes.new("ShaderNodeLayerWeight"); hlw.inputs["Blend"].default_value = 0.4
hramp = hnt.nodes.new("ShaderNodeValToRGB")
hramp.color_ramp.elements[0].position = 0.0; hramp.color_ramp.elements[0].color = (1.0, 0.85, 0.6, 1)
hramp.color_ramp.elements[1].position = 1.0; hramp.color_ramp.elements[1].color = (0, 0, 0, 1)
hem = hnt.nodes.new("ShaderNodeEmission"); hem.inputs["Strength"].default_value = 3.0
hmix = hnt.nodes.new("ShaderNodeMixShader")
htr = hnt.nodes.new("ShaderNodeBsdfTransparent")
hnt.links.new(hlw.outputs["Facing"], hramp.inputs["Fac"])
hnt.links.new(hramp.outputs["Color"], hem.inputs["Color"])
hnt.links.new(hramp.outputs["Color"], hmix.inputs["Fac"])
hnt.links.new(htr.outputs["BSDF"], hmix.inputs[1])
hnt.links.new(hem.outputs["Emission"], hmix.inputs[2])
hnt.links.new(hmix.outputs["Shader"], hout.inputs["Surface"])
halo.data.materials.append(hmat)
halo.visible_shadow = False


# ------------------------------------------------------------------
# Camera + compositor glare
# ------------------------------------------------------------------
cam_data = bpy.data.cameras.new("Cam"); cam_data.lens = 14
cam = bpy.data.objects.new("Cam", cam_data); sc.collection.objects.link(cam)
sc.camera = cam


def set_sun_light(d):
    """Direction the sunlight comes FROM (drives lighting + night-lights mask)."""
    d = Vector(d).normalized()
    sun_vec.inputs[0].default_value = d.x
    sun_vec.inputs[1].default_value = d.y
    sun_vec.inputs[2].default_value = d.z
    sun.rotation_euler = Vector((0, 0, -1)).rotation_difference(-d).to_euler()


def set_sun_disk(d):
    """Where the visible sun disk sits in the sky (glare source)."""
    d = Vector(d).normalized()
    disk.location = d * 26.0
    halo.location = d * 26.0


def set_sun(d):
    set_sun_light(d)
    set_sun_disk(d)


def look_at(obj, target):
    d = (Vector(target) - obj.location)
    obj.rotation_euler = Vector((0, 0, -1)).rotation_difference(d.normalized()).to_euler()


def build_glare():
    sc.use_nodes = True
    ct = sc.node_tree
    ct.nodes.clear()
    rl = ct.nodes.new("CompositorNodeRLayers")
    glare = ct.nodes.new("CompositorNodeGlare")
    try:
        glare.glare_type = 'FOG_GLOW'
    except Exception:
        pass
    for attr, val in [("quality", 'HIGH'), ("threshold", 1.0), ("size", 6), ("mix", 0.0)]:
        try: setattr(glare, attr, val)
        except Exception: pass
    streak = ct.nodes.new("CompositorNodeGlare")
    try: streak.glare_type = 'STREAKS'
    except Exception: pass
    for attr, val in [("quality", 'HIGH'), ("threshold", 1.3), ("streaks", 4), ("angle_offset", 0.25), ("fade", 0.9), ("mix", 0.35)]:
        try: setattr(streak, attr, val)
        except Exception: pass
    ghosts = ct.nodes.new("CompositorNodeGlare")
    try: ghosts.glare_type = 'GHOSTS'
    except Exception: pass
    for attr, val in [("quality", 'HIGH'), ("threshold", 1.1), ("iterations", 3), ("color_modulation", 0.6), ("mix", 0.45)]:
        try: setattr(ghosts, attr, val)
        except Exception: pass
    comp = ct.nodes.new("CompositorNodeComposite")
    ct.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ct.links.new(glare.outputs["Image"], streak.inputs["Image"])
    ct.links.new(streak.outputs["Image"], ghosts.inputs["Image"])
    ct.links.new(ghosts.outputs["Image"], comp.inputs["Image"])


def render_to(path, res=(1920, 1080), samples=128):
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


# ------------------------------------------------------------------
def setup_camera(kind):
    if kind == "hero":
        cam.location = (0.0, 0.05, 2.35)
    elif kind == "close":
        cam.location = (-0.55, 0.35, 2.05)
    elif kind == "day":
        cam.location = (0.0, 0.05, 2.55)
    look_at(cam, (0, 0, 0))


build_glare()

if MODE == "save":
    set_sun_light((0.88, 0.22, 0.42))
    set_sun_disk((0.62, 0.46, -0.64))
    setup_camera("hero")
    blend_path = os.path.join(OUT, "earth.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("SAVED", blend_path)
    import sys as _s; _s.exit(0)

elif MODE == "test":
    variant = argv[1] if len(argv) > 1 else "hero"
    if variant == "day":
        set_sun((0.30, 0.26, 0.92))
        setup_camera("day")
    else:
        set_sun_light((0.88, 0.22, 0.42))
        set_sun_disk((0.62, 0.46, -0.64))
        setup_camera("hero")
    render_to(os.path.join(OUT, "earth_test.png"), res=(560, 315), samples=28)

elif MODE == "stills":
    # hero — lit Earth with the sun + lens glare in the corner
    set_sun_light((0.88, 0.22, 0.42))
    set_sun_disk((0.62, 0.46, -0.64))
    setup_camera("hero")
    render_to(os.path.join(OUT, "earth_hero.png"), res=(1920, 1080), samples=130)
    # day side — pure daylit Earth
    set_sun_light((0.30, 0.26, 0.92))
    set_sun_disk((0.30, 0.26, 0.92))
    setup_camera("day")
    render_to(os.path.join(OUT, "earth_day.png"), res=(1920, 1080), samples=130)

elif MODE == "anim":
    set_sun_light((0.88, 0.22, 0.42))
    set_sun_disk((0.62, 0.46, -0.64))
    setup_camera("hero")
    FRAMES = 72                       # 3 s @ 24fps, seamless 360 loop
    ROT = math.radians(360)           # full spin -> seamless loop
    sc.frame_start, sc.frame_end = 1, FRAMES
    sc.render.fps = 24
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
    sc.cycles.samples = 24
    earth.rotation_mode = 'XYZ'
    clouds.rotation_mode = 'XYZ'
    for f in (1, FRAMES):
        frac = (f - 1) / (FRAMES - 1)
        earth.rotation_euler[2] = ROT * frac
        clouds.rotation_euler[2] = ROT * frac + 0.35 * math.sin(frac * math.pi)
        earth.keyframe_insert("rotation_euler", index=2, frame=f)
        clouds.keyframe_insert("rotation_euler", index=2, frame=f)
    for fc in earth.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    for fc in clouds.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    framedir = os.path.join(OUT, "earth_anim")
    sc.render.filepath = os.path.join(framedir, "f")
    bpy.ops.render.render(animation=True)
    print("ANIM DONE ->", framedir)
