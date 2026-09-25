const DEFAULT_API_URL =
  "http://192.168.0.8:5000";

export const API_URL =
  process.env.EXPO_PUBLIC_API_URL?.trim() ||
  DEFAULT_API_URL;

type ApiMethod =
  | "GET"
  | "POST"
  | "PUT"
  | "PATCH"
  | "DELETE";

type RequestOptions = {
  method?: ApiMethod;
  body?: unknown;
  token?: string | null;
  signal?: AbortSignal;
  headers?: Record<
    string,
    string
  >;
};

export class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(
    message: string,
    status: number,
    data?: unknown,
  ) {
    super(message);

    this.name =
      "ApiError";

    this.status =
      status;

    this.data =
      data;
  }
}

function buildUrl(
  path: string,
) {
  const normalizedPath =
    path.startsWith("/")
      ? path
      : `/${path}`;

  return `${API_URL}${normalizedPath}`;
}

function getErrorMessage(
  data: unknown,
  fallback: string,
) {
  if (
    typeof data ===
    "object" &&
    data !== null
  ) {
    if (
      "message" in data &&
      typeof (
        data as {
          message?: unknown;
        }
      ).message ===
        "string"
    ) {
      return (
        data as {
          message: string;
        }
      ).message;
    }

    if (
      "error" in data &&
      typeof (
        data as {
          error?: unknown;
        }
      ).error ===
        "string"
    ) {
      return (
        data as {
          error: string;
        }
      ).error;
    }
  }

  return fallback;
}

async function parseResponse(
  response: Response,
) {
  if (
    response.status === 204
  ) {
    return null;
  }

  const contentType =
    response.headers.get(
      "content-type",
    );

  if (
    contentType?.includes(
      "application/json",
    )
  ) {
    return response.json();
  }

  const text =
    await response.text();

  return text || null;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    token,
    signal,
    headers = {},
  } = options;

  const requestHeaders: Record<
    string,
    string
  > = {
    Accept:
      "application/json",
    ...headers,
  };

  if (
    body !== undefined
  ) {
    requestHeaders[
      "Content-Type"
    ] =
      "application/json";
  }

  if (token) {
    requestHeaders.Authorization =
      `Bearer ${token}`;
  }

  let response: Response;

  try {
    response =
      await fetch(
        buildUrl(path),
        {
          method,
          headers:
            requestHeaders,
          body:
            body !==
            undefined
              ? JSON.stringify(
                  body,
                )
              : undefined,
          signal,
        },
      );
  } catch (error) {
    if (
      error instanceof
        Error &&
      error.name ===
        "AbortError"
    ) {
      throw error;
    }

    throw new ApiError(
      "Não foi possível conectar ao servidor.",
      0,
      error,
    );
  }

  const data =
    await parseResponse(
      response,
    );

  if (!response.ok) {
    throw new ApiError(
      getErrorMessage(
        data,
        `Erro ${response.status}`,
      ),
      response.status,
      data,
    );
  }

  return data as T;
}

export const api = {
  get<T>(
    path: string,
    options: Omit<
      RequestOptions,
      "method" | "body"
    > = {},
  ) {
    return apiRequest<T>(
      path,
      {
        ...options,
        method: "GET",
      },
    );
  },

  post<T>(
    path: string,
    body?: unknown,
    options: Omit<
      RequestOptions,
      "method" | "body"
    > = {},
  ) {
    return apiRequest<T>(
      path,
      {
        ...options,
        method: "POST",
        body,
      },
    );
  },

  put<T>(
    path: string,
    body?: unknown,
    options: Omit<
      RequestOptions,
      "method" | "body"
    > = {},
  ) {
    return apiRequest<T>(
      path,
      {
        ...options,
        method: "PUT",
        body,
      },
    );
  },

  patch<T>(
    path: string,
    body?: unknown,
    options: Omit<
      RequestOptions,
      "method" | "body"
    > = {},
  ) {
    return apiRequest<T>(
      path,
      {
        ...options,
        method: "PATCH",
        body,
      },
    );
  },

  delete<T>(
    path: string,
    options: Omit<
      RequestOptions,
      "method" | "body"
    > = {},
  ) {
    return apiRequest<T>(
      path,
      {
        ...options,
        method:
          "DELETE",
      },
    );
  },
};