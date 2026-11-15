"""Work around a bug in Blender-as-a-Python-module (pip `bpy`): the embedded Mantaflow
`manta` module is initialised before its class registry links base classes, so e.g.
LevelsetGrid does not inherit Grid<Real>.setConst and every fluid bake aborts.
We re-link the static type objects (tp_base / tp_bases / tp_mro) with ctypes.
Import this module once after `import bpy` and before baking."""
import ctypes
import bpy  # noqa: F401
import manta

HIER = {
    "Solver": "PbClass", "GridBase": "PbClass", "Grid_Real": "GridBase", "Grid_int": "GridBase",
    "Grid_Vec3": "GridBase", "LevelsetGrid": "Grid_Real", "MACGrid": "Grid_Vec3", "FlagGrid": "Grid_int",
    "Grid4dBase": "PbClass", "Grid4d_Real": "Grid4dBase", "Grid4d_int": "Grid4dBase",
    "Grid4d_Vec3": "Grid4dBase", "Grid4d_Vec4": "Grid4dBase",
    "Shape": "PbClass", "Box": "Shape", "Sphere": "Shape", "Cylinder": "Shape", "Slope": "Shape",
    "NullShape": "Shape", "Mesh": "PbClass", "VortexSheetMesh": "Mesh", "MeshDataBase": "PbClass",
    "MeshDataImpl_int": "MeshDataBase", "MeshDataImpl_Real": "MeshDataBase", "MeshDataImpl_Vec3": "MeshDataBase",
    "MovingObstacle": "PbClass", "NoiseField": "PbClass", "Timings": "PbClass",
    "ParticleBase": "PbClass", "ParticleSystem_BasicParticleData": "ParticleBase",
    "ParticleSystem_ParticleIndexData": "ParticleBase", "ParticleSystem_TurbulenceParticleData": "ParticleBase",
    "ParticleSystem_VortexParticleData": "ParticleBase",
    "BasicParticleSystem": "ParticleSystem_BasicParticleData",
    "ParticleIndexSystem": "ParticleSystem_ParticleIndexData",
    "TurbulenceParticleSystem": "ParticleSystem_TurbulenceParticleData",
    "VortexParticleSystem": "ParticleSystem_VortexParticleData",
    "ParticleDataBase": "PbClass", "ParticleDataImpl_Real": "ParticleDataBase",
    "ParticleDataImpl_Vec3": "ParticleDataBase", "ParticleDataImpl_int": "ParticleDataBase",
}
OFF_BASE, OFF_BASES, OFF_MRO = 256, 336, 344     # PyTypeObject field offsets, 64-bit CPython 3.11-3.13

def _types():
    out = {}
    for n in dir(manta):
        o = getattr(manta, n)
        if isinstance(o, type):
            out[o.__name__] = o
    return out

def apply():
    T = _types()
    if "LevelsetGrid" not in T or len(T["LevelsetGrid"].__mro__) > 2:
        return False                      # already fine (regular Blender build)
    keep = []
    def chain(name):
        c = [T[name]]
        while name in HIER and HIER[name] in T:
            name = HIER[name]; c.append(T[name])
        return c + [object]
    PyObj = ctypes.py_object
    for name in HIER:
        if name not in T:
            continue
        cls = T[name]; base = T.get(HIER[name])
        if base is None:
            continue
        mro = tuple(chain(name)); bases = (base,)
        keep += [mro, bases]
        for tup in (mro, bases, base):
            ctypes.pythonapi.Py_IncRef(PyObj(tup))
        addr = id(cls)
        ctypes.c_void_p.from_address(addr + OFF_BASE).value = id(base)
        ctypes.c_void_p.from_address(addr + OFF_BASES).value = id(bases)
        ctypes.c_void_p.from_address(addr + OFF_MRO).value = id(mro)
        ctypes.pythonapi.PyType_Modified(PyObj(cls))
    apply._keep = keep
    return True

apply()
