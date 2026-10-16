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
  canRequestCancellation?: boolean;
  cancellationRequestStatus?: "pending" | null;
  rescheduleRequestStatus?: "pending" | null;
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

export type BookingActionsResponse = {
  rescheduleRequestStatus: "pending" | null;
  rescheduleSlots: {
    id: number;
    startsAt: string;
    localDate: string;
    localTime: string;
    timezone: string;
  }[];
  canRebook: boolean;
  rebookExperienceSlug: string | null;
};

export function getBookingActions(bookingId: string) {
  return withAuthenticatedRequest((token) =>
    api.get<BookingActionsResponse>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/actions`,
      { token },
    ),
  );
}

export function requestBookingReschedule(
  bookingId: string, slotId: number, reason?: string,
) {
  return withAuthenticatedRequest((token) =>
    api.post<BookingResponse>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/reschedule-request`,
      { slotId, reason },
      { token },
    ),
  );
}

export function withdrawBookingReschedule(bookingId: string) {
  return withAuthenticatedRequest((token) =>
    api.post<BookingResponse>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/reschedule-request/withdraw`,
      undefined,
      { token },
    ),
  );
}

export function withdrawBookingCancellation(bookingId: string) {
  return withAuthenticatedRequest((token) =>
    api.post<BookingResponse>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/cancel-request/withdraw`,
      undefined,
      { token },
    ),
  );
}

export type BookingTimeline = {
  items: { at: string; label: string }[];
};

export function getBookingTimeline(bookingId: string) {
  return withAuthenticatedRequest((token) =>
    api.get<BookingTimeline>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/timeline`,
      { token },
    ),
  );
}

export type NoShowDispute = {
  id: number;
  status: "pending" | "accepted" | "rejected";
  justification: string;
  evidenceReference: string | null;
  resolutionNote: string | null;
  createdAt: string;
  resolvedAt: string | null;
};

export type NoShowDisputesResponse = {
  canDispute: boolean;
  items: NoShowDispute[];
};

export function getNoShowDisputes(bookingId: string) {
  return withAuthenticatedRequest((token) =>
    api.get<NoShowDisputesResponse>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/no-show-disputes`,
      { token },
    ),
  );
}

export function createNoShowDispute(
  bookingId: string, justification: string, evidenceReference?: string,
) {
  return withAuthenticatedRequest((token) =>
    api.post<{ dispute: NoShowDispute }>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/no-show-disputes`,
      { justification, evidenceReference: evidenceReference || "" },
      { token },
    ),
  );
}

export type BookingReviewResponse = {
  eligible: boolean;
  review: { rating: number; recommended: boolean; comment: string | null } | null;
};

export function getBookingReview(bookingId: string) {
  return withAuthenticatedRequest((token) =>
    api.get<BookingReviewResponse>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/review`, { token },
    ),
  );
}

export function saveBookingReview(
  bookingId: string, rating: number, recommended: boolean, comment: string,
) {
  return withAuthenticatedRequest((token) =>
    api.post<{ saved: boolean }>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/review`,
      { rating, recommended, comment }, { token },
    ),
  );
}

export type CalendarBookingPayload = {
  ics: string;
  startsAt: string;
  endsAt: string;
  title: string;
  uid: string;
};

export function getBookingCalendar(bookingId: string) {
  return withAuthenticatedRequest((token) =>
    api.get<CalendarBookingPayload>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/calendar`,
      { token },
    ),
  );
}

export function getBookingSafeShare(bookingId: string) {
  return withAuthenticatedRequest((token) =>
    api.get<{ message: string }>(
      `/api/v1/bookings/${encodeURIComponent(bookingId)}/share`,
      { token },
    ),
  );
}
