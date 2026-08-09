# pytorch3d renderer stub for Windows compatibility

def _not_available(*args, **kwargs):
    raise ImportError("pytorch3d not available on Windows. Use trimesh instead.")


look_at_view_transform = _not_available
FoVPerspectiveCameras = _not_available
PointLights = _not_available
DirectionalLights = _not_available
AmbientLights = _not_available
Materials = _not_available
RasterizationSettings = _not_available
MeshRenderer = _not_available
MeshRasterizer = _not_available
SoftPhongShader = _not_available
TexturesUV = _not_available
TexturesVertex = _not_available
camera_position_from_spherical_angles = _not_available
BlendParams = _not_available
