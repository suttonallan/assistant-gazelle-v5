/**
 * Supabase Database Types
 *
 * Types auto-générés représentant le schema PostgreSQL
 * À regénérer avec: npx supabase gen types typescript --local
 *
 * Pour l'instant, types manuels basés sur migrations SQL
 */

export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export interface Database {
  public: {
    Tables: {
      vincent_dindy_piano_updates: {
        Row: {
          gazelle_id: string;
          status: string | null;
          a_faire: string | null;
          travail: string | null;
          observations: string | null;
          usage: string | null;
          updated_at: string;
          updated_by: string | null;
          completed_in_tournee_id: string | null;
        };
        Insert: {
          gazelle_id: string;
          status?: string | null;
          a_faire?: string | null;
          travail?: string | null;
          observations?: string | null;
          usage?: string | null;
          updated_at?: string;
          updated_by?: string | null;
          completed_in_tournee_id?: string | null;
        };
        Update: {
          gazelle_id?: string;
          status?: string | null;
          a_faire?: string | null;
          travail?: string | null;
          observations?: string | null;
          usage?: string | null;
          updated_at?: string;
          updated_by?: string | null;
          completed_in_tournee_id?: string | null;
        };
      };
      tournees: {
        Row: {
          id: string;
          nom: string;
          date_debut: string;
          date_fin: string;
          status: string;
          etablissement: string;
          technicien_responsable: string | null;
          piano_ids: Json | null;  // Deprecated - use tournee_pianos table
          notes: string | null;
          created_at: string;
          updated_at: string;
          created_by: string;
        };
        Insert: {
          id: string;
          nom: string;
          date_debut: string;
          date_fin: string;
          status: string;
          etablissement: string;
          technicien_responsable?: string | null;
          piano_ids?: Json | null;  // Deprecated
          notes?: string | null;
          created_at?: string;
          updated_at?: string;
          created_by: string;
        };
        Update: {
          id?: string;
          nom?: string;
          date_debut?: string;
          date_fin?: string;
          status?: string;
          etablissement?: string;
          technicien_responsable?: string | null;
          piano_ids?: Json | null;  // Deprecated
          notes?: string | null;
          created_at?: string;
          updated_at?: string;
          created_by?: string;
        };
      };
      tournee_pianos: {
        Row: {
          id: string;
          tournee_id: string;
          gazelle_id: string;
          ordre: number | null;
          ajoute_le: string;
          ajoute_par: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          tournee_id: string;
          gazelle_id: string;
          ordre?: number | null;
          ajoute_le?: string;
          ajoute_par?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          tournee_id?: string;
          gazelle_id?: string;
          ordre?: number | null;
          ajoute_le?: string;
          ajoute_par?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      activate_tournee: {
        Args: { p_tournee_id: string };
        Returns: boolean;
      };
      count_tournee_pianos: {
        Args: { p_tournee_id: string };
        Returns: number;
      };
      get_tournee_piano_ids: {
        Args: { p_tournee_id: string };
        Returns: string[];
      };
    };
    Enums: {
      [_ in never]: never;
    };
  };
}
