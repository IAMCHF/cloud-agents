import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("渲染工作区标题", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Cloud Agents" })).toBeInTheDocument();
  });
});
