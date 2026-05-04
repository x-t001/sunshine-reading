export type UserBasic = {
  id: number;
  username: string;
  nickname: string;
  email: string;
  role: "reader" | "author" | "reviewer" | "admin";
  is_staff?: boolean;
  is_superuser?: boolean;
};

export type CurrentUser = UserBasic & {
  avatar: string;
  bio: string;
  phone: string;
};

export type UpdateCurrentUserPayload = Partial<Pick<CurrentUser, "nickname" | "avatar" | "bio" | "phone" | "email">>;
