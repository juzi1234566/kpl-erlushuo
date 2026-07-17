/** 0–999 转汉字数目，作图鉴编目用 */
export function 汉数(n: number): string {
  const 位 = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"];
  if (n < 10) return 位[n];
  if (n < 20) return `十${n % 10 ? 位[n % 10] : ""}`;
  if (n < 100) return `${位[Math.floor(n / 10)]}十${n % 10 ? 位[n % 10] : ""}`;
  return `${位[Math.floor(n / 100)]}百${n % 100 ? 汉数(n % 100) : ""}`;
}
