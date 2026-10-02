import {
  api,
} from "@/api/client";

import {
  followGraphTarget,
  saveGraphTarget,
  unfollowGraphTarget,
  unsaveGraphTarget,
} from "@/api/graph";

import type {
  Professional,
  Service,
} from "@/mocks/data";

import type {
  WorkPost,
} from "@/api/feed";

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
  posts: WorkPost[];
};

export type FollowResponse = {
  following: boolean;
};

export type FavoriteProfessionalResponse = {
  favorited: boolean;
};

function requireGraphId(
  value: string,
) {
  if (!/^\d+$/.test(value)) {
    throw new Error(
      "Este item ainda não possui um ID real do backend.",
    );
  }

  const id = Number(value);

  if (
    !Number.isInteger(id) ||
    id <= 0
  ) {
    throw new Error(
      "ID inválido para sincronização.",
    );
  }

  return id;
}

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
    `/api/v1/professionals/${encodeURIComponent(professionalId)}`,
  );
}

export async function followProfessional(
  professionalId: string,
) {
  const response =
    await followGraphTarget(
      "professional",
      requireGraphId(
        professionalId,
      ),
    );

  return {
    following:
      response.following,
  };
}

export async function unfollowProfessional(
  professionalId: string,
) {
  const response =
    await unfollowGraphTarget(
      "professional",
      requireGraphId(
        professionalId,
      ),
    );

  return {
    following:
      response.following,
  };
}

export async function favoriteProfessional(
  professionalId: string,
) {
  const response =
    await saveGraphTarget(
      "professional",
      requireGraphId(
        professionalId,
      ),
    );

  return {
    favorited:
      response.saved,
  };
}

export async function unfavoriteProfessional(
  professionalId: string,
) {
  const response =
    await unsaveGraphTarget(
      "professional",
      requireGraphId(
        professionalId,
      ),
    );

  return {
    favorited:
      response.saved,
  };
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
    items: WorkPost[];
    nextCursor?: string | null;
  }>(
    `/api/professionals/${professionalId}/posts?${query.toString()}`,
  );
}