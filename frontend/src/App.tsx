import { useState } from 'react'
import { SeismicMap } from './components/SeismicMap'
import { useSeismicData } from './hooks/useSeismicData'
import './App.css'

function App() {
  const [selectedFileIds, setSelectedFileIds] = useState<number[]>([])
  const [showLines, setShowLines] = useState(true)
  const [showPoints, setShowPoints] = useState(true)
  const [showTraces, setShowTraces] = useState(false)
  const { files, summary, layers, loading, uploading, error, uploadFiles } = useSeismicData(selectedFileIds)
  const selectedFiles = files.filter((file) => selectedFileIds.includes(file.id))

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (selectedFiles.length === 0) return

    try {
      const fileIds = await uploadFiles(selectedFiles)
      if (fileIds.length > 0) setSelectedFileIds(fileIds)
    } catch {
      // The hook exposes the user-facing error state.
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div><span className="eyebrow">WEBGIS / DATA SERVING</span><h1>Seismic field atlas</h1></div>
        <span className="connection"><i /> PostGIS connected</span>
      </header>
      <section className="workspace">
        <aside className="sidebar">
          <label className="field-label" htmlFor="file-upload">Upload SEG-Y files</label>
          <label className={`upload-button${uploading ? ' is-uploading' : ''}`} htmlFor="file-upload">
            <span>{uploading ? 'Processing...' : 'Choose .sgy files'}</span><b>+</b>
          </label>
          <input id="file-upload" className="sr-only" type="file" accept=".sgy,application/octet-stream" multiple disabled={uploading} onChange={handleFileUpload} />
          <small className="upload-hint">Files are sent to Backend 1 for processing.</small>
          <label className="field-label" htmlFor="file-select">Processed surveys</label>
          <select id="file-select" multiple size={6} value={selectedFileIds.map(String)} onChange={(event) => setSelectedFileIds(Array.from(event.target.selectedOptions, (option) => Number(option.value)))}>
            {files.map((file) => <option key={file.id} value={file.id}>{file.label}</option>)}
          </select>
          {selectedFiles.length > 0 && <div className="file-status"><span style={{ background: '#e4572e' }} /> <strong>{selectedFiles.length} selected</strong><small>map EPSG:4326</small></div>}
          <div className="rule" />
          <p className="section-label">Map layers</p>
          <label className="toggle"><input type="checkbox" checked={showLines} onChange={(event) => setShowLines(event.target.checked)} /><span>Seismic lines</span><b>{summary?.processed_line_count ?? 0}</b></label>
          <label className="toggle"><input type="checkbox" checked={showPoints} onChange={(event) => setShowPoints(event.target.checked)} /><span>Shot points</span><b>{summary?.processed_shot_point_count ?? 0}</b></label>
          <label className="toggle"><input type="checkbox" checked={showTraces} onChange={(event) => setShowTraces(event.target.checked)} /><span>Trace positions</span><b>{summary?.processed_trace_count ?? 0}</b></label>
          <div className="sidebar-footer"><span>API endpoint</span><code>localhost:8001</code></div>
        </aside>
          <div className="map-panel"><SeismicMap data={layers} showLines={showLines} showPoints={showPoints} showTraces={showTraces} />{selectedFileIds.length === 0 && <div className="map-empty"><span>⌁</span><strong>Select surveys to begin</strong><small>Processed geometry will appear here</small></div>}{loading && <div className="loading">Loading data...</div>}{error && <div className="error">{error}</div>}<div className="map-legend"><span><i className="line-key" />Line</span><span><i className="point-key" />Shot point</span><span><i className="trace-key" />Trace</span></div></div>
      </section>
      <footer className="summary"><div><span className="eyebrow">SELECTED DATASET</span><strong>{summary?.filename ?? 'No survey selected'}</strong></div><div className="metrics"><span><b>{summary?.processed_line_count ?? 0}</b> lines</span><span><b>{summary?.processed_shot_point_count ?? 0}</b> shot points</span><span><b>{summary?.processed_trace_count ?? 0}</b> traces</span></div></footer>
    </main>
  )
}

export default App
