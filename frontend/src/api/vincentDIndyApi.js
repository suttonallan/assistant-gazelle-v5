/**
 * API client pour le module Vincent-d'Indy
 */

export const getPianos = async (apiUrl) => {
  const response = await fetch(`${apiUrl}/api/vincent-dindy/pianos`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const getPiano = async (apiUrl, pianoId) => {
  const response = await fetch(`${apiUrl}/api/vincent-dindy/pianos/${pianoId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const submitReport = async (apiUrl, report) => {
  const response = await fetch(`${apiUrl}/api/vincent-dindy/reports`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(report),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const getReports = async (apiUrl, options = {}) => {
  const { status, limit = 50 } = options;
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  params.append('limit', limit);

  const response = await fetch(`${apiUrl}/api/vincent-dindy/reports?${params}`);

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  return response.json();
};

export const getStats = async (apiUrl) => {
  const response = await fetch(`${apiUrl}/api/vincent-dindy/stats`);

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  return response.json();
};

export const updatePiano = async (apiUrl, pianoId, updates) => {
  const response = await fetch(`${apiUrl}/api/vincent-dindy/pianos/${pianoId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

// ============ TOURNÉES API ============

export const getTournees = async (apiUrl) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/tournees`);

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  const data = await response.json();
  return data.tournees || [];
};

export const createTournee = async (apiUrl, tourneeData) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/tournees`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(tourneeData),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const updateTournee = async (apiUrl, tourneeId, updates) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/tournees/${tourneeId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const deleteTournee = async (apiUrl, tourneeId) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/tournees/${tourneeId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const addPianoToTournee = async (apiUrl, tourneeId, gazelleId) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/tournees/${tourneeId}/pianos/${gazelleId}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const removePianoFromTournee = async (apiUrl, tourneeId, gazelleId) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/tournees/${tourneeId}/pianos/${gazelleId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const getActivity = async (apiUrl, limit = 50) => {
  const response = await fetch(`${apiUrl}/api/vincent-dindy/activity?limit=${limit}`);

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  const data = await response.json();
  return data.activity || [];
};

