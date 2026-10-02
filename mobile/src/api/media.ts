import {
  api,
  ApiError,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";


export type UploadableImage = {
  uri: string;
  name: string;
  type: "image/jpeg" | "image/png" | "image/webp";
};

export type ProfessionalMediaImage = {
  storedPath: string;
  url: string;
  focusX?: number | null;
  focusY?: number | null;
};

export type ProfessionalPortfolioMedia = {
  id: number;
  imageUrl: string;
  storedPath?: string;
  caption?: string | null;
  sortOrder: number;
};

export type MediaCompletion = {
  percentage: number;
  readyToPublish: boolean;
  portfolioCount: number;
  isActive: boolean;
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

    const refreshedToken =
      await refreshSession();

    return operation(
      refreshedToken,
    );
  }
}


function imageFormData(
  image: UploadableImage,
  extras: Record<
    string,
    string | number | undefined
  > = {},
) {
  const form =
    new FormData();

  form.append(
    "file",
    {
      uri: image.uri,
      name: image.name,
      type: image.type,
    } as unknown as Blob,
  );

  for (
    const [
      key,
      value,
    ] of Object.entries(
      extras,
    )
  ) {
    if (
      value === undefined
    ) {
      continue;
    }

    form.append(
      key,
      String(value),
    );
  }

  return form;
}


export function uploadProfessionalAvatar(
  image: UploadableImage,
  focus: {
    x?: number;
    y?: number;
  } = {},
) {
  const body =
    imageFormData(
      image,
      {
        focusX: focus.x,
        focusY: focus.y,
      },
    );

  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        avatar: ProfessionalMediaImage;
        completion: MediaCompletion;
      }>(
        "/api/v1/media/professional/avatar",
        body,
        { token },
      ),
  );
}


export function uploadProfessionalCover(
  image: UploadableImage,
  focus: {
    x?: number;
    y?: number;
  } = {},
) {
  const body =
    imageFormData(
      image,
      {
        focusX: focus.x,
        focusY: focus.y,
      },
    );

  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        cover: ProfessionalMediaImage;
        completion: MediaCompletion;
      }>(
        "/api/v1/media/professional/cover",
        body,
        { token },
      ),
  );
}


export function uploadProfessionalPortfolioItem(
  image: UploadableImage,
  caption?: string,
) {
  const body =
    imageFormData(
      image,
      {
        caption:
          caption?.trim() ||
          undefined,
      },
    );

  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        item: ProfessionalPortfolioMedia;
        completion: MediaCompletion;
      }>(
        "/api/v1/media/professional/portfolio",
        body,
        { token },
      ),
  );
}


export function deleteProfessionalPortfolioItem(
  itemId: number,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        completion: MediaCompletion;
        portfolio: ProfessionalPortfolioMedia[];
      }>(
        (
          "/api/v1/media/professional/portfolio/"
          + itemId
        ),
        { token },
      ),
  );
}


export function reorderProfessionalPortfolio(
  itemIds: number[],
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        portfolio: ProfessionalPortfolioMedia[];
      }>(
        "/api/v1/media/professional/portfolio/order",
        {
          itemIds,
        },
        { token },
      ),
  );
}


export function updateProfessionalCoverFocus(
  focusX: number,
  focusY: number,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        focusX: number;
        focusY: number;
      }>(
        "/api/v1/media/professional/cover/focus",
        {
          focusX,
          focusY,
        },
        { token },
      ),
  );
}
