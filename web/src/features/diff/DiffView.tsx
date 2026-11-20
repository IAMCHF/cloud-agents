/** 只读 CodeMirror 6 diff 视图：按行标记新增/删除/hunk，不解析完整原文。 */

import { EditorState } from "@codemirror/state";
import {
  Decoration,
  type DecorationSet,
  EditorView,
  lineNumbers,
  ViewPlugin,
  type ViewUpdate,
} from "@codemirror/view";
import { useEffect, useRef } from "react";

const diffLineHighlighter = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;

    constructor(view: EditorView) {
      this.decorations = buildDecorations(view);
    }

    update(update: ViewUpdate): void {
      if (update.docChanged) {
        this.decorations = buildDecorations(update.view);
      }
    }
  },
  { decorations: (plugin) => plugin.decorations },
);

const diffTheme = EditorView.theme({
  "&": {
    height: "100%",
    backgroundColor: "transparent",
    color: "var(--color-foreground)",
  },
  ".cm-scroller": {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
    fontSize: "12px",
    lineHeight: "1.55",
    overflow: "auto",
  },
  ".cm-content": { padding: "8px 0" },
  ".cm-gutters": {
    backgroundColor: "transparent",
    color: "var(--color-muted)",
    border: "none",
  },
});

export function DiffView({ diff }: { diff: string }) {
  const host = useRef<HTMLDivElement | null>(null);
  const view = useRef<EditorView | null>(null);

  useEffect(() => {
    if (host.current === null) {
      return;
    }
    const state = createState(diff);
    if (view.current === null) {
      view.current = new EditorView({ state, parent: host.current });
    } else {
      view.current.setState(state);
    }
    return () => {
      view.current?.destroy();
      view.current = null;
    };
  }, [diff]);

  if (diff.trim() === "") {
    return (
      <p className="p-4 text-xs text-muted">
        本轮暂无文件变更；执行写文件或补丁后在这里显示 diff。
      </p>
    );
  }
  return <div ref={host} className="h-full min-h-0" data-testid="diff-view" />;
}

function createState(diff: string): EditorState {
  return EditorState.create({
    doc: diff,
    extensions: [
      lineNumbers(),
      EditorView.editable.of(false),
      EditorState.readOnly.of(true),
      diffLineHighlighter,
      diffTheme,
    ],
  });
}

function buildDecorations(view: EditorView): DecorationSet {
  const ranges = [];
  for (let number = 1; number <= view.state.doc.lines; number += 1) {
    const line = view.state.doc.line(number);
    let className: string | null = null;
    if (line.text.startsWith("+++") || line.text.startsWith("---")) {
      className = "cm-diff-file";
    } else if (line.text.startsWith("@@")) {
      className = "cm-diff-hunk";
    } else if (line.text.startsWith("+")) {
      className = "cm-diff-added";
    } else if (line.text.startsWith("-")) {
      className = "cm-diff-removed";
    }
    if (className !== null) {
      ranges.push(Decoration.line({ class: className }).range(line.from));
    }
  }
  return Decoration.set(ranges);
}
