/**
 * Zod Validators - Runtime Type Safety
 *
 * Validation stricte pour:
 * - Données API entrantes (Gazelle, Supabase)
 * - Payloads sortants (updates, creates)
 * - Formulaires utilisateur
 *
 * @example
 * ```ts
 * const result = PianoUpdateSchema.safeParse(formData);
 * if (result.success) {
 *   await updatePiano(result.data);
 * } else {
 *   console.error(result.error.issues);
 * }
 * ```
 */

import { z } from 'zod';
import { PianoStatus, PianoType, PianoUsage } from '@types/piano.types';
import { TourneeStatus } from '@types/tournee.types';

// ==========================================
// BASE SCHEMAS
// ==========================================

/** Email validation */
export const EmailSchema = z.string().email('Email invalide');

/** Gazelle ID format: alphanumeric */
export const GazelleIdSchema = z.string().min(1, 'Gazelle ID requis');

/** Tournee ID format: tournee_{timestamp} */
export const TourneeIdSchema = z.string().regex(/^tournee_\d+$/, 'Format ID tournée invalide');

/** Date string ISO 8601 */
export const DateStringSchema = z.string().datetime({ offset: true });

/** Non-empty text */
export const NonEmptyTextSchema = z.string().min(1).trim();

// ==========================================
// PIANO SCHEMAS
// ==========================================

/** Piano Status enum */
export const PianoStatusSchema = z.nativeEnum(PianoStatus);

/** Piano Type enum */
export const PianoTypeSchema = z.nativeEnum(PianoType);

/** Piano Usage enum */
export const PianoUsageSchema = z.nativeEnum(PianoUsage);

/**
 * Gazelle Piano Raw data (from GraphQL)
 */
export const GazellePianoRawSchema = z.object({
  id: GazelleIdSchema,
  serialNumber: z.string().nullable().optional(),
  make: z.string(),
  model: z.string().nullable().optional(),
  location: z.string(),
  type: z.enum(['GRAND', 'DIGITAL_GRAND', 'UPRIGHT']),
  status: z.string().optional(),
  notes: z.string().optional(),
  calculatedLastService: z.string().nullable().optional(),
  calculatedNextService: z.string().nullable().optional(),
  serviceIntervalMonths: z.number().int().min(0).optional(),
  tags: z.array(z.string()).nullable().optional()
});

/**
 * Piano complet (fusionné Gazelle + Supabase)
 */
export const PianoSchema = z.object({
  // Gazelle data
  gazelleId: GazelleIdSchema,
  serialNumber: z.string().nullable(),
  make: z.string(),
  model: z.string().nullable(),
  location: z.string(),
  type: PianoTypeSchema,
  lastTuned: z.date().nullable(),
  nextService: z.date().nullable(),
  serviceIntervalMonths: z.number().int().min(0),
  tags: z.array(z.string()),

  // Supabase overlays
  status: PianoStatusSchema,
  usage: PianoUsageSchema.nullable(),
  aFaire: z.string().nullable(),
  travail: z.string().nullable(),
  observations: z.string().nullable(),
  isHidden: z.boolean(),
  completedInTourneeId: TourneeIdSchema.nullable(),
  updatedAt: z.date(),
  updatedBy: EmailSchema.nullable()
});

/**
 * Piano Update payload
 */
export const PianoUpdateSchema = z.object({
  pianoId: GazelleIdSchema,
  status: PianoStatusSchema.optional(),
  usage: PianoUsageSchema.optional(),
  aFaire: z.string().optional(),
  travail: z.string().optional(),
  observations: z.string().optional(),
  isHidden: z.boolean().optional(),
  completedInTourneeId: TourneeIdSchema.nullable().optional(),
  updatedBy: EmailSchema
});

/**
 * Batch update payload
 */
export const PianoBatchUpdateSchema = z.object({
  updates: z.array(PianoUpdateSchema).min(1, 'Au moins une mise à jour requise')
});

/**
 * Piano filters
 */
export const PianoFiltersSchema = z.object({
  status: z.array(PianoStatusSchema).optional(),
  usage: z.array(PianoUsageSchema).optional(),
  type: z.array(PianoTypeSchema).optional(),
  includeHidden: z.boolean().optional(),
  tourneeId: TourneeIdSchema.optional(),
  search: z.string().optional(),
  lastTunedMonthsAgo: z
    .object({
      min: z.number().int().min(0).optional(),
      max: z.number().int().min(0).optional()
    })
    .optional()
});

// ==========================================
// TOURNEE SCHEMAS
// ==========================================

/** Tournee Status enum */
export const TourneeStatusSchema = z.nativeEnum(TourneeStatus);

/** Etablissement enum */
export const EtablissementSchema = z.enum([
  'vincent-dindy',
  'orford',
  'place-des-arts'
]);

/**
 * Tournée complète
 */
export const TourneeSchema = z.object({
  id: TourneeIdSchema,
  nom: NonEmptyTextSchema,
  dateDebut: z.date(),
  dateFin: z.date(),
  status: TourneeStatusSchema,
  etablissement: EtablissementSchema,
  technicienResponsable: EmailSchema,
  pianoIds: z.array(GazelleIdSchema),
  notes: z.string().nullable(),
  createdAt: z.date(),
  updatedAt: z.date(),
  createdBy: EmailSchema
});

/**
 * Tournée Create payload
 */
export const TourneeCreateSchema = z
  .object({
    nom: NonEmptyTextSchema,
    dateDebut: z.date(),
    dateFin: z.date(),
    etablissement: EtablissementSchema,
    technicienResponsable: EmailSchema,
    notes: z.string().optional(),
    pianoIds: z.array(GazelleIdSchema).optional()
  })
  .refine((data) => data.dateFin >= data.dateDebut, {
    message: 'Date de fin doit être après date de début',
    path: ['dateFin']
  });

/**
 * Tournée Update payload
 */
export const TourneeUpdateSchema = z
  .object({
    id: TourneeIdSchema,
    nom: NonEmptyTextSchema.optional(),
    dateDebut: z.date().optional(),
    dateFin: z.date().optional(),
    status: TourneeStatusSchema.optional(),
    technicienResponsable: EmailSchema.optional(),
    notes: z.string().optional(),
    pianoIds: z.array(GazelleIdSchema).optional()
  })
  .refine(
    (data) => {
      if (data.dateDebut && data.dateFin) {
        return data.dateFin >= data.dateDebut;
      }
      return true;
    },
    {
      message: 'Date de fin doit être après date de début',
      path: ['dateFin']
    }
  );

/**
 * Tournee Piano Operation
 */
export const TourneePianoOperationSchema = z.object({
  tourneeId: TourneeIdSchema,
  pianoId: GazelleIdSchema,
  operation: z.enum(['add', 'remove'])
});

/**
 * Tournee filters
 */
export const TourneeFiltersSchema = z.object({
  status: z.array(TourneeStatusSchema).optional(),
  etablissement: EtablissementSchema.optional(),
  technicienResponsable: EmailSchema.optional(),
  dateRange: z
    .object({
      start: z.date().optional(),
      end: z.date().optional()
    })
    .optional()
});

/**
 * Tournee Activation Options
 */
export const TourneeActivationOptionsSchema = z.object({
  tourneeId: TourneeIdSchema,
  deactivateOthers: z.boolean().optional().default(true),
  resetCompletedPianos: z.boolean().optional().default(true)
});

// ==========================================
// HELPER FUNCTIONS
// ==========================================

/**
 * Parse et valide un piano depuis API
 *
 * @example
 * ```ts
 * const result = parsePiano(apiResponse);
 * if (!result.success) {
 *   console.error('Validation error:', result.error);
 * }
 * ```
 */
export function parsePiano(data: unknown) {
  return PianoSchema.safeParse(data);
}

/**
 * Parse et valide une tournée depuis API
 */
export function parseTournee(data: unknown) {
  return TourneeSchema.safeParse(data);
}

/**
 * Valide un update de piano avant envoi API
 */
export function validatePianoUpdate(data: unknown) {
  return PianoUpdateSchema.safeParse(data);
}

/**
 * Valide une création de tournée avant envoi API
 */
export function validateTourneeCreate(data: unknown) {
  return TourneeCreateSchema.safeParse(data);
}

/**
 * Valide un batch update
 */
export function validateBatchUpdate(data: unknown) {
  return PianoBatchUpdateSchema.safeParse(data);
}

/**
 * Helper: Convertir date string ISO → Date object
 */
export function parseISODate(dateStr: string | null): Date | null {
  if (!dateStr) return null;
  try {
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
  } catch {
    return null;
  }
}

/**
 * Helper: Convertir Date → ISO string pour API
 */
export function toISOString(date: Date | null): string | null {
  if (!date) return null;
  try {
    return date.toISOString();
  } catch {
    return null;
  }
}

/**
 * Helper: Valider email simple (pour formulaires)
 */
export function isValidEmail(email: string): boolean {
  return EmailSchema.safeParse(email).success;
}

/**
 * Helper: Extraire messages d'erreur Zod lisibles
 */
export function formatZodError(error: z.ZodError): string[] {
  return error.issues.map((issue) => {
    const path = issue.path.join('.');
    return `${path}: ${issue.message}`;
  });
}

// Export types inférés depuis schemas
export type PianoData = z.infer<typeof PianoSchema>;
export type PianoUpdateData = z.infer<typeof PianoUpdateSchema>;
export type TourneeData = z.infer<typeof TourneeSchema>;
export type TourneeCreateData = z.infer<typeof TourneeCreateSchema>;
export type TourneeUpdateData = z.infer<typeof TourneeUpdateSchema>;
