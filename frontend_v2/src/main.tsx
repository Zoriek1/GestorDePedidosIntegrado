import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'animate.css' // Biblioteca de animações CSS
import './index.css'
import App from './app/App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
