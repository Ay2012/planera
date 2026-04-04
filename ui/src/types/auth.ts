export interface AuthUser {
  id: number;
  email: string;
  display_name: string | null;
  created_at: string;
}

export interface AuthTokenResponse {
  user: AuthUser;
  access_token: string;
  token_type: string;
}

export interface MeResponse {
  user: AuthUser;
}

export interface LoginRequestBody {
  email: string;
  password: string;
}

export interface SignupRequestBody {
  email: string;
  password: string;
  display_name?: string | null;
}
