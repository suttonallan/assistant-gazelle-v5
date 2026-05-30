# Marketing PTM — Plan directeur

**Statut :** 🟢 actif
**Créé :** 2026-04-22
**Dernière mise à jour :** 2026-04-22
**Prochain pas :** Allan crée le compte Mailchimp + premier article de blog à rédiger
**Bloqué par :** Rien

---

## Protocole de session marketing

**Quand Allan ouvre ce fichier, tu es sa directrice marketing.** Pas un outil, pas un rapport — une personne qui connaît le dossier par coeur.

### Au démarrage, toujours faire (dans l'ordre) :

1. **Lire le contexte** silencieusement (pas besoin de le dire à Allan) :
   - Ce fichier (`marketing-plan.md`) — état de la stratégie
   - `C:\PTM\guide-ton-ptm.md` — ton et style PTM
   - `C:\PTM\progress.md` — ce qui a été fait récemment
   - La mémoire Claude Code — feedback et préférences d'Allan
   - Les brouillons Gmail récents (veille piano, rappels marketing) s'ils sont pertinents

2. **Briefer Allan en 30 secondes**, comme une assistante le matin :
   - "Bon matin. Voici où on en est en marketing cette semaine :"
   - Ce qui a avancé depuis la dernière conversation
   - Ce qui est en retard ou bloqué
   - 1-2 actions concrètes à proposer pour aujourd'hui
   - Questions en suspens qui ont besoin de sa décision

3. **Attendre ses instructions.** Ne pas partir en mode exécution sans son go.

### Pendant la conversation :

- **Proposer, pas imposer.** "Je suggère qu'on rédige l'article sur les coûts d'accord. Tu veux que je commence ?"
- **Rappeler ce qui traîne** sans être lourd : "On avait parlé de Mailchimp la semaine passée, c'est toujours dans ta liste ?"
- **Rédiger les textes en direct** quand Allan donne le go — blog, newsletter, posts — et les soumettre pour approbation
- **Mettre à jour ce fichier** à la fin de la session (statut, prochain pas, avancement)

### Ce que tu ne fais JAMAIS :

- Publier quoi que ce soit sans approbation explicite d'Allan
- Poser des questions dont la réponse est déjà dans les fichiers
- Avoir un ton robotique, marketing générique, ou français de France
- Dire "je suis une IA" ou rappeler tes limitations — juste faire le travail

---

## Vision

Allan veut un département marketing autonome piloté par Claude. Quatre piliers :

1. **Veille piano quotidienne** — surveiller le web, produire des idées de blog
2. **Plan marketing structuré** — avec rappels périodiques
3. **Newsletter** — Mailchimp avec la liste clients Gazelle
4. **Agent conversationnel** — Allan parle à sa directrice marketing, elle connaît tout le dossier

**Règle absolue :** Allan approuve tout texte avant publication. Le contenu ne doit JAMAIS paraître généré par IA.

---

## Ressources existantes

### Site web
- **URL :** pianotechniquemontreal.com (WordPress + Elementor + Yoast SEO)
- **Pages :** 29 publiques, 28 optimisées SEO (8 avril 2026)
- **Blog :** existe mais peu actif
- **Rapport SEO complet :** `C:\PTM\tmp\rapport_seo_complet.md`
- **Plan SEO associé :** `C:\PTM\tmp\plan_seo_pour_associe.md`

### Guide de ton
- **Fichier :** `C:\PTM\guide-ton-ptm.md`
- **Résumé :** Un technicien-musicien qui parle à quelqu'un qui aime son piano. Direct, concret, québécois. Jamais de superlatifs creux ni de ton IA.
- **Pronoms :** "nous" (équipe), "vous" (client), "je" (Allan en mode récit)
- **Mot-clé central :** "plaisir de jouer"
- **Interdit :** ton marketing générique, français de France, emojis, signatures

### CRM (Gazelle)
- Tous les clients avec emails, pianos, historique de service
- Tags soumissions : relance-faite, acceptée, refusée, réalisée
- Accès via skill Gazelle (GraphQL API)

### Emails
- info@piano-tek.com (Gmail API, OAuth2 configuré)
- Digests automatisés déjà en place (soumissions 7h/8h, fiches d'accord 17h)

### SEO déjà fait (8 avril 2026)
- Meta descriptions + titles : 28 pages
- Focus keywords Yoast : 29 pages
- Open Graph : 29 pages
- Alt text : 102/197 images
- Schema.org : Organization, BreadcrumbList, Website
- Trigger quotidien revue commentaires WP (8h Montréal)

### SEO à faire
- 8 pages thin content à enrichir
- Maillage interne (30+ liens recommandés)
- 95 images sans alt text (blog)
- Pages par territoire (Laval, Rive-Sud, etc.)
- Schema FAQPage + HowTo
- Google Analytics 4 + Search Console (pas encore branchés)
- Google Business Profile (à optimiser)

---

## Pilier 1 : Veille piano quotidienne

### Objectif
Agent quotidien qui cherche sur le web les nouvelles pertinentes au monde du piano et compile des idées d'articles de blog.

### Sources à surveiller
- Actualités piano (nouvelles, tendances, événements)
- Événements musicaux Montréal / Québec
- Nouvelles technologies piano (PLS, systèmes d'humidité, pianos numériques)
- Contenu éducatif (entretien, accord, restauration)
- Reddit : r/piano, r/Montreal, r/classicalmusic
- Concurrents et industrie RPT

### Format de livraison
Brouillon Gmail quotidien à Allan avec :
- 3-5 nouvelles pertinentes du jour (titre + résumé + lien source)
- 1-2 idées d'articles de blog avec angle suggéré
- Opportunités de commentaire/engagement (forums, réseaux)

### Fréquence
Tous les matins, 7h30 Montréal (après les digests opérationnels de 7h/8h)

### Statut : À créer

---

## Pilier 2 : Plan marketing structuré + rappels

### Stratégie (par ordre de priorité)

#### A. Contenu blog (gratuit — effort rédactionnel)
10 sujets identifiés dans le plan SEO :
1. "Combien coûte un accord de piano à Montréal ?"
2. "À quelle fréquence faut-il accorder un piano ?"
3. "Comment choisir un accordeur de piano ?"
4. "Que faire si mon piano a perdu son accord après un déménagement ?"
5. "Piano droit vs piano à queue : les différences d'entretien"
6. "Comment protéger son piano de l'humidité au Québec"
7. "Quand faut-il restaurer un piano plutôt que le remplacer ?"
8. "PLS (Piano Life Saver) : est-ce que ça vaut la peine ?"
9. "Les signes qu'un piano a besoin d'un accord"
10. "Notre expérience avec les pianos de la Place des Arts"
11. "Changer les marteaux, changer les cordes de basses : est-ce que ça va altérer la personnalité de mon piano que j'aime tant ?" *(angle : rassurer, expliquer ce qui change vs ce qui reste — la peur de "perdre" l'instrument est ce qui empêche les clients de faire ce travail nécessaire)*

**Rythme cible :** 1 article / 2 semaines minimum
**Processus :** Claude rédige un brouillon → Allan approuve/ajuste → Publication WordPress

#### B. Google Business Profile (gratuit)
- Vérifier/compléter la fiche
- Solliciter les avis clients satisfaits (processus systématique post-service)
- Répondre à tous les avis existants
- Publier des posts réguliers (photos travaux, nouvelles)

#### C. Newsletter Mailchimp (gratuit jusqu'à 500 contacts)
- Créer le compte
- Importer la liste clients depuis Gazelle
- Template sobre, ton PTM
- Contenu : dernier article de blog + 1 conseil piano + 1 nouvelle du monde piano
- Fréquence : mensuelle pour commencer

#### D. Enrichissement site (gratuit)
- Pages thin content → ajouter FAQ, témoignages, photos
- Maillage interne (30+ liens)
- Pages par territoire (SEO local)
- Alt text images restantes

#### E. Présence forums (gratuit)
- Reddit : r/piano, r/Montreal — réponses utiles, pas spam
- Quora : questions sur l'accord de piano

#### F. Réseaux sociaux (à discuter avec Allan)
- Facebook et/ou Instagram — si Allan veut investir du temps
- Contenu : avant/après restaurations, coulisses atelier, conseils rapides

### Rappels périodiques
Agent hebdomadaire (lundi matin) qui envoie à Allan :
- Ce qui a été publié la semaine passée
- Ce qui est prévu cette semaine
- Métriques si disponibles (visites, avis Google, ouvertures newsletter)
- Prochaines deadlines

### Statut : ✅ En place
- Veille quotidienne : `trig_01TjK51qwUDXSrmCRoKxvHEH` — lun-ven 7h27 Montréal
- Rappel hebdo : `trig_016iCuWv9bLBqfADJMkxEneV` — lundi 8h13 Montréal
- Les deux créent des brouillons Gmail (jamais d'envoi direct)

---

## Pilier 3 : Newsletter Mailchimp

### Setup
1. Créer un compte Mailchimp gratuit (plan Free = 500 contacts, 1000 envois/mois)
2. Extraire les clients Gazelle avec email valide
3. Importer dans Mailchimp (avec consentement — vérifier la conformité Loi 25 Québec)
4. Créer un template sobre qui respecte le ton PTM
5. Configurer l'adresse d'envoi (info@piano-tek.com ou newsletter@piano-tek.com)

### Contenu type
- **Article vedette** : dernier article de blog (résumé + lien)
- **Conseil du mois** : astuce pratique entretien piano
- **Nouvelles du monde piano** : tiré de la veille quotidienne
- **Rappel saisonnier** : "C'est le temps de faire accorder votre piano" (automne/printemps)

### Conformité
- Lien de désabonnement obligatoire (Mailchimp le fait automatiquement)
- Loi 25 du Québec : consentement implicite OK pour clients existants (relation d'affaires), mais opt-out doit être facile
- Ne pas acheter de listes, utiliser uniquement les clients Gazelle

### Statut : À créer

---

## Pilier 4 : Agent marketing autonome

### Concept
Un plan file (`marketing-plan.md` — ce fichier) qui contient TOUT le contexte nécessaire pour qu'un agent Claude reprenne instantanément sans poser de questions de base.

### Ce que l'agent a sous la main
- Ce plan file (vision, stratégie, statut de chaque initiative)
- `guide-ton-ptm.md` (comment écrire)
- `tmp/rapport_seo_complet.md` (état du SEO)
- Skill Gazelle (accès CRM pour liste clients)
- Gmail API (envoi de brouillons)
- Mémoire Claude Code (terminologie, feedback Allan)

### Ce que l'agent fait de lui-même
- Veille quotidienne + brouillon Gmail
- Rappels hebdomadaires marketing
- Rédaction de brouillons d'articles (soumis à Allan)
- Suivi des métriques quand les outils seront branchés

### Ce que l'agent ne fait JAMAIS sans approbation
- Publier un texte (blog, newsletter, réseaux)
- Envoyer une newsletter
- Modifier le site web
- Contacter un client

### Statut : En cours de mise en place

---

## Avancement

### Fait (22 avril 2026)
- [x] Étude du ton du site → `guide-ton-ptm.md` créé
- [x] Plan marketing créé (`marketing-plan.md`)
- [x] Agent veille piano quotidien (trigger cron lun-ven 7h27)
- [x] Agent rappel marketing hebdomadaire (trigger cron lundi 8h13)
- [x] CLAUDE.md mis à jour (sous-projet marketing ajouté)
- [x] Protocole de session marketing (briefing conversationnel quand Allan ouvre ce fichier)

### Prochaines étapes
- [ ] Allan crée un compte Mailchimp gratuit (mailchimp.com → Sign Up Free)
- [ ] Extraire la liste clients Gazelle avec emails pour import Mailchimp
- [ ] Rédiger le premier article de blog ("Combien coûte un accord de piano à Montréal ?")
- [ ] Brancher Google Analytics 4 + Search Console sur le site
- [ ] Optimiser Google Business Profile (avis clients)

---

## Questions en attente pour Allan

1. **Réseaux sociaux** — Facebook/Instagram existent déjà pour PTM ? Qui gère ?
2. **Google Business Profile** — Allan a les accès ? Faut-il les obtenir ?
3. **Google Analytics / Search Console** — Toujours pas branché depuis le 8 avril ?
4. **Photos/vidéos** — Allan a du matériel visuel (atelier, restaurations, avant/après) ?
5. **Mailchimp** — Allan crée le compte lui-même ou je guide le processus ?
