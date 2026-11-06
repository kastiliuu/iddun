import {
  api,
  ApiError,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

export type NotificationKind =
  | "booking"
  | "iddun_now"
  | "follow"
  | "like"
  | "comment"
  | "membership"
  | "review"
  | "system";

/** Abas da central (PR 6a/6b; DEC-ID-216). */
export type NotificationCategory =
  | "bookings"
  | "social"
  | "work"
  | "system";

export type NotificationContextType =
  | "client"
  | "professional"
  | "establishment";

export type NotificationItem = {
  id: string;
  kind: NotificationKind;
  title: string;
  body: string;
  actionType?: string | null;
  actionId?: string | null;
  read: boolean;
  readAt?: string | null;
  createdAt: string;
  category?: NotificationCategory;
  contextType?: NotificationContextType | null;
  contextId?: string | null;
  groupCount?: number;
  /** Nome do contexto (ex.: a empresa) só quando o acesso ainda vale. */
  contextLabel?: string | null;
};

/** Destino autorizado pelo servidor ao abrir (DEC-ID-220, 221). */
export type NotificationTarget = {
  type:
    | "booking"
    | "review_booking"
    | "pro_booking"
    | "experience"
    | "post"
    | "professional"
    | "establishment"
    | "membership"
    | "business_team";
  id: string | null;
  webPath: string;
};

export type NotificationCounts = {
  all: number;
  bookings: number;
  social: number;
  work: number;
};

export type NotificationPreferences = {
  bookingEnabled: boolean;
  iddunNowEnabled: boolean;
  followEnabled: boolean;
  systemEnabled: boolean;
  pushEnabled: boolean;
  socialEnabled: boolean;
  workEnabled: boolean;
  /** Reservas são essenciais: sempre ativas (DEC-ID-218). */
  bookingEssential?: boolean;
};

export type NotificationListResponse = {
  items: NotificationItem[];
  counts?: NotificationCounts;
  unreadCount: number;
  pagination: {
    offset: number;
    limit: number;
    total: number;
    nextOffset: number | null;
    hasMore: boolean;
  };
};

async function withAuthenticatedRequest<T>(
  operation: (
    token: string,
  ) => Promise<T>,
) {
  let token =
    await getAccessToken();

  if (!token) {
    token =
      await refreshSession();
  }

  try {
    return await operation(
      token,
    );
  } catch (error) {
    if (
      !(
        error instanceof ApiError
      ) ||
      error.status !== 401
    ) {
      throw error;
    }

    token =
      await refreshSession();

    return operation(
      token,
    );
  }
}

export function getNotifications(
  options: {
    offset?: number;
    limit?: number;
    unreadOnly?: boolean;
    category?: Exclude<NotificationCategory, "system">;
  } = {},
) {
  const query =
    new URLSearchParams();

  query.set(
    "offset",
    String(
      options.offset ?? 0,
    ),
  );
  query.set(
    "limit",
    String(
      options.limit ?? 30,
    ),
  );

  if (options.unreadOnly) {
    query.set(
      "unreadOnly",
      "true",
    );
  }

  if (options.category) {
    query.set(
      "category",
      options.category,
    );
  }

  return withAuthenticatedRequest(
    (token) =>
      api.get<NotificationListResponse>(
        `/api/v1/notifications?${query.toString()}`,
        { token },
      ),
  );
}

export function markNotificationRead(
  notificationId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        notification:
          NotificationItem;
      }>(
        `/api/v1/notifications/${notificationId}/read`,
        undefined,
        { token },
      ),
  );
}

/** Marca como lida e recebe o destino só se o acesso vale agora. */
export function openNotification(
  notificationId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        notification:
          NotificationItem;
        target:
          NotificationTarget | null;
      }>(
        `/api/v1/notifications/${notificationId}/open`,
        undefined,
        { token },
      ),
  );
}

export function markAllNotificationsRead() {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        updated: number;
        unreadCount: number;
      }>(
        "/api/v1/notifications/read-all",
        undefined,
        { token },
      ),
  );
}

export function getNotificationPreferences() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<{
        preferences:
          NotificationPreferences;
      }>(
        "/api/v1/notifications/preferences",
        { token },
      ),
  );
}

export function updateNotificationPreferences(
  payload: Partial<
    NotificationPreferences
  >,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        preferences:
          NotificationPreferences;
      }>(
        "/api/v1/notifications/preferences",
        payload,
        { token },
      ),
  );
}
