import {
  api,
  ApiError,
} from "@/api/client";
import {
  getAccessToken,
  refreshSession,
} from "@/api/auth";

export type JobStatus =
  | "draft"
  | "published"
  | "closed";

export type JobApplicationStatus =
  | "submitted"
  | "withdrawn";

export type JobPost = {
  id: string;
  title: string;
  specialty?: string | null;
  description?: string;
  city?: string | null;
  state?: string | null;
  neighborhood?: string | null;
  employmentType?: string | null;
  compensationText?: string | null;
  status: JobStatus;
  publishedAt?: string | null;
  closedAt?: string | null;
  createdAt: string;
  applicationsCount?: number;
  establishment: {
    id: string;
    routeId: string;
    name: string;
    logo?: string | null;
    city?: string | null;
    state?: string | null;
    neighborhood?: string | null;
  };
};

export type JobApplication = {
  id: string;
  status: JobApplicationStatus;
  message?: string | null;
  createdAt: string;
  job: JobPost;
  professional?: {
    id: string;
    routeId: string;
    name: string;
    specialty?: string | null;
    avatar?: string | null;
    city?: string | null;
    state?: string | null;
  };
};

export type JobsResponse = {
  items: JobPost[];
  pagination: {
    offset: number;
    limit: number;
    total: number;
    nextOffset: number | null;
    hasMore: boolean;
  };
};

export type ManagedJobsResponse = {
  establishment: {
    id: string;
    routeId: string;
    name: string;
  };
  accessRole:
    | "owner"
    | "manager";
  items: JobPost[];
};

export type CreateJobPayload = {
  title: string;
  specialty?: string;
  description: string;
  city?: string;
  state?: string;
  neighborhood?: string;
  employmentType?: string;
  compensationText?: string;
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

    token =
      await refreshSession();

    return operation(
      token,
    );
  }
}

export function getJobs(
  params: {
    query?: string;
    city?: string;
    specialty?: string;
    offset?: number;
    limit?: number;
  } = {},
  signal?: AbortSignal,
) {
  const query =
    new URLSearchParams();

  if (params.query?.trim()) {
    query.set(
      "q",
      params.query.trim(),
    );
  }

  if (params.city?.trim()) {
    query.set(
      "city",
      params.city.trim(),
    );
  }

  if (
    params.specialty?.trim()
  ) {
    query.set(
      "specialty",
      params.specialty.trim(),
    );
  }

  query.set(
    "offset",
    String(
      params.offset ?? 0,
    ),
  );
  query.set(
    "limit",
    String(
      params.limit ?? 20,
    ),
  );

  return api.get<JobsResponse>(
    `/api/v1/jobs?${query.toString()}`,
    { signal },
  );
}

export function getJob(
  jobId: string,
) {
  return api.get<{
    job: JobPost;
  }>(
    `/api/v1/jobs/${jobId}`,
  );
}

export function applyToJob(
  jobId: string,
  message?: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        application:
          JobApplication;
      }>(
        `/api/v1/jobs/${jobId}/apply`,
        { message },
        { token },
      ),
  );
}

export function withdrawJobApplication(
  jobId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.delete<{
        application:
          JobApplication;
        withdrawn: boolean;
      }>(
        `/api/v1/jobs/${jobId}/apply`,
        { token },
      ),
  );
}

export function getMyJobApplications() {
  return withAuthenticatedRequest(
    (token) =>
      api.get<{
        items:
          JobApplication[];
      }>(
        "/api/v1/jobs/applications/mine",
        { token },
      ),
  );
}

export function getManagedJobs(
  establishmentId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.get<ManagedJobsResponse>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/jobs`,
        { token },
      ),
  );
}

export function createJob(
  establishmentId: string,
  payload: CreateJobPayload,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.post<{
        job: JobPost;
      }>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/jobs`,
        payload,
        { token },
      ),
  );
}

export function updateJob(
  establishmentId: string,
  jobId: string,
  payload: Partial<
    CreateJobPayload
  >,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        job: JobPost;
      }>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/jobs/${jobId}`,
        payload,
        { token },
      ),
  );
}

export function publishJob(
  establishmentId: string,
  jobId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        job: JobPost;
      }>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/jobs/${jobId}/publish`,
        undefined,
        { token },
      ),
  );
}

export function closeJob(
  establishmentId: string,
  jobId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.put<{
        job: JobPost;
      }>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/jobs/${jobId}/close`,
        undefined,
        { token },
      ),
  );
}

export function getJobApplications(
  establishmentId: string,
  jobId: string,
) {
  return withAuthenticatedRequest(
    (token) =>
      api.get<{
        job: JobPost;
        items:
          JobApplication[];
      }>(
        `/api/v1/establishments/${encodeURIComponent(establishmentId)}/jobs/${jobId}/applications`,
        { token },
      ),
  );
}
