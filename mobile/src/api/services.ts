import {
  api,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

import type {
  Service,
} from "@/mocks/data";

export type ServiceListResponse = {
  items: Service[];
  nextCursor?: string | null;
};

export type ServiceSearchParams = {
  search?: string;
  category?: string;
  city?: string;
  authorId?: string;
  cursor?: string | null;
  limit?: number;
};

export type ServiceAvailability = {
  date: string;
  slots: string[];
};

export type ServiceAvailabilityResponse = {
  serviceId: string;
  date: string;
  slots: string[];
};

export type FavoriteServiceResponse = {
  favorited: boolean;
};

function buildQuery(
  params: ServiceSearchParams,
) {
  const query =
    new URLSearchParams();

  if (params.search?.trim()) {
    query.set(
      "search",
      params.search.trim(),
    );
  }

  if (params.category?.trim()) {
    query.set(
      "category",
      params.category.trim(),
    );
  }

  if (params.city?.trim()) {
    query.set(
      "city",
      params.city.trim(),
    );
  }

  if (params.authorId?.trim()) {
    query.set(
      "authorId",
      params.authorId.trim(),
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

export async function getServices(
  params: ServiceSearchParams = {},
) {
  const query =
    buildQuery(params);

  return api.get<ServiceListResponse>(
    `/api/services?${query}`,
  );
}

export async function getService(
  serviceId: string,
) {
  return api.get<Service>(
    `/api/services/${serviceId}`,
  );
}

export async function getServiceAvailability(
  serviceId: string,
  date: string,
) {
  /*
   * Endpoint previsto:
   *
   * GET /api/services/{id}/availability?date=2026-09-23
   *
   * Resposta:
   *
   * {
   *   serviceId: "srv_1",
   *   date: "2026-09-23",
   *   slots: [
   *     "09:00",
   *     "10:30",
   *     "14:00"
   *   ]
   * }
   */
  const query =
    new URLSearchParams();

  query.set(
    "date",
    date,
  );

  return api.get<ServiceAvailabilityResponse>(
    `/api/services/${serviceId}/availability?${query.toString()}`,
  );
}

export async function favoriteService(
  serviceId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<FavoriteServiceResponse>(
        `/api/services/${serviceId}/favorite`,
        undefined,
        {
          token,
        },
      ),
  );
}

export async function unfavoriteService(
  serviceId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<FavoriteServiceResponse>(
        `/api/services/${serviceId}/favorite`,
        {
          token,
        },
      ),
  );
}

export type CreateServicePayload = {
  name: string;
  description: string;
  category: string;
  price: number;
  durationMinutes: number;
  location?: string | null;
  imageUrl?: string | null;
};

export type CreateServiceResponse = {
  service: Service;
};

export async function createService(
  payload: CreateServicePayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<CreateServiceResponse>(
        "/api/services",
        {
          name:
            payload.name.trim(),

          description:
            payload.description.trim(),

          category:
            payload.category.trim(),

          price:
            payload.price,

          durationMinutes:
            payload.durationMinutes,

          location:
            payload.location?.trim() ||
            null,

          imageUrl:
            payload.imageUrl?.trim() ||
            null,
        },
        {
          token,
        },
      ),
  );
}

export type UpdateServicePayload =
  Partial<CreateServicePayload>;

export async function updateService(
  serviceId: string,
  payload: UpdateServicePayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.patch<CreateServiceResponse>(
        `/api/services/${serviceId}`,
        {
          ...payload,

          name:
            payload.name?.trim(),

          description:
            payload.description?.trim(),

          category:
            payload.category?.trim(),

          location:
            payload.location?.trim(),

          imageUrl:
            payload.imageUrl?.trim(),
        },
        {
          token,
        },
      ),
  );
}

export async function deleteService(
  serviceId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        success: boolean;
      }>(
        `/api/services/${serviceId}`,
        {
          token,
        },
      ),
  );
}