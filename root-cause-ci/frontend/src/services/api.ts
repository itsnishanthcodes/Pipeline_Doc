import type { HealthResponse } from '../types/health';

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${baseUrl}/health`);
  if (!response.ok) {
    throw new Error(`Health request failed with status ${response.status}`);
  }
  return response.json() as Promise<HealthResponse>;
}
