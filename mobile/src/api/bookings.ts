import {
  api,
  ApiError,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

export type BookingStatus =
  | "pending"
  | "confirmed"
  | "cancelled"
  | "completed"
  | "no_show";

export type BookingParty = {
  id: string;
  slug: string;
  name: string;
};

export type BookingExperience = {
  id: string;
  slug: string;
  title: string;
  durationMinutes: number;
};

export type BookingSlot = {
  id: number;
  startsAt: string;
  endsAt: string;
  localDate: string;
  localTime: string;
  localEndsAt: string;
  timezone: string;
};

export type Booking = {
  id: string;
  status: BookingStatus;
  price: number;
  experience: BookingExperience;
  professional: BookingParty;
  establishment: BookingParty | null;
  slot: BookingSlot;
  holdExpiresAt: string | null;
  confirmedAt: string | null;
  cancelledAt: string | null;
  completedAt: string | null;
  cancellationReason: string | null;
  createdAt: string;
  canConfirm: boolean;
  canCancel: boolean;
};

export type BookingResponse = {
  booking: Booking;
};

export type ConfirmBookingResponse = {
  booking: Booking;
  calendarSynced: boolean;
};

export type BookingPagination = {
  offset: number;
  limit: number;
  total: number;
  nextOffset: number | null;
  hasMore: boolean;
};

export type BookingListResponse = {
  items: Booking[];
  pagination: BookingPagination;
};

export type BookingListParams = {
  status?: BookingStatus;
  offset?: number;
  limit?: number;
};

function buildQuery(
  params: BookingListParams,
) {
  const query =
    new URLSearchParams();

  if (params.status) {
    query.set(
      "status",
      params.status,
    );
  }

  query.set(
    "offset",
    String(
      params.offset ?? 0,
    ),
  );

  query.set(
    "limit",
    String(
      params.limit ?? 20,
    ),
  );

  return query.toString();
}

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

    const refreshedToken =
      await refreshSession();

    return operation(
      refreshedToken,
    );
  }
}

export function holdExperienceSlot(
  experienceSlug: string,
  slotId: number,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<BookingResponse>(
        (
          "/api/v1/experiences/"
          + encodeURIComponent(
            experienceSlug,
          )
          + `/slots/${slotId}/hold`
        ),
        undefined,
        { token },
      ),
  );
}

export function getBookings(
  params: BookingListParams = {},
) {
  const query =
    buildQuery(params);

  return withAuthenticatedRequest(
    (token) =>
      api.get<BookingListResponse>(
        `/api/v1/bookings?${query}`,
        { token },
      ),
  );
}

export function getBooking(
  bookingId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.get<BookingResponse>(
        `/api/v1/bookings/${bookingId}`,
        { token },
      ),
  );
}

export function confirmBooking(
  bookingId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<ConfirmBookingResponse>(
        `/api/v1/bookings/${bookingId}/confirm`,
        undefined,
        { token },
      ),
  );
}

export function cancelBooking(
  bookingId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<BookingResponse>(
        `/api/v1/bookings/${bookingId}/cancel`,
        undefined,
        { token },
      ),
  );
}
