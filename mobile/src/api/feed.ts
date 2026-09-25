import {
  api,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

import type {
  Post,
} from "@/mocks/data";

export type FeedMode =
  | "for-you"
  | "following";

export type FeedResponse = {
  items: Post[];
  nextCursor?: string | null;
};

export type FeedParams = {
  mode?: FeedMode;
  cursor?: string | null;
  limit?: number;
};

export type CreatePostPayload = {
  caption: string;
  imageUrl: string;
  serviceId?: string | null;
};

export type CreatePostResponse = {
  post: Post;
};

function buildFeedQuery({
  mode = "for-you",
  cursor,
  limit = 20,
}: FeedParams = {}) {
  const params =
    new URLSearchParams();

  params.set(
    "mode",
    mode,
  );

  params.set(
    "limit",
    String(limit),
  );

  if (cursor) {
    params.set(
      "cursor",
      cursor,
    );
  }

  return params.toString();
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

  try {
    return await request(token);
  } catch (error) {
    /*
     * Nesta camada ainda não fazemos
     * inspeção automática de todo erro.
     *
     * A renovação centralizada de 401
     * poderá entrar futuramente no
     * próprio client.ts.
     */
    throw error;
  }
}

export async function getFeed(
  params: FeedParams = {},
) {
  const query =
    buildFeedQuery(params);

  /*
   * Endpoint previsto:
   *
   * GET /api/feed?mode=for-you
   *
   * ou
   *
   * GET /api/feed?mode=following
   *
   * Resposta:
   *
   * {
   *   items: [...],
   *   nextCursor: "..."
   * }
   */
  return api.get<FeedResponse>(
    `/api/feed?${query}`,
  );
}

export async function getPost(
  postId: string,
) {
  return api.get<Post>(
    `/api/posts/${postId}`,
  );
}

export async function createPost(
  payload: CreatePostPayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<CreatePostResponse>(
        "/api/posts",
        {
          caption:
            payload.caption.trim(),

          imageUrl:
            payload.imageUrl,

          serviceId:
            payload.serviceId ??
            null,
        },
        {
          token,
        },
      ),
  );
}

export async function deletePost(
  postId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        success: boolean;
      }>(
        `/api/posts/${postId}`,
        {
          token,
        },
      ),
  );
}

export async function favoritePost(
  postId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        favorited: boolean;
      }>(
        `/api/posts/${postId}/favorite`,
        undefined,
        {
          token,
        },
      ),
  );
}

export async function unfavoritePost(
  postId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        favorited: boolean;
      }>(
        `/api/posts/${postId}/favorite`,
        {
          token,
        },
      ),
  );
}

export async function addComment(
  postId: string,
  text: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        id: string;
        text: string;
        createdAt: string;
      }>(
        `/api/posts/${postId}/comments`,
        {
          text:
            text.trim(),
        },
        {
          token,
        },
      ),
  );
}