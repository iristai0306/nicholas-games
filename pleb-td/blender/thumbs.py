import bpy, os, sys
exec(open("/root/.openclaw/workspace-wayne/nicholas-games/pleb-td/blender/plebs.py").read().split("if __name__ == '__main__':")[0])

TOWERS = ["pleb_basic","pleb_scout","pleb_guard","pleb_bomber","pleb_mage","pleb_king"]

for name in TOWERS:
    clear_scene()
    cfg = next(c for c in ROSTER if c["name"] == name)
    build_pleb(**cfg)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 40
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 4
    sc.render.resolution_x = 160
    sc.render.resolution_y = 160
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'

    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.10, 0.16, 0.26, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.4

    def lamp(loc, energy, size, color=(1,1,1)):
        d = bpy.data.lights.new("L", 'AREA'); d.energy = energy; d.size = size; d.color = color
        o = bpy.data.objects.new("L", d); bpy.context.collection.objects.link(o)
        o.location = loc
        v = Vector((0,0,0.85)) - Vector(loc)
        o.rotation_euler = v.to_track_quat('-Z','Y').to_euler()

    lamp((-2.6,-3.0,3.4), 420, 3.0, (1.0,0.96,0.9))
    lamp((3.0,-2.2,2.0), 170, 3.5, (0.7,0.82,1.0))
    lamp((0.6,3.2,2.6), 260, 2.5, (0.7,0.85,1.0))

    cd = bpy.data.cameras.new("c"); cd.lens = 70
    cam = bpy.data.objects.new("c", cd); bpy.context.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (1.05, -2.35, 1.42)
    d = Vector((0,0,0.92)) - Vector(cam.location)
    cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()

    sc.render.filepath = os.path.join(OUT, "thumb_" + name + ".png")
    bpy.ops.render.render(write_still=True)
    print("THUMB", name)
