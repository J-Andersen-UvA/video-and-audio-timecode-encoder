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
    if node.GetName() == name:
        return node

    for childIndex in range(node.GetChildCount()):
        result = findNode(node.GetChild(childIndex), name)

        if result:
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


fbxPath = (
    r"E:\Recordings\2026-07-13"
    r"\test_260713_2\unreal\CC\test_260713_2.fbx"
)

manager, scene = loadScene(fbxPath)

try:
    rootNode = findNode(scene.GetRootNode(), "root")

    if rootNode is None:
        raise RuntimeError("Could not find the root skeleton node")

    animStackCount = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId))

    for stackIndex in range(animStackCount):
        animStack = scene.GetSrcObject(
            fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId),
            stackIndex,
        )

        print(f"\nAnimation stack: {animStack.GetName()}")

        layerCount = animStack.GetMemberCount(
            fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId)
        )

        for layerIndex in range(layerCount):
            animLayer = animStack.GetMember(
                fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId),
                layerIndex,
            )

            print(f"Layer: {animLayer.GetName()}")

            for propertyName in timecodeNames:
                prop = rootNode.FindProperty(propertyName)

                if not prop.IsValid():
                    print(f"  {propertyName}: not found")
                    continue

                curve = prop.GetCurve(animLayer)

                if curve is None:
                    print(
                        f"  {propertyName}: static "
                        f"value={getStaticValue(prop)!r}"
                    )
                    continue

                print(
                    f"  {propertyName}: "
                    f"{curve.KeyGetCount()} keys"
                )

                for keyIndex in range(curve.KeyGetCount()):
                    keyTime = curve.KeyGetTime(keyIndex)
                    keyValue = curve.KeyGetValue(keyIndex)

                    print(
                        f"    frame={keyTime.GetFrameCount()}, "
                        f"seconds={keyTime.GetSecondDouble():.6f}, "
                        f"value={keyValue}"
                    )

finally:
    manager.Destroy()