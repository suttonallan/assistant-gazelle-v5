// 🎙️ Voix d'Ivo : dicter une demande et écouter les réponses.
// Utilise ce que le navigateur offre déjà (aucun coût, rien à installer) :
//  - la dictée (reconnaissance vocale) de Chrome ou Safari, en français ;
//  - la lecture à voix haute du système (sur Mac, voix françaises comme Amélie).
// Si le navigateur ne le permet pas, les boutons ne s'affichent simplement pas.
import { useCallback, useEffect, useRef, useState } from 'react'

const Reconnaissance = typeof window !== 'undefined'
  ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null
export const dicteePossible = !!Reconnaissance
export const lecturePossible = typeof window !== 'undefined' && 'speechSynthesis' in window

const CLE_AUTO = 'ivoLectureAuto'
export const lireLectureAuto = () => { try { return localStorage.getItem(CLE_AUTO) === '1' } catch { return false } }
export const ecrireLectureAuto = (v) => { try { localStorage.setItem(CLE_AUTO, v ? '1' : '0') } catch {} }

// Retire ce qui se lit mal à voix haute (émojis, symboles de mise en forme).
const nettoyer = (t) => String(t || '')
  .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, '')
  .replace(/[*_#`>]/g, '')
  .replace(/https?:\/\/\S+/g, 'un lien')
  .replace(/\s+/g, ' ')
  .trim()

const voixFrancaise = () => {
  const v = window.speechSynthesis.getVoices()
  return v.find((x) => /fr[-_]CA/i.test(x.lang)) || v.find((x) => /^fr/i.test(x.lang)) || null
}

export function lireAVoixHaute(texte, { onFin } = {}) {
  if (!lecturePossible) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(nettoyer(texte))
  u.lang = 'fr-CA'
  u.rate = 0.95
  const v = voixFrancaise()
  if (v) u.voice = v
  if (onFin) { u.onend = onFin; u.onerror = onFin }
  window.speechSynthesis.speak(u)
}

export const arreterLecture = () => { if (lecturePossible) window.speechSynthesis.cancel() }

/** Dictée : appelle onTexte(texte) quand la personne a fini de parler. */
export function useDictee(onTexte) {
  const [ecoute, setEcoute] = useState(false)
  const [erreur, setErreur] = useState('')
  const reco = useRef(null)
  const rappel = useRef(onTexte)
  rappel.current = onTexte

  useEffect(() => () => { try { reco.current?.abort() } catch {} }, [])

  const basculer = useCallback(() => {
    if (!Reconnaissance) return
    if (ecoute) { try { reco.current?.stop() } catch {} return }
    arreterLecture() // ne pas s'entendre soi-même pendant qu'on parle
    const r = new Reconnaissance()
    r.lang = 'fr-CA'
    r.interimResults = false
    r.continuous = false
    r.onresult = (e) => {
      const t = Array.from(e.results).map((x) => x[0]?.transcript || '').join(' ').trim()
      if (t) rappel.current?.(t)
    }
    r.onerror = (e) => {
      setErreur(e?.error === 'not-allowed'
        ? "Le micro n'est pas autorisé : acceptez la demande du navigateur, puis réessayez."
        : e?.error === 'no-speech' ? "Je n'ai rien entendu. Réessayez." : '')
    }
    r.onend = () => setEcoute(false)
    reco.current = r
    setErreur('')
    setEcoute(true)
    try { r.start() } catch { setEcoute(false) }
  }, [ecoute])

  return { ecoute, erreur, basculer }
}
