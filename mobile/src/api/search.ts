import { api } from "@/api/client";

export type GlobalSearchKind =
  | "experience"
  | "professional"
  | "establishment"
  | "post";

export type GlobalSearchItem = {
  id: string;
  routeId: string;
  kind: GlobalSearchKind;
  title: string;
  subtitle?: string | null;
  image?: string | null;
  works?: { imageUrl: string; caption: string | null }[];
  worksCount?: number;
  serviceImageUrl?: string | null;
  professionalSlug?: string | null;
  location?: string | null;
  rating: number;
  reviewsCount: number;
  category?: string | null;
  price?: number;
  availableSlotsCount?: number;
  /** Próximo horário real (DEC-ID-183); nulo sem slot futuro. */
  nextAvailableLabel?: string | null;
};

/** Contagens reais por tipo (PR 5a; DEC-ID-180). */
export type GlobalSearchCounts = {
  experiences: number;
  professionals: number;
  establishments: number;
  posts: number;
  total: number;
};

export type GlobalSearchPage = {
  offset: number;
  limit: number;
  total: number;
  nextOffset: number | null;
};

export type GlobalSearchSort =
  | "recommended"
  | "lowest_price"
  | "highest_rating"
  | "newest";

export type GlobalSearchResponse = {
  query: string;
  location: string;
  category: string;
  items: GlobalSearchItem[];
  sections: {
    professionals: GlobalSearchItem[];
    establishments: GlobalSearchItem[];
    experiences: GlobalSearchItem[];
    posts: GlobalSearchItem[];
  };
  counts?: GlobalSearchCounts;
  /** Presente quando a busca pede um tipo só. */
  page?: GlobalSearchPage | null;
};

export type GlobalSearchParams = {
  query?: string;
  category?: string;
  location?: string;
  limit?: number;
  /** PR 5a: um tipo só, com paginação. */
  type?: GlobalSearchKind;
  offset?: number;
  /** Só serviços (DEC-ID-181). */
  priceMin?: number;
  priceMax?: number;
  available?: boolean;
  sort?: GlobalSearchSort;
};

export function globalSearch(
  params: GlobalSearchParams = {},
  signal?: AbortSignal,
) {
  const query =
    new URLSearchParams();

  if (params.query?.trim()) {
    query.set(
      "q",
      params.query.trim(),
    );
  }

  if (params.category?.trim()) {
    query.set(
      "category",
      params.category.trim(),
    );
  }

  if (params.location?.trim()) {
    query.set(
      "location",
      params.location.trim(),
    );
  }

  query.set(
    "limit",
    String(
      params.limit ?? 8,
    ),
  );

  if (params.type) {
    query.set("type", params.type);
  }

  if (params.offset) {
    query.set("offset", String(params.offset));
  }

  if (params.priceMin !== undefined) {
    query.set("priceMin", String(params.priceMin));
  }

  if (params.priceMax !== undefined) {
    query.set("priceMax", String(params.priceMax));
  }

  if (params.available) {
    query.set("available", "1");
  }

  if (params.sort && params.sort !== "recommended") {
    query.set("sort", params.sort);
  }

  return api.get<GlobalSearchResponse>(
    `/api/v1/search?${query.toString()}`,
    { signal },
  );
}
