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
  location?: string | null;
  rating: number;
  reviewsCount: number;
  category?: string | null;
  price?: number;
  availableSlotsCount?: number;
};

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
};

export type GlobalSearchParams = {
  query?: string;
  category?: string;
  location?: string;
  limit?: number;
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

  return api.get<GlobalSearchResponse>(
    `/api/v1/search?${query.toString()}`,
    { signal },
  );
}
