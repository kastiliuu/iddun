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
  | "system";

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
};

export type NotificationPreferences = {
  bookingEnabled: boolean;
  iddunNowEnabled: boolean;
  followEnabled: boolean;
  systemEnabled: boolean;
  pushEnabled: boolean;
};

export type NotificationListResponse = {
  items: NotificationItem[];
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
