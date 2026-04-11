import { env, isDemoOnlyMode } from "@/config/env";

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  raw?: boolean;
  /** When set, sends `Authorization: Bearer <token>`. */
  authToken?: string | null;
  /** Auth and health checks may still call the API while `VITE_API_FALLBACK_MODE=demo`. */
  allowInDemoOnly?: boolean;
}

function buildUrl(path: string) {
  if (/^https?:\/\//.test(path)) return path;
  return `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

async function buildErrorMessage(response: Response) {
  const text = await response.text();

  if (!text) {
    return "API request failed.";
  }

  try {
    const payload = JSON.parse(text) as { detail?: unknown; message?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      const messages = payload.detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item && typeof (item as { msg: unknown }).msg === "string") {
            return (item as { msg: string }).msg;
          }
          return null;
        })
        .filter(Boolean);
      if (messages.length > 0) return dedupeMessages(messages as string[]).join(" ");
    }
    if (payload.detail && typeof payload.detail === "object" && "message" in payload.detail) {
      const message = (payload.detail as { message?: unknown }).message;
      if (typeof message === "string") return message;
    }
    if (typeof payload.message === "string") return payload.message;
  } catch {
    // Fall through to the raw text body when the response is not JSON.
  }

  return text;
}

function dedupeMessages(parts: string[]) {
  return [...new Set(parts.map((p) => p.trim()).filter(Boolean))];
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (isDemoOnlyMode && !options.allowInDemoOnly) {
    throw new ApiError("Demo-only mode enabled.");
  }

  const headers = new Headers(options.headers);

  if (options.authToken) {
    headers.set("Authorization", `Bearer ${options.authToken}`);
  }

  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(path), {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(await buildErrorMessage(response), response.status);
  }

  if (options.raw) {
    return (await response.text()) as T;
  }

  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }

  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/json")) {
    return JSON.parse(text) as T;
  }

  return text as T;
}

/** Authenticated request helper — passes `Authorization: Bearer` for you. */
export function requestWithAuth<T>(path: string, accessToken: string | null, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { ...options, authToken: accessToken });
}
