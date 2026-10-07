import {
  api,
  ApiError,
} from "@/api/client";
import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

export type MembershipStatus =
  | "pending"
  | "active"
  | "rejected"
  | "inactive";

export type TeamMembership = {
  id: string;
  status: MembershipStatus;
  roleName?: string | null;
  isPrimary: boolean;
  startedAt?: string | null;
  endedAt?: string | null;
  professional: {
    id: string;
    routeId: string;
    name: string;
    specialty?: string | null;
    avatar?: string | null;
  };
  establishment: {
    id: string;
    routeId: string;
    name: string;
    city?: string | null;
    state?: string | null;
    logo?: string | null;
  };
};

export type TeamResponse = {
  establishment: {
    id: string;
    routeId: string;
    name: string;
  };
  accessRole: "owner" | "manager";
  items: TeamMembership[];
};

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

    return request(token);
  }
}

export function getTeamInvitations() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<{
        items: TeamMembership[];
      }>(
        "/api/v1/team/invitations",
        { token },
      ),
  );
}

export function acceptTeamInvitation(
  membershipId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        membership: TeamMembership;
      }>(
        `/api/v1/team/invitations/${membershipId}/accept`,
        undefined,
        { token },
      ),
  );
}

export function rejectTeamInvitation(
  membershipId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        membership: TeamMembership;
      }>(
        `/api/v1/team/invitations/${membershipId}/reject`,
        undefined,
        { token },
      ),
  );
}

export function getManagedEstablishmentTeam(
  establishmentId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.get<TeamResponse>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/team`,
        { token },
      ),
  );
}

export function inviteProfessionalToTeam(
  establishmentId: string,
  payload: {
    email: string;
    roleName?: string;
  },
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        membership: TeamMembership;
      }>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/team`,
        payload,
        { token },
      ),
  );
}

export function removeProfessionalFromTeam(
  establishmentId: string,
  membershipId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        membership: TeamMembership;
        removed: boolean;
      }>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/team/${membershipId}`,
        { token },
      ),
  );
}
