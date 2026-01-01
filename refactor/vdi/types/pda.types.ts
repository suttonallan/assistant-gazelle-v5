/**
 * Types pour Place des Arts
 */

export interface PDAPianoMapping {
  id: string;
  piano_abbreviation: string;
  gazelle_piano_id: string;
  location?: string | null;
  is_uncertain?: boolean;
  uncertainty_note?: string | null;
  created_at: Date;
  updated_at: Date;
  created_by?: string | null;
}

export interface PDARequest {
  id: string;
  piano: string; // Abréviation (ex: "SALLE1", "GRAND")
  room: string;
  for_who: string;
  appointment_date: string;
  status: string;
  // ... autres champs
}

export interface PianoMappingStats {
  abbreviation: string;
  gazelle_piano_id?: string;
  request_count: number;
  last_request_date?: string;
  mapped: boolean;
}

