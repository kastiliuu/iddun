import { api } from "@/api/client";

export type CatalogExperience = {
  id: string;
  slug: string;
  title: string;
  description: string;
  category: string;
  categoryLabel: string;
  professional: string;
  professionalSlug: string;
  establishment: string | null;
  establishmentSlug: string | null;
  location: string;
  price: number;
  regularPrice: number;
  durationMinutes: number;
  rating: number;
  reviews: number;
  establishmentRating: number | null;
  establishmentReviews: number;
  availableSlotsCount: number;
  imageUrl: string;
  webUrl: string;
};

export type CatalogResponse = {
  items: CatalogExperience[];
  total: number;
  nextOffset: number | null;
};

export function getRealExperiences(
  params: {
    search?: string;
    category?: string;
    limit?: number;
  } = {},
  signal?: AbortSignal,
) {
  const query = new URLSearchParams();
  if (params.search?.trim()) {
    query.set("search", params.search.trim());
  }
  if (params.category) {
    query.set("category", params.category);
  }
  query.set("limit", String(params.limit ?? 20));
  return api.get<CatalogResponse>(
    `/api/v1/experiences?${query.toString()}`,
    { signal },
  );
}

