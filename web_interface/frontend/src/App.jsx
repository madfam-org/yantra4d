import { useState, useEffect } from 'react'
import axios from 'axios'
import Controls from './components/Controls'
import Viewer from './components/Viewer'
import './index.css'

function App() {
  const [params, setParams] = useState({
    size: 20.0,
    thick: 2.5,
    show_base: true,
    show_walls: true,
    show_mech: true
  })
  const [stlUrl, setStlUrl] = useState(null)
  const [logs, setLogs] = useState("Ready.")
  const [loading, setLoading] = useState(false)

  const handleGenerate = async () => {
    setLoading(true)
    setLogs(prev => prev + "\nGenerating...")
    try {
      const res = await axios.post('http://localhost:5000/api/render', params)
      setStlUrl(res.data.stl_url + "?t=" + Date.now()) // Cache bust
      setLogs(prev => prev + "\nGenerated STL.")
    } catch (e) {
      setLogs(prev => prev + "\nError: " + e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    setLoading(true)
    setLogs(prev => prev + "\nVerifying design...")
    try {
      const res = await axios.post('http://localhost:5000/api/verify')
      setLogs(prev => prev + "\n\n--- VERIFICATION REPORT ---\n" + res.data.output)
      if (res.data.passed) setLogs(prev => prev + "\n[PASS] Design Verified.")
      else setLogs(prev => prev + "\n[FAIL] Issues detected.")
    } catch (e) {
      setLogs(prev => prev + "\nVerify Error: " + e.message)
    } finally {
      setLoading(false)
    }
  }

  // Debounced auto-generate
  useEffect(() => {
    const timer = setTimeout(() => {
      handleGenerate()
    }, 500)
    return () => clearTimeout(timer)
  }, [params])

  return (
    <div className="layout">
      <div className="sidebar">
        <h2>Tablaco Studio</h2>
        <Controls params={params} setParams={setParams} />
        <div style={{ flex: 1 }}></div>
        <button className="btn" onClick={handleGenerate} disabled={loading}>
          {loading ? 'Processing...' : 'Force Regenerate'}
        </button>
        <button className="btn btn-secondary" onClick={handleVerify} disabled={loading}>
          Run Verification Suite
        </button>
      </div>
      <div className="main-view">
        <div className="viewer-container">
          <Viewer stlUrl={stlUrl} />
        </div>
        <div className="console">
          {logs}
        </div>
      </div>
    </div>
  )
}

export default App
