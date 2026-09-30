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

let refreshPromise: Promise<string> | null =
  null;

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

function isAuthenticationError(
  error: unknown,
): error is ApiError {
  return (
    error instanceof ApiError &&
    (error.status === 401 ||
      error.status === 403)
  );
}

function requireUser(
  user: CurrentUser,
): NonNullable<CurrentUser> {
  if (
    !user ||
    typeof user.name !== "string" ||
    typeof user.email !== "string"
  ) {
    throw new ApiError(
      "Não foi possível confirmar sua conta.",
      502,
    );
  }

  return user;
}

async function saveTokens(
  tokens: AuthTokens,
) {
  const {
    accessToken,
    refreshToken,
  } = tokens;

  if (
    typeof accessToken !== "string" ||
    !accessToken ||
    typeof refreshToken !== "string" ||
    !refreshToken
  ) {
    throw new ApiError(
      "A resposta de autenticação está incompleta.",
      502,
    );
  }

  // Se a segunda gravação falhar, o refresh token já estará
  // disponível para recuperar a sessão na próxima tentativa.
  await SecureStore.setItemAsync(
    REFRESH_TOKEN_KEY,
    refreshToken,
  );

  await SecureStore.setItemAsync(
    ACCESS_TOKEN_KEY,
    accessToken,
  );
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

async function fetchCurrentUser(
  token: string,
) {
  const response =
    await api.get<CurrentUser>(
      "/api/auth/me",
      { token },
    );

  const user = requireUser(response);

  store.setUser(user);

  return user;
}

export async function login(
  payload: LoginPayload,
) {
  const response =
    await api.post<AuthResponse>(
      "/api/auth/login",
      {
        email: payload.email
          .trim()
          .toLowerCase(),
        password: payload.password,
      },
    );

  const user = requireUser(
    response.user,
  );

  await saveTokens(response);
  store.setUser(user);

  return response;
}

export async function registerClient(
  payload: RegisterClientPayload,
) {
  const response =
    await api.post<AuthResponse>(
      "/api/auth/register",
      {
        name: payload.name.trim(),
        email: payload.email
          .trim()
          .toLowerCase(),
        password: payload.password,
        role: "client",
      },
    );

  const user = requireUser(
    response.user,
  );

  await saveTokens(response);
  store.setUser(user);

  return response;
}

async function performRefresh() {
  const refreshToken =
    await getRefreshToken();

  if (!refreshToken) {
    throw new ApiError(
      "Sessão expirada. Entre novamente.",
      401,
    );
  }

  const response =
    await api.post<RefreshResponse>(
      "/api/auth/refresh",
      { refreshToken },
    );

  await saveTokens(response);

  return response.accessToken;
}

export async function refreshSession() {
  const operation =
    refreshPromise ??
    performRefresh();

  refreshPromise = operation;

  try {
    return await operation;
  } catch (error) {
    if (
      isAuthenticationError(error)
    ) {
      await clearSession();
    }

    throw error;
  } finally {
    if (
      refreshPromise === operation
    ) {
      refreshPromise = null;
    }
  }
}

export async function getCurrentUser() {
  let token =
    await getAccessToken();

  if (!token) {
    const refreshToken =
      await getRefreshToken();

    if (!refreshToken) {
      store.setUser(null);
      return null;
    }

    try {
      token =
        await refreshSession();
    } catch (error) {
      if (
        isAuthenticationError(error)
      ) {
        return null;
      }

      throw error;
    }
  }

  try {
    return await fetchCurrentUser(
      token,
    );
  } catch (error) {
    if (
      !isAuthenticationError(error)
    ) {
      throw error;
    }

    try {
      // Outra requisição pode já ter renovado a sessão.
      const storedToken =
        await getAccessToken();

      const nextToken =
        storedToken &&
        storedToken !== token
          ? storedToken
          : await refreshSession();

      return await fetchCurrentUser(
        nextToken,
      );
    } catch (retryError) {
      if (
        isAuthenticationError(
          retryError,
        )
      ) {
        await clearSession();
        return null;
      }

      throw retryError;
    }
  }
}

export async function logout() {
  // Se uma renovação estiver em andamento, esperamos para
  // revogar o token mais recente no servidor.
  if (refreshPromise) {
    try {
      await refreshPromise;
    } catch {
      // A limpeza local continua.
    }
  }

  const token =
    await getAccessToken();

  if (token) {
    try {
      await api.post(
        "/api/auth/logout",
        undefined,
        { token },
      );
    } catch {
      // Mesmo offline, a pessoa pode sair deste aparelho.
    }
  }

  await clearSession();
}

export async function clearSession() {
  if (refreshPromise) {
    try {
      await refreshPromise;
    } catch {
      // A limpeza local continua.
    }
  }

  try {
    await clearAuthTokens();
  } finally {
    store.setUser(null);
  }
}

export async function hasStoredSession() {
  const accessToken =
    await getAccessToken();

  if (accessToken) {
    return true;
  }

  const refreshToken =
    await getRefreshToken();

  return Boolean(refreshToken);
}