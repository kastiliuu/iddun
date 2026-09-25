import {
  api,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

export type BookingStatus =
  | "pending"
  | "confirmed"
  | "cancelled"
  | "completed";

export type Booking = {
  id: string;

  serviceId: string;

  professionalId?: string | null;

  establishmentId?: string | null;

  customerId: string;

  serviceName: string;

  professionalName?: string | null;

  establishmentName?: string | null;

  date: string;

  time: string;

  startsAt: string;

  durationMinutes: number;

  price: number;

  status: BookingStatus;

  location?: string | null;

  notes?: string | null;

  createdAt: string;
};

export type CreateBookingPayload = {
  serviceId: string;

  date: string;

  time: string;

  notes?: string | null;
};

export type CreateBookingResponse = {
  booking: Booking;
};

export type BookingListResponse = {
  items: Booking[];

  nextCursor?: string | null;
};

export type BookingListParams = {
  status?: BookingStatus;

  cursor?: string | null;

  limit?: number;
};

export type CancelBookingResponse = {
  booking: Booking;
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

  if (params.cursor) {
    query.set(
      "cursor",
      params.cursor,
    );
  }

  query.set(
    "limit",
    String(
      params.limit ?? 20,
    ),
  );

  return query.toString();
}

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

  return request(token);
}

export async function createBooking(
  payload: CreateBookingPayload,
) {
  /*
   * Endpoint previsto:
   *
   * POST /api/bookings
   *
   * {
   *   serviceId: "srv_1",
   *   date: "2026-09-23",
   *   time: "14:30",
   *   notes: null
   * }
   *
   * O backend DEVE validar novamente:
   *
   * - serviço existe
   * - profissional/estabelecimento existe
   * - horário ainda está livre
   * - não existe conflito
   * - duração
   * - preço atual
   * - regras de agenda
   *
   * O app nunca deve ser
   * a fonte da verdade.
   */
  return withAuthenticatedRequest(
    (token) =>
      api.post<CreateBookingResponse>(
        "/api/bookings",
        {
          serviceId:
            payload.serviceId,

          date:
            payload.date,

          time:
            payload.time,

          notes:
            payload.notes?.trim() ||
            null,
        },
        {
          token,
        },
      ),
  );
}

export async function getBookings(
  params: BookingListParams = {},
) {
  const query =
    buildQuery(params);

  /*
   * Retorna agendamentos
   * do usuário autenticado.
   */
  return withAuthenticatedRequest(
    (token) =>
      api.get<BookingListResponse>(
        `/api/bookings?${query}`,
        {
          token,
        },
      ),
  );
}

export async function getBooking(
  bookingId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.get<Booking>(
        `/api/bookings/${bookingId}`,
        {
          token,
        },
      ),
  );
}

export async function cancelBooking(
  bookingId: string,
) {
  /*
   * Preferimos uma ação explícita
   * de cancelamento em vez de
   * simplesmente DELETE.
   *
   * Isso preserva histórico,
   * auditoria e possíveis regras
   * de cancelamento.
   */
  return withAuthenticatedRequest(
    (token) =>
      api.post<CancelBookingResponse>(
        `/api/bookings/${bookingId}/cancel`,
        undefined,
        {
          token,
        },
      ),
  );
}

export async function confirmBooking(
  bookingId: string,
) {
  /*
   * Esse endpoint será mais útil
   * para profissional/estabelecimento
   * quando o fluxo permitir
   * confirmação manual.
   */
  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        booking: Booking;
      }>(
        `/api/bookings/${bookingId}/confirm`,
        undefined,
        {
          token,
        },
      ),
  );
}

export async function completeBooking(
  bookingId: string,
) {
  /*
   * Depois poderemos usar isso
   * para liberar automaticamente
   * a etapa de avaliação.
   */
  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        booking: Booking;
      }>(
        `/api/bookings/${bookingId}/complete`,
        undefined,
        {
          token,
        },
      ),
  );
}