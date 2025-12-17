#!/usr/bin/env python3
"""
🎓 Interface Web d'Entraînement des Sommaires - Piano-Tek

Interface web intuitive pour raffiner les formats de sommaires.
Lancez ce script et ouvrez http://localhost:5001 dans votre navigateur.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

# Charger les variables d'environnement
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from flask import Flask, render_template_string, request, jsonify
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from core.supabase_storage import SupabaseStorage
from modules.assistant.services.queries import GazelleQueries

# Importer la classe SummaryTrainer depuis train_summaries.py
# Note: On doit importer depuis le module directement
import importlib.util
spec = importlib.util.spec_from_file_location("train_summaries", Path(__file__).parent / "train_summaries.py")
train_summaries_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(train_summaries_module)
SummaryTrainer = train_summaries_module.SummaryTrainer

app = Flask(__name__)
trainer = SummaryTrainer()

# Template HTML principal
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎓 Entraînement Sommaires - Piano-Tek</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .tab {
            background: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            color: #667eea;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .tab:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
        .tab.active {
            background: #667eea;
            color: white;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-group textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .btn:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .result-box {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            border-left: 4px solid #667eea;
        }
        
        .result-box h3 {
            color: #667eea;
            margin-bottom: 15px;
        }
        
        .result-box pre {
            background: white;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.6;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
            font-size: 1.2em;
        }
        
        .error {
            background: #fee;
            border-left-color: #f00;
            color: #c00;
        }
        
        .success {
            background: #efe;
            border-left-color: #0a0;
        }
        
        .format-selector {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .format-btn {
            flex: 1;
            padding: 12px;
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s;
        }
        
        .format-btn:hover {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .format-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .client-list {
            max-height: 300px;
            overflow-y: auto;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 10px;
        }
        
        .client-item {
            padding: 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .client-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        
        .client-item.selected {
            background: #667eea;
            color: white;
        }
        
        .hidden {
            display: none;
        }
        
        .feedback-section {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 2px solid #e0e0e0;
        }
        
        .rating {
            display: flex;
            gap: 10px;
            margin: 15px 0;
        }
        
        .rating-btn {
            flex: 1;
            padding: 10px;
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            text-align: center;
            transition: all 0.2s;
        }
        
        .rating-btn:hover {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .rating-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Entraînement des Sommaires</h1>
            <p>Raffinez les formats de sommaires avec vos vraies données</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('day')">📅 Sommaire Journée</button>
            <button class="tab" onclick="showTab('client')">👤 Sommaire Client</button>
            <button class="tab" onclick="showTab('history')">📊 Historique</button>
            <button class="tab" onclick="showTab('compare')">⚖️ Comparer</button>
        </div>
        
        <!-- Tab: Sommaire Journée -->
        <div id="tab-day" class="card">
            <h2>📅 Générer un Sommaire de Journée</h2>
            <form id="day-form">
                <div class="form-group">
                    <label>Date</label>
                    <input type="date" id="day-date" value="{{ today }}" required>
                </div>
                <div class="form-group">
                    <label>Technicien (optionnel)</label>
                    <select id="day-technician">
                        <option value="">Tous</option>
                        <option value="Nick">Nick</option>
                        <option value="Jean-Philippe">Jean-Philippe</option>
                        <option value="Allan">Allan</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Format</label>
                    <div class="format-selector">
                        <div class="format-btn active" data-format="compact" onclick="selectFormat('compact', this)">Compact</div>
                        <div class="format-btn" data-format="detailed" onclick="selectFormat('detailed', this)">Détaillé</div>
                        <div class="format-btn" data-format="v4" onclick="selectFormat('v4', this)">V4 Style</div>
                    </div>
                    <input type="hidden" id="day-format" value="compact">
                </div>
                <button type="submit" class="btn">🚀 Générer</button>
            </form>
            <div id="day-result"></div>
        </div>
        
        <!-- Tab: Sommaire Client -->
        <div id="tab-client" class="card hidden">
            <h2>👤 Générer un Sommaire Client</h2>
            <form id="client-form">
                <div class="form-group">
                    <label>Rechercher un client</label>
                    <input type="text" id="client-search" placeholder="Nom, ville, ou ID (cli_xxx)" required>
                    <button type="button" class="btn btn-secondary" onclick="searchClient()" style="margin-top: 10px;">🔍 Rechercher</button>
                </div>
                <div id="client-results" class="client-list hidden"></div>
                <div class="form-group" id="client-selected-group" style="display: none;">
                    <label>Client sélectionné</label>
                    <div id="client-selected" style="padding: 12px; background: #f8f9fa; border-radius: 8px;"></div>
                    <input type="hidden" id="client-id">
                </div>
                <div class="form-group">
                    <label>Format</label>
                    <div class="format-selector">
                        <div class="format-btn active" data-format="compact" onclick="selectFormat('compact', this)">Compact</div>
                        <div class="format-btn" data-format="detailed" onclick="selectFormat('detailed', this)">Détaillé</div>
                        <div class="format-btn" data-format="v4" onclick="selectFormat('v4', this)">V4 Style</div>
                    </div>
                    <input type="hidden" id="client-format" value="compact">
                </div>
                <button type="submit" class="btn" disabled id="client-submit">🚀 Générer</button>
            </form>
            <div id="client-result"></div>
        </div>
        
        <!-- Tab: Historique -->
        <div id="tab-history" class="card hidden">
            <h2>📊 Historique d'Entraînement</h2>
            <div id="history-content">
                <div class="loading">Chargement...</div>
            </div>
        </div>
        
        <!-- Tab: Comparer -->
        <div id="tab-compare" class="card hidden">
            <h2>⚖️ Comparer les Formats</h2>
            <p style="color: #666; margin-bottom: 20px;">Générez un sommaire dans les 3 formats pour comparer</p>
            <form id="compare-form">
                <div class="form-group">
                    <label>Type</label>
                    <select id="compare-type">
                        <option value="day">Sommaire Journée</option>
                        <option value="client">Sommaire Client</option>
                    </select>
                </div>
                <div id="compare-day-params">
                    <div class="form-group">
                        <label>Date</label>
                        <input type="date" id="compare-date" value="{{ today }}" required>
                    </div>
                    <div class="form-group">
                        <label>Technicien (optionnel)</label>
                        <select id="compare-technician">
                            <option value="">Tous</option>
                            <option value="Nick">Nick</option>
                            <option value="Jean-Philippe">Jean-Philippe</option>
                            <option value="Allan">Allan</option>
                        </select>
                    </div>
                </div>
                <div id="compare-client-params" style="display: none;">
                    <div class="form-group">
                        <label>ID Client</label>
                        <input type="text" id="compare-client-id" placeholder="cli_xxx">
                    </div>
                </div>
                <button type="submit" class="btn">🚀 Comparer les 3 Formats</button>
            </form>
            <div id="compare-result"></div>
        </div>
    </div>
    
    <script>
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('day-date').value = today;
        document.getElementById('compare-date').value = today;
        
        let selectedClientId = null;
        let selectedFormat = 'compact';
        
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('[id^="tab-"]').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            
            // Show selected tab
            document.getElementById('tab-' + tabName).classList.remove('hidden');
            event.target.classList.add('active');
        }
        
        function selectFormat(format, element) {
            selectedFormat = format;
            document.querySelectorAll('.format-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
            const formId = element.closest('.card').querySelector('form').id;
            document.getElementById(formId.replace('-form', '-format')).value = format;
        }
        
        // Stocker les formats générés
        let cachedDayFormats = null;
        let cachedDayAppointments = [];  // Données brutes des rendez-vous
        let cachedClientFormats = null;
        let currentDayFormat = 'compact';
        let currentClientFormat = 'compact';
        
        // Day Summary Form
        document.getElementById('day-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resultDiv = document.getElementById('day-result');
            resultDiv.innerHTML = '<div class="loading">⏳ Génération des 3 formats en cours...</div>';
            
            const data = {
                date: document.getElementById('day-date').value,
                technicien: document.getElementById('day-technician').value || null
            };
            
            try {
                // Générer les 3 formats en une seule fois
                const formats = ['compact', 'detailed', 'v4'];
                const promises = formats.map(format => 
                    fetch('/api/generate-day', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({...data, format})
                    }).then(r => r.json())
                );
                
                const results = await Promise.all(promises);
                
                if (results[0].success) {
                    // Stocker les 3 formats et les données brutes
                    cachedDayFormats = {
                        compact: results[0].summary,
                        detailed: results[1].summary,
                        v4: results[2].summary
                    };
                    cachedDayAppointments = results[0].appointments || [];  // Données brutes
                    
                    // Debug: vérifier les données reçues
                    console.log('📊 Rendez-vous reçus:', cachedDayAppointments.length);
                    cachedDayAppointments.forEach((apt, idx) => {
                        const hasDetails = apt.associated_contacts?.length > 0 || apt.service_history_notes?.length > 0 || apt.client_notes;
                        if (hasDetails) {
                            console.log(`✅ RV ${idx + 1} (${apt.client_name}) a des détails:`, {
                                contacts: apt.associated_contacts?.length || 0,
                                service_notes: apt.service_history_notes?.length || 0,
                                client_notes: !!apt.client_notes
                            });
                        }
                    });
                    
                    currentDayFormat = 'compact';
                    
                    // Afficher le format compact par défaut
                    displayDayResult(cachedDayFormats.compact, 'compact');
                } else {
                    resultDiv.innerHTML = `<div class="result-box error"><h3>❌ Erreur</h3><p>${results[0].error}</p></div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="result-box error"><h3>❌ Erreur</h3><p>${error.message}</p></div>`;
            }
        });
        
        function displayDayResult(summary, format) {
            const resultDiv = document.getElementById('day-result');
            currentDayFormat = format;
            
            // Utiliser les données brutes des rendez-vous pour créer les cartes
            const appointments = cachedDayAppointments || [];
            
            resultDiv.innerHTML = `
                <div class="result-box success">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3>✅ Sommaire Généré (${appointments.length} rendez-vous)</h3>
                        <div class="format-selector" style="max-width: 400px;">
                            <div class="format-btn ${format === 'compact' ? 'active' : ''}" onclick="switchDayFormat('compact')" style="padding: 8px 15px; font-size: 0.9em;">Compact</div>
                            <div class="format-btn ${format === 'detailed' ? 'active' : ''}" onclick="switchDayFormat('detailed')" style="padding: 8px 15px; font-size: 0.9em;">Détaillé</div>
                            <div class="format-btn ${format === 'v4' ? 'active' : ''}" onclick="switchDayFormat('v4')" style="padding: 8px 15px; font-size: 0.9em;">V4 Style</div>
                        </div>
                    </div>
                    ${appointments.length > 0 ? `
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; margin-bottom: 20px;">
                            ${appointments.map((apt, idx) => {
                                const time = apt.appointment_time || 'N/A';
                                const client = apt.client_name || 'N/A';
                                const title = apt.title || apt.description || 'Service';
                                const address = apt.client_address ? `${apt.client_address}, ${apt.client_city || ''}`.trim() : '';
                                const phone = apt.client_phone || '';
                                // Détecter si ce rendez-vous a des données enrichies à afficher
                                // On considère qu'il y a des détails si:
                                // - Il y a des contacts associés
                                // - Il y a des notes de service (timeline)
                                // - Il y a des notes client
                                // - Il y a des pianos avec des notes (IMPORTANT: les notes de piano sont souvent très détaillées)
                                const hasDetails = apt.associated_contacts?.length > 0 || 
                                                   apt.service_history_notes?.length > 0 || 
                                                   apt.client_notes || 
                                                   (apt.pianos?.length > 0 && apt.pianos.some(p => p.notes));
                                
                                return `
                                <div class="appointment-card" onclick="showAppointmentDetails(${idx})" style="
                                    background: white;
                                    border: 2px solid ${hasDetails ? '#667eea' : '#e0e0e0'};
                                    border-radius: 10px;
                                    padding: 15px;
                                    cursor: pointer;
                                    transition: all 0.3s;
                                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                    position: relative;
                                " onmouseover="this.style.borderColor='#667eea'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0,0,0,0.15)'" 
                                   onmouseout="this.style.borderColor='${hasDetails ? '#667eea' : '#e0e0e0'}'; this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)'">
                                    ${hasDetails ? '<div style="position: absolute; top: 10px; right: 10px; background: #667eea; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75em;">✨ Détails</div>' : ''}
                                    <div style="font-weight: bold; color: #667eea; margin-bottom: 8px; font-size: 1.1em;">🕐 ${time}</div>
                                    <div style="font-size: 1.2em; font-weight: 600; margin-bottom: 5px; color: #333;">${client}</div>
                                    <div style="color: #666; font-size: 0.95em; margin-bottom: 8px;">${title}</div>
                                    ${address ? `<div style="color: #999; font-size: 0.85em; margin-top: 5px;">📍 ${address}</div>` : ''}
                                    ${phone ? `<div style="color: #999; font-size: 0.85em;">📞 ${phone}</div>` : ''}
                                </div>
                            `;
                            }).join('')}
                        </div>
                    ` : ''}
                    <pre>${summary}</pre>
                    ${getFeedbackSection('day', summary)}
                </div>
            `;
        }
        
        function showAppointmentDetails(index) {
            const apt = cachedDayAppointments[index];
            if (!apt) {
                alert('Rendez-vous non trouvé');
                return;
            }
            
            // DEBUG: Afficher toutes les clés disponibles
            console.log('🔍 DEBUG: Toutes les clés du rendez-vous:', Object.keys(apt));
            console.log('🔍 DEBUG: Données complètes:', apt);
            
            let details = `🕐 ${apt.appointment_time || 'N/A'}\n`;
            details += `👤 ${apt.client_name || 'N/A'}\n`;
            details += `📋 ${apt.title || apt.description || 'Service'}\n\n`;
            
            if (apt.client_address) {
                details += `📍 ${apt.client_address}`;
                if (apt.client_city) details += `, ${apt.client_city}`;
                details += `\n`;
            }
            if (apt.client_phone) details += `📞 ${apt.client_phone}\n`;
            
            // AFFICHER TOUS LES CONTACTS
            if (apt.associated_contacts?.length > 0) {
                details += `\n👥 Contacts associés (${apt.associated_contacts.length}):\n`;
                apt.associated_contacts.forEach(c => {
                    details += `   • ${c.name || 'N/A'}`;
                    if (c.role) details += ` (${c.role})`;
                    if (c.phone) details += ` - 📞 ${c.phone}`;
                    if (c.email) details += ` - ✉️ ${c.email}`;
                    details += `\n`;
                });
            } else {
                details += `\n👥 Contacts associés: Aucun\n`;
            }
            
            // AFFICHER TOUTES LES NOTES DE SERVICE
            if (apt.service_history_notes?.length > 0) {
                details += `\n📝 Notes service (${apt.service_history_notes.length}):\n`;
                apt.service_history_notes.forEach((note, idx) => {
                    details += `   ${idx + 1}. ${note.substring(0, 500)}${note.length > 500 ? '...' : ''}\n\n`;
                });
            } else {
                details += `\n📝 Notes service: Aucune\n`;
            }
            
            // ============================================================
            // AFFICHAGE DES PIANOS AVEC LEURS NOTES
            // ============================================================
            // IMPORTANT: Les notes des pianos sont souvent très détaillées et contiennent
            // des informations cruciales (historique, réparations, problèmes récurrents).
            // On les affiche en premier car elles sont généralement plus pertinentes
            // que les notes client générales.
            if (apt.pianos?.length > 0) {
                details += `\n🎹 Pianos (${apt.pianos.length}):\n`;
                apt.pianos.forEach((piano, idx) => {
                    // Construire la ligne d'information du piano
                    let pianoInfo = `   ${idx + 1}. ${piano.make || ''} ${piano.model || ''}`.trim();
                    if (piano.serial_number) pianoInfo += ` (S/N: ${piano.serial_number})`;
                    if (piano.year) pianoInfo += ` - ${piano.year}`;
                    if (piano.type) pianoInfo += ` - ${piano.type}`;
                    if (piano.location) pianoInfo += ` - 📍 ${piano.location}`;
                    details += `${pianoInfo}\n`;
                    
                    // Afficher les notes du piano (tronquées à 500 caractères pour lisibilité)
                    // Les notes complètes sont disponibles dans l'objet si besoin
                    if (piano.notes) {
                        details += `      📝 ${piano.notes.substring(0, 500)}${piano.notes.length > 500 ? '...' : ''}\n`;
                    }
                });
            } else {
                details += `\n🎹 Pianos: Aucun\n`;
            }
            
            // AFFICHER TOUTES LES NOTES CLIENT
            if (apt.client_notes) {
                details += `\n📋 Notes client (${apt.client_notes.length} caractères):\n`;
                details += `   ${apt.client_notes.substring(0, 2000)}${apt.client_notes.length > 2000 ? '...' : ''}\n`;
            } else {
                details += `\n📋 Notes client: Aucune\n`;
            }
            
            // AFFICHER TOUTES LES AUTRES DONNÉES DISPONIBLES
            details += `\n\n🔍 AUTRES DONNÉES DISPONIBLES:\n`;
            const importantKeys = ['external_id', 'client_external_id', 'location', 'description', 'technicien'];
            importantKeys.forEach(key => {
                if (apt[key]) {
                    details += `   ${key}: ${apt[key]}\n`;
                }
            });
            
            // Afficher dans une modale ou un popup
            const modal = document.createElement('div');
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;';
            modal.innerHTML = `
                <div style="background: white; border-radius: 15px; padding: 30px; max-width: 600px; max-height: 80vh; overflow-y: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h2 style="color: #667eea; margin: 0;">📅 Détails du Rendez-vous</h2>
                        <button onclick="this.closest('div[style*=\"position: fixed\"]').remove()" style="background: #f0f0f0; border: none; border-radius: 50%; width: 30px; height: 30px; cursor: pointer; font-size: 1.2em;">×</button>
                    </div>
                    <pre style="white-space: pre-wrap; font-family: inherit; line-height: 1.6;">${details}</pre>
                </div>
            `;
            document.body.appendChild(modal);
            modal.onclick = (e) => {
                if (e.target === modal) modal.remove();
            };
        }
        
        function switchDayFormat(format) {
            if (cachedDayFormats && cachedDayFormats[format]) {
                displayDayResult(cachedDayFormats[format], format);
            }
        }
        
        // Client Search
        async function searchClient() {
            const search = document.getElementById('client-search').value;
            if (!search) return;
            
            const resultsDiv = document.getElementById('client-results');
            resultsDiv.innerHTML = '<div class="loading">🔍 Recherche...</div>';
            resultsDiv.classList.remove('hidden');
            
            try {
                const response = await fetch(`/api/search-clients?q=${encodeURIComponent(search)}`);
                const clients = await response.json();
                
                if (clients.length === 0) {
                    resultsDiv.innerHTML = '<div class="result-box error">Aucun résultat trouvé</div>';
                    return;
                }
                
                resultsDiv.innerHTML = clients.map((client, idx) => {
                    const type = client._source === 'contact' ? '📧 Contact' : '👤 Client';
                    const name = client.name || client.company_name || client.first_name || 'N/A';
                    return `
                        <div class="client-item" onclick="selectClient('${client.external_id}', '${name}', '${type}')">
                            <strong>${type}</strong> ${name} - ${client.city || 'N/A'}
                        </div>
                    `;
                }).join('');
            } catch (error) {
                resultsDiv.innerHTML = `<div class="result-box error">Erreur: ${error.message}</div>`;
            }
        }
        
        function selectClient(id, name, type) {
            selectedClientId = id;
            document.getElementById('client-id').value = id;
            document.getElementById('client-selected').innerHTML = `<strong>${type}</strong> ${name}`;
            document.getElementById('client-selected-group').style.display = 'block';
            document.getElementById('client-submit').disabled = false;
            document.querySelectorAll('.client-item').forEach(el => el.classList.remove('selected'));
            event.target.classList.add('selected');
        }
        
        // Client Summary Form
        document.getElementById('client-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!selectedClientId) return;
            
            const resultDiv = document.getElementById('client-result');
            resultDiv.innerHTML = '<div class="loading">⏳ Génération des 3 formats en cours...</div>';
            
            const data = {
                client_id: selectedClientId
            };
            
            try {
                // Générer les 3 formats en une seule fois
                const formats = ['compact', 'detailed', 'v4'];
                const promises = formats.map(format => 
                    fetch('/api/generate-client', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({...data, format})
                    }).then(r => r.json())
                );
                
                const results = await Promise.all(promises);
                
                if (results[0].success) {
                    // Stocker les 3 formats
                    cachedClientFormats = {
                        compact: results[0].summary,
                        detailed: results[1].summary,
                        v4: results[2].summary
                    };
                    currentClientFormat = 'compact';
                    
                    // Afficher le format compact par défaut
                    displayClientResult(cachedClientFormats.compact, 'compact');
                } else {
                    resultDiv.innerHTML = `<div class="result-box error"><h3>❌ Erreur</h3><p>${results[0].error}</p></div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="result-box error"><h3>❌ Erreur</h3><p>${error.message}</p></div>`;
            }
        });
        
        function displayClientResult(summary, format) {
            const resultDiv = document.getElementById('client-result');
            currentClientFormat = format;
            resultDiv.innerHTML = `
                <div class="result-box success">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3>✅ Sommaire Généré</h3>
                        <div class="format-selector" style="max-width: 400px;">
                            <div class="format-btn ${format === 'compact' ? 'active' : ''}" onclick="switchClientFormat('compact')" style="padding: 8px 15px; font-size: 0.9em;">Compact</div>
                            <div class="format-btn ${format === 'detailed' ? 'active' : ''}" onclick="switchClientFormat('detailed')" style="padding: 8px 15px; font-size: 0.9em;">Détaillé</div>
                            <div class="format-btn ${format === 'v4' ? 'active' : ''}" onclick="switchClientFormat('v4')" style="padding: 8px 15px; font-size: 0.9em;">V4 Style</div>
                        </div>
                    </div>
                    <pre>${summary}</pre>
                    ${getFeedbackSection('client', summary)}
                </div>
            `;
        }
        
        function switchClientFormat(format) {
            if (cachedClientFormats && cachedClientFormats[format]) {
                displayClientResult(cachedClientFormats[format], format);
            }
        }
        
        // Compare Form
        document.getElementById('compare-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resultDiv = document.getElementById('compare-result');
            resultDiv.innerHTML = '<div class="loading">⏳ Génération en cours...</div>';
            
            const type = document.getElementById('compare-type').value;
            const data = { type };
            
            if (type === 'day') {
                data.date = document.getElementById('compare-date').value;
                data.technicien = document.getElementById('compare-technician').value || null;
            } else {
                data.client_id = document.getElementById('compare-client-id').value;
            }
            
            try {
                const response = await fetch('/api/compare-formats', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                
                if (result.success) {
                    resultDiv.innerHTML = `
                        <div class="result-box success">
                            <h3>⚖️ Comparaison des 3 Formats</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
                                <div>
                                    <h4>📝 Compact</h4>
                                    <pre style="font-size: 0.85em;">${result.compact}</pre>
                                </div>
                                <div>
                                    <h4>📋 Détaillé</h4>
                                    <pre style="font-size: 0.85em;">${result.detailed}</pre>
                                </div>
                                <div>
                                    <h4>🔄 V4 Style</h4>
                                    <pre style="font-size: 0.85em;">${result.v4}</pre>
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `<div class="result-box error"><h3>❌ Erreur</h3><p>${result.error}</p></div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="result-box error"><h3>❌ Erreur</h3><p>${error.message}</p></div>`;
            }
        });
        
        // Type selector for compare
        document.getElementById('compare-type').addEventListener('change', (e) => {
            if (e.target.value === 'day') {
                document.getElementById('compare-day-params').style.display = 'block';
                document.getElementById('compare-client-params').style.display = 'none';
            } else {
                document.getElementById('compare-day-params').style.display = 'none';
                document.getElementById('compare-client-params').style.display = 'block';
            }
        });
        
        // Load history on tab show
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                if (this.textContent.includes('Historique')) {
                    loadHistory();
                }
            });
        });
        
        async function loadHistory() {
            const contentDiv = document.getElementById('history-content');
            try {
                const response = await fetch('/api/history');
                const history = await response.json();
                
                if (history.length === 0) {
                    contentDiv.innerHTML = '<div class="result-box">Aucun historique pour le moment.</div>';
                    return;
                }
                
                contentDiv.innerHTML = history.map(item => `
                    <div class="result-box" style="margin-bottom: 15px;">
                        <h4>${item.type} - ${new Date(item.timestamp).toLocaleString('fr-FR')}</h4>
                        <pre style="font-size: 0.9em; max-height: 200px; overflow-y: auto;">${item.summary}</pre>
                        ${item.feedback ? `<p><strong>Feedback:</strong> ${item.feedback}</p>` : ''}
                        ${item.rating ? `<p><strong>Note:</strong> ${'⭐'.repeat(item.rating)}</p>` : ''}
                    </div>
                `).join('');
            } catch (error) {
                contentDiv.innerHTML = `<div class="result-box error">Erreur: ${error.message}</div>`;
            }
        }
        
        function getFeedbackSection(type, summary) {
            return `
                <div class="feedback-section">
                    <h4>💬 Votre Feedback</h4>
                    <div class="form-group">
                        <label>Note (1-5)</label>
                        <div class="rating">
                            ${[1,2,3,4,5].map(n => `<div class="rating-btn" onclick="setRating(${n}, this, '${type}')">${n} ⭐</div>`).join('')}
                        </div>
                        <input type="hidden" id="rating-${type}" value="">
                    </div>
                    <div class="form-group">
                        <label>Commentaires</label>
                        <textarea id="feedback-${type}" placeholder="Ex: Très bien, mais ajouter plus de détails sur les pianos..."></textarea>
                    </div>
                    <button class="btn" onclick="saveFeedback('${type}', \`${summary.replace(/`/g, '\\`')}\`)">💾 Enregistrer Feedback</button>
                </div>
            `;
        }
        
        let currentRating = null;
        function setRating(rating, element, type) {
            currentRating = rating;
            const section = element.closest('.feedback-section');
            section.querySelectorAll('.rating-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
            const typeInput = section.querySelector('input[type="hidden"]');
            if (typeInput) {
                typeInput.value = rating;
            }
        }
        
        async function saveFeedback(type, summary) {
            const rating = document.getElementById('rating-' + type).value;
            const feedback = document.getElementById('feedback-' + type).value;
            
            if (!rating && !feedback) {
                alert('Veuillez fournir au moins une note ou un commentaire');
                return;
            }
            
            try {
                const response = await fetch('/api/save-feedback', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        type,
                        summary,
                        rating: rating ? parseInt(rating) : null,
                        feedback
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ Feedback enregistré !');
                } else {
                    alert('❌ Erreur: ' + result.error);
                }
            } catch (error) {
                alert('❌ Erreur: ' + error.message);
            }
        }
        
        // Allow Enter key in search
        document.getElementById('client-search').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchClient();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template_string(HTML_TEMPLATE, today=today)

@app.route('/api/generate-day', methods=['POST'])
def generate_day():
    try:
        data = request.json
        date = datetime.fromisoformat(data['date'])
        technicien = data.get('technicien')
        format_style = data.get('format', 'compact')
        
        result = trainer.generate_day_summary(date, technicien, format_style)
        appointments = result.get('appointments', [])
        
        # DEBUG: Vérifier les données avant envoi JSON
        print(f"\n🔍 API: {len(appointments)} rendez-vous à retourner")
        for idx, apt in enumerate(appointments):
            has_contacts = bool(apt.get('associated_contacts'))
            has_notes = bool(apt.get('service_history_notes'))
            has_client_notes = bool(apt.get('client_notes'))
            print(f"  RV {idx+1} ({apt.get('client_name', 'N/A')}): contacts={has_contacts}, notes={has_notes}, client_notes={has_client_notes}")
            if has_contacts:
                print(f"    -> {len(apt.get('associated_contacts', []))} contacts")
            if has_notes:
                print(f"    -> {len(apt.get('service_history_notes', []))} notes service")
            if has_client_notes:
                print(f"    -> {len(apt.get('client_notes', ''))} caractères notes client")
        
        return jsonify({
            'success': True,
            'summary': result.get('summary', 'Erreur de génération'),
            'appointments': appointments,  # Retourner les données brutes
            'appointments_count': result.get('appointments_count', 0)
        })
    except Exception as e:
        import traceback
        print(f"❌ ERREUR API: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-client', methods=['POST'])
def generate_client():
    try:
        data = request.json
        client_id = data['client_id']
        format_style = data.get('format', 'compact')
        
        result = trainer.generate_client_summary(client_id, format_style)
        
        if not result.get('found'):
            return jsonify({'success': False, 'error': result.get('summary', 'Client non trouvé')}), 404
        
        return jsonify({
            'success': True,
            'summary': result.get('summary', 'Erreur de génération')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search-clients')
def search_clients():
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify([])
        
        clients = trainer.queries.search_clients([query])
        return jsonify(clients)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/compare-formats', methods=['POST'])
def compare_formats():
    try:
        data = request.json
        type = data['type']
        
        results = {}
        formats = ['compact', 'detailed', 'v4']
        
        if type == 'day':
            date = datetime.fromisoformat(data['date'])
            technicien = data.get('technicien')
            for fmt in formats:
                result = trainer.generate_day_summary(date, technicien, fmt)
                results[fmt] = result.get('summary', '')
        else:
            client_id = data['client_id']
            for fmt in formats:
                result = trainer.generate_client_summary(client_id, fmt)
                results[fmt] = result.get('summary', '') if result.get('found') else 'Client non trouvé'
        
        return jsonify({
            'success': True,
            'compact': results.get('compact', ''),
            'detailed': results.get('detailed', ''),
            'v4': results.get('v4', '')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history')
def get_history():
    try:
        history = trainer.results[-20:]  # Derniers 20 résultats
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-feedback', methods=['POST'])
def save_feedback():
    try:
        data = request.json
        # Créer un enregistrement d'entraînement
        training_record = {
            'timestamp': datetime.now().isoformat(),
            'type': data['type'] + '_summary',
            'summary': data['summary'],
            'feedback': {
                'mode': 'web',
                'rating': data.get('rating'),
                'feedback': data.get('feedback'),
                'implicit_rating': data.get('rating')
            }
        }
        trainer.results.append(training_record)
        trainer._save_results()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🎓 Interface Web d'Entraînement des Sommaires")
    print("="*70)
    print("\n✅ Serveur démarré !")
    print("🌐 Ouvrez votre navigateur à: http://localhost:5001")
    print("\nAppuyez sur Ctrl+C pour arrêter le serveur.\n")
    app.run(host='0.0.0.0', port=5001, debug=True)

