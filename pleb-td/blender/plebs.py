"""
PLEBANIA 3D — canonical pleb generator for Blender 4.0
A pleb = white sphere + thin stick limbs + two deadpan eye slits + a small diagonal mouth.
Gear is the only thing that changes between classes.
Run: blender -b -P plebs.py
"""
import bpy, math, os
from mathutils import Vector

ROOT = "/root/.openclaw/workspace-wayne/nicholas-games/pleb-td"
OUT = os.path.join(ROOT, "models")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- proportions
# feet at z=0, total height 1.50, body is a sphere of radius 0.52
R = 0.52
BODY_Z = 1.50 - R          # 0.98
LEG_TOP = BODY_Z - R * 0.55
INK = (0.055, 0.055, 0.062)

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, color, rough=0.62, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    m.use_backface_culling = False
    m.diffuse_color = (*color, 1.0)
    return m

def _finish(obj, name, m, bevel=0.0, smooth=True):
    obj.name = name
    if m:
        obj.data.materials.append(m)
    if bevel > 0:
        md = obj.modifiers.new("bev", 'BEVEL')
        md.width = bevel
        md.segments = 2
        md.limit_method = 'ANGLE'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=md.name)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj

def sphere(name, loc, r, m, scale=(1, 1, 1), segs=32):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=segs // 2, location=loc)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, name, m)

def cube(name, loc, size, m, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = Vector(size) if isinstance(size, (tuple, list)) else Vector((size,) * 3)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, name, m, bevel)

def stick(name, p0, p1, radius, m, verts=10):
    """Thin cylinder from p0 to p1 — the pleb's stick limbs."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    mid = (a + b) / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=d.length, location=mid, vertices=verts)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, name, m, smooth=True)

def cone(name, loc, r, h, m, verts=20, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=0, depth=h, location=loc, rotation=rot, vertices=verts)
    return _finish(bpy.context.object, name, m)

def cyl(name, loc, r, h, m, rot=(0, 0, 0), verts=20):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, rotation=rot, vertices=verts)
    return _finish(bpy.context.object, name, m)

def join(objs, name):
    for o in bpy.data.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.object
    o.name = name
    o.data.name = name + "_mesh"
    # join keeps the active object's origin, so the mesh ends up offset in local
    # space. Snap the origin to the world origin without moving the geometry,
    # otherwise every pleb gets shifted down by its body height.
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    return o

# ---------------------------------------------------------------- the pleb
def build_pleb(name, accent=(0.98, 0.80, 0.18), *, s=1.0, hat=None, gear=None,
               body_scale=1.0, arm_lift=0.0):
    m_body = mat("body", (0.985, 0.982, 0.972), rough=0.55)     # <- tinted per-enemy in game
    m_ink = mat("ink", INK, rough=0.75)
    m_acc = mat(name + "_accent", accent, rough=0.4)
    m_white = mat("eye_white", (0.99, 0.99, 0.99), rough=0.3)

    parts = []
    fx = -1.0                                   # front is -Y

    # ---------- body: one plain white sphere ----------
    parts.append(sphere(f"{name}_body", (0, 0, BODY_Z), R * body_scale, m_body, segs=40))

    # ---------- stick legs ----------
    for sx in (-1, 1):
        parts.append(stick(f"{name}_leg{sx}",
                           (sx * 0.155, 0, LEG_TOP),
                           (sx * 0.245, 0, 0.045), 0.042, m_ink))

    # ---------- stick arms (right one out, left one down — the pleb pose) ----------
    parts.append(stick(f"{name}_armL",
                       (-0.40, 0, BODY_Z - 0.03),
                       (-0.74, 0, BODY_Z - 0.16 + arm_lift), 0.042, m_ink))
    parts.append(stick(f"{name}_armR",
                       (0.40, 0, BODY_Z - 0.03),
                       (0.78, 0, BODY_Z - 0.05 - arm_lift), 0.042, m_ink))

    # ---------- face: two deadpan slits + a small diagonal mouth ----------
    fy = fx * (R * 0.985)
    eye_z = BODY_Z + 0.115
    for sx in (-1, 1):
        # each slit tilts inward-down, matching the 2D art
        parts.append(cube(f"{name}_eye{sx}", (sx * 0.175, fy, eye_z),
                          (0.175, 0.055, 0.036), m_ink, rot=(0, sx * math.radians(11), 0), bevel=0.014))
    parts.append(cube(f"{name}_mouth", (0.055, fy, BODY_Z - 0.135),
                      (0.135, 0.05, 0.032), m_ink, rot=(0, math.radians(-24), 0), bevel=0.012))

    # ------------------------------------------------------------ optional gear
    top = BODY_Z + R * body_scale

    if hat == "cone":
        parts.append(cone(f"{name}_hat", (0, 0, top + 0.20), 0.40, 0.40, m_acc, verts=24))
        parts.append(cyl(f"{name}_hatband", (0, 0, top + 0.015), 0.405, 0.05, m_acc, verts=24))
        parts.append(sphere(f"{name}_pom", (0, 0, top + 0.415), 0.075, m_white, segs=14))

    elif hat == "helmet":
        h = sphere(f"{name}_helm", (0, 0, top - 0.10), R * 0.60, m_acc, scale=(1.03, 1.0, 0.72), segs=32)
        parts.append(h)
        parts.append(cyl(f"{name}_crest", (0, 0, top + 0.16), 0.05, 0.32, m_ink, verts=10))

    elif hat == "crown":
        parts.append(cyl(f"{name}_crownring", (0, 0, top + 0.02), 0.34, 0.13, m_acc, verts=12))
        for i in range(6):
            a = i * math.tau / 6
            parts.append(cone(f"{name}_spike{i}",
                              (math.cos(a) * 0.28, math.sin(a) * 0.28, top + 0.15),
                              0.075, 0.20, m_acc, verts=4))

    if gear == "bomb":
        parts.append(sphere(f"{name}_bomb", (0.80, -0.26, BODY_Z - 0.20), 0.20, m_ink, segs=24))
        parts.append(cyl(f"{name}_fuse", (0.80, -0.28, BODY_Z + 0.02), 0.02, 0.16, m_acc,
                         rot=(math.radians(22), 0, 0), verts=8))
        parts.append(sphere(f"{name}_spark", (0.80, -0.33, BODY_Z + 0.10), 0.045, m_acc, segs=12))

    elif gear == "shield":
        parts.append(cyl(f"{name}_shield", (-0.78, -0.10, BODY_Z - 0.06), 0.30, 0.07, m_acc,
                         rot=(math.radians(90), 0, 0), verts=6))
        parts.append(cube(f"{name}_boss", (-0.81, -0.10, BODY_Z - 0.06), (0.13, 0.05, 0.13), m_ink, bevel=0.02))

    elif gear == "staff":
        parts.append(stick(f"{name}_staff", (0.80, -0.10, BODY_Z - 0.55), (0.80, -0.10, BODY_Z + 0.85), 0.032, m_ink))
        parts.append(sphere(f"{name}_orb", (0.80, -0.10, BODY_Z + 0.92), 0.10, m_acc, segs=20))
        parts.append(cyl(f"{name}_orbring", (0.80, -0.10, BODY_Z + 0.92), R * 0.24, 0.02, m_acc, verts=16))

    elif gear == "flag":
        parts.append(stick(f"{name}_pole", (0.78, 0, BODY_Z - 0.60), (0.78, 0, BODY_Z + 1.05), 0.026, m_ink))
        parts.append(cube(f"{name}_cloth", (0.99, 0, BODY_Z + 0.78), (0.40, 0.03, 0.26), m_acc))

    obj = join(parts, name)
    if s != 1.0:
        obj.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = (0, 0, 0)
    return obj

# ---------------------------------------------------------------- roster
ROSTER = [
    dict(name="pleb_basic",  accent=(0.98, 0.80, 0.18)),
    dict(name="pleb_scout",  accent=(0.36, 0.80, 0.46),  hat="cone"),
    dict(name="pleb_bomber", accent=(0.95, 0.55, 0.20),  gear="bomb"),
    dict(name="pleb_guard",  accent=(0.62, 0.48, 0.88),  gear="shield"),
    dict(name="pleb_mage",   accent=(0.90, 0.36, 0.58),  gear="staff"),
    dict(name="pleb_brute",  accent=(0.28, 0.30, 0.38),  hat="helmet", body_scale=1.14),
    dict(name="pleb_king",   accent=(0.98, 0.82, 0.26),  hat="crown", body_scale=1.06),
    dict(name="pleb_banner", accent=(0.32, 0.56, 0.92),  gear="flag"),
]

def export(obj, path):
    for o in bpy.data.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              use_selection=True, export_apply=True, export_yup=True)

# ---------------------------------------------------------------- render rig
def setup_render(res=(1600, 900), samples=64, transparent=False):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 5
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'

    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.055, 0.07, 0.11, 1)
    bg.inputs[1].default_value = 1.15

    if not transparent:
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
        fl = bpy.context.object
        fl.data.materials.append(mat("floor", (0.085, 0.105, 0.15), rough=0.85))

    def lamp(name, loc, energy, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA')
        d.energy = energy; d.size = size; d.color = color
        o = bpy.data.objects.new(name, d)
        bpy.context.collection.objects.link(o)
        o.location = loc
        v = Vector((0, 0, 0.85)) - Vector(loc)
        o.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()

    lamp("key", (-4.0, -5.2, 5.6), 1500, 5.5, (1.0, 0.97, 0.92))
    lamp("fill", (5.2, -3.4, 3.0), 480, 7.0, (0.70, 0.82, 1.0))
    lamp("rim", (1.0, 6.0, 4.6), 950, 4.5, (0.62, 0.80, 1.0))

    cd = bpy.data.cameras.new("c")
    cd.lens = 62
    cam = bpy.data.objects.new("c", cd)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    return cam

def aim(cam, loc, target=(0, 0, 0.80)):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- main
def main():
    for cfg in ROSTER:
        clear_scene()
        o = build_pleb(**cfg)
        path = os.path.join(OUT, cfg["name"] + ".glb")
        export(o, path)
        print("EXPORTED", os.path.basename(path), "verts", len(o.data.vertices), "tris", len(o.data.polygons))

    # combined roster
    clear_scene()
    objs = []
    for i, cfg in enumerate(ROSTER):
        o = build_pleb(**cfg)
        o.location = ((i - (len(ROSTER) - 1) / 2) * 1.55, 0, 0)
        objs.append(o)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "plebs_roster.glb"),
                              export_format='GLB', use_selection=True, export_apply=True)

    # roster render — two rows of four
    clear_scene()
    cam = setup_render((1600, 900), 72)
    for i, cfg in enumerate(ROSTER):
        o = build_pleb(**cfg)
        col, row = i % 4, i // 4
        o.location = ((col - 1.5) * 1.52, 0.86 - row * 1.70, 0)
        o.rotation_euler = (0, 0, (col - 1.5) * -0.06)
    aim(cam, (0.0, -8.6, 3.3), (0, -0.42, 0.86))
    cam.data.lens = 50
    bpy.context.scene.render.filepath = os.path.join(OUT, "preview_roster.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED roster")

    # hero
    clear_scene()
    cam = setup_render((900, 900), 72)
    build_pleb("pleb_basic", (0.98, 0.80, 0.18))
    aim(cam, (1.9, -4.0, 2.05), (0, 0, 0.82))
    cam.data.lens = 68
    bpy.context.scene.render.filepath = os.path.join(OUT, "preview_hero.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED hero")

if __name__ == '__main__':
    main()
