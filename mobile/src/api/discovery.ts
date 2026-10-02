import { api } from "@/api/client";
import type { WorkPost } from "@/api/feed";
import type { Professional } from "@/mocks/data";

export type DiscoveryResponse = {
  professionals: Professional[];
  establishments: Professional[];
  posts: WorkPost[];
};

export type DiscoveryParams = {
  search?: string;
  category?: string;
  city?: string;
  limit?: number;
};

export function getDiscovery(
  params: DiscoveryParams = {},
  signal?: AbortSignal,
) {
  const query = new URLSearchParams();

  if (params.search?.trim()) {
    query.set("search", params.search.trim());
  }

  if (params.category?.trim()) {
    query.set("category", params.category.trim());
  }

  if (params.city?.trim()) {
    query.set("city", params.city.trim());
  }

  query.set(
    "limit",
    String(params.limit ?? 8),
  );

  return api.get<DiscoveryResponse>(
    `/api/v1/discovery?${query.toString()}`,
    { signal },
  );
}
