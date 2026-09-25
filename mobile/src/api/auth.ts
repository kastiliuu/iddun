import * as SecureStore from "expo-secure-store";

import {
  api,
  ApiError,
} from "@/api/client";

import {
  CurrentUser,
  store,
} from "@/store/local";

const ACCESS_TOKEN_KEY =
  "iddun_access_token";

const REFRESH_TOKEN_KEY =
  "iddun_refresh_token";

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterClientPayload = {
  name: string;
  email: string;
  password: string;
};

export type AuthTokens = {
  accessToken: string;
  refreshToken?: string | null;
};

export type AuthResponse = {
  user: CurrentUser;
  accessToken: string;
  refreshToken?: string | null;
};

export type RefreshResponse = {
  accessToken: string;
  refreshToken?: string | null;
};

async function saveTokens(
  tokens: AuthTokens,
) {
  await SecureStore.setItemAsync(
    ACCESS_TOKEN_KEY,
    tokens.accessToken,
  );

  if (tokens.refreshToken) {
    await SecureStore.setItemAsync(
      REFRESH_TOKEN_KEY,
      tokens.refreshToken,
    );
  } else {
    await SecureStore.deleteItemAsync(
      REFRESH_TOKEN_KEY,
    );
  }
}

export async function getAccessToken() {
  return SecureStore.getItemAsync(
    ACCESS_TOKEN_KEY,
  );
}

export async function getRefreshToken() {
  return SecureStore.getItemAsync(
    REFRESH_TOKEN_KEY,
  );
}

export async function clearAuthTokens() {
  await Promise.all([
    SecureStore.deleteItemAsync(
      ACCESS_TOKEN_KEY,
    ),

    SecureStore.deleteItemAsync(
      REFRESH_TOKEN_KEY,
    ),
  ]);
}

export async function login(
  payload: LoginPayload,
) {
  /*
   * Contrato previsto:
   *
   * POST /api/auth/login
   *
   * {
   *   email,
   *   password
   * }
   *
   * resposta:
   *
   * {
   *   user: {...},
   *   accessToken: "...",
   *   refreshToken: "..."
   * }
   */

  const response =
    await api.post<AuthResponse>(
      "/api/auth/login",
      {
        email:
          payload.email
            .trim()
            .toLowerCase(),

        password:
          payload.password,
      },
    );

  await saveTokens({
    accessToken:
      response.accessToken,

    refreshToken:
      response.refreshToken,
  });

  store.setUser(
    response.user,
  );

  return response;
}

export async function registerClient(
  payload: RegisterClientPayload,
) {
  /*
   * Cadastro de CLIENTE.
   *
   * Profissional e estabelecimento
   * terão fluxo complementar próprio.
   */

  const response =
    await api.post<AuthResponse>(
      "/api/auth/register",
      {
        name:
          payload.name.trim(),

        email:
          payload.email
            .trim()
            .toLowerCase(),

        password:
          payload.password,

        role: "client",
      },
    );

  await saveTokens({
    accessToken:
      response.accessToken,

    refreshToken:
      response.refreshToken,
  });

  store.setUser(
    response.user,
  );

  return response;
}

export async function refreshSession() {
  const refreshToken =
    await getRefreshToken();

  if (!refreshToken) {
    throw new ApiError(
      "Sessão expirada.",
      401,
    );
  }

  try {
    const response =
      await api.post<RefreshResponse>(
        "/api/auth/refresh",
        {
          refreshToken,
        },
      );

    await saveTokens({
      accessToken:
        response.accessToken,

      refreshToken:
        response.refreshToken ??
        refreshToken,
    });

    return response.accessToken;
  } catch (error) {
    await clearSession();

    throw error;
  }
}

export async function getCurrentUser() {
  const token =
    await getAccessToken();

  if (!token) {
    return null;
  }

  try {
    const user =
      await api.get<CurrentUser>(
        "/api/auth/me",
        {
          token,
        },
      );

    store.setUser(user);

    return user;
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 401
    ) {
      try {
        const newToken =
          await refreshSession();

        const user =
          await api.get<CurrentUser>(
            "/api/auth/me",
            {
              token:
                newToken,
            },
          );

        store.setUser(
          user,
        );

        return user;
      } catch {
        await clearSession();

        return null;
      }
    }

    throw error;
  }
}

export async function logout() {
  const token =
    await getAccessToken();

  /*
   * Tentamos invalidar a sessão
   * também no servidor.
   *
   * Se estiver offline,
   * ainda assim limpamos
   * a sessão local.
   */
  if (token) {
    try {
      await api.post(
        "/api/auth/logout",
        undefined,
        {
          token,
        },
      );
    } catch {
      // Logout local continua.
    }
  }

  await clearSession();
}

export async function clearSession() {
  await clearAuthTokens();

  store.setUser(null);
}

export async function hasStoredSession() {
  const token =
    await getAccessToken();

  return Boolean(token);
}