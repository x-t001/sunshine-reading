export type Category = {
  id: string;
  name: string;
  slug: string;
};

export type ChapterPreview = {
  id: string;
  novelId: string;
  chapterNo: number;
  title: string;
  updatedAt: string;
};

export type Novel = {
  id: string;
  title: string;
  author: string;
  categoryId: string;
  cover: string;
  summary: string;
  status: "ongoing" | "completed";
  wordCount: number;
  updatedAt: string;
  recommend: boolean;
};

export type RankingItem = {
  rank: number;
  novelId: string;
  score: number;
  trend: "up" | "down" | "same";
};

export type ChapterContent = {
  chapterId: string;
  novelId: string;
  title: string;
  content: string;
};
