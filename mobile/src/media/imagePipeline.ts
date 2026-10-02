import {
  CameraType,
  launchCameraAsync,
  launchImageLibraryAsync,
  requestCameraPermissionsAsync,
  requestMediaLibraryPermissionsAsync,
  UIImagePickerPreferredAssetRepresentationMode,
  type ImagePickerAsset,
} from "expo-image-picker";

import {
  ImageManipulator,
  SaveFormat,
} from "expo-image-manipulator";

import type {
  UploadableImage,
} from "@/api/media";


export type MediaKind =
  | "avatar"
  | "cover"
  | "portfolio";

export type MediaSource =
  | "camera"
  | "library";

export class MediaPermissionError
  extends Error {
  constructor(message: string) {
    super(message);
    this.name =
      "MediaPermissionError";
  }
}


const MAX_SIDE_BY_KIND:
  Record<MediaKind, number> = {
    avatar: 1400,
    cover: 2200,
    portfolio: 2000,
  };

const QUALITY_BY_KIND:
  Record<MediaKind, number> = {
    avatar: 0.88,
    cover: 0.84,
    portfolio: 0.86,
  };


async function ensurePermission(
  source: MediaSource,
) {
  const permission =
    source === "camera"
      ? await requestCameraPermissionsAsync()
      : await requestMediaLibraryPermissionsAsync();

  if (!permission.granted) {
    throw new MediaPermissionError(
      source === "camera"
        ? (
          "Autorize o acesso à câmera "
          + "para fotografar seu trabalho."
        )
        : (
          "Autorize o acesso às fotos "
          + "para escolher uma imagem."
        ),
    );
  }
}


async function selectAsset(
  source: MediaSource,
  kind: MediaKind,
) {
  await ensurePermission(
    source,
  );

  const allowsEditing =
    kind === "avatar";

  const options = {
    mediaTypes:
      ["images"] as const,
    allowsEditing,
    aspect:
      kind === "avatar"
        ? [1, 1] as [number, number]
        : undefined,
    quality: 1,
    exif: false,
    base64: false,
    preferredAssetRepresentationMode:
      UIImagePickerPreferredAssetRepresentationMode.Compatible,
  };

  const result =
    source === "camera"
      ? await launchCameraAsync({
          ...options,
          cameraType:
            CameraType.back,
        })
      : await launchImageLibraryAsync(
          options,
        );

  if (
    result.canceled ||
    !result.assets?.length
  ) {
    return null;
  }

  return result.assets[0];
}


function resizeTarget(
  asset: ImagePickerAsset,
  maxSide: number,
) {
  if (
    asset.width <= 0 ||
    asset.height <= 0
  ) {
    return null;
  }

  const largestSide =
    Math.max(
      asset.width,
      asset.height,
    );

  if (
    largestSide <= maxSide
  ) {
    return null;
  }

  return asset.width >=
    asset.height
    ? {
        width: maxSide,
      }
    : {
        height: maxSide,
      };
}


async function normalizeAsset(
  asset: ImagePickerAsset,
  kind: MediaKind,
): Promise<UploadableImage> {
  const context =
    ImageManipulator.manipulate(
      asset.uri,
    );

  const resize =
    resizeTarget(
      asset,
      MAX_SIDE_BY_KIND[
        kind
      ],
    );

  if (resize) {
    context.resize(
      resize,
    );
  }

  const image =
    await context.renderAsync();

  try {
    const result =
      await image.saveAsync({
        compress:
          QUALITY_BY_KIND[
            kind
          ],
        format:
          SaveFormat.JPEG,
      });

    return {
      uri: result.uri,
      name:
        (
          "iddun-"
          + kind
          + "-"
          + Date.now()
          + ".jpg"
        ),
      type:
        "image/jpeg",
    };
  } finally {
    image.release();
    context.release();
  }
}


export async function pickAndPrepareImage(
  source: MediaSource,
  kind: MediaKind,
) {
  const asset =
    await selectAsset(
      source,
      kind,
    );

  if (!asset) {
    return null;
  }

  return normalizeAsset(
    asset,
    kind,
  );
}
