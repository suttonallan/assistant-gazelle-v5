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

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
  const userRole = currentUser?.role || 'technicien';
  const technicianGazelleId = currentUser?.gazelleId || null;  // ID Gazelle (source de vérité)

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
 * Card compacte Niveau 1 - Optimisée mobile.
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
      }}
      onClick={onClick}
    >
      <CardContent>
        {/* Header: Time + Client */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AccessTime fontSize="small" color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              {appointment.time_slot}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {appointment.is_new_client && (
              <Chip label="Nouveau" size="small" color="success" />
            )}
            {appointment.has_alerts && (
              <Badge badgeContent={<Warning fontSize="small" />} color="error">
                <span />
              </Badge>
            )}
            {appointment.priority === 'high' && (
              <Chip label="!" size="small" color="warning" />
            )}
          </Box>
        </Box>

        {/* Contact name (principal) */}
        <Typography
          variant="h6"
          sx={{
            mb: 0.5,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical'
          }}
        >
          {appointment.client_name}
        </Typography>

        {/* Billing client (institution) - Si différent */}
        {appointment.billing_client && (
          <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary', mb: 1 }}>
            Facturer à: {appointment.billing_client}
          </Typography>
        )}

        {/* Location (PRIORITÉ TERRAIN) */}
        {(appointment.neighborhood || appointment.address_short) && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
            <LocationOn fontSize="small" color="action" />
            {appointment.neighborhood && (
              <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
                {appointment.neighborhood}
              </Typography>
            )}
            {appointment.neighborhood && appointment.address_short && (
              <Typography variant="body2" color="text.secondary">•</Typography>
            )}
            {appointment.address_short && (
              <Typography variant="body2" color="text.secondary">
                {appointment.address_short}
              </Typography>
            )}
          </Box>
        )}

        {/* Piano */}
        {appointment.piano_brand && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
            <Piano fontSize="small" color="action" />
            <Typography variant="body2">
              {appointment.piano_brand} {appointment.piano_model}
              {appointment.piano_type && ` (${appointment.piano_type})`}
            </Typography>
            {appointment.has_dampp_chaser && (
              <Chip
                label="PLS"
                size="small"
                color="info"
                sx={{ height: '20px', fontSize: '0.7rem', fontWeight: 'bold' }}
              />
            )}
          </Box>
        )}

        {/* Dernière visite */}
        {appointment.last_visit_date && (
          <Typography variant="caption" color="text.secondary">
            Dernière visite: {appointment.last_visit_date}
            {appointment.days_since_last_visit && (
              <> ({appointment.days_since_last_visit} jours)</>
            )}
          </Typography>
        )}

        {/* Action items */}
        {appointment.action_items.length > 0 && (
          <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {appointment.action_items.map((item, i) => (
              <Chip
                key={i}
                label={item}
                size="small"
                variant="outlined"
                color="primary"
              />
            ))}
          </Box>
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

      {/* Infos Confort */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
          <InfoOutlined /> Informations pratiques
        </Typography>

        {comfort.dog_name && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Pets fontSize="small" />
            <Typography>Chien: {comfort.dog_name}</Typography>
          </Box>
        )}

        {comfort.access_code && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <VpnKey fontSize="small" />
            <Typography>Code: {comfort.access_code}</Typography>
          </Box>
        )}

        {comfort.parking_info && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <LocalParking fontSize="small" />
            <Typography>{comfort.parking_info}</Typography>
          </Box>
        )}

        {comfort.contact_phone && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Phone fontSize="small" />
            <Typography>{comfort.contact_phone}</Typography>
          </Box>
        )}

        {comfort.special_notes && (
          <Typography variant="body2" sx={{ mt: 1, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
            {comfort.special_notes}
          </Typography>
        )}
      </Box>

      <Divider sx={{ my: 2 }} />

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
