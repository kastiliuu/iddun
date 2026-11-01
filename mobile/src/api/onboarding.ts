import {
  api,
  ApiError,
} from "@/api/client";

import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

export type CompletionStep = {
  key: string;
  label: string;
  complete: boolean;
};

export type RecommendedAction = {
  key: string;
  label: string;
};

export type ProfessionalCompletion = {
  percentage: number;
  readyToPublish: boolean;
  steps: CompletionStep[];
  recommendedActions: RecommendedAction[];
};

export type ProfessionalExperience = {
  id: number;
  companyName: string;
  roleTitle: string;
  description?: string | null;
  startedAt: string;
  endedAt?: string | null;
  isCurrent: boolean;
  verified: boolean;
  verificationStatus: string;
  establishment?: {
    id: number;
    slug: string;
    name: string;
  } | null;
};

export type ProfessionalPortfolioItem = {
  id: number;
  imageUrl: string;
  caption?: string | null;
  sortOrder: number;
};

export type ProfessionalMembership = {
  id: number;
  status: string;
  isPrimary: boolean;
  roleName?: string | null;
  establishment: {
    id: number;
    slug: string;
    name: string;
  };
};

// Etapas e estados do onboarding (backend: app/services/onboarding_steps.py).
// Cadastro concluído, perfil 100% e publicado são campos distintos;
// reservável é decidido por serviço e não vem neste objeto.
export type OnboardingStep = {
  key: string;
  label: string;
  required: boolean;
  applicable: boolean;
  complete: boolean;
};

export type MissingRequirement = {
  key: string;
  message: string;
};

export type OnboardingJourney = {
  steps: OnboardingStep[];
  currentStep: string;
  registrationComplete: boolean;
  readyToPublish: boolean;
  profileComplete: boolean;
  profileCompletion: number;
  published: boolean;
  missingRequirements: MissingRequirement[];
};

export type ProfessionalOnboardingProfile = {
  id: string;
  slug: string;
  displayName: string;
  primarySpecialty?: string | null;
  categories: string[];
  attendanceModalities: string[];
  bio: string;
  phone: string;
  headline?: string;
  instagram?: string;
  whatsappEnabled?: boolean;
  visualTheme?: "beauty" | "barber" | "tattoo";
  city: string;
  state: string;
  avatarUrl?: string | null;
  coverUrl?: string | null;
  avatarFocusX: number;
  avatarFocusY: number;
  coverFocusX: number;
  coverFocusY: number;
  portfolioCount: number;
  portfolio: ProfessionalPortfolioItem[];
  isActive: boolean;
  onboardingCompleted: boolean;
  publishedAt?: string | null;
  completion: ProfessionalCompletion;
  journey?: OnboardingJourney;
  experiences: ProfessionalExperience[];
  memberships: ProfessionalMembership[];
};

export type ProfessionalOnboardingResponse = {
  profile: ProfessionalOnboardingProfile | null;
};

export type ProfessionalDraftPayload = {
  displayName: string;
  primarySpecialty: string;
  categories: string[];
  attendanceModalities?: string[];
  city: string;
  state: string;
  bio?: string;
  phone?: string;
};

// Salvamento parcial: chave ausente preserva o valor salvo; null ou ""
// em campo opcional limpa. Nome, tipo, cidade e UF não podem ser limpos.
export type ProfessionalDraftPatch = Partial<{
  displayName: string;
  headline: string | null;
  primarySpecialty: string | null;
  categories: string[] | null;
  city: string | null;
  state: string | null;
  bio: string | null;
  phone: string | null;
  whatsappEnabled: boolean;
  instagram: string | null;
  attendanceModalities: string[] | null;
  visualTheme: "beauty" | "barber" | "tattoo" | null;
}>;

export type BusinessHours = Partial<Record<"monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday", { start: string; end: string }[]>>;

export type EstablishmentDraftPayload = {
  // Id estável devolvido no primeiro salvamento. Sem ele, o servidor só
  // reaproveita um rascunho nunca publicado com o mesmo nome e cidade.
  establishmentId?: string;
  operationMode?: "physical" | "mobile" | "hybrid";
  businessHoursMode?: "scheduled" | "fixed_hours";
  businessHours?: BusinessHours;
  commercialEmail?: string;
  name: string;
  category: string;
  city: string;
  state: string;
  description?: string;
  phone?: string;
  neighborhood?: string;
};

export type EstablishmentDraftPatch = Partial<{
  name: string;
  category: string;
  city: string;
  state: string;
  description: string | null;
  phone: string | null;
  neighborhood: string | null;
  addressLine1: string | null;
  addressLine2: string | null;
  postalCode: string | null;
  commercialEmail: string | null;
  operationMode: "physical" | "mobile" | "hybrid" | null;
  businessHoursMode: "scheduled" | "fixed_hours" | null;
  businessHours: BusinessHours | null;
  whatsappEnabled: boolean;
}>;

export type EstablishmentDraft = {
  id: string;
  slug: string;
  name: string;
  category?: string | null;
  description: string;
  phone: string;
  whatsappEnabled?: boolean;
  neighborhood: string;
  city: string;
  state: string;
  operationMode?: "physical" | "mobile" | "hybrid" | null;
  businessHoursMode?: "scheduled" | "fixed_hours" | null;
  businessHours?: BusinessHours | null;
  addressLine1?: string | null;
  addressLine2?: string | null;
  postalCode?: string | null;
  commercialEmail?: string;
  isActive: boolean;
  onboardingCompleted: boolean;
  publishedAt?: string | null;
  profileCompletion: number;
  journey?: OnboardingJourney;
};

export type EstablishmentDraftResponse = {
  establishment: EstablishmentDraft;
};

export type EstablishmentPublishResponse = EstablishmentDraftResponse & {
  alreadyPublished: boolean;
};

export type ProfessionalExperiencePayload = {
  companyName: string;
  roleTitle: string;
  description?: string;
  startedAt: string;
  endedAt?: string | null;
  isCurrent: boolean;
  establishmentId?: number | null;
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

export function getProfessionalOnboarding() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<ProfessionalOnboardingResponse>(
        "/api/v1/onboarding/professional",
        { token },
      ),
  );
}

export function saveProfessionalDraft(
  payload: ProfessionalDraftPayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<ProfessionalOnboardingResponse>(
        "/api/v1/onboarding/professional",
        payload,
        { token },
      ),
  );
}

export function patchProfessionalDraft(
  changes: ProfessionalDraftPatch,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.patch<ProfessionalOnboardingResponse>(
        "/api/v1/onboarding/professional",
        changes,
        { token },
      ),
  );
}

export function listEstablishmentDrafts() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<{ establishments: EstablishmentDraft[] }>(
        "/api/v1/onboarding/establishments",
        { token },
      ),
  );
}

export function getEstablishmentDraft(
  establishmentId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.get<EstablishmentDraftResponse>(
        `/api/v1/onboarding/establishments/${encodeURIComponent(establishmentId)}`,
        { token },
      ),
  );
}

export function patchEstablishmentDraft(
  establishmentId: string,
  changes: EstablishmentDraftPatch,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.patch<EstablishmentDraftResponse>(
        `/api/v1/onboarding/establishments/${encodeURIComponent(establishmentId)}`,
        changes,
        { token },
      ),
  );
}

export function publishEstablishment(
  establishmentId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<EstablishmentPublishResponse>(
        `/api/v1/onboarding/establishments/${encodeURIComponent(establishmentId)}/publish`,
        undefined,
        { token },
      ),
  );
}

export function saveEstablishmentDraft(
  payload: EstablishmentDraftPayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<EstablishmentDraftResponse>(
        "/api/v1/onboarding/establishment",
        payload,
        { token },
      ),
  );
}

export function addProfessionalExperience(
  payload: ProfessionalExperiencePayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        experience: ProfessionalExperience;
        completion: ProfessionalCompletion;
      }>(
        "/api/v1/onboarding/professional/experiences",
        payload,
        { token },
      ),
  );
}

export function removeProfessionalExperience(
  experienceId: number,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<void>(
        (
          "/api/v1/onboarding/professional/experiences/"
          + experienceId
        ),
        { token },
      ),
  );
}

export function publishProfessionalProfile() {
  return withAuthenticatedRequest(
    (token) =>
      api.post<ProfessionalOnboardingResponse & { alreadyPublished?: boolean }>(
        "/api/v1/onboarding/professional/publish",
        undefined,
        { token },
      ),
  );
}
