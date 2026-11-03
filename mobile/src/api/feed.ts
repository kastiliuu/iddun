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

import {
  imageFormData,
  readImageBlob,
  type UploadableImage,
} from "@/api/media";


export type FeedMode =
  | "for-you"
  | "following";

export type WorkPostAuthorKind =
  | "client"
  | "professional"
  | "establishment";

export type WorkPostStatus =
  | "draft"
  | "published"
  | "archived"
  | "hidden"
  | "removed";

export type WorkPostAuthor = {
  id: string;
  /** Nulo para Cliente, que ainda não tem perfil público (PR 4). */
  routeId: string | null;
  kind: WorkPostAuthorKind;
  name: string;
  avatar?: string | null;
  specialty?: string | null;
  rating?: number | null;
  reviewsCount?: number;
};

export type WorkPostService = {
  id: string;
  name: string;
  price?: number;
  availabilityLabel?: string | null;
  image?: string | null;
  category?: string | null;
};

export type WorkPostMedia = {
  url: string;
  focusX: number;
  focusY: number;
  alt: string;
};

export type WorkPost = {
  id: string;
  authorId: string;
  authorKind: WorkPostAuthorKind;
  author: WorkPostAuthor;
  /** Primeira imagem; nula em publicação só de texto (PR 3). */
  image: string | null;
  /** Carrossel até 10 imagens, na ordem escolhida. */
  media?: WorkPostMedia[];
  likesCount?: number;
  likedByMe?: boolean;
  /** A conta pode remover este post (autoria). */
  mine?: boolean;
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
  canManage?: boolean;
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
  /** Até 10 imagens; nenhuma vale para publicação só de texto. */
  images?: {
    image: UploadableImage;
    alt?: string;
  }[];
  /** Formato antigo, uma imagem. */
  image?: UploadableImage;
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


async function postFormData(
  payload: CreatePostPayload,
) {
  const form = new FormData();
  const images =
    payload.images ??
    (payload.image
      ? [{ image: payload.image }]
      : []);

  for (const item of images) {
    form.append(
      "images",
      await readImageBlob(item.image),
      item.image.name,
    );
    form.append(
      "altTexts",
      item.alt?.trim() ?? "",
    );
  }

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
  const token =
    await getAccessToken();

  return api.get<WorkPost>(
    `/api/v1/posts/${postId}`,
    token
      ? { token }
      : undefined,
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
  return withAuthenticatedRequest(
    async (token) => {
      const form = await postFormData(payload);
      return api.post<CreatePostResponse>(
        "/api/v1/posts",
        form,
        { token },
      );
    },
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


export async function replacePostImage(
  postId: string,
  image: UploadableImage,
  focusX = 50,
  focusY = 50,
) {
  return withAuthenticatedRequest(
    async (token) => {
      const form = await imageFormData(image, {focusX, focusY});
      return api.post<CreatePostResponse>(
        `/api/v1/posts/${postId}/image`,
        form,
        { token },
      );
    },
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


// --------------------------------------------------------------------
// Curtir, comentar e denunciar (PR 3; DEC-ID-035, 229, 231, 275).

export type PostComment = {
  id: string;
  body: string;
  author: {
    name: string;
    avatar?: string | null;
  };
  createdAt: string | null;
  parentId: string | null;
  mine: boolean;
  canDelete: boolean;
  canHide: boolean;
  replies?: PostComment[];
};

export type PostCommentsResponse = {
  items: PostComment[];
  total: number;
  canModerate: boolean;
};

export type ReportCategory =
  | "spam"
  | "sexual"
  | "violence"
  | "harassment"
  | "misinformation"
  | "image_rights"
  | "other";

/** D-SOC-10. */
export const REPORT_CATEGORIES: {
  id: ReportCategory;
  label: string;
}[] = [
  { id: "spam", label: "Spam ou golpe" },
  { id: "sexual", label: "Conteúdo sexual" },
  { id: "violence", label: "Violência ou ódio" },
  { id: "harassment", label: "Assédio ou bullying" },
  { id: "misinformation", label: "Informação falsa" },
  { id: "image_rights", label: "Uso indevido de imagem ou direito autoral" },
  { id: "other", label: "Outro motivo" },
];


export function setPostLike(
  postId: string,
  liked: boolean,
) {
  return withAuthenticatedRequest(
    (token) => {
      const path = `/api/v1/posts/${postId}/like`;
      return liked
        ? api.put<{ liked: boolean; likesCount: number }>(path, {}, { token })
        : api.delete<{ liked: boolean; likesCount: number }>(path, { token });
    },
  );
}


export async function getPostComments(
  postId: string,
) {
  const token =
    await getAccessToken();

  return api.get<PostCommentsResponse>(
    `/api/v1/posts/${postId}/comments`,
    token
      ? { token }
      : undefined,
  );
}


export function addPostComment(
  postId: string,
  body: string,
  parentId?: string | null,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<{ comment: PostComment }>(
        `/api/v1/posts/${postId}/comments`,
        { body, parentId: parentId ?? null },
        { token },
      ),
  );
}


export function deletePostComment(
  commentId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{ success: boolean }>(
        `/api/v1/comments/${commentId}`,
        { token },
      ),
  );
}


export function hidePostComment(
  commentId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<{ success: boolean }>(
        `/api/v1/comments/${commentId}/hide`,
        {},
        { token },
      ),
  );
}


/** Sem protocolo nem confirmação para quem denuncia (DEC-ID-275 B). */
export function reportContent(
  target: "post" | "comment",
  targetId: string,
  category: ReportCategory,
  description?: string,
) {
  const path =
    target === "post"
      ? `/api/v1/posts/${targetId}/report`
      : `/api/v1/comments/${targetId}/report`;

  return withAuthenticatedRequest(
    (token) =>
      api.post<null>(
        path,
        {
          category,
          description: description?.trim() || null,
        },
        { token },
      ),
  );
}
