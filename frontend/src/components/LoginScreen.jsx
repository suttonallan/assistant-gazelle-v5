import { useState } from 'react'
import { ROLES } from '../config/roles'

// Utiliser les vrais emails depuis la configuration des rôles
// IMPORTANT: gazelleId est l'ID Gazelle du technicien (source de vérité)
// Voir docs/REGLE_IDS_GAZELLE.md
const USERS = [
  {
    id: 1,
    name: 'Allan',
    email: ROLES.admin.email,
    role: 'admin',
    pin: '6342',
    gazelleId: 'usr_ReUSmIJmBF86ilY1'  // ID Gazelle technicien
  },
  {
    id: 2,
    name: 'Louise',
    email: ROLES.louise.email,
    role: 'admin',
    pin: '6343',
    gazelleId: null  // Louise n'est pas technicien
  },
  {
    id: 3,
    name: 'Nick',
    email: ROLES.nick.email,
    role: 'technician',
    pin: '6344',
    gazelleId: 'usr_HcCiFk7o0vZ9xAI0'  // ID Gazelle technicien Nicolas
  },
  {
    id: 4,
    name: 'JP',
    email: ROLES.jeanphilippe.email,
    role: 'technician',
    pin: '6345',
    gazelleId: 'usr_ofYggsCDt2JAVeNP'  // ID Gazelle technicien JP
  },
]

export default function LoginScreen({ onLogin }) {
  const [selectedUser, setSelectedUser] = useState(null)
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')

  const handleLogin = (e) => {
    e.preventDefault()

    if (!selectedUser) {
      setError('Veuillez sélectionner un utilisateur')
      return
    }

    if (pin === selectedUser.pin) {
      // Sauvegarder dans localStorage
      localStorage.setItem('currentUser', JSON.stringify(selectedUser))
      onLogin(selectedUser)
    } else {
      setError('PIN incorrect')
      setPin('')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full overflow-hidden">
        <div className="p-8 md:p-10">
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold text-gray-800 mb-2">
                Vincent-d'Indy
              </h1>
              <p className="text-gray-600">Dashboard Techniciens</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Qui êtes-vous ?
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {USERS.map((user) => (
                    <button
                      key={user.id}
                      type="button"
                      onClick={() => {
                        setSelectedUser(user)
                        setError('')
                      }}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        selectedUser?.id === user.id
                          ? 'border-blue-500 bg-blue-50 shadow-md'
                          : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="text-2xl mb-1">👤</div>
                      <div className="text-sm font-medium text-gray-800">
                        {user.name}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {user.role === 'admin' ? 'Admin' : 'Tech'}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {selectedUser && (
                <div>
                  <label htmlFor="pin" className="block text-sm font-medium text-gray-700 mb-2">
                    Entrez votre PIN
                  </label>
                  <input
                    type="password"
                    id="pin"
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-2xl tracking-widest"
                    placeholder="••••"
                    maxLength={4}
                    autoFocus
                  />
                </div>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={!selectedUser || pin.length !== 4}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                Se connecter
              </button>
            </form>

            <div className="mt-6 text-center text-xs text-gray-500">
              <p>Sélectionnez votre nom et entrez votre PIN à 4 chiffres</p>
            </div>
          </div>
      </div>
    </div>
  )
}
