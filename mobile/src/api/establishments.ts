import {
  api,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

import {
  followGraphTarget,
  saveGraphTarget,
  unfollowGraphTarget,
  unsaveGraphTarget,
} from "@/api/graph";

import type {
  Professional,
  Service,
  Post,
} from "@/mocks/data";

export type EstablishmentListResponse = {
  items: Professional[];
  nextCursor?: string | null;
};

export type EstablishmentSearchParams = {
  search?: string;
  category?: string;
  city?: string;
  cursor?: string | null;
  limit?: number;
};

export type EstablishmentProfileResponse = {
  establishment: Professional;
  services: Service[];
  posts: Post[];
  team: Professional[];
};

export type EstablishmentTeamResponse = {
  items: Professional[];
};

export type FollowEstablishmentResponse = {
  following: boolean;
};

export type FavoriteEstablishmentResponse = {
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
  params: EstablishmentSearchParams,
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

export async function getEstablishments(
  params: EstablishmentSearchParams = {},
) {
  const query =
    buildQuery(params);

  /*
   * Endpoint previsto:
   *
   * GET /api/establishments
   *
   * Exemplos:
   *
   * /api/establishments?city=Curitiba
   * /api/establishments?category=Unhas
   * /api/establishments?search=Atelier
   */
  return api.get<EstablishmentListResponse>(
    `/api/establishments?${query}`,
  );
}

export async function getEstablishment(
  establishmentId: string,
) {
  /*
   * Perfil completo do estabelecimento.
   *
   * Resposta esperada:
   *
   * {
   *   establishment: {...},
   *   services: [...],
   *   posts: [...],
   *   team: [...]
   * }
   */
  return api.get<EstablishmentProfileResponse>(
    `/api/establishments/${establishmentId}`,
  );
}

export async function getEstablishmentServices(
  establishmentId: string,
) {
  return api.get<{
    items: Service[];
  }>(
    `/api/establishments/${establishmentId}/services`,
  );
}

export async function getEstablishmentPosts(
  establishmentId: string,
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
    `/api/establishments/${establishmentId}/posts?${query.toString()}`,
  );
}

export async function getEstablishmentTeam(
  establishmentId: string,
) {
  return api.get<EstablishmentTeamResponse>(
    `/api/establishments/${establishmentId}/team`,
  );
}

export async function followEstablishment(
  establishmentId: string,
) {
  const response =
    await followGraphTarget(
      "establishment",
      requireGraphId(
        establishmentId,
      ),
    );

  return {
    following:
      response.following,
  };
}

export async function unfollowEstablishment(
  establishmentId: string,
) {
  const response =
    await unfollowGraphTarget(
      "establishment",
      requireGraphId(
        establishmentId,
      ),
    );

  return {
    following:
      response.following,
  };
}

export async function favoriteEstablishment(
  establishmentId: string,
) {
  const response =
    await saveGraphTarget(
      "establishment",
      requireGraphId(
        establishmentId,
      ),
    );

  return {
    favorited:
      response.saved,
  };
}

export async function unfavoriteEstablishment(
  establishmentId: string,
) {
  const response =
    await unsaveGraphTarget(
      "establishment",
      requireGraphId(
        establishmentId,
      ),
    );

  return {
    favorited:
      response.saved,
  };
}

export type LinkProfessionalPayload = {
  professionalId: string;
};

export type LinkProfessionalResponse = {
  linked: boolean;
  professional: Professional;
};

export async function linkProfessionalToEstablishment(
  establishmentId: string,
  professionalId: string,
) {
  /*
   * Endpoint previsto:
   *
   * POST /api/establishments/{id}/team
   *
   * {
   *   professionalId: "pro_1"
   * }
   *
   * Futuramente podemos colocar
   * fluxo de convite/aceite antes
   * de efetivar o vínculo.
   */
  return withAuthenticatedRequest(
    (token) =>
      api.post<LinkProfessionalResponse>(
        `/api/establishments/${establishmentId}/team`,
        {
          professionalId,
        },
        {
          token,
        },
      ),
  );
}

export async function unlinkProfessionalFromEstablishment(
  establishmentId: string,
  professionalId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        unlinked: boolean;
      }>(
        `/api/establishments/${establishmentId}/team/${professionalId}`,
        {
          token,
        },
      ),
  );
}