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

export type CatalogPagination = {
  offset: number;
  limit: number;
  total: number;
  nextOffset: number | null;
  hasMore: boolean;
};

export type CatalogResponse = {
  items: CatalogExperience[];
  total: number;
  nextOffset: number | null;
  pagination: CatalogPagination;
};

export function getRealExperiences(
  params: {
    search?: string;
    category?: string;
    limit?: number;
    offset?: number;
    location?: string;
    sort?:
      | "recommended"
      | "lowest_price"
      | "highest_rating"
      | "biggest_saving"
      | "newest";
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
  if (params.location?.trim()) {
    query.set(
      "location",
      params.location.trim(),
    );
  }
  if (params.sort) {
    query.set("sort", params.sort);
  }
  query.set(
    "limit",
    String(params.limit ?? 20),
  );
  query.set(
    "offset",
    String(params.offset ?? 0),
  );
  return api.get<CatalogResponse>(
    `/api/v1/experiences?${query.toString()}`,
    { signal },
  );
}



export type ExperienceAvailabilitySlot = {
  id: number;
  startsAt: string;
  endsAt: string;
  deadline: string;
};

export type ExperienceAvailabilityDay = {
  date: string;
  slots: ExperienceAvailabilitySlot[];
};

export type ExperienceAvailabilityResponse = {
  experienceId: string;
  timezone: string;
  days: ExperienceAvailabilityDay[];
};

export function getRealExperience(
  slug: string,
  signal?: AbortSignal,
) {
  return api.get<CatalogExperience>(
    `/api/v1/experiences/${encodeURIComponent(slug)}`,
    { signal },
  );
}

export function getExperienceAvailability(
  slug: string,
  signal?: AbortSignal,
) {
  return api.get<ExperienceAvailabilityResponse>(
    `/api/v1/experiences/${encodeURIComponent(slug)}/availability`,
    { signal },
  );
}
