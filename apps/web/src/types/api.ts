export type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
};

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
