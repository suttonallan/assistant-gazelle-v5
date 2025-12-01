# 📊 GAZELLE DATA DICTIONARY

**Date de création :** 2025-11-30  
**Source :** Exports CSV Gazelle officiels  
**Objectif :** Référence complète pour le développement V5

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble](#vue-densemble)
2. [Diagramme des relations](#diagramme-des-relations)
3. [Tables détaillées](#tables-détaillées)
   - [Clients](#1-clients)
   - [Contacts](#2-contacts)
   - [Contact Locations](#3-contact-locations)
   - [Contact Phones](#4-contact-phones)
   - [Pianos](#5-pianos)
   - [Piano Measurements](#6-piano-measurements)
   - [Piano Photos](#7-piano-photos)
   - [Client Timelines](#8-client-timelines)
   - [Events](#9-events)
   - [Estimates](#10-estimates)
   - [Invoices](#11-invoices)
   - [Invoice Items](#12-invoice-items)
   - [Invoice Payments](#13-invoice-payments)
   - [Master Service List (MSL)](#14-master-service-list-msl)
   - [Email Suppressions](#15-email-suppressions)
4. [Conventions des IDs Gazelle](#conventions-des-ids-gazelle)
5. [Notes pour V5](#notes-pour-v5)

---

## Vue d'ensemble

| # | Table | Clé Primaire | Clés Étrangères | Nb colonnes |
|---|-------|--------------|-----------------|-------------|
| 1 | Clients | Client ID | - | 37 |
| 2 | Contacts | Contact ID | Client ID | 14 |
| 3 | Contact Locations | Location ID | Contact ID | 16 |
| 4 | Contact Phones | Phone ID | Contact ID | 7 |
| 5 | Pianos | Piano ID | Client ID | 36 |
| 6 | Piano Measurements | Measurement ID | Piano ID, Client ID | 32 |
| 7 | Piano Photos | ID | Piano ID, Client ID | 15 |
| 8 | Client Timelines | - | Client ID, Piano Token | 13 |
| 9 | Events | Event ID | Client ID | 25 |
| 10 | Estimates | Estimate ID | Client ID, Piano ID, MSL Item ID | 53 |
| 11 | Invoices | Invoice ID | Client ID | 38 |
| 12 | Invoice Items | Invoice Item ID | Invoice ID, Piano ID | 41 |
| 13 | Invoice Payments | Payment ID | Invoice ID, Client ID | 14 |
| 14 | MSL | MSL Item ID | MSL Group ID | 23 |
| 15 | Email Suppressions | - | - | 3 |

---

## Diagramme des relations

```
                              ┌─────────────────┐
                              │     CLIENTS     │
                              │   (Client ID)   │
                              └────────┬────────┘
                                       │
          ┌────────────────┬───────────┼───────────┬────────────────┐
          │                │           │           │                │
          ▼                ▼           ▼           ▼                ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐
   │  CONTACTS   │  │   PIANOS    │  │ EVENTS  │  │INVOICES │  │  TIMELINES  │
   │(Contact ID) │  │ (Piano ID)  │  │(Event ID)│ │(Inv. ID)│  │             │
   └──────┬──────┘  └──────┬──────┘  └─────────┘  └────┬────┘  └─────────────┘
          │                │                           │
     ┌────┴────┐      ┌────┴────┐                 ┌────┴────┐
     │         │      │         │                 │         │
     ▼         ▼      ▼         ▼                 ▼         ▼
┌─────────┐┌──────┐┌───────┐┌────────┐      ┌─────────┐┌──────────┐
│LOCATIONS││PHONES││MEASURE││ PHOTOS │      │INV ITEMS││ PAYMENTS │
└─────────┘└──────┘│ MENTS │└────────┘      └─────────┘└──────────┘
                   └───────┘

                              ┌─────────────────┐
                              │  MASTER SERVICE │
                              │   LIST (MSL)    │
                              └─────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   ESTIMATES     │
                              │  INVOICE ITEMS  │
                              └─────────────────┘
```

---

## Tables détaillées

---

### 1. CLIENTS

**Description :** Table principale des clients. Chaque client a un identifiant unique `Client ID` utilisé par toutes les autres tables.

**Clé primaire :** `Client ID`  
**Format ID :** `cli_xxxxxxxxxxxxxxxxx`

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| Client ID | string | Identifiant unique | cli_j3CIqBa4AjxyUSFN |
| Status | string | Statut du client | ACTIVE, INACTIVE |
| Company Name | string | Nom de l'entreprise | Ville de Saint-Lambert |
| Default Contact First Name | string | Prénom du contact principal | Sophie |
| Default Contact Last Name | string | Nom du contact principal | Abbott-Brown |
| Default Contact Default Address Line 1 | string | Adresse ligne 1 | 123 rue Principale |
| Default Contact Default Address Line 2 | string | Adresse ligne 2 | App. 4 |
| Default Contact Default City | string | Ville | Saint-Lambert |
| Default Contact Default State/Province | string | Province | QC |
| Default Contact Default Postal Code | string | Code postal | J4P 2R6 |
| Default Contact Default Geo Zone | string | Zone géographique | |
| Default Contact Default Email | string | Email principal | email@example.com |
| Default Contact Default Phone | string | Téléphone principal | (450) 672-4444 |
| Default Contact Wants Email | boolean | Accepte emails | true/false |
| Default Contact Wants Phone Call | boolean | Accepte appels | true/false |
| Default Contact Wants Text Message | boolean | Accepte SMS | true/false |
| Region | string | Région | Montréal |
| Reference ID | string | ID de référence externe | |
| Preference Notes | string | Notes de préférences | |
| Personal Notes | string | Notes personnelles | |
| No Contact Until | date | Ne pas contacter avant | 2025-01-01 |
| No Contact Reason | string | Raison | |
| Referred By | string | Référé par | |
| Referral Notes | string | Notes de référence | |
| Referred By Client ID | string | ID client référent | cli_xxx |
| Referred By Client Name | string | Nom client référent | |
| Reason Inactive | string | Raison d'inactivité | |
| Preferred Technician | string | Technicien préféré | Nicolas |
| Created | datetime | Date de création | 2018-09-11T14:33:45Z |
| Updated | datetime | Dernière modification | 2025-06-17T15:54:41Z |
| Custom 1 | string | Champ personnalisé 1 | |
| Custom 2 | string | Champ personnalisé 2 | |
| Custom 3 | string | Champ personnalisé 3 | |
| Client Type | string | Type de client | Résidentiel, Institutionnel |
| Reminders | string | Rappels | |
| Localization Name | string | Localisation | |
| Locale | string | Langue | fr_CA |

---

### 2. CONTACTS

**Description :** Contacts associés aux clients. Un client peut avoir plusieurs contacts.

**Clé primaire :** `Contact ID`  
**Clé étrangère :** `Client ID` → Clients  
**Format ID :** `con_xxxxxxxxxxxxxxxxx`

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| Contact ID | string | Identifiant unique | con_M7JWG5NfrgOS7AKd |
| Client ID | string | Référence au client | cli_xxx |
| Title | string | Titre | M., Mme |
| First Name | string | Prénom | Jean |
| Last Name | string | Nom | Tremblay |
| Suffix | string | Suffixe | Jr., PhD |
| Default Contact for Client | boolean | Contact principal | true/false |
| Default Billing Contact for Client | boolean | Contact facturation | true/false |
| Wants Email | boolean | Accepte emails | true/false |
| Wants Text | boolean | Accepte SMS | true/false |
| Wants Phone Calls | boolean | Accepte appels | true/false |
| Role | string | Rôle | Propriétaire, Gestionnaire |
| Created | datetime | Date de création | |
| Updated | datetime | Dernière modification | |

---

### 3. CONTACT LOCATIONS

**Description :** Adresses des contacts. Un contact peut avoir plusieurs adresses.

**Clé primaire :** `Location ID`  
**Clé étrangère :** `Contact ID` → Contacts

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| Location ID | string | Identifiant unique | |
| Contact ID | string | Référence au contact | con_xxx |
| Address Line 1 | string | Adresse ligne 1 | 123 rue Principale |
| Address Line 2 | string | Adresse ligne 2 | App. 4 |
| City | string | Ville | Montréal |
| State/Province | string | Province | QC |
| Postal Code | string | Code postal | H2X 1Y4 |
| Geo Zone | string | Zone géographique | |
| Usage Type | string | Type d'usage | Domicile, Travail |
| Created | datetime | Date de création | |
| Updated | datetime | Dernière modification | |
| Country Code | string | Code pays | CA |
| Location Type | string | Type de localisation | address, coordinates, What3Words |
| Latitude | float | Latitude (si coordinates) | 45.5017 |
| Longitude | float | Longitude (si coordinates) | -73.5673 |
| What3Words | string | What3Words (si applicable) | |

---

### 4. CONTACT PHONES

**Description :** Numéros de téléphone des contacts.

**Clé primaire :** `Phone ID`  
**Clé étrangère :** `Contact ID` → Contacts

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| Phone ID | string | Identifiant unique | |
| Contact ID | string | Référence au contact | con_xxx |
| Phone Number | string | Numéro de téléphone | (514) 555-1234 |
| Default Phone for Contact | boolean | Téléphone principal | true/false |
| Type | string | Type | Mobile, Domicile, Travail |
| Created | datetime | Date de création | |
| Updated | datetime | Dernière modification | |

---

### 5. PIANOS

**Description :** Table des pianos. Chaque piano est lié à un client.

**Clé primaire :** `Piano ID`  
**Clé étrangère :** `Client ID` → Clients  
**Format ID :** `ins_xxxxxxxxxxxxxxxxx` (instrument)

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| Piano ID | string | Identifiant unique | ins_ZA67tcYGZGasJeOC |
| Client ID | string | Référence au client | cli_xxx |
| Client Company | string | Nom entreprise (dénormalisé) | |
| Client First Name | string | Prénom client (dénormalisé) | |
| Client Last Name | string | Nom client (dénormalisé) | |
| Contact Email | string | Email contact | |
| Contact Phone | string | Téléphone contact | |
| Type | string | Type de piano | upright, grand |
| Make | string | Marque | Yamaha, Steinway |
| Model | string | Modèle | U3, B |
| Serial Number | string | Numéro de série | 5410611 |
| Location | string | Emplacement | Salon, Local 204 |
| Year | integer | Année de fabrication | 1985 |
| Piano Status | string | Statut | ACTIVE |
| Tuning Interval (mo) | integer | Intervalle d'accord (mois) | 6, 12 |
| **Last Tuned** | date | **Date dernier accord** | 2025-06-15 |
| Reference ID | string | ID de référence externe | |
| Use Type | string | Type d'utilisation | Personnel, Professionnel |
| Case Color | string | Couleur | Noir, Brun |
| Case Finish | string | Finition | Lustré, Satiné |
| **Notes** | text | **Notes / Historique de service** | "Marteau #45 à remplacer" |
| Player Installed | boolean | Système player installé | true/false |
| Player Make | string | Marque player | |
| Player Model | string | Modèle player | |
| Player Serial Number | string | Numéro série player | |
| **Dampp Chaser Installed** | boolean | **Système humidité installé** | true/false |
| **Dampp Chaser Model** | string | Modèle Dampp Chaser | |
| **Dampp Chaser Date** | date | Date installation | |
| Consignment | boolean | En consignation | true/false |
| Rental | boolean | En location | true/false |
| Rental Contract Ends | date | Fin de contrat location | |
| Total Loss | boolean | Perte totale | true/false |
| Needs Repair or Rebuilding | boolean | Nécessite réparation | true/false |
| Has Ivory | boolean | Touches en ivoire | true/false |
| Self Scheduler Url | string | URL auto-planification | |
| Size | string | Taille | 5'10", 48" |
| Tags | string | Tags | "Vincent-d'Indy, Priorité 1" |

**⚠️ Important pour V5 :**
- `Last Tuned` = Date du dernier accord (à mettre à jour automatiquement!)
- `Notes` = Historique de service du piano
- `Dampp Chaser *` = Infos système d'humidité

---

### 6. PIANO MEASUREMENTS

**Description :** Mesures d'humidité et de pitch des pianos.

**Clé primaire :** `Measurement ID`  
**Clés étrangères :** `Piano ID` → Pianos, `Client ID` → Clients

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| Client ID | string | Référence au client | cli_xxx |
| Piano ID | string | Référence au piano | ins_xxx |
| Piano Make | string | Marque (dénormalisé) | Yamaha |
| Piano Model | string | Modèle (dénormalisé) | U3 |
| Piano Serial Number | string | Numéro série (dénormalisé) | |
| Piano Location | string | Emplacement (dénormalisé) | |
| Piano Year | integer | Année (dénormalisé) | |
| Measurement ID | string | Identifiant unique | |
| **taken on** | datetime | **Date de la mesure** | 2025-11-15 |
| **humidity** | float | **Humidité (%)** | 42.5 |
| **temperature** | float | **Température** | 21.0 |
| A0 Pitch | float | Pitch A0 | |
| A1 Pitch | float | Pitch A1 | |
| A2 Pitch | float | Pitch A2 | |
| A3 Pitch | float | Pitch A3 | |
| A4 Pitch | float | Pitch A4 | 440.0 |
| A5 Pitch | float | Pitch A5 | |
| A6 Pitch | float | Pitch A6 | |
| A7 Pitch | float | Pitch A7 | |
| A0 Dip | float | Dip A0 | |
| A1 Dip | float | Dip A1 | |
| A2 Dip | float | Dip A2 | |
| A3 Dip | float | Dip A3 | |
| A4 Dip | float | Dip A4 | |
| A5 Dip | float | Dip A5 | |
| A6 Dip | float | Dip A6 | |
| A7 Dip | float | Dip A7 | |
| D6 Sustain Plucked | float | Sustain D6 (plucked) | |
| G6 Sustain Plucked | float | Sustain G6 (plucked) | |
| C7 Sustain Plucked | float | Sustain C7 (plucked) | |
| D6 Sustain Played | float | Sustain D6 (played) | |
| G6 Sustain Played | float | Sustain G6 (played) | |
| C7 Sustain Played | float | Sustain C7 (played) | |

**⚠️ Important pour V5 :**
- `humidity` et `temperature` = Données pour le système d'alertes humidité
- `taken on` = Date de mesure pour le suivi

---

### 7. PIANO PHOTOS

**Description :** Photos des pianos avec métadonnées et URLs de téléchargement.

**Clé primaire :** `ID`  
**Clés étrangères :** `Piano ID` → Pianos, `Client ID` → Clients  
**Format ID :** `pph_xxxxxxxxxxxxxxxxx`

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| ID | string | Identifiant unique | pph_Of2qgzzOxRnwnZPe |
| Piano ID | string | Référence au piano | ins_xxx |
| Client ID | string | Référence au client | cli_xxx |
| Client Company | string | Entreprise (dénormalisé) | |
| Client First Name | string | Prénom (dénormalisé) | Anne-Marie |
| Client Last Name | string | Nom (dénormalisé) | Voisard |
| Type | string | Type de piano | upright, grand |
| Make | string | Marque | Yamaha |
| Model | string | Modèle | P116S |
| Serial Number | string | Numéro de série | 5410611 |
| Photo Filename | string | Nom du fichier | abc123.jpg |
| Photo Size | integer | Taille (KB) | 17 |
| Photo Uploaded At | datetime | Date upload | 2022-06-07 13:35:13 |
| **Photo Notes** | text | **Notes sur la photo** | "Déménagé à l'île Bizard" |
| Photo URL | string | URL de téléchargement | https://... (expire 7 jours) |

**⚠️ Note :** Les URLs expirent après 7 jours. Télécharger les photos localement si nécessaire.

---

### 8. CLIENT TIMELINES

**Description :** Historique des interactions avec chaque client.

**Clés étrangères :** `Client ID` → Clients, `Piano Token` → Pianos

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| Client ID | string | Référence au client | cli_xxx |
| Type | string | Type d'entrée | NOTE, SERVICE, CALL |
| Timestamp | datetime | Date/heure | 2025-11-15 10:30:00 |
| **Comment** | text | **Commentaire / Notes** | "Accord effectué, RAS" |
| System Message | string | Message système | |
| Piano Token | string | Référence au piano | ins_xxx |
| Piano Type | string | Type de piano | upright |
| Piano Make | string | Marque | Yamaha |
| Piano Model | string | Modèle | U3 |
| Piano Serial Number | string | Numéro de série | |
| Piano Location | string | Emplacement | |
| Piano Year | integer | Année | |
| Created By | string | Créé par | usr_xxx |

**⚠️ Important :** Cette table contient l'historique général du CLIENT, pas du piano. Pour l'historique spécifique d'un piano, utiliser le champ `Notes` de la table Pianos ou filtrer par `Piano Token`.

---

### 9. EVENTS

**Description :** Événements du calendrier (rendez-vous).

**Clé primaire :** `Event ID`  
**Clé étrangère :** `Client ID` → Clients  
**Format ID :** `evt_xxxxxxxxxxxxxxxxx`

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| Event ID | string | Identifiant unique | evt_xxx |
| Title | string | Titre | Accord annuel |
| Notes | text | Notes | |
| All Day | boolean | Journée entière | true/false |
| Start | datetime | Date/heure début | 2025-12-01 09:00 |
| Timezone | string | Fuseau horaire | America/Montreal |
| Duration (minutes) | integer | Durée en minutes | 60 |
| Buffer (minutes) | integer | Temps tampon | 15 |
| Type | string | Type | APPOINTMENT, BLOCK |
| Status | string | Statut | ACTIVE, CANCELLED |
| Client | string | ID client | cli_xxx |
| User First Name | string | Prénom technicien | Nicolas |
| User Last Name | string | Nom technicien | Gaudreau |
| Client Company | string | Entreprise (dénormalisé) | |
| Default Contact First Name | string | Prénom contact | |
| Default Contact Last Name | string | Nom contact | |
| Default Contact Default Address Line 1 | string | Adresse | |
| Default Contact Default Address Line 2 | string | Adresse 2 | |
| Default Contact Default City | string | Ville | |
| Default Contact Default State/Province | string | Province | |
| Default Contact Default Postal Code | string | Code postal | |
| Default Contact Default Geo Zone | string | Zone géo | |
| Default Contact Default Email | string | Email | |
| Default Contact Default Phone | string | Téléphone | |
| Created At | datetime | Date création | |

---

### 10. ESTIMATES

**Description :** Soumissions avec options, groupes et items.

**Clé primaire :** `Estimate ID`  
**Clés étrangères :** `Client ID` → Clients, `Piano ID` → Pianos, `Master Service Item ID` → MSL

| Colonne | Type | Description |
|---------|------|-------------|
| Estimate ID | string | Identifiant unique |
| Created By | string | Créé par |
| Client ID | string | Référence au client |
| Client Company | string | Entreprise |
| Client First Name | string | Prénom |
| Client Last Name | string | Nom |
| Client Primary Phone | string | Téléphone |
| Client Primary Email | string | Email |
| Piano ID | string | Référence au piano |
| Piano Make | string | Marque |
| Piano Model | string | Modèle |
| Piano Serial Number | string | Numéro série |
| Piano Year | integer | Année |
| Piano Location | string | Emplacement |
| Estimate Number | string | Numéro de soumission |
| Estimate Notes | text | Notes |
| Expires On | date | Date expiration |
| Estimated On | date | Date de soumission |
| Created At | datetime | Date création |
| Archived? | boolean | Archivé |
| Option Number | integer | Numéro d'option |
| Allow Self Scheduling This Option | boolean | Auto-planification |
| Show Option To Client First | boolean | Montrer en premier |
| Option Notes | text | Notes option |
| Piano Potential Performance Level | string | Niveau potentiel |
| Current Performance Level | string | Niveau actuel |
| Option Target Performance Level | string | Niveau cible |
| Option Subtotal | decimal | Sous-total option |
| Option Tax Total | decimal | Taxes option |
| Option Total | decimal | Total option |
| Option Recommendation Type | string | Type recommandation |
| Option Recommendation Name | string | Nom recommandation |
| Group Name | string | Nom du groupe |
| Item Name | string | Nom de l'item |
| Item Description | text | Description |
| Item Educational Description | text | Description éducative |
| Item Amount | decimal | Montant |
| Item External URL | string | URL externe |
| Item Is Taxable? | boolean | Taxable |
| Item Is Tuning? | boolean | Est un accord |
| Item Type | string | Type |
| **Master Service Item ID** | string | **Référence MSL** |
| Item Quantity | decimal | Quantité |
| Item Duration In Minutes | integer | Durée |
| Item Subtotal | decimal | Sous-total |
| Item Tax Total | decimal | Taxes |
| Item Total | decimal | Total |
| Tags | string | Tags |
| Tax: tps (5.0%) | decimal | TPS |
| Tax: tvq (9.975%) | decimal | TVQ |

---

### 11. INVOICES

**Description :** Factures.

**Clé primaire :** `Invoice ID`  
**Clé étrangère :** `Client ID` → Clients  
**Format ID :** `inv_xxxxxxxxxxxxxxxxx`

| Colonne | Type | Description |
|---------|------|-------------|
| Invoice Date | date | Date de facture |
| Net Days | integer | Délai de paiement |
| Invoice ID | string | Identifiant unique |
| Invoice Number | string | Numéro de facture |
| Invoice Status | string | Statut (PAID, UNPAID, etc.) |
| Created By | string | Créé par |
| Subtotal | decimal | Sous-total |
| Tax: tps (5.0%) | decimal | TPS |
| Tax: tvq (9.975%) | decimal | TVQ |
| Tax Total | decimal | Total taxes |
| Total Due | decimal | Total dû |
| Tip | decimal | Pourboire |
| Paid | decimal | Montant payé |
| Balance Remaining | decimal | Solde restant |
| Most Recent Payment Date | date | Date dernier paiement |
| Notes | text | Notes |
| Client ID | string | Référence au client |
| Client Company | string | Entreprise |
| Client First Name | string | Prénom |
| Client Last Name | string | Nom |
| Client Primary Phone | string | Téléphone |
| Client Primary Email | string | Email |
| Client Address (Line 1) | string | Adresse |
| Client Address (Line 2) | string | Adresse 2 |
| Client City | string | Ville |
| Client State/Province | string | Province |
| Client Postal Code | string | Code postal |
| Alt. Billing Company | string | Entreprise facturation alt. |
| Alt. Billing First Name | string | Prénom facturation alt. |
| Alt. Billing Last Name | string | Nom facturation alt. |
| Alt. Billing Phone | string | Téléphone facturation alt. |
| Alt. Billing Email | string | Email facturation alt. |
| Alt. Billing Address (Line 1) | string | Adresse facturation alt. |
| Alt. Billing Address (Line 2) | string | Adresse 2 facturation alt. |
| Alt. Billing City | string | Ville facturation alt. |
| Alt. Billing State/Province | string | Province facturation alt. |
| Alt. Billing Postal Code | string | Code postal facturation alt. |
| Most Recent Payment Method | string | Mode de paiement |
| Archived? | boolean | Archivé |

---

### 12. INVOICE ITEMS

**Description :** Lignes de facture (items individuels).

**Clés étrangères :** `Invoice ID` → Invoices, `Piano ID` → Pianos

| Colonne | Type | Description |
|---------|------|-------------|
| Invoice Date | date | Date de facture |
| Net Days | integer | Délai paiement |
| Invoice ID | string | Référence à la facture |
| Invoice Number | string | Numéro facture |
| Invoice Status | string | Statut |
| Created By | string | Créé par |
| Most Recent Payment Date | date | Date paiement |
| Notes | text | Notes |
| Client ID | string | Référence client |
| Client Company | string | Entreprise |
| Client First Name | string | Prénom |
| Client Last Name | string | Nom |
| Client Primary Phone | string | Téléphone |
| Client Primary Email | string | Email |
| Client Address (Line 1) | string | Adresse |
| Client Address (Line 2) | string | Adresse 2 |
| Client City | string | Ville |
| Client State/Province | string | Province |
| Client Postal Code | string | Code postal |
| Alt. Billing Company | string | Facturation alt. entreprise |
| Alt. Billing First Name | string | Facturation alt. prénom |
| Alt. Billing Last Name | string | Facturation alt. nom |
| Alt. Billing Phone | string | Facturation alt. téléphone |
| Alt. Billing Email | string | Facturation alt. email |
| Alt. Billing Address (Line 1) | string | Facturation alt. adresse |
| Alt. Billing Address (Line 2) | string | Facturation alt. adresse 2 |
| Alt. Billing City | string | Facturation alt. ville |
| Alt. Billing State/Province | string | Facturation alt. province |
| Alt. Billing Postal Code | string | Facturation alt. code postal |
| Invoice Item ID | string | ID de la ligne |
| **Piano ID** | string | **Référence au piano** |
| **Description** | text | **Description du service** |
| Type | string | Type (SERVICE, PRODUCT) |
| Amount | decimal | Montant unitaire |
| Quantity | decimal | Quantité |
| Subtotal | decimal | Sous-total |
| Tax Total | decimal | Taxes |
| Total | decimal | Total |
| Tax: tps (5.0%) | decimal | TPS |
| Tax: tvq (9.975%) | decimal | TVQ |
| Archived? | boolean | Archivé |
| Client Reference ID | string | ID référence client |

**⚠️ Important pour V5 :**
- `Piano ID` permet de lier un service à un piano spécifique
- `Description` contient le détail du service effectué
- Utile pour le système de commissions et le suivi des services

---

### 13. INVOICE PAYMENTS

**Description :** Paiements des factures.

**Clés étrangères :** `Invoice ID` → Invoices, `Client ID` → Clients

| Colonne | Type | Description |
|---------|------|-------------|
| Invoice ID | string | Référence à la facture |
| Invoice Number | string | Numéro facture |
| Client ID | string | Référence client |
| Client Company | string | Entreprise |
| Client First Name | string | Prénom |
| Client Last Name | string | Nom |
| Payment ID | string | ID du paiement |
| Payment Recorded By First Name | string | Enregistré par (prénom) |
| Payment Recorded By Last Name | string | Enregistré par (nom) |
| Payment Type | string | Type (CASH, CHEQUE, CARD, etc.) |
| Payment Amount | decimal | Montant |
| Payment Currency | string | Devise (CAD) |
| Payment Notes | text | Notes |
| Payment Created At | datetime | Date enregistrement |

---

### 14. MASTER SERVICE LIST (MSL)

**Description :** Liste maîtresse des services et produits offerts.

**Clé primaire :** `MSL Item ID`  
**Clé étrangère :** `MSL Group ID` (groupe parent)

| Colonne | Type | Description |
|---------|------|-------------|
| MSL Group ID | string | ID du groupe |
| **MSL Item ID** | string | **ID de l'item** |
| Group Name (en_US) | string | Nom groupe (anglais) |
| Group Name (fr_CA) | string | Nom groupe (français) |
| Group Archived | boolean | Groupe archivé |
| Group Multi Choice | boolean | Choix multiples |
| Item Name (en_US) | string | Nom item (anglais) |
| Item Name (fr_CA) | string | Nom item (français) |
| Item Description (en_US) | text | Description (anglais) |
| Item Description (fr_CA) | text | Description (français) |
| Item Education (en_US) | text | Description éducative (anglais) |
| Item Education (fr_CA) | text | Description éducative (français) |
| **Duration (Mins)** | integer | **Durée en minutes** |
| **Amount** | decimal | **Prix** |
| Type | string | Type (SERVICE, PRODUCT) |
| External URL | string | URL externe |
| Archived | boolean | Item archivé |
| Tuning | boolean | Est un accord |
| Taxable | boolean | Taxable |
| Archived | boolean | Archivé (dupliqué?) |
| Self Schedulable | boolean | Auto-planifiable |
| Any Technician | boolean | Tout technicien |
| Only Technicians | string | Techniciens spécifiques |

**⚠️ Important pour V5 :**
- Cette table est essentielle pour le mapping inventaire/commissions
- `MSL Item ID` est référencé dans Estimates et peut être utilisé pour le suivi

---

### 15. EMAIL SUPPRESSIONS

**Description :** Liste des emails qui ne doivent plus recevoir de communications.

| Colonne | Type | Description |
|---------|------|-------------|
| Suppression Type | string | Type (BOUNCE, COMPLAINT, UNSUBSCRIBE) |
| Email Address | string | Adresse email |
| Notes | text | Notes |

---

## Conventions des IDs Gazelle

| Préfixe | Type | Exemple |
|---------|------|---------|
| `cli_` | Client | cli_j3CIqBa4AjxyUSFN |
| `con_` | Contact | con_M7JWG5NfrgOS7AKd |
| `ins_` | Piano (instrument) | ins_ZA67tcYGZGasJeOC |
| `pph_` | Photo de piano | pph_Of2qgzzOxRnwnZPe |
| `evt_` | Event (RDV) | evt_xxx |
| `inv_` | Invoice (facture) | inv_xxx |
| `usr_` | User (technicien) | usr_xxx |
| `msl_` | MSL Item | msl_xxx |

---

## Notes pour V5

### Tables prioritaires pour la sync API

1. **Clients** ✅ (déjà sync - 100 clients)
2. **Pianos** 🔴 (Last Tuned, Notes, Dampp Chaser)
3. **Events** 🔴 (rendez-vous, confirmations)
4. **Piano Measurements** 🔴 (humidité pour alertes)
5. **Client Timelines** 🟡 (historique)
6. **Invoices / Invoice Items** 🟡 (facturation, commissions)
7. **MSL** 🟡 (mapping inventaire)

### Champs critiques pour le système Vincent-d'Indy

| Besoin | Table | Champ |
|--------|-------|-------|
| Date dernier accord | Pianos | `Last Tuned` |
| Notes/historique piano | Pianos | `Notes` |
| Humidité | Piano Measurements | `humidity`, `temperature` |
| Système humidité installé | Pianos | `Dampp Chaser *` |
| Services effectués | Invoice Items | `Description`, `Piano ID` |
| Technicien assigné | Events | `User First Name`, `User Last Name` |

### Mutations API à explorer

Pour écrire dans Gazelle depuis V5 :
- Créer une Timeline Entry
- Mettre à jour `Last Tuned` d'un piano
- Mettre à jour `Notes` d'un piano
- Créer une mesure d'humidité (Piano Measurement)

---

**Document créé le :** 2025-11-30  
**Dernière mise à jour :** 2025-11-30  
**Version :** 1.0
