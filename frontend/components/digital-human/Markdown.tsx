import type { ReactNode } from "react";

/** Inline styles. Any marker without a partner is removed so no raw symbols show. */
function inline(text: string): ReactNode[] {
  const clean = text
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/~~/g, "");
  return clean.split(/(\*\*[^*]+\*\*|__[^_]+__)/g).map((part, index) => {
    const bold = /^(\*\*|__)(.+)\1$/.exec(part);
    const plain = (bold ? bold[2] : part)
      .replace(/(^|[^\p{L}\p{N}])[*_](?=\S)([^*_]+?)[*_](?![\p{L}\p{N}])/gu, "$1$2")
      .replace(/\*\*|__|`/g, "")
      .replace(/(^|\s)[*#]+(?=\s|$)/g, "$1");
    return bold ? <strong key={index}>{plain}</strong> : plain;
  });
}

type Block =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] };

function parse(content: string): Block[] {
  const lines = content
    .replace(/\\([\\`*_{}[\]()#+\-.!|>~])/g, "$1")
    .replace(/\s+[*•-]\s+(?=\*\*)/g, "\n- ") // bullets the model ran together on one line
    .split(/\r?\n/);
  const blocks: Block[] = [];
  for (const raw of lines) {
    let line = raw.trim().replace(/^>+\s*/, "");
    if (!line || /^```/.test(line) || /^[\s|:\-_*=]{3,}$/.test(line)) continue;
    if (line.startsWith("|")) line = line.split("|").map((cell) => cell.trim()).filter(Boolean).join(" · ");
    const heading = /^#{1,6}\s*(.+)$/.exec(line);
    const item = /^([-*+•–]|\d{1,3}[.)])\s+(.+)$/.exec(line);
    if (heading) blocks.push({ kind: "heading", text: heading[1] });
    else if (item) {
      const ordered = /^\d/.test(item[1]);
      const last = blocks.at(-1);
      if (last?.kind === "list" && last.ordered === ordered) last.items.push(item[2]);
      else blocks.push({ kind: "list", ordered, items: [item[2]] });
    } else blocks.push({ kind: "paragraph", text: line });
  }
  return blocks;
}

export function Markdown({ content }: { content: string }) {
  return <div className="answer-content">
    {parse(content).map((block, index) => {
      if (block.kind === "heading") return <h3 key={index}>{inline(block.text)}</h3>;
      if (block.kind === "paragraph") return <p key={index}>{inline(block.text)}</p>;
      const List = block.ordered ? "ol" : "ul";
      return <List key={index}>{block.items.map((item, position) => <li key={position}>{inline(item)}</li>)}</List>;
    })}
  </div>;
}
