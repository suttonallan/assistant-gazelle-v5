import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Card,
  CardContent,
  Typography,
  Chip,
  Drawer,
  IconButton,
  Box,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  Badge,
  CircularProgress,
} from '@mui/material';
import {
  LocationOn,
  AccessTime,
  Piano,
  Warning,
  Close,
} from '@mui/icons-material';

// Utiliser le proxy Vite en développement, ou l'URL de production
import { API_URL as API_BASE } from '../utils/apiConfig';

/**
 * Chat Intelligent - Interface moderne pour la journée du technicien.
 *
 * Design:
 * - Mobile-first (cards compactes)
 * - Drawer pour détails (swipe up sur mobile)
 * - Icônes pour scannabilité rapide
 */
export default function ChatIntelligent({ currentUser }) {
  const [query, setQuery] = useState("aujourd'hui");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [appointmentDetail, setAppointmentDetail] = useState(null);

  // Déterminer rôle et ID Gazelle du technicien depuis currentUser
  const userRole = currentUser?.role || 'admin';
  const technicianGazelleId = currentUser?.id || null;  // ID Gazelle (dans users.id, pas gazelleId)
  const userName = currentUser?.name || 'Utilisateur';
  const userEmail = currentUser?.email || '';

  // Helper: détecter si l'utilisateur est un technicien
  // Inclut Nick, JP (Jean-Philippe), et Allan
  const isTechnician = () => {
    if (userRole === 'technician') return true;
    const nameLower = userName.toLowerCase();
    const emailLower = userEmail.toLowerCase();
    // Noms des techniciens (variantes)
    if (nameLower === 'nick' || nameLower === 'nicolas') return true;
    if (nameLower === 'jp' || nameLower === 'jean-philippe' || nameLower.includes('jean-philippe')) return true;
    if (nameLower === 'allan') return true;
    // Emails des techniciens
    if (emailLower.includes('nicolas@') || emailLower.includes('nick@')) return true;
    if (emailLower.includes('jp@') || emailLower.includes('jean-philippe@')) return true;
    if (emailLower.includes('allan@') || emailLower.includes('asutton@')) return true;
    return false;
  };

  // Titre et suggestions selon le rôle
  const getTitleByRole = () => {
    if (userRole === 'admin') return '🎯 Vue d\'ensemble';
    if (isTechnician()) return '🎵 Mes journées, nos clients';
    return '📋 Planification & Clients'; // Louise, Margot, autres assistants
  };

  const getQuickButtonsByRole = () => {
    if (userRole === 'admin' || isTechnician()) {
      // Techniciens et admin: leurs propres RV
      return [
        { label: "Aujourd'hui", query: "aujourd'hui" },
        { label: "Demain", query: "demain" },
        { label: "Après-demain", query: "après-demain" }
      ];
    } else {
      // Assistantes: RV des techniciens
      return [
        { label: "RV de Nick", query: "rv de nick demain" },
        { label: "RV de JP", query: "rv de jean-philippe demain" },
        { label: "Tous les RV demain", query: "tous les rv demain" }
      ];
    }
  };

  const getPlaceholderByRole = () => {
    if (userRole === 'admin') {
      return "Ex: Tous les RV demain, Stats du mois, Client Anne-Marie...";
    } else if (isTechnician()) {
      return "Ex: Ma journée demain, Cette semaine, Client Anne-Marie...";
    } else {
      return "Ex: RV de Nick demain, Client Anne-Marie, Qui va à Place des Arts...";
    }
  };

  // Auto-load journée d'aujourd'hui au mount
  useEffect(() => {
    handleQuickQuery("aujourd'hui");
  }, []);

  const handleQuery = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/chat/query`, {
        query: query,
        technician_id: technicianGazelleId,  // ID Gazelle du technicien
        user_role: userRole
      });
      setResponse(res.data);
    } catch (error) {
      console.error('Erreur query:', error);
      alert('Erreur lors de la requête');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickQuery = async (quickQuery) => {
    setQuery(quickQuery);
    setLoading(true);

    const payload = {
      query: quickQuery,
      technician_id: technicianGazelleId,  // ID Gazelle du technicien
      user_role: userRole
    };

    console.log('[ChatIntelligent] Sending query:', payload);

    try {
      const res = await axios.post(`${API_BASE}/api/chat/query`, payload);
      console.log('[ChatIntelligent] Query response:', res.data);
      setResponse(res.data);
    } catch (error) {
      console.error('[ChatIntelligent] Query error:', error);
      console.error('[ChatIntelligent] Error response:', error.response?.data);
    } finally {
      setLoading(false);
    }
  };

  const handleCardClick = async (appointment) => {
    setSelectedAppointment(appointment);
    setDrawerOpen(true);
    setDetailLoading(true);

    try {
      const res = await axios.get(
        `${API_BASE}/api/chat/appointment/${appointment.appointment_id}`
      );
      setAppointmentDetail(res.data);
    } catch (error) {
      console.error('Erreur détails:', error);
      alert('Erreur lors du chargement des détails');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedAppointment(null);
    setAppointmentDetail(null);
  };

  return (
    <Box sx={{ p: 2, maxWidth: 800, mx: 'auto' }}>
      {/* Header avec recherche */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
          {getTitleByRole()}
        </Typography>

        {/* Quick buttons - adaptés au rôle */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          {getQuickButtonsByRole().map((btn, idx) => (
            <Chip
              key={idx}
              label={btn.label}
              onClick={() => handleQuickQuery(btn.query)}
              color="primary"
              variant="outlined"
            />
          ))}
        </Box>

        {/* Search bar */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            placeholder={getPlaceholderByRole()}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
            size="small"
          />
          <Button
            variant="contained"
            onClick={handleQuery}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Go'}
          </Button>
        </Box>
      </Box>

      {/* Overview stats */}
      {response?.day_overview && (
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip
              icon={<AccessTime />}
              label={`${response.day_overview.total_appointments} RDV`}
              color="primary"
            />
            <Chip
              icon={<Piano />}
              label={`${response.day_overview.total_pianos} pianos`}
            />
            <Chip
              label={`~${response.day_overview.estimated_duration_hours.toFixed(1)}h`}
            />
            {response.day_overview.neighborhoods.map((n, i) => (
              <Chip
                key={i}
                icon={<LocationOn />}
                label={n}
                variant="outlined"
                size="small"
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Réponse textuelle (questions de suivi) */}
      {response?.text_response && (
        <Box sx={{ mb: 3, p: 2, bgcolor: 'info.light', borderRadius: 2, borderLeft: '4px solid', borderColor: 'info.main' }}>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', color: 'info.contrastText' }}>
            {response.text_response}
          </Typography>
        </Box>
      )}

      {/* Cards Niveau 1: Appointments */}
      {loading && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {response?.day_overview?.appointments.map((apt, index) => (
        <AppointmentCard
          key={index}
          appointment={apt}
          onClick={() => handleCardClick(apt)}
        />
      ))}

      {response?.day_overview?.appointments.length === 0 && !response?.text_response && (
        <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
          <Typography>Aucun rendez-vous pour cette journée</Typography>
        </Box>
      )}

      {/* Drawer Niveau 2: Détails */}
      <Drawer
        anchor="bottom"
        open={drawerOpen}
        onClose={closeDrawer}
        PaperProps={{
          sx: {
            maxHeight: '90vh',
            borderTopLeftRadius: 16,
            borderTopRightRadius: 16,
          }
        }}
      >
        <AppointmentDetailDrawer
          appointment={selectedAppointment}
          detail={appointmentDetail}
          loading={detailLoading}
          onClose={closeDrawer}
        />
      </Drawer>
    </Box>
  );
}

/**
 * Card compacte Niveau 1 - Optimisée TERRAIN: Quartier + PLS scannable en 1 sec.
 */
function AppointmentCard({ appointment, onClick }) {
  return (
    <Card
      sx={{
        mb: 2,
        cursor: 'pointer',
        '&:hover': {
          boxShadow: 4,
          transform: 'translateY(-2px)',
        },
        transition: 'all 0.2s',
        borderLeft: appointment.priority === 'high' ? '4px solid #ff9800' : '4px solid transparent',
      }}
      onClick={onClick}
    >
      <CardContent sx={{ pb: 1.5, '&:last-child': { pb: 1.5 } }}>
        {/* LIGNE 1: Heure + Badges + Quartier GROS */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          {/* Heure + Badges */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <AccessTime fontSize="small" color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 'bold', fontSize: '1.1rem' }}>
              {appointment.time_slot}
            </Typography>
            {appointment.is_new_client && (
              <Chip label="Nouveau" size="small" color="success" sx={{ height: 20, fontSize: '0.7rem' }} />
            )}
            {appointment.has_alerts && (
              <Warning fontSize="small" color="error" />
            )}
            {appointment.priority === 'high' && (
              <Chip label="URGENT" size="small" color="warning" sx={{ height: 20, fontSize: '0.7rem', fontWeight: 'bold' }} />
            )}
          </Box>

          {/* QUARTIER GROS - PRIORITÉ TERRAIN */}
          {appointment.neighborhood && (
            <Box sx={{
              bgcolor: 'primary.main',
              color: 'white',
              px: 1.5,
              py: 0.5,
              borderRadius: 1,
              fontWeight: 'bold',
              fontSize: '1rem'
            }}>
              {appointment.neighborhood}
            </Box>
          )}
        </Box>

        {/* LIGNE 2: Nom Client + Badge PLS */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
          <Typography
            variant="body1"
            sx={{
              fontWeight: 500,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}
          >
            {appointment.client_name}
          </Typography>

          {/* Badge PLS à côté du nom */}
          {appointment.has_dampp_chaser && (
            <Chip
              label="PLS"
              size="small"
              color="info"
              sx={{ height: '20px', fontSize: '0.7rem', fontWeight: 'bold' }}
            />
          )}
        </Box>

        {/* LIGNE 3: Piano + Lieu - Format ultra-compact */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
          {/* Piano */}
          {appointment.piano_brand && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Piano fontSize="small" color="action" />
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {appointment.piano_brand} {appointment.piano_model}
              </Typography>
            </Box>
          )}

          {/* Lieu (adresse courte) */}
          {appointment.address_short && (
            <>
              <Typography variant="body2" color="text.secondary">•</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>
                {appointment.address_short}
              </Typography>
            </>
          )}
        </Box>

        {/* LIGNE 4: Action items (collapsed si > 2) */}
        {appointment.action_items.length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
            {appointment.action_items.slice(0, 3).map((item, i) => (
              <Chip
                key={i}
                label={item}
                size="small"
                variant="outlined"
                color="primary"
                sx={{ height: '22px', fontSize: '0.7rem' }}
              />
            ))}
            {appointment.action_items.length > 3 && (
              <Chip
                label={`+${appointment.action_items.length - 3}`}
                size="small"
                variant="outlined"
                sx={{ height: '22px', fontSize: '0.7rem' }}
              />
            )}
          </Box>
        )}

        {/* LIGNE 5: Dernière visite (très petit, bas de carte) */}
        {appointment.last_visit_date && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, fontSize: '0.7rem' }}>
            Dernière visite: {appointment.last_visit_date}
            {appointment.days_since_last_visit && ` (${appointment.days_since_last_visit}j)`}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Drawer Niveau 2 - Détails complets + Timeline.
 */
function AppointmentDetailDrawer({ appointment, detail, loading, onClose }) {
  if (loading) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Chargement des détails...</Typography>
      </Box>
    );
  }

  if (!detail) {
    return <Box sx={{ p: 3 }}>Aucun détail disponible</Box>;
  }

  const { overview, comfort, timeline_summary, timeline_entries } = detail;

  // Vérifier si le RV est passé (pour masquer description si futur)
  const appointmentDate = new Date(overview.date);
  const now = new Date();
  const isPastAppointment = appointmentDate < now;

  // Générer un briefing intelligent en texte fluide
  const generateSmartBriefing = () => {
    const sentences = [];

    // 🔴 PRIORITÉ 1: Animaux
    if (comfort.dog_name || comfort.cat_name) {
      const pets = [];
      if (comfort.dog_name) pets.push(`chien ${comfort.dog_name}${comfort.dog_breed ? ` (${comfort.dog_breed})` : ''}`);
      if (comfort.cat_name) pets.push(`chat ${comfort.cat_name}`);
      sentences.push(`🐾 ${pets.join(', ')}`);
    }

    // 🔴 PRIORITÉ 2: Accès
    if (comfort.access_code) {
      sentences.push(`🔑 Code: ${comfort.access_code}`);
    }
    if (comfort.access_instructions) {
      sentences.push(comfort.access_instructions);
    }
    if (comfort.floor_number) {
      sentences.push(`Étage ${comfort.floor_number}`);
    }
    if (comfort.parking_info) {
      sentences.push(comfort.parking_info);
    }

    // Contact
    if (comfort.contact_phone) {
      sentences.push(`📞 ${comfort.contact_phone}`);
    }

    // Préférences piano
    const pianoPrefs = [];
    if (comfort.preferred_tuning_hz) pianoPrefs.push(`accordage ${comfort.preferred_tuning_hz}Hz`);
    if (comfort.climate_sensitive) pianoPrefs.push('sensible au climat');
    if (pianoPrefs.length > 0) {
      sentences.push(`🎹 ${pianoPrefs.join(', ')}`);
    }

    // Client
    if (comfort.preferred_language) {
      sentences.push(`Langue: ${comfort.preferred_language}`);
    }
    if (comfort.temperament) {
      sentences.push(`${comfort.temperament}`);
    }

    // ⚠️ Choses à surveiller
    if (comfort.special_notes) {
      sentences.push(`⚠️ ${comfort.special_notes}`);
    }

    // Résumés IA
    if (detail.client_smart_summary) {
      sentences.push(detail.client_smart_summary);
    }
    if (detail.piano_smart_summary && isPastAppointment) {
      sentences.push(detail.piano_smart_summary);
    }

    // Historique
    if (timeline_summary) {
      sentences.push(timeline_summary);
    }

    return sentences.filter(s => s).join('. ');
  };

  const smartBriefing = generateSmartBriefing();

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
          {overview.client_name}
        </Typography>
        <IconButton onClick={onClose}>
          <Close />
        </IconButton>
      </Box>

      {/* BRIEFING INTELLIGENT: Texte fluide regroupant toutes les infos pertinentes */}
      {smartBriefing && (
        <Box sx={{ mb: 3 }}>
          <Typography
            variant="body1"
            sx={{
              p: 2,
              bgcolor: 'grey.50',
              borderRadius: 1,
              lineHeight: 1.8,
              fontSize: '1rem'
            }}
          >
            {smartBriefing}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
