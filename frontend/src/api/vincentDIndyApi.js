/**
 * API client pour le module Vincent-d'Indy
 */

export const getPianos = async (apiUrl) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/pianos`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const getPiano = async (apiUrl, pianoId) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/pianos/${pianoId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erreur inconnue' }));
    throw new Error(error.detail || `Erreur ${response.status}`);
  }

  return response.json();
};

export const submitReport = async (apiUrl, report) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/reports`, {
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

  const response = await fetch(`${apiUrl}/vincent-dindy/reports?${params}`);

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  return response.json();
};

export const getStats = async (apiUrl) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/stats`);

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  return response.json();
};

export const updatePiano = async (apiUrl, pianoId, updates) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/pianos/${pianoId}`, {
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

export const getActivity = async (apiUrl, limit = 50) => {
  const response = await fetch(`${apiUrl}/vincent-dindy/activity?limit=${limit}`);

  if (!response.ok) {
    throw new Error(`Erreur ${response.status}`);
  }

  const data = await response.json();
  return data.activity || [];
};

