/**
 * File d'attente offline pour la saisie de service du technicien.
 *
 * Objectif : sur réseau faible/intermittent (ex. Orford), la saisie ne doit
 * JAMAIS disparaître. On persiste chaque sauvegarde dans localStorage AVANT
 * l'appel réseau ; on la retire seulement quand le serveur a confirmé. Tant
 * qu'une entrée reste en file, elle est ré-essayée (au retour du réseau et
 * périodiquement). Les sauvegardes visées sont idempotentes (upsert de la fiche
 * tampon), donc un ré-essai ne crée pas de doublon.
 */
const KEY = 'ptm_offline_service_queue_v1';

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
}

function write(queue) {
  try {
    localStorage.setItem(KEY, JSON.stringify(queue));
  } catch {
    // localStorage plein/indisponible : on ne casse pas la saisie pour autant.
  }
}

/** Ajoute/remplace l'entrée en file pour un piano (clé = pianoId). */
export function enqueue(pianoId, entry) {
  const q = read();
  q[pianoId] = { ...entry, queuedAt: new Date().toISOString() };
  write(q);
}

/** Retire l'entrée d'un piano (après confirmation serveur). */
export function dequeue(pianoId) {
  const q = read();
  if (pianoId in q) {
    delete q[pianoId];
    write(q);
  }
}

export function getEntry(pianoId) {
  return read()[pianoId] || null;
}

export function getAll() {
  return read();
}

export function pendingCount() {
  return Object.keys(read()).length;
}

/**
 * Tente d'envoyer toutes les entrées en file.
 * sendOne(pianoId, entry) doit retourner une promesse : résolue => on retire
 * l'entrée ; rejetée => on la garde pour un prochain essai.
 * Retourne { ok, fail }.
 */
export async function flush(sendOne) {
  const q = read();
  const ids = Object.keys(q);
  let ok = 0;
  let fail = 0;
  for (const pianoId of ids) {
    try {
      await sendOne(pianoId, q[pianoId]);
      dequeue(pianoId);
      ok += 1;
    } catch {
      fail += 1;
    }
  }
  return { ok, fail };
}
