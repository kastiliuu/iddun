import {
  api,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

import { imageFormData, type UploadableImage } from "@/api/media";

/*
 * Serviços do profissional no app (rotas /api/v1/onboarding/professional/...).
 * As funções antigas que chamavam /api/services, rota que não existe no
 * backend e que nenhuma tela usava, foram removidas na V1 PR 3.
 */

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

  return request(token);
}

export type ManagedService = {
  id: number;
  title: string;
  category: string;
  status: "draft" | "published" | "paused" | "archived";
  price: number;
  durationMinutes: number;
  establishmentId: number | null;
};

export type ManagedServicesResponse = {
  items: ManagedService[];
};

export function getManagedServices() {
  return withAuthenticatedRequest((token) =>
    api.get<ManagedServicesResponse>(
      "/api/v1/onboarding/professional/services",
      { token },
    ),
  );
}

export type ServiceDraftInput = {
  establishmentId?: number | null;
  name: string;
  category: string;
  shortDescription: string;
  description?: string;
  price: number;
  regularPrice: number;
  durationMinutes: number;
};

export type ServiceDraftResult = {
  service: ManagedService;
};

export function createProfessionalServiceDraft(payload: ServiceDraftInput) {
  return withAuthenticatedRequest((token) =>
    api.post<ServiceDraftResult>(
      "/api/v1/onboarding/professional/services",
      payload,
      { token },
    ),
  );
}

export type ProfessionalServiceDetail = ServiceDraftInput & {
  id: number;
  status: ManagedService["status"];
  establishmentId: number | null;
  imageUrl?: string | null;
};

export function getProfessionalServiceDetail(id: number) {
  return withAuthenticatedRequest((token) =>
    api.get<{ service: ProfessionalServiceDetail }>(
      `/api/v1/onboarding/professional/services/${id}`, { token },
    ),
  );
}

export function updateProfessionalServiceDraft(id: number, payload: Partial<ServiceDraftInput>) {
  return withAuthenticatedRequest((token) =>
    api.patch<ServiceDraftResult>(
      `/api/v1/onboarding/professional/services/${id}`,
      payload,
      { token },
    ),
  );
}

export function changeProfessionalServiceStatus(id: number, action: "publish" | "pause") {
  return withAuthenticatedRequest((token) =>
    api.post<{ service: ManagedService }>(
      `/api/v1/onboarding/professional/services/${id}/status`,
      { action },
      { token },
    ),
  );
}

export type ServiceEstablishment = { id: number; name: string };

export function getProfessionalServiceEstablishments() {
  return withAuthenticatedRequest((token) =>
    api.get<{ items: ServiceEstablishment[] }>(
      "/api/v1/onboarding/professional/service-establishments",
      { token },
    ),
  );
}

export type ManagedAvailabilitySlot = {
  id: number;
  startsAt: string;
  endsAt: string;
  status: string;
};

export function getProfessionalServiceAvailability(serviceId: number) {
  return withAuthenticatedRequest((token) =>
    api.get<{ items: ManagedAvailabilitySlot[] }>(
      `/api/v1/onboarding/professional/services/${serviceId}/availability`,
      { token },
    ),
  );
}

export function createProfessionalServiceAvailability(
  serviceId: number,
  payload: { date: string; time: string },
) {
  return withAuthenticatedRequest((token) =>
    api.post<{ items: ManagedAvailabilitySlot[] }>(
      `/api/v1/onboarding/professional/services/${serviceId}/availability`,
      payload,
      { token },
    ),
  );
}

export function changeProfessionalSlotStatus(
  serviceId: number, slotId: number, action: "block" | "reopen",
) {
  return withAuthenticatedRequest((token) =>
    api.post<{ slot: ManagedAvailabilitySlot }>(
      `/api/v1/onboarding/professional/services/${serviceId}/availability/${slotId}/status`,
      { action }, { token },
    ),
  );
}

export function createProfessionalSlotsFromSchedule(serviceId: number, date: string) {
  return withAuthenticatedRequest((token) =>
    api.post<{ createdCount: number }>(
      `/api/v1/onboarding/professional/services/${serviceId}/availability/from-schedule`,
      { date }, { token },
    ),
  );
}

// V1-CONV-D06: vários horários num dia, tudo ou nada (mesmas regras da Web).
export function createProfessionalSlotsBatch(serviceId: number, date: string, times: string[]) {
  return withAuthenticatedRequest((token) =>
    api.post<{ createdCount: number }>(
      `/api/v1/onboarding/professional/services/${serviceId}/availability/batch`,
      { date, times }, { token },
    ),
  );
}

// V1-CONV-D06: foto do serviço (rascunho ou pausado; JPG, PNG ou WEBP até 5 MB).
export function uploadProfessionalServiceImage(serviceId: number, image: UploadableImage) {
  return withAuthenticatedRequest(async (token) => {
    const body = await imageFormData(image);
    return api.post<{ imageUrl: string }>(
      `/api/v1/onboarding/professional/services/${serviceId}/image`,
      body, { token },
    );
  });
}

export type WeeklyScheduleDay = {
  weekday: number;
  label: string;
  enabled: boolean;
  start: string;
  end: string;
  break_enabled: boolean;
  break_start: string;
  break_end: string;
};

export function getProfessionalWeeklySchedule() {
  return withAuthenticatedRequest((token) =>
    api.get<{ days: WeeklyScheduleDay[] }>(
      "/api/v1/onboarding/professional/weekly-schedule", { token },
    ),
  );
}

export function updateProfessionalWeeklySchedule(days: WeeklyScheduleDay[]) {
  return withAuthenticatedRequest((token) =>
    api.put<{ days: WeeklyScheduleDay[] }>(
      "/api/v1/onboarding/professional/weekly-schedule", { days }, { token },
    ),
  );
}
