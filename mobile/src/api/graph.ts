import {
  api,
  ApiError,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";


export type FollowTargetType =
  | "professional"
  | "establishment";

export type SaveTargetType =
  | "professional"
  | "establishment"
  | "experience"
  | "portfolio_item"
  | "work_post";

export type GraphReference<
  T extends string = string,
> = {
  targetType: T;
  targetId: number;
};

export type GraphState = {
  follows: GraphReference<FollowTargetType>[];
  saves: GraphReference<SaveTargetType>[];
};

export type GraphReconcileResponse = {
  state: GraphState;
  imported: GraphState;
  rejected: GraphState;
};

export type SavedProfile = {
  id: string;
  routeId: string;
  kind:
    | "professional"
    | "establishment";
  name: string;
  avatar?: string | null;
  specialty?: string | null;
  location?: string | null;
  rating?: number | null;
  reviewsCount?: number;
};

export type SavedExperience = {
  id: string;
  entityId: number;
  name: string;
  image?: string | null;
  category?: string | null;
  professionalName?: string | null;
  location?: string | null;
  durationMinutes?: number;
  price?: number;
};

export type SavedPortfolioItem = {
  id: string;
  professionalRouteId: string;
  authorName: string;
  image: string;
  caption: string;
};

export type SavedItemsResponse = {
  profiles: SavedProfile[];
  experiences: SavedExperience[];
  posts: import("@/api/feed").WorkPost[];
  portfolioItems: SavedPortfolioItem[];
};


async function withAuthenticatedRequest<T>(
  operation: (
    token: string,
  ) => Promise<T>,
) {
  let token =
    await getAccessToken();

  if (!token) {
    token =
      await refreshSession();
  }

  try {
    return await operation(
      token,
    );
  } catch (error) {
    if (
      !(
        error instanceof ApiError
      ) ||
      error.status !== 401
    ) {
      throw error;
    }

    token =
      await refreshSession();

    return operation(
      token,
    );
  }
}


export function getBeautyGraph() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<GraphState>(
        "/api/v1/graph",
        { token },
      ),
  );
}


export function followGraphTarget(
  targetType: FollowTargetType,
  targetId: number,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        following: true;
        targetType: FollowTargetType;
        targetId: number;
      }>(
        (
          "/api/v1/graph/follows/"
          + targetType
          + "/"
          + targetId
        ),
        undefined,
        { token },
      ),
  );
}


export function unfollowGraphTarget(
  targetType: FollowTargetType,
  targetId: number,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        following: false;
        removed: boolean;
        targetType: FollowTargetType;
        targetId: number;
      }>(
        (
          "/api/v1/graph/follows/"
          + targetType
          + "/"
          + targetId
        ),
        { token },
      ),
  );
}


export function saveGraphTarget(
  targetType: SaveTargetType,
  targetId: number,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        saved: true;
        targetType: SaveTargetType;
        targetId: number;
      }>(
        (
          "/api/v1/graph/saves/"
          + targetType
          + "/"
          + targetId
        ),
        undefined,
        { token },
      ),
  );
}


export function unsaveGraphTarget(
  targetType: SaveTargetType,
  targetId: number,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        saved: false;
        removed: boolean;
        targetType: SaveTargetType;
        targetId: number;
      }>(
        (
          "/api/v1/graph/saves/"
          + targetType
          + "/"
          + targetId
        ),
        { token },
      ),
  );
}


export function reconcileBeautyGraph(
  state: GraphState,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<GraphReconcileResponse>(
        "/api/v1/graph/reconcile",
        state,
        { token },
      ),
  );
}



export function getSavedItems() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<SavedItemsResponse>(
        "/api/v1/graph/saved-items",
        { token },
      ),
  );
}
