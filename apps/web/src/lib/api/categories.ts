import { apiRequest } from "@/lib/api/request";
import type { Category } from "@/types/category";

export function getCategories(): Promise<Category[]> {
  return apiRequest<Category[]>("/categories/", {
    auth: false,
  });
}
