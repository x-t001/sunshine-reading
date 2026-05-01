import { ChapterContent, ChapterPreview } from "@/types/novel";

export const chapterPreviews: ChapterPreview[] = [
  { id: "ch1", novelId: "n1", chapterNo: 1, title: "第1章 雨夜来信", updatedAt: "2026-04-20" },
  { id: "ch2", novelId: "n1", chapterNo: 2, title: "第2章 旧楼灯影", updatedAt: "2026-04-21" },
  { id: "ch3", novelId: "n1", chapterNo: 3, title: "第3章 城市边界", updatedAt: "2026-04-23" },
  { id: "ch4", novelId: "n2", chapterNo: 1, title: "第1章 初雪", updatedAt: "2026-04-15" },
  { id: "ch5", novelId: "n2", chapterNo: 2, title: "第2章 归途", updatedAt: "2026-04-18" },
  { id: "ch6", novelId: "n3", chapterNo: 1, title: "第1章 星门开启", updatedAt: "2026-04-26" },
];

export const chapterContents: ChapterContent[] = [
  {
    chapterId: "ch1",
    novelId: "n1",
    title: "第1章 雨夜来信",
    content:
      "夜雨落在旧城区的铁皮屋檐上，发出密集而沉闷的声响。\n\n顾言撑着伞站在街角，手里那封没有署名的信早已被雨水浸出褶皱。\n\n信里只有一句话：如果你想知道父亲离开的真相，今晚十点来北港旧楼。",
  },
  {
    chapterId: "ch2",
    novelId: "n1",
    title: "第2章 旧楼灯影",
    content:
      "北港旧楼的电梯停在十三层，门缝里透出昏黄灯光。\n\n顾言按下按钮，电梯却没有任何反应。\n\n楼道尽头，忽然传来一阵鞋跟敲击地面的声音。",
  },
  {
    chapterId: "ch3",
    novelId: "n1",
    title: "第3章 城市边界",
    content:
      "清晨五点，城市边缘的高架桥下已经开始拥堵。\n\n顾言握紧方向盘，脑海里反复回放昨夜看到的监控画面。\n\n那个背影，分明像极了十年前失踪的父亲。",
  },
];
