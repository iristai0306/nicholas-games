import bpy, os, sys
sys.argv = ["blender"]
exec(open("/root/.openclaw/workspace-wayne/nicholas-games/pleb-td/blender/plebs.py").read().split("if __name__ == '__main__':")[0])

clear_scene()
cam = setup_render((1600, 900), 72)
for i, cfg in enumerate(ROSTER):
    o = build_pleb(**cfg)
    col, row = i % 4, i // 4
    o.location = ((col - 1.5) * 1.62, 0.95 - row * 1.95, 0)
    o.rotation_euler = (0, 0, (col - 1.5) * -0.07)
    o.scale = (0.95, 0.95, 0.95)
cam.data.lens = 45
aim_cam(cam, (0.0, -9.6, 3.15), (0, -0.45, 1.0))
bpy.context.scene.render.filepath = os.path.join(OUT, "preview_roster.png")
bpy.ops.render.render(write_still=True)
print("DONE")
