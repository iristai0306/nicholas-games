"""
PLEBANIA 3D — pleb character generator for Blender 4.0
Run headless:  blender -b -P plebs.py
Outputs: models/*.glb  +  models/preview_*.png
"""
import bpy, math, os
from mathutils import Vector

ROOT = "/root/.openclaw/workspace-wayne/nicholas-games/pleb-td"
OUT = os.path.join(ROOT, "models")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- scene utils
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, color, rough=0.45, metal=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*color, 1.0)
    return m

def _finish(obj, name, m, bevel):
    obj.name = name
    if m:
        obj.data.materials.append(m)
    if bevel > 0:
        md = obj.modifiers.new("bev", 'BEVEL')
        md.width = bevel
        md.segments = 3
        md.limit_method = 'ANGLE'
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=md.name)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj

def cube(name, loc, size, m=None, bevel=0.1, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = Vector(size) if isinstance(size, (tuple, list)) else Vector((size,) * 3)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, name, m, bevel)

def sphere(name, loc, r, m=None, segs=24, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=segs // 2, location=loc)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, name, m, 0)

def cyl(name, loc, r, h, m=None, rot=(0, 0, 0), verts=20, bevel=0.03, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=loc, rotation=rot, vertices=verts)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=h, location=loc, rotation=rot, vertices=verts)
    return _finish(bpy.context.object, name, m, bevel)

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
    return o

# ---------------------------------------------------------------- the pleb
# Local build: feet on z=0, front faces -Y.
BODY_W, BODY_D, BODY_H = 0.92, 0.80, 1.05
LEG_H = 0.30

def build_pleb(name, body_col, accent_col, *, s=1.0, hat=None, gear=None,
               eye_col=(0.05, 0.05, 0.07), wide=1.0, tall=1.0):
    m_body = mat(name + "_body", body_col)
    m_accent = mat(name + "_accent", accent_col, rough=0.35)
    m_eye = mat(name + "_eye", eye_col, rough=0.15)
    m_white = mat("eye_white", (0.97, 0.97, 0.98), rough=0.25)
    m_dark = mat("dark", (0.12, 0.12, 0.14), rough=0.6)

    parts = []

    # legs
    for sx in (-1, 1):
        parts.append(cube(f"{name}_leg{sx}", (sx * 0.24, 0.02, LEG_H / 2), (0.30, 0.34, LEG_H), m_dark, 0.06))
        # feet
        parts.append(cube(f"{name}_foot{sx}", (sx * 0.24, -0.05, 0.05), (0.32, 0.44, 0.10), m_accent, 0.045))

    # body
    bw = BODY_W * wide
    bh = BODY_H * tall
    body_z = LEG_H + bh / 2
    parts.append(cube(f"{name}_body", (0, 0, body_z), (bw, BODY_D, bh), m_body, min(0.28, bw * 0.30)))

    # face plate (slightly proud of the front)
    fy = -BODY_D / 2
    eye_z = body_z + bh * 0.20
    eye_dx = bw * 0.215
    for sx in (-1, 1):
        parts.append(sphere(f"{name}_eyewhite{sx}", (sx * eye_dx, fy - 0.015, eye_z), 0.135,
                            m_white, 20, (1.0, 0.42, 1.15)))
        parts.append(sphere(f"{name}_eye{sx}", (sx * eye_dx, fy - 0.085, eye_z - 0.005), 0.072,
                            m_eye, 18, (1.0, 0.75, 1.0)))
        parts.append(sphere(f"{name}_glint{sx}", (sx * eye_dx - 0.028, fy - 0.135, eye_z + 0.045), 0.024,
                            m_white, 12))

    # mouth
    parts.append(cube(f"{name}_mouth", (0, fy - 0.02, body_z - bh * 0.16), (bw * 0.20, 0.05, 0.055), m_dark, 0.02))

    # arms
    for sx in (-1, 1):
        parts.append(sphere(f"{name}_arm{sx}", (sx * (bw / 2 + 0.06), -0.02, body_z - bh * 0.10), 0.13,
                            m_body, 18, (1.0, 1.0, 1.7)))

    # ---- optional hat
    if hat == "crown":
        bpy.ops.mesh.primitive_cylinder_add(radius=bw * 0.36, depth=0.16,
                                            location=(0, 0, LEG_H + bh + 0.06), vertices=10)
        ring = _finish(bpy.context.object, f"{name}_crownring", m_accent, 0.02)
        parts.append(ring)
        for i in range(6):
            a = i * math.tau / 6
            parts.append(cyl(f"{name}_spike{i}",
                             (math.cos(a) * bw * 0.30, math.sin(a) * bw * 0.30, LEG_H + bh + 0.20),
                             0.075, 0.20, m_accent, verts=4, bevel=0.0, r2=0.0))
    elif hat == "helmet":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=bw * 0.55, segments=24, ring_count=12,
                                             location=(0, 0, LEG_H + bh - 0.12))
        h = bpy.context.object
        h.scale = (1.0, 0.95, 0.62)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        parts.append(_finish(h, f"{name}_helm", m_accent, 0))
        parts.append(cyl(f"{name}_crest", (0, 0, LEG_H + bh + 0.20), 0.055, 0.34, m_dark, verts=8, bevel=0.0))
    elif hat == "cone":
        parts.append(cyl(f"{name}_cone", (0, 0, LEG_H + bh + 0.10), bw * 0.40, 0.42, m_accent, verts=16, bevel=0.02, r2=0.0))
        parts.append(sphere(f"{name}_pom", (0, 0, LEG_H + bh + 0.34), 0.075, m_white, 14))

    # ---- optional gear held in front
    if gear == "bomb":
        parts.append(sphere(f"{name}_bomb", (0, -BODY_D / 2 - 0.20, body_z - bh * 0.20), 0.20, m_dark, 22))
        parts.append(cyl(f"{name}_fuse", (0, -BODY_D / 2 - 0.24, body_z - bh * 0.20 + 0.22), 0.022, 0.16,
                         m_accent, rot=(0.35, 0, 0), verts=8, bevel=0.0))
    elif gear == "shield":
        sh = cyl(f"{name}_shield", (-bw / 2 - 0.16, -0.10, body_z), 0.30, 0.09, m_accent,
                 rot=(math.pi / 2, 0, 0), verts=8, bevel=0.03)
        parts.append(sh)
        parts.append(cube(f"{name}_boss", (-bw / 2 - 0.21, -0.10, body_z), (0.14, 0.06, 0.14), m_dark, 0.03))
    elif gear == "staff":
        parts.append(cyl(f"{name}_staff", (bw / 2 + 0.18, -0.08, LEG_H + bh * 0.55), 0.035, 1.30, m_dark, verts=10, bevel=0.0))
        parts.append(sphere(f"{name}_orb", (bw / 2 + 0.18, -0.08, LEG_H + bh * 0.55 + 0.68), 0.10, m_accent, 18))
    elif gear == "flag":
        parts.append(cyl(f"{name}_pole", (bw / 2 + 0.16, -0.02, LEG_H + bh * 0.55), 0.025, 1.15, m_dark, verts=8, bevel=0.0))
        parts.append(cube(f"{name}_flag", (bw / 2 + 0.36, -0.02, LEG_H + bh * 0.95), (0.36, 0.04, 0.24), m_accent, 0.01))

    obj = join(parts, name)
    if s != 1.0:
        obj.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = (0, 0, 0)
    return obj

# ---------------------------------------------------------------- roster
ROSTER = [
    dict(name="pleb_basic",  body_col=(0.16, 0.66, 0.78), accent_col=(0.98, 0.80, 0.18)),
    dict(name="pleb_scout",  body_col=(0.36, 0.80, 0.42), accent_col=(0.14, 0.42, 0.22), hat="cone"),
    dict(name="pleb_bomber", body_col=(0.95, 0.55, 0.20), accent_col=(0.35, 0.18, 0.10), gear="bomb"),
    dict(name="pleb_guard",  body_col=(0.62, 0.45, 0.85), accent_col=(0.30, 0.22, 0.55), gear="shield"),
    dict(name="pleb_mage",   body_col=(0.90, 0.36, 0.55), accent_col=(0.98, 0.86, 0.35), gear="staff"),
    dict(name="pleb_brute",  body_col=(0.85, 0.26, 0.26), accent_col=(0.20, 0.20, 0.24), hat="helmet", wide=1.22, tall=1.05),
    dict(name="pleb_king",   body_col=(0.98, 0.84, 0.30), accent_col=(0.85, 0.55, 0.12), hat="crown", tall=1.05),
    dict(name="pleb_banner", body_col=(0.30, 0.52, 0.90), accent_col=(0.95, 0.95, 0.98), gear="flag"),
]

def export(obj, path):
    for o in bpy.data.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )

# ---------------------------------------------------------------- render setup
def setup_render(res=(1200, 800), samples=48):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'

    # world
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.045, 0.055, 0.09, 1)
    bg.inputs[1].default_value = 1.0

    # floor
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    fl = bpy.context.object
    m = mat("floor", (0.11, 0.13, 0.18), rough=0.75)
    fl.data.materials.append(m)

    # key / fill / rim
    def lamp(name, loc, energy, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA')
        d.energy = energy
        d.size = size
        d.color = color
        o = bpy.data.objects.new(name, d)
        bpy.context.collection.objects.link(o)
        o.location = loc
        # aim at origin
        dirv = Vector((0, 0, 1.0)) - Vector(loc)
        o.rotation_euler = dirv.to_track_quat('-Z', 'Y').to_euler()
        return o

    lamp("key",  (-4.2, -5.0, 6.2), 1400, 6.0, (1.0, 0.96, 0.90))
    lamp("fill", (5.0, -3.2, 3.4), 500, 7.0, (0.72, 0.82, 1.0))
    lamp("rim",  (1.2, 6.5, 5.0), 900, 5.0, (0.65, 0.80, 1.0))

    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 62
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    return cam

def aim_cam(cam, loc, target=(0, 0, 0.95)):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- main
def main():
    clear_scene()
    # neutral helpers first so material names stay stable
    made = []
    for cfg in ROSTER:
        clear_scene()
        o = build_pleb(**cfg)
        path = os.path.join(OUT, cfg["name"] + ".glb")
        export(o, path)
        print("EXPORTED", path, "verts:", len(o.data.vertices), "tris:", len(o.data.polygons))
        made.append(cfg)

    # ---------------- combined roster file
    clear_scene()
    spacing = 1.7
    objs = []
    for i, cfg in enumerate(ROSTER):
        o = build_pleb(**cfg)
        o.location = ((i - (len(ROSTER) - 1) / 2) * spacing, 0, 0)
        objs.append(o)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "plebs_roster.glb"),
                              export_format='GLB', use_selection=True, export_apply=True)

    # ---------------- renders
    clear_scene()
    cam = setup_render((1500, 900), 64)
    for i, cfg in enumerate(ROSTER):
        o = build_pleb(**cfg)
        col, row = i % 4, i // 4
        o.location = ((col - 1.5) * 1.55, 0.9 - row * 1.85, 0)
        o.rotation_euler = (0, 0, (col - 1.5) * -0.055)
        o.scale = (0.95, 0.95, 0.95)
    aim_cam(cam, (0.0, -8.4, 3.5), (0, -0.35, 0.95))
    bpy.context.scene.render.filepath = os.path.join(OUT, "preview_roster.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED roster")

    # hero shot: single basic pleb, close
    clear_scene()
    cam = setup_render((900, 900), 64)
    build_pleb("pleb_basic", (0.16, 0.66, 0.78), (0.98, 0.80, 0.18))
    cam.data.lens = 55
    aim_cam(cam, (2.1, -4.4, 2.0), (0, 0, 0.80))
    bpy.context.scene.render.filepath = os.path.join(OUT, "preview_hero.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED hero")

if os.environ.get('PLEB_SKIP_EXPORT') != '1':
    pass

if __name__ == '__main__':
    main()
