import { apiRequest } from "@/lib/api/request";
import type { RankingType } from "@/types/ranking";

export function getRankings(): Promise<RankingType[]> {
  return apiRequest<RankingType[]>("/rankings/");
}
