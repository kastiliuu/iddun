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

export type ProfessionalOnboardingProfile = {
  id: string;
  slug: string;
  displayName: string;
  primarySpecialty?: string | null;
  categories: string[];
  bio: string;
  phone: string;
  city: string;
  state: string;
  avatarUrl?: string | null;
  coverUrl?: string | null;
  portfolioCount: number;
  isActive: boolean;
  onboardingCompleted: boolean;
  publishedAt?: string | null;
  completion: ProfessionalCompletion;
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
  city: string;
  state: string;
  bio?: string;
  phone?: string;
};

export type EstablishmentDraftPayload = {
  name: string;
  category: string;
  city: string;
  state: string;
  description?: string;
  phone?: string;
  neighborhood?: string;
};

export type EstablishmentDraftResponse = {
  establishment: {
    id: string;
    slug: string;
    name: string;
    category?: string | null;
    description: string;
    phone: string;
    neighborhood: string;
    city: string;
    state: string;
    isActive: boolean;
    onboardingCompleted: boolean;
    profileCompletion: number;
  };
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
      api.post<ProfessionalOnboardingResponse>(
        "/api/v1/onboarding/professional/publish",
        undefined,
        { token },
      ),
  );
}
