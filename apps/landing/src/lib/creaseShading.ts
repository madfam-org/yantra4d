import { BufferAttribute, Vector3, type BufferGeometry, type Mesh, type Object3D } from 'three';
import { computeCreaseNormals } from './creaseNormals';

/**
 * Give every mesh under `root` that carries no normals a copy of its geometry with crease-angle
 * normals, and return the copies so the caller can dispose them.
 *
 * The source geometry is left alone: `useLoader` caches it and every clone of the scene shares
 * it. Normals are worked out on world-space positions, so the crease test sees the part at its
 * real proportions whatever transform the node carries (the pipeline's files keep quantized
 * positions under a node scale), then turned back into the mesh's own space.
 */
export function shadeWithCreaseNormals(root: Object3D, creaseAngleDeg: number): BufferGeometry[] {
  const made: BufferGeometry[] = [];
  const point = new Vector3();
  root.updateMatrixWorld(true);
  root.traverse((child) => {
    const mesh = child as Mesh;
    if (!mesh.isMesh || !mesh.geometry?.getAttribute('position') || mesh.geometry.getAttribute('normal')) return;
    const geometry = mesh.geometry.index ? mesh.geometry.toNonIndexed() : mesh.geometry.clone();
    const position = geometry.getAttribute('position');
    const world = new Float32Array(position.count * 3);
    for (let i = 0; i < position.count; i++) {
      point.fromBufferAttribute(position, i).applyMatrix4(mesh.matrixWorld).toArray(world, i * 3);
    }
    const normals = computeCreaseNormals(world, creaseAngleDeg);
    // A normal n in world space is M^-T applied to the local one, so the local one is M^T n.
    const m = mesh.matrixWorld.elements;
    for (let i = 0; i < normals.length; i += 3) {
      const x = normals[i], y = normals[i + 1], z = normals[i + 2];
      const lx = m[0] * x + m[1] * y + m[2] * z;
      const ly = m[4] * x + m[5] * y + m[6] * z;
      const lz = m[8] * x + m[9] * y + m[10] * z;
      const length = Math.hypot(lx, ly, lz) || 1;
      normals[i] = lx / length; normals[i + 1] = ly / length; normals[i + 2] = lz / length;
    }
    geometry.setAttribute('normal', new BufferAttribute(normals, 3));
    mesh.geometry = geometry;
    made.push(geometry);
  });
  return made;
}
