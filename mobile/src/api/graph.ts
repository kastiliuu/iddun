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
  | "portfolio_item";

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
