"use client";

import Link from "next/link";
import { ReviewerLayout } from "@/components/ReviewerLayout";

const actionCards = [
  {
    href: "/reviewer/novels",
    title: "待审核作品",
    description: "查看作者提交的作品，领取后进行通过或驳回。",
  },
  {
    href: "/reviewer/novels/reviewing",
    title: "我的作品审核",
    description: "继续处理已领取但尚未完成的作品审核任务。",
  },
  {
    href: "/reviewer/chapters",
    title: "待审核章节",
    description: "检查章节正文、字数和发布状态，完成内容审核。",
  },
  {
    href: "/reviewer/chapters/reviewing",
    title: "我的章节审核",
    description: "继续处理已领取但尚未完成的章节审核任务。",
  },
  {
    href: "/reviewer/audit-logs",
    title: "审核记录",
    description: "查看提交、领取、通过、驳回等审核流转历史。",
  },
];

export default function ReviewerHomePage() {
  return (
    <ReviewerLayout title="审核中心" description="处理作品和章节的内容审核任务。">
      <div className="grid gap-3 md:grid-cols-3">
        {actionCards.map((item) => (
          <Link key={item.href} href={item.href} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm hover:border-emerald-200">
            <h2 className="text-base font-semibold text-zinc-900">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-500">{item.description}</p>
          </Link>
        ))}
      </div>
    </ReviewerLayout>
  );
}
