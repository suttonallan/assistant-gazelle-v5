import { useState, useEffect } from 'react'
import { ROLES } from '../config/roles'

// Base de données des utilisateurs avec leurs PINs
// IMPORTANT: gazelleId est l'ID Gazelle du technicien (source de vérité)
// Voir docs/REGLE_IDS_GAZELLE.md
const USERS = [
  {
    id: 1,
    name: 'Allan',
    initials: 'AS',
    email: ROLES.admin.email,
    role: 'admin',
    pin: '6342',
    gazelleId: 'usr_ofYggsCDt2JAVeNP'  // ID Gazelle technicien ALLAN
  },
  {
    id: 2,
    name: 'Louise',
    initials: 'L',
    email: ROLES.louise.email,
    role: 'admin',
    pin: '6343',
    gazelleId: null  // Louise n'est pas technicien
  },
  {
    id: 3,
    name: 'Nick',
    initials: 'NL',
    email: ROLES.nick.email,
    role: 'technician',
    pin: '6344',
    gazelleId: 'usr_HcCiFk7o0vZ9xAI0'  // ID Gazelle technicien Nicolas
  },
  {
    id: 4,
    name: 'JP',
    initials: 'JP',
    email: ROLES.jeanphilippe.email,
    role: 'technician',
    pin: '6345',
    gazelleId: 'usr_ReUSmIJmBF86ilY1'  // ID Gazelle technicien JP
  },
  {
    id: 5,
    name: 'Margot',
    initials: 'MC',
    email: ROLES.margot.email,
    role: 'assistant',
    pin: '6341',
    gazelleId: 'usr_bbt59aCUqUaDWA8n'  // Margot Charignon dans Gazelle
  },
  // ═══════════════════════════════════════════════════════════════════
  // TECHNICIENS TEMPORAIRES — Weekend VDI
  // Chaque technicien voit SEULEMENT la vue technicien Vincent-d'Indy
  // Ses notes sont identifiées par leurs initiales dans le champ travail
  // ═══════════════════════════════════════════════════════════════════
  { id: 6, name: 'Alexandre', initials: 'AB', email: 'alexandre.bourke@gmail.com', role: 'technician_vdi', pin: '6346', gazelleId: null },
  { id: 7, name: 'Nikolas', initials: 'NG', email: 'nikolas.gaudreault@gmail.com', role: 'technician_vdi', pin: '6347', gazelleId: null },
  { id: 8, name: 'Guillaume', initials: 'GL', email: 'guillaume@laccordeur.ca', role: 'technician_vdi', pin: '6348', gazelleId: null },
]

export default function LoginScreen({ onLogin }) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')

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

  const authenticateWithPin = (pinCode) => {
    const user = USERS.find(u => u.pin === pinCode)

    if (user) {
      // Sauvegarder dans localStorage
      localStorage.setItem('currentUser', JSON.stringify(user))
      onLogin(user)
    } else {
      setError('PIN incorrect')
      // Réinitialiser après 1 seconde
      setTimeout(() => {
        setPin('')
        setError('')
      }, 1000)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden">
        <div className="p-8">
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
