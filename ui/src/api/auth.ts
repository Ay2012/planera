import { request } from "@/api/client";
import type { AuthTokenResponse, LoginRequestBody, MeResponse, SignupRequestBody } from "@/types/auth";

export async function loginRequest(body: LoginRequestBody) {
  return request<AuthTokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
    allowInDemoOnly: true,
  });
}

export async function signupRequest(body: SignupRequestBody) {
  return request<AuthTokenResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(body),
    allowInDemoOnly: true,
  });
}

export async function meRequest(accessToken: string) {
  return request<MeResponse>("/auth/me", {
    method: "GET",
    authToken: accessToken,
    allowInDemoOnly: true,
  });
}
