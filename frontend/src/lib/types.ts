// Types alignés sur la structure réelle de la base de données DataInsight AI

export type ChatRole = "user" | "assistant";

export interface TableRow {
  [column: string]: string | number | null;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  /** Texte principal de la réponse (Markdown simple) */
  text: string;
  /** URL relative vers le graphique généré (ex : /exports/charts/foo.png) */
  chartUrl?: string | null;
  /** Données tabulaires JSON retournées par l'IA */
  displayDf?: TableRow[] | null;
  /** Code Python exécuté par l'IA */
  code?: string | null;
  /** URL relative vers le PDF généré (ex : /exports/pdfs/rapport_xxx.pdf) */
  pdfUrl?: string | null;
  /** Nom d'affichage du PDF */
  pdfName?: string | null;
}

export interface Dataset {
  /** ID BDD (undefined pour les sessions invité) */
  id?: number | string;
  /** guest_file_id pour les invités */
  guestFileId?: string;
  name: string;
  rows: number;
  columns: number;
  uploadedAt?: string;
  suggestedQuestions: string[];
  ragProfile?: Record<string, unknown>;
}

export interface UserFile {
  id: number;
  filename: string;
  row_count: number;
  col_count: number;
  columns: string[];
  suggested_questions: string[];
  uploaded_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  file_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface AuthUser {
  id: number;
  email: string;
  username: string;
}
