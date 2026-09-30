// Use the web backend by default. Set EXPO_PUBLIC_API_URL to a
// reachable LAN address when developing on a physical device.
const DEFAULT_API_URL =
  "https://iddun-web.onrender.com";

const REQUEST_TIMEOUT_MS = 20_000;

export const API_URL =
  (
    process.env.EXPO_PUBLIC_API_URL?.trim() ||
    DEFAULT_API_URL
  ).replace(/\/+$/, "");

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

    if (
      "error" in data &&
      typeof data.error === "object" &&
      data.error !== null &&
      "message" in data.error &&
      typeof data.error.message === "string"
    ) {
      return data.error.message;
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

  const controller = new AbortController();
  let timedOut = false;
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  let rejectCancellation:
    | ((reason: Error) => void)
    | undefined;

  const cancellation = new Promise<never>(
    (_, reject) => {
      rejectCancellation = reject;
    },
  );

  const cancelFromCaller = () => {
    controller.abort();

    const error = new Error(
      "Requisição cancelada.",
    );
    error.name = "AbortError";
    rejectCancellation?.(error);
  };

  if (signal?.aborted) {
    cancelFromCaller();
  } else {
    signal?.addEventListener(
      "abort",
      cancelFromCaller,
    );
  }

  const request = async (): Promise<T> => {
    const response = await fetch(
      buildUrl(path),
      {
        method,
        headers: requestHeaders,
        body:
          body !== undefined
            ? JSON.stringify(body)
            : undefined,
        signal: controller.signal,
      },
    );

    const data =
      await parseResponse(response);

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
  };

  const timeout = new Promise<never>(
    (_, reject) => {
      timeoutId = setTimeout(() => {
        timedOut = true;
        controller.abort();

        reject(
          new ApiError(
            "O servidor demorou para responder. Tente novamente.",
            0,
          ),
        );
      }, REQUEST_TIMEOUT_MS);
    },
  );

  try {
    return await Promise.race([
      request(),
      timeout,
      cancellation,
    ]);
  } catch (error) {
    if (timedOut) {
      throw new ApiError(
        "O servidor demorou para responder. Tente novamente.",
        0,
        error,
      );
    }

    if (error instanceof ApiError) {
      throw error;
    }

    if (
      signal?.aborted ||
      (error instanceof Error &&
        error.name === "AbortError")
    ) {
      throw error;
    }

    throw new ApiError(
      "Não foi possível conectar ao servidor.",
      0,
      error,
    );
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
    }

    signal?.removeEventListener(
      "abort",
      cancelFromCaller,
    );
  }
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
        method: "DELETE",
      },
    );
  },
};