import bpy
import math
import mathutils

def fit_camera_to_obj(cam, obj, scene, padding):
    """Calculates camera position to frame a mesh perfectly."""
    matrix = obj.matrix_world
    corners = [matrix @ mathutils.Vector(corner) for corner in obj.bound_box]
    center = sum(corners, mathutils.Vector()) / 8
    radius = max((corner - center).length for corner in corners)
    
    fov = cam.data.angle
    # Handle sensor fitting logic
    if cam.data.sensor_fit != 'HORIZONTAL' and not (cam.data.sensor_fit == 'AUTO' and scene.render.resolution_x >= scene.render.resolution_y):
        fov = 2 * math.atan(math.tan(cam.data.angle / 2) * scene.render.resolution_y / scene.render.resolution_x)

    distance = (radius * padding) / math.sin(fov / 2)
    forward = cam.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, -1))
    cam.location = center - (forward * distance)