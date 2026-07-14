import sys
from pathlib import Path

import UnrealRootNodeReadTimecode as unreal_reader


def print_node_properties(node, indent=0):
    if node is None:
        return

    prefix = "  " * indent

    try:
        prop = node.GetFirstProperty()
    except Exception as exc:
        print(f"{prefix}Property enumeration unavailable: {exc}")
        return

    if prop is None:
        print(f"{prefix}Property count: 0")
        return

    count = 0
    while prop is not None:
        try:
            prop_name = prop.GetName()
        except Exception:
            prop_name = "<unknown>"

        try:
            prop_value = prop.Get()
        except Exception as exc:
            prop_value = f"<unavailable: {exc}>"

        print(f"{prefix}  Property[{count}]: {prop_name} = {prop_value}")
        count += 1
        try:
            prop = node.GetNextProperty(prop)
        except Exception:
            break

    print(f"{prefix}Property count: {count}")


def print_node_tree(node, indent=0, max_depth=8):
    if node is None:
        return

    prefix = "  " * indent
    print(f"{prefix}Node: {node.GetName()}")

    attr = node.GetNodeAttribute()
    if attr is not None:
        try:
            attr_type = attr.GetAttributeType()
            print(f"{prefix}  Attribute type: {attr_type}")
        except Exception as exc:
            print(f"{prefix}  Attribute type: <unavailable: {exc}>")

    print_node_properties(node, indent + 1)

    if indent < max_depth:
        for i in range(node.GetChildCount()):
            child = node.GetChild(i)
            print_node_tree(child, indent + 1, max_depth)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) not in (2, 3):
        print(f"Usage: {argv[0]} <fbx_file> [frame_index]")
        return 1

    fbx_file = Path(argv[1])
    if not fbx_file.exists():
        print(f"File not found: {fbx_file}")
        return 1

    frame_index = 0
    if len(argv) == 3:
        try:
            frame_index = int(argv[2])
        except ValueError:
            print(f"Invalid frame index: {argv[2]}")
            return 1

    manager = unreal_reader.fbx.FbxManager.Create()
    ios = unreal_reader.fbx.FbxIOSettings.Create(manager, unreal_reader.fbx.IOSROOT)
    manager.SetIOSettings(ios)

    importer = unreal_reader.fbx.FbxImporter.Create(manager, "")
    if not importer.Initialize(str(fbx_file), -1, manager.GetIOSettings()):
        print(f"Failed to initialize FBX importer for '{fbx_file}'")
        return 1

    scene = unreal_reader.fbx.FbxScene.Create(manager, "scene")
    importer.Import(scene)
    importer.Destroy()

    root = scene.GetRootNode()
    if root is None:
        print("No root node found")
        return 1

    print(f"FBX file: {fbx_file}")
    print(f"Frame index: {frame_index}")
    print("Root node tree:")
    print_node_tree(root)

    print("\nCandidate skeleton/root nodes:")
    for i in range(root.GetChildCount()):
        child = root.GetChild(i)
        print(f"- {child.GetName()}")
        try:
            attr = child.GetNodeAttribute()
            if attr is not None:
                print(f"  attribute type: {attr.GetAttributeType()}")
            else:
                print("  no node attribute")
        except Exception as exc:
            print(f"  attribute type: <unavailable: {exc}>")

        print_node_properties(child, 1)

    return 0


if __name__ == "__main__":
    sys.exit(main())

