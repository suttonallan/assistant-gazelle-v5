# Base de connaissances : Revision de soumissions Gazelle

## Positionnement et ton

Piano Technique Montreal se positionne comme un service **premium/ultra-luxe** de restauration et d'entretien de pianos. Les soumissions doivent refléter ce positionnement :

- **Ton expert et rassurant** : le client doit sentir qu'il confie son instrument à un artisan qui comprend chaque nuance
- **Descriptions orientées bénéfice client** : expliquer le "pourquoi" (bénéfice pour le piano et le pianiste), pas le "comment" (jargon technique)
- **educationDescription** : utiliser ce champ pour éduquer le client sur l'importance du travail proposé
- **Valoriser chaque intervention** : même les petits items doivent communiquer leur valeur

## Regles de description client

1. **Bénéfice avant technique** : "Stabilisation du sommier pour garantir la tenue d'accord" plutôt que "Traitement de colle cyanoacrylate"
2. **Langage accessible** : éviter les termes que seul un technicien comprendrait
3. **Contexte du problème** : expliquer brièvement pourquoi l'intervention est nécessaire
4. **Résultat attendu** : décrire ce que le client va constater après l'intervention

## Regles de regroupement

- **Utiliser les groupes MSL Gazelle tels quels** : ne pas inventer de nouveaux groupes
- Les groupes disponibles dans le catalogue MSL font foi
- Si un item ne correspond à aucun groupe existant, le laisser non-groupé

## Categorie "Pour techniciens"

- **JAMAIS inclure dans une soumission client** les items du groupe "Pour techniciens"
- Ces items sont des templates internes pour les notes de service
- Si un item "Pour techniciens" apparaît dans une soumission, le signaler comme erreur

## Prix de reference

- En cas de doublon entre groupes, les prix des groupes **"Services de base"** et **"Soins préventifs"** font foi
- Les prix sont en **centimes** dans l'API (45000 = 450.00$)
- Quantité 100 = 1 unité (format Gazelle : quantité en centièmes)

## Pattern bonus/suivi

Pour les items offerts en valeur ajoutée :
- Nom : décrire le service normalement
- Description : "Inclus avec votre restauration. Valeur estimée : XXX$"
- Prix : 0$ (amount: 0)
- Cela montre au client la valeur totale du service sans facturer

## Detection d'items manquants logiques

Quand une soumission contient certains travaux, d'autres items devraient logiquement être présents :

| Si la soumission contient... | Suggérer d'ajouter... |
|---|---|
| Installation PLS (piano droit ou queue) | Accord post-installation (mit_TgX2fFMZUYgLCT27, 255$) |
| Installation PLS | Termes d'entretien PLS (mit_z2hKAeRcxrVQCavS ou mit_ZDoRzgX05UBmSa7L, 0$) |
| Traitement colle cyanoacrylate | Accord de suivi (inclus, valeur estimée) |
| Remplacement marteaux | Harmonisation (mit_7uKnCPp7zkIF5gri ou mit_2zxFJh3StVzLwbhH) |
| Restauration étouffoirs | Réglage des étouffoirs (mit_nJdwrqAkKUK8bZbh) |
| Remplacement cordes | Accord de stabilisation (plusieurs séances) |
| Grand entretien | Nettoyage en profondeur (mit_3N7FCjQDl1yUDKuU) |
| Tout travail majeur | Frais de déplacement si applicable |

## Catalogue MSL complet (items actifs)

### Accessoires
| ID | Nom | Prix |
|---|---|---|
| mit_CX6CvWXbjs08vg70 | Traitement de l'eau (PLS) : 227 ml | 15$ |
| mit_6ZDKykOYEcVw3N8N | Traitement de l'eau (PLS) : 455 ml | 25$ |
| mit_eRqZsLAzRs3ypEGC | Ensemble d'entretien Cory | 35$ |
| mit_4VBlVSRsbsU6tBlv | Poli à piano Cory | 26$ |
| mit_MnWfmDHQLItiuK8v | Key-Brite par Cory 4 oz | 13$ |
| mit_yrcD7eM07CUkv59S | Key-Brite par Cory 8 oz | 23$ |
| mit_WjJaA8w1bhgFySgB | Coupelles Piattino laiton, petites (3) | 140$ |
| mit_C16UWD1nA0Du1In9 | Coupelles Piattino laiton, grandes | 180$ |
| mit_jXY9DVWeYtkL0dRe | Coupelles Piattino nickel, petites | 140$ |
| mit_UDPCleMKmUM7Hjf7 | Coupelles de bois noir lustré | 24$ |
| mit_42NwKWMNgvFkJqND | Coupelles de bois | 21$ |
| mit_UnCf3GnLXAEUHdVW | Mousse insonorisante | 225$ |
| mit_fyEqQE6rT6xpzLwk | Panneau insonorisant | 0$ |
| mit_gyGVUkVr0VerJyI2 | Lampe pour piano | 44$ |
| mit_OBI7ZAclUPYEVHPs | Banc de piano | 67$ |
| mit_WeMurqs2S1FQNz1r | Chariot pour piano à queue | 222$ |
| mit_Ysj6myvNuSMytygY | Chariot pour piano droit | 134$ |
| mit_cj2oK260VTb8s0rU | Sourdine pour piano à queue | 479$ |
| mit_jzL54TJvQwX38xsS | Frais d'envoi | 89$ |
| mit_D9ecPrXBKZBB6CPG | Prise de mesure | 179$ |
| mit_NITJAbY1DVbUpEOs | Installation | 455$ |
| mit_n4K8I0PYnrNfbST7 | Système Silent pour piano droit Kioshi | 2500$ |
| mit_fG9TTYyBzuOKGfzy | Système Silent pour piano à queue | 7000$ |
| mit_tycyqSHsyV5MQNKg | Système Silent Adsilent pour piano droit | 4800$ |
| mit_tqVoNJo5xpXCixGy | Buff-Brite 4 Oz. | 16$ |
| mit_98Sp6ndUKH1rlgBX | Système Silent Yamaha piano droit | 3500$ |

### Clavier: Touches, plateau, cadre
| ID | Nom | Prix |
|---|---|---|
| mit_2vxXTFwRXE4Yh8WI | Nettoyer et polir les touches blanches | 178$ |
| mit_MOX58zToXx1m78aN | Entretien du plateau du clavier | 15$ |
| mit_yKVZf3BoTem94l1O | Remplacer les garnitures de mortaises | 850$ |
| mit_qNPh1OIZQCXJpxyl | Niveler le clavier | 178$ |
| mit_vhjkRc3p9XXYM6SC | Ajuster l'enfoncement | 111$ |
| mit_SOsFOX9rCBaOGQWq | Polir les pilotes | 67$ |
| mit_nmNZCAf3lTHYDqG6 | Libérer le clavier | 100$ |
| mit_XNGp1p5czm9hi3MG | Remplacer les revêtements du clavier | 850$ |
| mit_OF7DZlCG7wZGrdtr | Recollage des touches blanches | 850$ |

### Cordes, étouffoirs, pédales
| ID | Nom | Prix |
|---|---|---|
| mit_EWMpUOmrZffwhzYi | Réglage de la Una Corda | 22$ |
| mit_uJF881ae2F2tc1Gw | Ajuster la pédale forte | 15$ |

### Harmonisation
| ID | Nom | Prix |
|---|---|---|
| mit_0DsxNgredRZ46oXT | Harmoniser la Una Corda | 44$ |
| mit_7uKnCPp7zkIF5gri | Sabler et harmoniser les marteaux usés | 368$ |
| mit_2zxFJh3StVzLwbhH | Harmonisation sommaire | 149$ |

### Mécanique
| ID | Nom | Prix |
|---|---|---|
| mit_JXoNASXgOzNWyCwA | Serrer toutes les vis | 30$ |
| mit_jGA59eb4jnC9ODrB | Lubrifier la mécanique | 30$ |
| mit_cVsZFyQlqJr1Hw7q | Réglage des étouffoirs | 178$ |
| mit_2yxeBkl09hksLS2m | Réglages de la mécanique | 150$ |
| mit_jNHZ0ip62mnzICdH | Révision du pivotage | 1250$ |
| mit_pDYrT2B8oxWAJ7ou | Remplacement des têtes de marteaux (piano droit) | 1200$ |
| mit_hTpsqYpJhXHlAdov | Remplacer les garnitures de contre-attrapes | 75$ |
| mit_AFmBrvUSZ4fpuuRS | Lanières (sangles de brides) | 75$ |
| mit_2LruBPj0LvcriHXy | Reconditionner les pièces d'action originales | 1602$ |
| mit_3dTMaENjnAziNGJ8 | Prélèvement ou retour des éléments pour atelier | 149$ |
| mit_4rsEr3uH4jziC3s2 | Remplacement des cordelettes de ressorts de marteaux (Yamaha) | 850$ |

### Nettoyage
| ID | Nom | Prix |
|---|---|---|
| mit_3N7FCjQDl1yUDKuU | Nettoyage en profondeur | 149$ |
| mit_13nOkMj3SnfW2mkX | Polir la quincaillerie en laiton | 89$/h |

### Restauration du sommier
| ID | Nom | Prix |
|---|---|---|
| mit_snt7Q7J3beHzo3aW | Traitement de colle cyanoacrylate | 450$ |

### Restauration: cordes
| ID | Nom | Prix |
|---|---|---|
| mit_BIdfLL8drkD5Igup | Calcul de l'échelonnage des cordes | 178$ |
| mit_1MCLdVhY4kLA4zXy | Cordes non-filées | 200$ |
| mit_ETMfGO6m7Yc65hJu | Installer les cordes non-filées | 534$ |
| mit_2HBYLndAxf1C993j | Cordes des basses | 1200$ |
| mit_uiSzTQHCmcYYte4n | Installer les cordes des basses | 800$ |
| mit_c8jIoZiNt2rZRfQk | Resurfacer la terminaison en V | 534$ |
| mit_7AxIo3W3Hfx7y3aJ | Avertissement : accord instable | 0$ |
| mit_tifTIvpHzWQSd8mV | Remplacer les chevilles | 450$ |

### Restauration: pédales et tringlerie
| ID | Nom | Prix |
|---|---|---|
| mit_rn8bAs5M0ucswLeG | Polir les pédales | 267$ |
| mit_iu5pcmtu3N9YEt9d | Remplacer les pédales | 375$ |
| mit_vI39tyNotyzGHv2B | Réparer et ajuster le mécanisme de la pédale Sostenuto | 178$ |
| mit_vr4xM7oCiuAqNzCp | Restaurer le pédalier | 534$ |
| mit_0mIyqcorWrUMgRlU | Remplacer le feutre de la sourdine (piano droit) | 150$ |
| mit_y93rDr6Hby95Ep4s | Installation d'une sourdine manuelle | 150$ |
| mit_7azafTMkswT7hnYo | Installation d'une sourdine mécanique | 350$ |
| mit_6eSVN0Me6CRMiqLz | Réparer la pédale cassée (ou remplacer) | 375$ |

### Restauration: étouffoirs
| ID | Nom | Prix |
|---|---|---|
| mit_dt0P0ZEBJAWmodVO | Installer de nouveaux étouffoirs | 445$ |
| mit_K86vpRJtgcCfnRXI | Remplacer les garnitures du guide des étouffoirs | 267$ |
| mit_nJdwrqAkKUK8bZbh | Réglage des étouffoirs | 337$ |
| mit_nffVqUSX0iuGaCbQ | Refaire la finition des têtes d'étouffoirs | 712$ |

### Réparation du fini lustré
| ID | Nom | Prix |
|---|---|---|
| mit_6w8HN4N3waC3KpoW | Réparation du fini lustré en acrylique | 250$/h |

### Services de base
| ID | Nom | Prix |
|---|---|---|
| mit_N6BwvFPuAnai6zXh | Entretien et accord | 255$ |
| mit_tHdTbZYDos7SgJzX | Service Premium | 368$ |
| mit_HJ1snRRwAIRsjdyn | L'extra-propre: Entretien et accord + nettoyage | 368$ |
| mit_o04b33O4D45Q39DD | Révision et maintenance du clavier pour pianos Silent et hybrides | 455$ |

### Soins préventifs: Contrôle de l'humidité
| ID | Nom | Prix |
|---|---|---|
| mit_xd1qOqOdcw6lBOKD | Installation PLS (piano droit) | 975$ |
| mit_6PLBOHu1iOHGv6Ka | Installation PLS (piano à queue) | 1135$ |
| mit_TgX2fFMZUYgLCT27 | Accord post-installation | 255$ |
| mit_2eBOzDvunD7PHs6M | Entretien annuel du système PLS | 45$ |
| mit_6ocqn0yaeqNK0Vxk | Traitement de l'eau (PLS) : 227 ml | 15$ |
| mit_YIVFKP1W1fc0IEkI | Traitement de l'eau (PLS) : 455 ml | 20$ |
| mit_5OVkQqqmysDFvCZG | Système PLS sec pour piano à queue | 444$ |
| mit_Mtn6qHFZQahlRYD9 | Système PLS sec pour piano droit | 340$ |
| mit_bomDsKfTgCHqBzOB | Installation PLS à deux cuves | 1400$ |
| mit_DcAcexEgBPgnhnvm | Installation PLS à deux cuves - arrière | 1112$ |
| mit_l9rEclzgq3v9B1nd | Sous-couverture (Piano à queue) | 239$ |
| mit_Epu75jqUwEE8W79p | Couverture arrière (Piano droit) | 199$ |
| mit_h1yM2cB1SOKrvYki | Couverture de cordes (piano 6' et moins) | 625$ |
| mit_kmWnI1JTie5WVSRI | Couverture de cordes (piano 6'1"-7') | 665$ |
| mit_bk6hfFZ1KsfGPusi | Couverture de cordes (piano 7'1"-8') | 715$ |
| mit_WqmQNcfPEAyi1YFF | Couverture de cordes (piano 8'1"-9'+) | 765$ |
| mit_hmHgUOkKWj50kN0J | Housse de piano longue | 500$ |
| mit_z2hKAeRcxrVQCavS | Termes d'entretien et d'utilisation du système PLS | 0$ |
| mit_ZDoRzgX05UBmSa7L | Conditions d'entretien du système PLS sec | 0$ |
| mit_W6d9sM3kyouKBY0c | Test, nettoyage, remplacement des buvards | 0$ |
| mit_zBOyH2mWodFnHUDb | Barre chauffante 38 w | 96$ |
| mit_As9CuJVc4cA7XrJl | Doublure | 2$ |
| mit_4PnibxAbsD3gU5fV | Changer bidon et tube PLS | 55$ |
| mit_cIlOkw9NRs3tyBA9 | Inspection du système d'humidité PLS avant et après déménagement | 370$ |
| mit_DiraOAuXuhfb73ce | Contrôleur du PLS | 399$ |
| mit_Xrv7bjz0lOEqOrlD | Buvards, gaine, doublure | 5$ |

### Service
| ID | Nom | Prix |
|---|---|---|
| mit_GL9kL9FS1mHifXY3 | Accord 440Hz + nettoyage sommaire | 255$ |
| mit_fyPj2I8R4VQtEkkm | Accord 440Hz + nettoyage + entretien PLS | 255$ |
| mit_r5bWarMJXMuiT7XK | Visite de courtoisie Piano Vertu | 135$ |
| mit_4RPi7xzW23jUmAu2 | Visite de courtoisie Archambault | 145$ |
| mit_5v1BtmANq8JEK9bw | Accord de courtoisie Nantel Musique | 255$ |
| mit_YU1by6UBpLqwkEEF | Inspection | 255$ |
| mit_SQ80MXuL3WlvzsdI | Entretien et accord | 255$ |
| mit_k8aOEuIAayDWkCF6 | Entretien piano/clavier électronique | 200$ |
| mit_9i5f9F4gVT03OyNc | Frais de déplacement | 0$ |
| mit_ereoeediImAHFbhD | Frais de stationnement | 0$ |
| mit_GWA1I9rDnG93MkVM | Rabais | -150$ |
| mit_84EBTau3McarxAld | Retour | 149$ |
| mit_DqEnpYw3yVlvUQDG | Grand nettoyage du piano | 0$ |
| mit_BlOTmlMXn4uoqTEQ | Réparation de meuble | 0$ |
| mit_2jWu6SIvEJ2iQW7K | Frais d'expédition | 0$ |

### Service étendu
| ID | Nom | Prix |
|---|---|---|
| mit_l6o2sjpCLZn9ZUHi | Grand entretien piano droit | 1045$ |
| mit_FQKKxagZOiQQQHYh | Grand entretien piano à queue 1 journée | 1045$ |
| mit_0ivQbo2xhSgsZTAv | Grand entretien piano à queue; deux jours | 1995$ |
| mit_4V5KjTkSdKH44zqe | Journée entière, piano à queue | 770$ |
| mit_9m53Xb5EVfsECLOe | Journée entière, piano droit | 770$ |
| mit_N7I5EeCyqwgfznEu | Entretien de rodage pour piano neuf (2 techniciens) | 1025$ |

### Services au contrat (Orford)
| ID | Nom | Prix |
|---|---|---|
| mit_NDp7t2hJoYUSmCL4 | Une journée | 600$ |
