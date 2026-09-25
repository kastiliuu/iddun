import {
  api,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

import type {
  Professional,
  Service,
  Post,
} from "@/mocks/data";

export type ProfessionalListResponse = {
  items: Professional[];
  nextCursor?: string | null;
};

export type ProfessionalSearchParams = {
  search?: string;
  category?: string;
  city?: string;
  cursor?: string | null;
  limit?: number;
};

export type ProfessionalProfileResponse = {
  professional: Professional;
  services: Service[];
  posts: Post[];
};

export type FollowResponse = {
  following: boolean;
};

export type FavoriteProfessionalResponse = {
  favorited: boolean;
};

function buildQuery(
  params: ProfessionalSearchParams,
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

export async function getProfessionals(
  params: ProfessionalSearchParams = {},
) {
  const query =
    buildQuery(params);

  /*
   * Endpoint previsto:
   *
   * GET /api/professionals
   *
   * Exemplos:
   *
   * /api/professionals?category=Unhas
   * /api/professionals?search=Renata
   * /api/professionals?city=Curitiba
   */
  return api.get<ProfessionalListResponse>(
    `/api/professionals?${query}`,
  );
}

export async function getProfessional(
  professionalId: string,
) {
  /*
   * Perfil completo do profissional.
   *
   * Resposta esperada:
   *
   * {
   *   professional: {...},
   *   services: [...],
   *   posts: [...]
   * }
   */
  return api.get<ProfessionalProfileResponse>(
    `/api/professionals/${professionalId}`,
  );
}

export async function followProfessional(
  professionalId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<FollowResponse>(
        `/api/professionals/${professionalId}/follow`,
        undefined,
        {
          token,
        },
      ),
  );
}

export async function unfollowProfessional(
  professionalId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<FollowResponse>(
        `/api/professionals/${professionalId}/follow`,
        {
          token,
        },
      ),
  );
}

export async function favoriteProfessional(
  professionalId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<FavoriteProfessionalResponse>(
        `/api/professionals/${professionalId}/favorite`,
        undefined,
        {
          token,
        },
      ),
  );
}

export async function unfavoriteProfessional(
  professionalId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<FavoriteProfessionalResponse>(
        `/api/professionals/${professionalId}/favorite`,
        {
          token,
        },
      ),
  );
}

export async function getProfessionalServices(
  professionalId: string,
) {
  return api.get<{
    items: Service[];
  }>(
    `/api/professionals/${professionalId}/services`,
  );
}

export async function getProfessionalPosts(
  professionalId: string,
  cursor?: string | null,
) {
  const query =
    new URLSearchParams();

  if (cursor) {
    query.set(
      "cursor",
      cursor,
    );
  }

  query.set(
    "limit",
    "20",
  );

  return api.get<{
    items: Post[];
    nextCursor?: string | null;
  }>(
    `/api/professionals/${professionalId}/posts?${query.toString()}`,
  );
}