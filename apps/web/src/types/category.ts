export type Category = {
  id: number;
  name: string;
  slug: string;
  parent: number | null;
  sort_order: number;
};

export type CategorySummary = Pick<Category, "id" | "name" | "slug">;
