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
}

function buildUrl(path: string) {
  if (/^https?:\/\//.test(path)) return path;
  return `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (isDemoOnlyMode) {
    throw new ApiError("Demo-only mode enabled.");
  }

  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(path), {
    ...options,
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || "API request failed.", response.status);
  }

  if (options.raw) {
    return (await response.text()) as T;
  }

  return (await response.json()) as T;
}
