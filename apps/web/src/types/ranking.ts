import type { NovelListItem } from "@/types/novel";

export type RankingItem = {
  rank: number;
  score: string;
  calculated_at: string;
  novel: NovelListItem;
};

export type RankingType = {
  id: number;
  name: string;
  code: string;
  description: string;
  items: RankingItem[];
};
