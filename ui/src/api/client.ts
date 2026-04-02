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

async function buildErrorMessage(response: Response) {
  const text = await response.text();

  if (!text) {
    return "API request failed.";
  }

  try {
    const payload = JSON.parse(text) as { detail?: unknown; message?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
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
    throw new ApiError(await buildErrorMessage(response), response.status);
  }

  if (options.raw) {
    return (await response.text()) as T;
  }

  return (await response.json()) as T;
}
