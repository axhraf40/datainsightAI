/**
 * Client HTTP centralisé pour l'API DataInsight AI.
 * Toutes les requêtes passent par /api (proxifié vers http://localhost:8000).
 */

import type { AuthUser, Conversation, Dataset, UserFile } from "./types";

// ── Token de session ──────────────────────────────────────────────────────────
const TOKEN_KEY = "datainsight_token";
const BINDING_KEY = "datainsight_binding";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getBinding(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(BINDING_KEY);
}

export function setSession(token: string, binding: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(BINDING_KEY, binding);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(BINDING_KEY);
}

// ── Fetch de base ─────────────────────────────────────────────────────────────
async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const binding = getBinding();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (binding) headers["X-Session-Binding"] = binding;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, { ...options, headers });

  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      const json = await res.json();
      detail = json.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

// ── AUTH ──────────────────────────────────────────────────────────────────────

interface AuthResponse {
  token: string;
  binding: string;
  user: AuthUser;
}

export async function authLogin(email: string, password: string): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setSession(data.token, data.binding);
  return data;
}

export async function authRegister(
  email: string,
  username: string,
  password: string,
): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });
  setSession(data.token, data.binding);
  return data;
}

export async function authLogout(): Promise<void> {
  await apiFetch("/api/auth/logout", { method: "POST" }).catch(() => {});
  clearToken();
}

export async function updateProfile(
  email: string,
  username: string,
  password?: string,
): Promise<void> {
  await apiFetch("/api/auth/profile", {
    method: "PUT",
    body: JSON.stringify({ email, username, password: password || null }),
  });
}

// ── FILES ─────────────────────────────────────────────────────────────────────

export interface UploadResult {
  /** Défini si l'utilisateur est connecté */
  file_id?: number;
  conversation_id?: number;
  /** Défini si l'utilisateur est invité */
  guest_file_id?: string;
  filename: string;
  row_count: number;
  col_count: number;
  columns: string[];
  suggested_questions: string[];
  rag_profile: Record<string, unknown>;
  guest: boolean;
}

export async function uploadFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<UploadResult>("/api/files/upload", {
    method: "POST",
    body: form,
  });
}

export async function listFiles(): Promise<UserFile[]> {
  return apiFetch<UserFile[]>("/api/files");
}

export async function deleteFile(fileId: number): Promise<void> {
  await apiFetch(`/api/files/${fileId}`, { method: "DELETE" });
}

// ── CONVERSATIONS ─────────────────────────────────────────────────────────────

export async function listConversations(fileId?: number): Promise<Conversation[]> {
  const qs = fileId != null ? `?file_id=${fileId}` : "";
  return apiFetch<Conversation[]>(`/api/conversations${qs}`);
}

export async function createConversation(
  fileId: number | null,
  title: string,
): Promise<{ id: number; title: string }> {
  return apiFetch("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ file_id: fileId, title }),
  });
}

export async function renameConversation(
  convId: number,
  title: string,
): Promise<void> {
  await apiFetch(`/api/conversations/${convId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export interface ApiMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  chart_url?: string | null;
  display_df?: Record<string, unknown>[] | null;
  code?: string | null;
  pdf_url?: string | null;
  created_at: string;
}

export async function getMessages(convId: number): Promise<ApiMessage[]> {
  return apiFetch<ApiMessage[]>(`/api/conversations/${convId}/messages`);
}

// ── CHAT ──────────────────────────────────────────────────────────────────────

export interface AskPayload {
  prompt: string;
  conversation_id?: number | null;
  file_id?: number | null;
  guest_file_id?: string | null;
}

export interface AskResponse {
  conversation_id: number | null;
  answer: string;
  chart_url?: string | null;
  display_df?: Record<string, unknown>[] | null;
  code?: string | null;
  pdf_url?: string | null;
}

export async function askQuestion(payload: AskPayload): Promise<AskResponse> {
  return apiFetch<AskResponse>("/api/chat/ask", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── GUEST TRANSFER ────────────────────────────────────────────────────────────

export interface TransferResult {
  file_id: number;
  conversation_id: number;
  filename: string;
  row_count: number;
  col_count: number;
  rag_profile: Record<string, unknown>;
  suggested_questions: string[];
}

export async function transferGuest(
  guestFileId: string,
  guestMessages: Array<{ role: string; text: string }>,
): Promise<TransferResult> {
  return apiFetch<TransferResult>("/api/guest/transfer", {
    method: "POST",
    body: JSON.stringify({
      guest_file_id: guestFileId,
      guest_messages: guestMessages,
    }),
  });
}
