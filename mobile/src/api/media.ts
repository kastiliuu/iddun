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


async function imageFormData(
  image: UploadableImage,
  extras: Record<
    string,
    string | number | undefined
  > = {},
): Promise<FormData> {
  // Expo's fetch rejects a React Native { uri, name, type } object
  // masquerading as Blob. Read the normalized file as a real Blob.
  const fileResponse = await fetch(image.uri);

  if (!fileResponse.ok) {
    throw new Error("Não foi possível ler a imagem selecionada.");
  }

  const blob = await fileResponse.blob();

  if (!blob.size) {
    throw new Error("A imagem selecionada está vazia.");
  }

  const form = new FormData();
  form.append("file", blob, image.name);

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
  return withAuthenticatedRequest(
    async (token) => {
      const body = await imageFormData(image, {
        focusX: focus.x,
        focusY: focus.y,
      });
      return api.post<{
        avatar: ProfessionalMediaImage;
        completion: MediaCompletion;
      }>(
        "/api/v1/media/professional/avatar",
        body,
        { token },
      );
    },
  );
}


export function uploadProfessionalCover(
  image: UploadableImage,
  focus: {
    x?: number;
    y?: number;
  } = {},
) {
  return withAuthenticatedRequest(
    async (token) => {
      const body = await imageFormData(image, {
        focusX: focus.x,
        focusY: focus.y,
      });
      return api.post<{
        cover: ProfessionalMediaImage;
        completion: MediaCompletion;
      }>(
        "/api/v1/media/professional/cover",
        body,
        { token },
      );
    },
  );
}


export function uploadProfessionalPortfolioItem(
  image: UploadableImage,
  caption?: string,
) {
  return withAuthenticatedRequest(
    async (token) => {
      const body = await imageFormData(image, {
        caption:
          caption?.trim() ||
          undefined,
      });
      return api.post<{
        item: ProfessionalPortfolioMedia;
        completion: MediaCompletion;
      }>(
        "/api/v1/media/professional/portfolio",
        body,
        { token },
      );
    },
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
