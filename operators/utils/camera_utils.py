import bpy
import math
import mathutils

def fit_camera_to_obj(cam, obj, scene, padding):
    """Calculates camera position to frame a mesh perfectly."""
    matrix = obj.matrix_world
    verts = [matrix @ v.co for v in obj.data.vertices]
    center = sum(verts, mathutils.Vector()) / len(verts)
    cam_right = cam.matrix_world.to_quaternion() @ mathutils.Vector((1, 0, 0))
    cam_up = cam.matrix_world.to_quaternion() @ mathutils.Vector((0, 1, 0))
    proj_x = [(v - center).dot(cam_right) for v in verts]
    proj_y = [(v - center).dot(cam_up) for v in verts]
    radius = max(max(proj_x) - min(proj_x), max(proj_y) - min(proj_y)) / 2
    
    fov = cam.data.angle
    # Handle sensor fitting logic
    if cam.data.sensor_fit != 'HORIZONTAL' and not (cam.data.sensor_fit == 'AUTO' and scene.render.resolution_x >= scene.render.resolution_y):
        fov = 2 * math.atan(math.tan(cam.data.angle / 2) * scene.render.resolution_y / scene.render.resolution_x)

    distance = (radius * padding) / math.sin(fov / 2)
    forward = cam.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, -1))
    cam.location = center - (forward * distance)