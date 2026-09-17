import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../index.css'
import HseApp from './HseApp.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HseApp />
  </StrictMode>,
)
