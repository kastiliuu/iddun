import {
  api,
  ApiError,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

import {
  saveGraphTarget,
  unsaveGraphTarget,
} from "@/api/graph";

import type {
  UploadableImage,
} from "@/api/media";


export type FeedMode =
  | "for-you"
  | "following";

export type WorkPostAuthorKind =
  | "professional"
  | "establishment";

export type WorkPostStatus =
  | "draft"
  | "published"
  | "archived";

export type WorkPostAuthor = {
  id: string;
  kind: WorkPostAuthorKind;
  name: string;
  avatar?: string | null;
  specialty?: string | null;
};

export type WorkPostService = {
  id: string;
  name: string;
  price?: number;
  availabilityLabel?: string | null;
};

export type WorkPost = {
  id: string;
  authorId: string;
  authorKind: WorkPostAuthorKind;
  author: WorkPostAuthor;
  image: string;
  imageFocusX: number;
  imageFocusY: number;
  caption: string;
  serviceId?: string | null;
  service?: WorkPostService | null;
  commentsCount: number;
  publishedAt?: string | null;
  deepLink: string;
  status?: WorkPostStatus;
  experienceId?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type FeedResponse = {
  items: WorkPost[];
  nextCursor?: string | null;
};

export type FeedParams = {
  mode?: FeedMode;
  cursor?: string | null;
  limit?: number;
};

export type CreatorOption = {
  type: WorkPostAuthorKind;
  id: number;
  name: string;
};

export type CreatorExperienceOption = {
  id: number;
  title: string;
  authorType: WorkPostAuthorKind;
  authorId: number;
};

export type CreatorOptions = {
  authors: CreatorOption[];
  experiences: CreatorExperienceOption[];
};

export type CreatePostPayload = {
  authorType: WorkPostAuthorKind;
  authorId?: number | null;
  image: UploadableImage;
  caption?: string;
  experienceId?: number | null;
  status?: Extract<
    WorkPostStatus,
    "draft" | "published"
  >;
  focusX?: number;
  focusY?: number;
};

export type UpdatePostPayload = {
  caption?: string | null;
  experienceId?: number | null;
  status?: WorkPostStatus;
  focusX?: number;
  focusY?: number;
};

export type CreatePostResponse = {
  post: WorkPost;
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
    return await request(
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

    return request(
      token,
    );
  }
}


function postFormData(
  payload: CreatePostPayload,
) {
  const form =
    new FormData();

  form.append(
    "file",
    {
      uri:
        payload.image.uri,
      name:
        payload.image.name,
      type:
        payload.image.type,
    } as unknown as Blob,
  );

  form.append(
    "authorType",
    payload.authorType,
  );

  if (
    payload.authorId !==
      undefined &&
    payload.authorId !==
      null
  ) {
    form.append(
      "authorId",
      String(
        payload.authorId,
      ),
    );
  }

  if (
    payload.caption?.trim()
  ) {
    form.append(
      "caption",
      payload.caption.trim(),
    );
  }

  if (
    payload.experienceId !==
      undefined &&
    payload.experienceId !==
      null
  ) {
    form.append(
      "experienceId",
      String(
        payload.experienceId,
      ),
    );
  }

  form.append(
    "status",
    payload.status ??
      "published",
  );

  form.append(
    "focusX",
    String(
      payload.focusX ?? 50,
    ),
  );

  form.append(
    "focusY",
    String(
      payload.focusY ?? 50,
    ),
  );

  return form;
}


export async function getFeed(
  params: FeedParams = {},
) {
  const query =
    buildFeedQuery(params);

  if (
    params.mode ===
    "following"
  ) {
    return withAuthenticatedRequest(
      (token) =>
        api.get<FeedResponse>(
          `/api/v1/feed?${query}`,
          { token },
        ),
    );
  }

  return api.get<FeedResponse>(
    `/api/v1/feed?${query}`,
  );
}


export async function getPost(
  postId: string,
) {
  return api.get<WorkPost>(
    `/api/v1/posts/${postId}`,
  );
}


export async function getCreatorOptions() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<CreatorOptions>(
        "/api/v1/posts/options",
        { token },
      ),
  );
}


export async function getMyPosts() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<{
        items: WorkPost[];
      }>(
        "/api/v1/posts/mine",
        { token },
      ),
  );
}


export async function createPost(
  payload: CreatePostPayload,
) {
  const form =
    postFormData(
      payload,
    );

  return withAuthenticatedRequest(
    (token) =>
      api.post<CreatePostResponse>(
        "/api/v1/posts",
        form,
        { token },
      ),
  );
}


export async function updatePost(
  postId: string,
  payload: UpdatePostPayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<CreatePostResponse>(
        `/api/v1/posts/${postId}`,
        payload,
        { token },
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
        `/api/v1/posts/${postId}`,
        { token },
      ),
  );
}


export async function favoritePost(
  postId: string,
) {
  const targetId =
    Number(postId);

  if (
    !Number.isInteger(
      targetId,
    ) ||
    targetId <= 0
  ) {
    throw new Error(
      "Publicação inválida.",
    );
  }

  const response =
    await saveGraphTarget(
      "work_post",
      targetId,
    );

  return {
    favorited:
      response.saved,
  };
}


export async function unfavoritePost(
  postId: string,
) {
  const targetId =
    Number(postId);

  if (
    !Number.isInteger(
      targetId,
    ) ||
    targetId <= 0
  ) {
    throw new Error(
      "Publicação inválida.",
    );
  }

  const response =
    await unsaveGraphTarget(
      "work_post",
      targetId,
    );

  return {
    favorited:
      response.saved,
  };
}
