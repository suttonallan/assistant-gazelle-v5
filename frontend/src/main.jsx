// LOG: Début du fichier main.jsx
console.log('[main.jsx] Fichier chargé - ligne 1');

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

console.log('[main.jsx] Avant ReactDOM.createRoot');

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

console.log('[main.jsx] Après ReactDOM.createRoot');





