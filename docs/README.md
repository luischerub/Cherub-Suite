<h1><img src="media/brand.png" height="36" alt=""/> Cherub Suite</h1>

A Blender add-on that bundles common pie menu shortcuts and Asset Library authoring utilities into a single extension.

**Blender:** 5.0+  
**Version:** 0.3.4  
**License:** GPL-3.0-or-later

---

## Features

### Pie Menus

All pie menus are accessible via configurable hotkeys registered on install.

| Menu | Default Key | Description |
|------|-------------|-------------|
| **Save** | | File operations — save, save as, open, import, export, and recovery |
| **Selection** | | Vertex/Edge/Face mode switching, selection tools, X-ray, and auto-merge toggles |
| **Shading** | | Smooth/flat shading, mark sharp, flip/fix normals, and smooth-by-angle modifier |
| **Delete** | | Delete vertices, edges, faces, dissolve, and remove doubles |
| **Pivot** | | Snap pivot/origin and selection to cursor, center, or grid |
| **Modifiers** | | Add common modifiers — Mirror, Array, Subdivision Surface, Solidify, Wireframe, Remesh, and more |
| **Proportional Editing** | | Toggle proportional edit modes (regular, connected, projected) with all falloff types |
| **Specials** | | Edge Flow, Linear, Curve, Vertex Curve, Bezier Deform, and Shear |
| **UVs** | | Mark seams, unwrap, and toggle live unwrap |

---

### Edge Tools

Custom edge loop manipulation operators available through the Specials pie menu.

- **Edge Flow** — Interpolate edge loops to follow the natural curvature of surrounding geometry.
- **Edge Linear** — Straighten edge loops between their endpoints with optional even spacing.
- **Edge Curve** — Adjust curvature along an edge loop with tension control and customizable rails.
- **Bezier Deform** — Deform mesh geometry along a path defined by selected vertices.

---

### Shape Key Utilities

Available in the **Properties > Object Data > Shape Keys** panel.

- **Mesh Unifier** — Combine multiple selected meshes into one by storing each as a shape key on a base mesh.
- **Bake to Attributes** — Bake all shape key vertex positions as custom float vector attributes on the mesh.

---

### Asset Library Tools

Available in the **N-panel > Cherub** tab. Designed to speed up Asset Library authoring workflows.

- **Render Thumbnails** — Render square WEBP thumbnails for selected mesh objects, auto-framed and saved to a configurable output folder.
- **Assign Thumbnails** — Assign previously rendered WEBP thumbnails to assets marked in the current file.
- **Rename by Material** — Rename selected mesh objects to match their active material name.

**Settings (per scene):**

| Setting | Description |
|---------|-------------|
| Output Path | Folder where thumbnails are saved/loaded from |
| Resolution | Thumbnail render resolution (64–4096 px, default 512) |
| Padding | Camera framing padding around the object (default 1.1) |

---

## Installation

1. Download the latest release `.zip` from the [Releases](https://github.com/luischerub/Cherub-Suite/releases) page.
2. In Blender, go to **Edit > Preferences > Add-ons**.
3. Click **Install from Disk** and select the downloaded `.zip`.
4. Enable **Cherub Suite** in the add-on list.

---

## License

[GPL-3.0-or-later](https://spdx.org/licenses/GPL-3.0-or-later.html)
