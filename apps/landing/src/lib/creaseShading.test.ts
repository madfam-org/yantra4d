import { describe, it, expect } from 'vitest';
import { BufferAttribute, BufferGeometry, Group, Mesh, MeshStandardMaterial } from 'three';
import { shadeWithCreaseNormals } from './creaseShading';

/**
 * A unit square in the XY plane and a wall standing on its X = 0 edge, written the way the
 * models pipeline writes a mesh: indexed, positions as normalized int16.
 */
function quantizedFold(): BufferGeometry {
  const q = 32767;
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(new Int16Array([
    0, 0, 0, q, 0, 0, q, q, 0, 0, q, 0, // floor
    0, 0, q, 0, q, q, // top of the wall
  ]), 3, true));
  geometry.setIndex([0, 1, 2, 0, 2, 3, 0, 3, 5, 0, 5, 4]);
  return geometry;
}

describe('shadeWithCreaseNormals', () => {
  it('gives a mesh without normals a shaded copy and leaves the source alone', () => {
    const source = quantizedFold();
    const mesh = new Mesh(source, new MeshStandardMaterial());
    const root = new Group().add(mesh);

    const made = shadeWithCreaseNormals(root, 30);

    expect(made).toHaveLength(1);
    expect(mesh.geometry).toBe(made[0]);
    expect(mesh.geometry).not.toBe(source);
    expect(source.getAttribute('normal')).toBeUndefined();
    expect(source.index).not.toBeNull();
    expect(mesh.geometry.index).toBeNull();
    const normal = mesh.geometry.getAttribute('normal');
    expect(normal.count).toBe(12);
    // Floor corners point along Z, wall corners along X: the 90° edge is kept.
    for (let i = 0; i < 6; i++) expect(normal.getZ(i)).toBeCloseTo(1, 6);
    for (let i = 6; i < 12; i++) expect(normal.getX(i)).toBeCloseTo(1, 6);
  });

  it('judges the crease at the size the node draws the part', () => {
    // Two faces 20° apart as stored. The node flattens Z to a tenth, which leaves them 2° apart
    // on screen: one surface. Judged in the mesh's own space they would stay two.
    const tilt = Math.tan((20 * Math.PI) / 180);
    const geometry = new BufferGeometry();
    geometry.setAttribute('position', new BufferAttribute(new Float32Array([
      0, 0, 0, 1, 0, 0, 1, 1, 0,
      0, 0, 0, 1, 1, 0, 0, 1, 0,
      0, 0, 0, 0, 1, 0, -1, 1, -tilt,
      0, 0, 0, -1, 1, -tilt, -1, 0, -tilt,
    ]), 3));
    const mesh = new Mesh(geometry, new MeshStandardMaterial());
    mesh.scale.set(1, 1, 0.1);
    const root = new Group().add(mesh);

    shadeWithCreaseNormals(root, 10);

    const normal = mesh.geometry.getAttribute('normal');
    // Corner 0 (flat face) and corner 6 (tilted face) meet at the origin and share a normal.
    expect(normal.getX(0)).toBeCloseTo(normal.getX(6), 5);
    expect(normal.getZ(0)).toBeCloseTo(normal.getZ(6), 5);
    expect(normal.getX(0)).not.toBe(0);
    // Stored normals are unit length in the mesh's own space.
    expect(Math.hypot(normal.getX(0), normal.getY(0), normal.getZ(0))).toBeCloseTo(1, 5);
  });

  it('skips a mesh that already has normals', () => {
    const geometry = quantizedFold();
    geometry.setAttribute('normal', new BufferAttribute(new Float32Array(18), 3));
    const mesh = new Mesh(geometry, new MeshStandardMaterial());
    expect(shadeWithCreaseNormals(new Group().add(mesh), 30)).toHaveLength(0);
    expect(mesh.geometry).toBe(geometry);
  });

  it('turns the normals round under a mirroring transform', () => {
    const mesh = new Mesh(quantizedFold(), new MeshStandardMaterial());
    mesh.scale.set(-1, 1, 1);
    shadeWithCreaseNormals(new Group().add(mesh), 30);
    const normal = mesh.geometry.getAttribute('normal');
    for (let i = 0; i < 6; i++) expect(normal.getZ(i)).toBeCloseTo(1, 6);
    for (let i = 6; i < 12; i++) expect(normal.getX(i)).toBeCloseTo(1, 6);
  });
});
