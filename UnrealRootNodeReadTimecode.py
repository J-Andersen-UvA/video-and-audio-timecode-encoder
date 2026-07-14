import sys

import fbx


timecodeNames = [
    "TCHour",
    "TCMinute",
    "TCSecond",
    "TCFrame",
    "TCSubframe",
    "TCRate",
    "TCSlate",
]


def loadScene(path):
    manager = fbx.FbxManager.Create()
    ioSettings = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)
    manager.SetIOSettings(ioSettings)

    importer = fbx.FbxImporter.Create(manager, "")
    if not importer.Initialize(path, -1, ioSettings):
        raise RuntimeError(importer.GetStatus().GetErrorString())

    scene = fbx.FbxScene.Create(manager, "scene")
    if not importer.Import(scene):
        raise RuntimeError(importer.GetStatus().GetErrorString())

    importer.Destroy()
    return manager, scene


def findNode(node, name):
    if node is None:
        return None

    if node.GetName() == name:
        return node

    for childIndex in range(node.GetChildCount()):
        result = findNode(node.GetChild(childIndex), name)
        if result is not None:
            return result

    return None


def getStaticValue(prop):
    typeName = prop.GetPropertyDataType().GetName().lower()

    if typeName in {"int", "integer", "enum"}:
        return fbx.FbxPropertyInteger1(prop).Get()

    if typeName in {"float", "real", "double", "number"}:
        return fbx.FbxPropertyDouble1(prop).Get()

    if typeName in {"string", "kstring", "charptr"}:
        return fbx.FbxPropertyString(prop).Get()

    if typeName in {"bool", "boolean"}:
        return fbx.FbxPropertyBool1(prop).Get()

    return None


def _normalize_frame_index(frame_index, frame_count):
    if frame_count <= 0:
        return 0

    if frame_index < 0:
        frame_index = frame_count + frame_index
    if frame_index < 0:
        frame_index = frame_count + frame_index
    frame_index %= frame_count
    return frame_index


def _read_curve_value(curve, frame_index):
    if curve is None:
        return None

    key_count = curve.KeyGetCount()
    if key_count <= 0:
        return None

    key_index = _normalize_frame_index(frame_index, key_count)
    return curve.KeyGetValue(key_index)


def readTimecodeFromRootNodeUnrealStyle(fbx_scene, frame_index=0):
    """
    Read the timecode for a requested frame index from an FBX scene.

    Frame indexing is zero-based, with wrap-around for negative indices.
    -1 means the last frame and -2 means the second-to-last frame.
    """
    root_node = findNode(fbx_scene.GetRootNode(), "root")
    if root_node is None:
        return None

    animStackCount = fbx_scene.GetSrcObjectCount(
        fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId)
    )

    for stackIndex in range(animStackCount):
        animStack = fbx_scene.GetSrcObject(
            fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId),
            stackIndex,
        )
        if animStack is None:
            continue

        layerCount = animStack.GetMemberCount(
            fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId)
        )

        for layerIndex in range(layerCount):
            animLayer = animStack.GetMember(
                fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId),
                layerIndex,
            )
            if animLayer is None:
                continue

            values = {}
            for propertyName in timecodeNames:
                prop = root_node.FindProperty(propertyName)
                if not prop.IsValid():
                    continue

                curve = prop.GetCurve(animLayer)
                if curve is None:
                    static_value = getStaticValue(prop)
                    if static_value is not None:
                        values[propertyName] = static_value
                    continue

                key_value = _read_curve_value(curve, frame_index)
                if key_value is not None:
                    values[propertyName] = key_value

            if values:
                timecode_parts = []
                for propertyName in timecodeNames:
                    if propertyName in values:
                        value = values[propertyName]
                        if isinstance(value, float) and value.is_integer():
                            value = int(value)
                        timecode_parts.append(str(value))
                if timecode_parts:
                    return ":".join(timecode_parts)

    return None


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) not in (2, 3):
        print(f"Usage: {argv[0]} <fbx_file> [frame_index]")
        return 1

    fbx_file = argv[1]
    frame_index = 0
    if len(argv) == 3:
        try:
            frame_index = int(argv[2])
        except ValueError:
            print(f"Invalid frame index: {argv[2]}")
            return 1

    manager, scene = loadScene(fbx_file)
    try:
        timecode = readTimecodeFromRootNodeUnrealStyle(scene, frame_index)
        if timecode is None:
            print("No timecode found")
            return 1

        print(timecode)
        return 0
    finally:
        manager.Destroy()


if __name__ == "__main__":
    sys.exit(main())

