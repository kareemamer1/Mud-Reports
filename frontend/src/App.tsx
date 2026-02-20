import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/dashboard/:jobId" element={<Dashboard />} />
      <Route path="/dashboard/:jobId/:date" element={<Dashboard />} />
    </Routes>
  )
}

export default App
