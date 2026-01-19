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
  Divider,
  Badge,
  CircularProgress,
} from '@mui/material';
import {
  LocationOn,
  AccessTime,
  Piano,
  Warning,
  Close,
  InfoOutlined,
  Pets,
  VpnKey,
  LocalParking,
  Phone,
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
    try {
      const res = await axios.post(`${API_BASE}/api/chat/query`, {
        query: quickQuery,
        technician_id: technicianGazelleId,  // ID Gazelle du technicien
        user_role: userRole
      });
      setResponse(res.data);
    } catch (error) {
      console.error('Erreur quick query:', error);
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
          🎵 Ma Journée
        </Typography>

        {/* Quick buttons */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          <Chip
            label="Aujourd'hui"
            onClick={() => handleQuickQuery("aujourd'hui")}
            color="primary"
            variant="outlined"
          />
          <Chip
            label="Demain"
            onClick={() => handleQuickQuery("demain")}
            color="primary"
            variant="outlined"
          />
          <Chip
            label="Après-demain"
            onClick={() => handleQuickQuery("après-demain")}
            color="primary"
            variant="outlined"
          />
        </Box>

        {/* Search bar */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            placeholder="Ex: Ma journée de demain, Le 30 décembre..."
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

      {/* SECTION 1: INFOS CONFORT (SUR PLACE) */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main' }}>
          <InfoOutlined /> Sur Place
        </Typography>

        {/* Animaux (Priorité visuelle) */}
        {(comfort.dog_name || comfort.cat_name) && (
          <Box sx={{ p: 1.5, mb: 2, bgcolor: 'warning.light', borderRadius: 1, borderLeft: '4px solid', borderColor: 'warning.main' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Pets fontSize="medium" color="warning" />
              <Box>
                {comfort.dog_name && (
                  <Typography sx={{ fontWeight: 600 }}>
                    🐕 Chien: {comfort.dog_name}
                    {comfort.dog_breed && ` (${comfort.dog_breed})`}
                  </Typography>
                )}
                {comfort.cat_name && (
                  <Typography sx={{ fontWeight: 600 }}>
                    🐱 Chat: {comfort.cat_name}
                  </Typography>
                )}
              </Box>
            </Box>
          </Box>
        )}

        {/* Code d'accès */}
        {comfort.access_code && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5, p: 1, bgcolor: 'info.light', borderRadius: 1 }}>
            <VpnKey fontSize="small" color="info" />
            <Typography sx={{ fontWeight: 600, fontSize: '1rem' }}>
              Code: {comfort.access_code}
            </Typography>
          </Box>
        )}

        {/* Instructions d'accès détaillées */}
        {comfort.access_instructions && (
          <Box sx={{ mb: 1.5 }}>
            <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600, mb: 0.5 }}>
              📝 Accès:
            </Typography>
            <Typography variant="body2" sx={{ p: 1, bgcolor: 'grey.100', borderRadius: 1, fontSize: '0.9rem' }}>
              {comfort.access_instructions}
            </Typography>
          </Box>
        )}

        {/* Étage */}
        {comfort.floor_number && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              🏢 Étage: <strong>{comfort.floor_number}</strong>
            </Typography>
          </Box>
        )}

        {/* Stationnement */}
        {comfort.parking_info && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <LocalParking fontSize="small" />
            <Typography variant="body2">{comfort.parking_info}</Typography>
          </Box>
        )}

        {/* Contact téléphone */}
        {comfort.contact_phone && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Phone fontSize="small" color="primary" />
            <Typography sx={{ fontWeight: 600 }}>
              <a href={`tel:${comfort.contact_phone}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                {comfort.contact_phone}
              </a>
            </Typography>
          </Box>
        )}

        {/* Préférences techniques */}
        {comfort.preferred_tuning_hz && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              🎵 Accordage: <strong>{comfort.preferred_tuning_hz} Hz</strong>
            </Typography>
          </Box>
        )}

        {comfort.climate_sensitive && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Warning fontSize="small" color="warning" />
            <Typography variant="body2" color="warning.main" sx={{ fontWeight: 600 }}>
              Piano sensible au climat
            </Typography>
          </Box>
        )}

        {/* Notes Client: Langue et Tempérament */}
        {(comfort.preferred_language || comfort.temperament) && (
          <Box sx={{ mt: 2, p: 1.5, bgcolor: 'primary.light', borderRadius: 1, borderLeft: '4px solid', borderColor: 'primary.main' }}>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 1, color: 'primary.dark' }}>
              👤 Notes Client:
            </Typography>
            {comfort.preferred_language && (
              <Typography variant="body2" sx={{ mb: 0.5 }}>
                🌐 Langue: <strong>{comfort.preferred_language}</strong>
              </Typography>
            )}
            {comfort.temperament && (
              <Typography variant="body2">
                💭 Tempérament: <strong>{comfort.temperament}</strong>
              </Typography>
            )}
          </Box>
        )}

        {/* Notes spéciales (toujours à la fin, encadré) */}
        {comfort.special_notes && (
          <Box sx={{ mt: 2, p: 1.5, bgcolor: 'secondary.light', borderRadius: 1, borderLeft: '4px solid', borderColor: 'secondary.main' }}>
            <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5, color: 'secondary.dark' }}>
              ⚠️ Choses à surveiller:
            </Typography>
            <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
              {comfort.special_notes}
            </Typography>
          </Box>
        )}
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* RÉSUMÉS INTELLIGENTS IA */}
      {(detail.client_smart_summary || detail.piano_smart_summary) && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main' }}>
            🤖 Résumé Intelligent
          </Typography>

          {/* Résumé Client */}
          {detail.client_smart_summary && (
            <Box sx={{ mb: 2, p: 2, bgcolor: 'info.light', borderRadius: 1, borderLeft: '4px solid', borderColor: 'info.main' }}>
              <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5, color: 'info.dark' }}>
                👤 Client:
              </Typography>
              <Typography variant="body2" sx={{ lineHeight: 1.8, color: 'text.primary' }}>
                {detail.client_smart_summary}
              </Typography>
            </Box>
          )}

          {/* Résumé Piano */}
          {detail.piano_smart_summary && (
            <Box sx={{ p: 2, bgcolor: 'success.light', borderRadius: 1, borderLeft: '4px solid', borderColor: 'success.main' }}>
              <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5, color: 'success.dark' }}>
                🎹 Piano:
              </Typography>
              <Typography variant="body2" sx={{ lineHeight: 1.8, color: 'text.primary' }}>
                {detail.piano_smart_summary}
              </Typography>
            </Box>
          )}
        </Box>
      )}

      {/* Timeline Summary - Résumé intelligent SEULEMENT */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          📖 Historique
        </Typography>
        <Typography variant="body2" sx={{ p: 2, bgcolor: 'blue.50', borderRadius: 1, lineHeight: 1.6 }}>
          {timeline_summary}
        </Typography>
      </Box>
    </Box>
  );
}
