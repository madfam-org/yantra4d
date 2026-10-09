import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { BoxGeometry, Mesh, MeshStandardMaterial } from 'three'
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js'
import { useWorkerLoader } from '../../src/hooks/render/useWorkerLoader'

const CYCLES = 100

async function fixtures() {
  const geometry = new BoxGeometry()
  const material = new MeshStandardMaterial({ color: '#22c55e' })
  const mesh = new Mesh(geometry, material)
  try {
    const stl = new STLExporter().parse(mesh, { binary: true })
    const glb = await new GLTFExporter().parseAsync(mesh, { binary: true })
    return [new Blob([stl]), new Blob([glb])]
  } finally {
    geometry.dispose()
    material.dispose()
  }
}

function Model({ request, id, loaded }) {
  const { geometry, scene } = useWorkerLoader(request.url, request.glb)
  useEffect(() => { if (geometry) loaded(id) }, [geometry, loaded, id])
  if (!geometry) return null
  return <group position={[id === 0 ? -0.8 : 0.8, 0, 0]}>
    {scene ? <primitive object={scene} /> : <mesh geometry={geometry}><meshStandardMaterial color="#22c55e" /></mesh>}
  </group>
}

function Meter({ cycle, ready, sample }) {
  const progress = useRef({ cycle: -1, frames: 0, sent: false })
  useFrame(({ gl }) => {
    if (progress.current.cycle !== cycle) progress.current = { cycle, frames: 0, sent: false }
    if (!ready || progress.current.sent || ++progress.current.frames < 5) return
    progress.current.sent = true
    sample({ cycle, geometries: gl.info.memory.geometries, textures: gl.info.memory.textures, contextLost: gl.getContext().isContextLost() })
  })
  return null
}

export default function Probe() {
  const assets = useRef(null)
  const objectUrl = useRef(null)
  const rows = useRef([])
  const baseline = useRef(null)
  const readyIds = useRef(new Set())
  const failed = useRef(false)
  const [request, setRequest] = useState(null)
  const [ready, setReady] = useState(true)
  const [cycle, setCycle] = useState(-2)
  const [status, setStatus] = useState('Measuring the renderer baseline with ordinary box meshes…')
  const [report, setReport] = useState(null)

  const next = useCallback(index => {
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current)
    readyIds.current.clear()
    setReady(index === CYCLES)
    setCycle(index)
    if (index === CYCLES) { objectUrl.current = null; setRequest(null); return }
    const url = URL.createObjectURL(assets.current[index % 2])
    objectUrl.current = url
    setRequest({ url, glb: index % 2 === 1 })
    setStatus(`Running model ${index + 1}/${CYCLES} (${index % 2 ? 'GLB' : 'STL'})`)
  }, [])

  const loaded = useCallback(id => {
    if (failed.current) return
    readyIds.current.add(id)
    if (readyIds.current.size === 2) setReady(true)
  }, [])

  const sample = useCallback(row => {
    if (failed.current) return
    if (row.cycle === -2) { setCycle(-1); return }
    if (row.cycle === -1) {
      baseline.current = row
      setReady(false)
      setStatus(`Ready: renderer baseline ${row.geometries} geometries, ${row.textures} textures. 100 distinct STL/GLB swaps next.`)
      return
    }
    rows.current.push(row)
    if (row.cycle < CYCLES) { next(row.cycle + 1); return }
    const active = rows.current.slice(0, -1)
    const result = {
      completedAt: new Date().toISOString(),
      userAgent: navigator.userAgent,
      cycles: CYCLES,
      concurrentViewers: 2,
      samples: rows.current.length,
      baselineGeometryCount: baseline.current.geometries,
      baselineTextureCount: baseline.current.textures,
      activeGeometryMin: Math.min(...active.map(item => item.geometries)),
      activeGeometryMax: Math.max(...active.map(item => item.geometries)),
      finalGeometryCount: row.geometries,
      finalTextureCount: row.textures,
      contextLoss: rows.current.some(item => item.contextLost),
    }
    result.passed = result.baselineGeometryCount === 0
      && result.activeGeometryMin === 2 && result.activeGeometryMax === 2
      && result.finalGeometryCount === result.baselineGeometryCount
      && result.finalTextureCount === result.baselineTextureCount && !result.contextLoss
    setReport(result)
    setStatus(result.passed ? 'PASS — allocated geometry stayed at two, then returned to zero.' : 'FAIL — inspect allocation counts.')
    setReady(false)
  }, [next])

  useEffect(() => {
    if (cycle < 0 || report) return
    const timer = setTimeout(() => {
      failed.current = true
      setStatus(`FAIL — model ${cycle + 1} did not settle in 15 seconds.`)
      setReady(false)
    }, 15000)
    return () => clearTimeout(timer)
  }, [cycle, report])
  useEffect(() => () => { if (objectUrl.current) URL.revokeObjectURL(objectUrl.current) }, [])

  async function start() {
    setStatus('Preparing synthetic cube fixtures…')
    try { assets.current = await fixtures(); next(0) }
    catch (error) { setStatus(`FAIL — ${error.message}`) }
  }

  return <main style={{ fontFamily: 'system-ui', color: '#e2e8f0', background: '#0f172a', padding: 24, minHeight: '100vh' }}>
    <h1>Viewer resource probe</h1>
    <p>Real artifact loader and WebGL renderer. Synthetic cube assets; no API calls.</p>
    <button onClick={start} disabled={cycle !== -1 || ready} style={{ padding: 12 }}>Run 100 model swaps</button>
    <p role="status">{status}</p>
    <div style={{ height: 300, background: '#1e293b' }}>
      <Canvas camera={{ position: [3, 2, 5] }}>
        <ambientLight intensity={2} />
        {cycle === -2 && [0, 1].map(id => <mesh key={id} position={[id ? 0.8 : -0.8, 0, 0]}>
          <boxGeometry /><meshStandardMaterial color="#22c55e" />
        </mesh>)}
        {request && [0, 1].map(id => <Model key={id} request={request} id={id} loaded={loaded} />)}
        <Meter cycle={cycle} ready={ready} sample={sample} />
      </Canvas>
    </div>
    {report && <pre aria-label="Resource measurements">{JSON.stringify(report, null, 2)}</pre>}
    <p>This bounded probe covers geometry lifecycle. It does not certify large-model, textured-asset, WASM or production soak budgets.</p>
  </main>
}
