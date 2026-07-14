import { marked } from "marked";
import DOMPurify from "dompurify";

export function renderSafeMarkdown(source: string): string {
  const raw = marked.parse(source) as string;
  return DOMPurify.sanitize(raw);
}
