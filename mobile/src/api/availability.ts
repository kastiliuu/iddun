import {
  api,
  ApiError,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

export type IDDUNNowFilter =
  | "all"
  | "today"
  | "soon";

export type IDDUNNowItem = {
  id: string;
  slotId: number;

  serviceId: string;
  serviceEntityId: number;
  serviceName: string;
  category?: string | null;
  image?: string | null;
  price: number;
  durationMinutes: number;

  professionalId: string;
  professionalRouteId: string;
  professionalName: string;
  professionalAvatar?: string | null;

  establishmentId?: string | null;
  establishmentRouteId?: string | null;
  establishmentName?: string | null;

  location: string;
  startsAt: string;
  endsAt: string;
  timezone: string;
  timeLabel: string;
  urgent: boolean;
};

export type IDDUNNowResponse = {
  items: IDDUNNowItem[];
};

export type AvailabilityOption = {
  id: string;
  entityId: number;
  name: string;
  category: string;
  durationMinutes: number;
  price: number;
  image?: string | null;
  professionalId: string;
  professionalName: string;
  establishmentId?: string | null;
};

export type AvailabilityOptionsResponse = {
  items: AvailabilityOption[];
};

export type CreateAvailabilityPayload = {
  serviceId: string;
  date: string;
  time: string;
  cutoffMinutes?: number | null;
};

export type CreateAvailabilityResponse = {
  slot: IDDUNNowItem;
};

async function withAuthenticatedRequest<T>(
  request: (
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
    return await request(
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

    return request(
      token,
    );
  }
}

export function getIDDUNNow(
  filter: IDDUNNowFilter = "all",
  signal?: AbortSignal,
) {
  const query =
    new URLSearchParams();

  query.set(
    "filter",
    filter,
  );
  query.set(
    "limit",
    "30",
  );

  return api.get<IDDUNNowResponse>(
    `/api/v1/iddun-now?${query.toString()}`,
    { signal },
  );
}

export function getAvailabilityOptions() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<AvailabilityOptionsResponse>(
        "/api/v1/availability/options",
        { token },
      ),
  );
}

export function createAvailability(
  payload: CreateAvailabilityPayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<CreateAvailabilityResponse>(
        "/api/v1/availability",
        payload,
        { token },
      ),
  );
}
