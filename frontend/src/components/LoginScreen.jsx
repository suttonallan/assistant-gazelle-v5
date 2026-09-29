import { useState, useEffect } from 'react'
import { ROLES } from '../config/roles'
import { API_URL } from '../utils/apiConfig'
import { ecrireJeton } from '../utils/jetonApi'

// Utilisateurs de l'équipe. Les PIN ne sont PLUS ici : le serveur les vérifie
// (core/verrou_api.py) et remet un jeton de connexion.
// IMPORTANT: gazelleId est l'ID Gazelle du technicien (source de vérité)
// Voir docs/REGLE_IDS_GAZELLE.md
const USERS = [
  {
    id: 1,
    name: 'Allan',
    initials: 'AS',
    email: ROLES.admin.email,
    role: 'admin',
    gazelleId: 'usr_ofYggsCDt2JAVeNP'  // ID Gazelle technicien ALLAN
  },
  {
    id: 2,
    name: 'Louise',
    initials: 'L',
    email: ROLES.louise.email,
    role: 'admin',
    gazelleId: null  // Louise n'est pas technicien
  },
  {
    id: 3,
    name: 'Nick',
    initials: 'NL',
    email: ROLES.nick.email,
    role: 'technician',
    gazelleId: 'usr_HcCiFk7o0vZ9xAI0'  // ID Gazelle technicien Nicolas
  },
  {
    id: 4,
    name: 'JP',
    initials: 'JP',
    email: ROLES.jeanphilippe.email,
    role: 'technician',
    gazelleId: 'usr_ReUSmIJmBF86ilY1'  // ID Gazelle technicien JP
  },
  {
    id: 5,
    name: 'Margot',
    initials: 'MC',
    email: ROLES.margot.email,
    role: 'assistant',
    gazelleId: 'usr_bbt59aCUqUaDWA8n'  // Margot Charignon dans Gazelle
  },
  // ═══════════════════════════════════════════════════════════════════
  // TECHNICIENS TEMPORAIRES — Weekend VDI
  // Chaque technicien voit SEULEMENT la vue technicien Vincent-d'Indy
  // Ses notes sont identifiées par leurs initiales dans le champ travail
  // ═══════════════════════════════════════════════════════════════════
  { id: 6, name: 'Alexandre', initials: 'AB', email: 'alexandre.bourke@gmail.com', role: 'alexandre', gazelleId: null },
  { id: 8, name: 'Guillaume', initials: 'GL', email: 'guillaume@laccordeur.ca', role: 'guillaume', gazelleId: null },
]

export default function LoginScreen({ onLogin }) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [googleId, setGoogleId] = useState(null)

  // 🔐 Connexion Google : active dès que le serveur fournit l'identifiant de l'app
  useEffect(() => {
    fetch(`${API_URL}/api/auth/config`).then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.google_client_id) setGoogleId(d.google_client_id) }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!googleId) return
    const surCredential = async ({ credential }) => {
      setError('')
      try {
        const r = await fetch(`${API_URL}/api/auth/google`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ credential }),
        })
        const d = await r.json().catch(() => ({}))
        const user = r.ok ? USERS.find((u) => u.email === d.email) : null
        if (user) {
          ecrireJeton(d.jeton)
          localStorage.setItem('currentUser', JSON.stringify(user))
          onLogin(user)
        } else {
          setError(d.detail || 'Connexion Google refusée')
        }
      } catch {
        setError('Serveur injoignable, réessayez')
      }
    }
    const initialiser = () => {
      window.google.accounts.id.initialize({ client_id: googleId, callback: surCredential, auto_select: true })
      const zone = document.getElementById('bouton-google')
      if (zone) window.google.accounts.id.renderButton(zone, { theme: 'filled_blue', size: 'large', text: 'signin_with', shape: 'pill', width: 280 })
    }
    if (window.google?.accounts?.id) { initialiser(); return }
    const sc = document.createElement('script')
    sc.src = 'https://accounts.google.com/gsi/client'
    sc.async = true
    sc.onload = initialiser
    document.head.appendChild(sc)
  }, [googleId])

  // Écouter les touches du clavier
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Touches numériques (0-9)
      if (e.key >= '0' && e.key <= '9') {
        e.preventDefault()
        handlePinInput(e.key)
      }
      // Backspace ou Delete
      else if (e.key === 'Backspace' || e.key === 'Delete') {
        e.preventDefault()
        handleBackspace()
      }
      // Enter (valider si 4 chiffres)
      else if (e.key === 'Enter' && pin.length === 4) {
        e.preventDefault()
        authenticateWithPin(pin)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [pin]) // Dépendance: pin pour avoir la valeur à jour

  const handlePinInput = (digit) => {
    if (pin.length < 4) {
      const newPin = pin + digit
      setPin(newPin)
      setError('')

      // Auto-login dès que 4 chiffres sont entrés
      if (newPin.length === 4) {
        setTimeout(() => {
          authenticateWithPin(newPin)
        }, 100)
      }
    }
  }

  const handleBackspace = () => {
    setPin(pin.slice(0, -1))
    setError('')
  }

  const [verif, setVerif] = useState(false)

  const authenticateWithPin = async (pinCode) => {
    if (verif) return
    setVerif(true)
    try {
      const r = await fetch(`${API_URL}/api/auth/connexion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pinCode }),
      })
      const d = await r.json().catch(() => ({}))
      const user = r.ok ? USERS.find(u => u.email === d.email) : null
      if (user) {
        ecrireJeton(d.jeton)
        localStorage.setItem('currentUser', JSON.stringify(user))
        onLogin(user)
        return
      }
      setError(r.status === 429 ? d.detail : 'PIN incorrect')
    } catch {
      setError('Serveur injoignable, réessayez')
    } finally {
      setVerif(false)
    }
    setTimeout(() => {
      setPin('')
      setError('')
    }, 1500)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden">
        <div className="p-8">
          {googleId && (
            <div className="mb-8 text-center">
              <div className="text-4xl mb-4">🎹</div>
              <h1 className="text-2xl font-bold text-gray-800 mb-5">Assistant Gazelle</h1>
              <div id="bouton-google" className="flex justify-center" />
              <div className="mt-6 text-xs text-gray-400 uppercase tracking-wider">ou avec le PIN</div>
            </div>
          )}
          {/* Titre épuré */}
          <div className="text-center mb-8">
            <div className="text-4xl mb-4">🔒</div>
            <h1 className="text-2xl font-bold text-gray-800">
              Entrez votre PIN
            </h1>
          </div>

          {/* Affichage du PIN (points) */}
          <div className="mb-8">
            <div className="flex justify-center gap-3">
              {[0, 1, 2, 3].map((index) => (
                <div
                  key={index}
                  className={`w-14 h-14 rounded-xl border-2 flex items-center justify-center transition-all ${
                    pin.length > index
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-300 bg-white'
                  }`}
                >
                  {pin.length > index && (
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Message d'erreur */}
          {verif && !error && (
            <div className="text-center text-sm text-gray-500 mb-4">Vérification…</div>
          )}
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm text-center animate-shake">
              {error}
            </div>
          )}

          {/* Pavé numérique */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => (
              <button
                key={digit}
                onClick={() => handlePinInput(digit.toString())}
                className="h-16 rounded-xl bg-gray-100 hover:bg-gray-200 active:bg-gray-300 font-semibold text-xl text-gray-800 transition-colors touch-manipulation"
                disabled={pin.length >= 4}
              >
                {digit}
              </button>
            ))}

            {/* Ligne du bas: vide, 0, backspace */}
            <div></div>
            <button
              onClick={() => handlePinInput('0')}
              className="h-16 rounded-xl bg-gray-100 hover:bg-gray-200 active:bg-gray-300 font-semibold text-xl text-gray-800 transition-colors touch-manipulation"
              disabled={pin.length >= 4}
            >
              0
            </button>
            <button
              onClick={handleBackspace}
              className="h-16 rounded-xl bg-red-50 hover:bg-red-100 active:bg-red-200 font-semibold text-xl text-red-600 transition-colors touch-manipulation flex items-center justify-center"
              disabled={pin.length === 0}
            >
              ⌫
            </button>
          </div>

          {/* Texte d'aide */}
          <div className="text-center text-xs text-gray-400 mt-6">
            <div>Code PIN à 4 chiffres</div>
            <div className="mt-1 text-gray-500">💻 Clavier ou pavé tactile</div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-8px); }
          75% { transform: translateX(8px); }
        }
        .animate-shake {
          animation: shake 0.3s ease-in-out;
        }
        .touch-manipulation {
          -webkit-tap-highlight-color: transparent;
          user-select: none;
        }
      `}</style>
    </div>
  )
}
