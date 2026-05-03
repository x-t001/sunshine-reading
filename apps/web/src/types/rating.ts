export type MyRating = {
  score: number;
  comment: string;
};

export type RatingSummary = {
  novel_id: number;
  rating_score: number;
  rating_count: number;
  my_rating: MyRating | null;
};

export type SubmitRatingPayload = {
  score: number;
  comment?: string;
};
