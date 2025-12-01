# TODO - Fonctionnalités Vincent-d'Indy

## Vue Technicien - Améliorations

### 1. Filtre de vue des pianos ✅ FAIT
- [x] Par défaut : uniquement pianos de la tournée (jaunes = proposed)
- [x] Bouton "Tous les pianos" pour voir l'inventaire complet
- [ ] **IMPORTANT** : Le technicien peut écrire observations sur N'IMPORTE QUEL piano
  - Même si le piano n'est pas "proposé" par Nicolas (pas jaune)
  - Le technicien peut ouvrir un piano dans "Tous", ajouter travail/observations
  - Ces observations vont dans le champ "À faire" du piano
  - Nicolas peut ensuite voir ces notes

### 2. Boîte de recherche par local
- [ ] Ajouter une barre de recherche en haut de la vue technicien
- [ ] Recherche en temps réel sur le champ "local"
- [ ] Toujours identifier "VD" (Vincent-d'Indy) dans les résultats
- [ ] Exemple : rechercher "301" affiche "VD-301" ou "Local 301"
- [ ] La recherche fonctionne aussi bien en mode "À faire" qu'en mode "Tous"
- [ ] **Note** : Ne PAS ajouter le préfixe "VD-" automatiquement, juste s'assurer que la recherche fonctionne bien

### 3. Interface mobile optimisée
- [ ] Design responsive déjà en place
- [ ] Tester sur mobile réel
- [ ] Ajuster tailles de police si nécessaire
- [ ] S'assurer que la recherche fonctionne bien au tactile

## Partage de données - En cours ✅ IMPLÉMENTÉ

### Architecture actuelle
- [x] Backend : endpoint PUT `/vincent-dindy/pianos/{id}`
- [x] Stockage GitHub Gist pour modifications persistantes
- [x] Frontend : appels API au lieu de localStorage
- [x] Mise à jour optimiste pour réactivité

### À tester
- [ ] Vérifier partage entre Nicolas et technicien
- [ ] Tester sur deux navigateurs différents
- [ ] Confirmer que modifications apparaissent en temps réel (avec rafraîchissement)

## Prochaines étapes

1. **Priorité 1** : Ajouter boîte de recherche par local
2. **Priorité 2** : Tester partage de données après déploiement
3. **Priorité 3** : Tests sur mobile

## Notes techniques

### Recherche par local - Design proposé
```javascript
// État
const [searchLocal, setSearchLocal] = useState('');

// Filtrage
const pianosFiltres = useMemo(() => {
  let result = [...pianos];

  // ... filtres existants ...

  // Filtre de recherche par local
  if (searchLocal.trim()) {
    result = result.filter(p =>
      p.local.toLowerCase().includes(searchLocal.toLowerCase())
    );
  }

  return result;
}, [pianos, searchLocal, ...]);

// UI
<input
  type="text"
  placeholder="Rechercher par local (ex: 301, VD-301)"
  value={searchLocal}
  onChange={(e) => setSearchLocal(e.target.value)}
  className="w-full px-3 py-2 border rounded"
/>
```

### Identifiant VD
- Tous les locaux devraient afficher "VD-" comme préfixe
- Alternative : utiliser le champ "école" ou "client" = "Vincent-d'Indy"
- À discuter avec Nicolas

---

**Dernière mise à jour** : 2025-12-01
**Responsable** : Allan Sutton
**Assistant** : Claude Code
