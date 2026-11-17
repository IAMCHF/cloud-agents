import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

const candidates = [
  path.join(root, "control-plane", ".venv", "Scripts", "python.exe"),
  path.join(root, "control-plane", ".venv", "bin", "python"),
];
const python = candidates.find((candidate) => existsSync(candidate)) ?? "python";

const child = spawn(python, [path.join(root, "control-plane", "tests", "e2e", "mock_stack.py")], {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env },
});

for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => child.kill(signal));
}
child.on("exit", (code) => {
  process.exit(code ?? 0);
});
