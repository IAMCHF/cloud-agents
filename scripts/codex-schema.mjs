#!/usr/bin/env node
/**
 * 由 pin 版本 codex 生成 app-server JSON Schema，并生成 TypeScript 类型绑定。
 *
 *   pnpm codex:schema          # 重新生成（schema + TS）
 *   pnpm codex:schema:check    # 漂移校验：与仓库内产物比对，不一致则退出 1
 *
 * 与客户端 yice-agent 的 generate-codex-schema.ps1 同流程（版本校验 + 必需产物校验 + 清理过期文件），
 * 差别是跨平台（Node，CI 可用 Linux 二进制）且不含 PowerShell/Windows 依赖。
 */
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { copyFile, mkdir, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { compile } from "json-schema-to-typescript";

const exec = promisify(execFile);

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const CODEX_BIN = path.join(ROOT, "node_modules", "@openai", "codex", "bin", "codex.js");
const BINDING_DIR = path.join(ROOT, "web", "src", "codex");
const PIN_FILE = path.join(BINDING_DIR, "codex-version.txt");
const SCHEMA_DIR = path.join(BINDING_DIR, "schema");
const GENERATED_DIR = path.join(BINDING_DIR, "generated");

// 三个根 schema：客户端发起的请求、服务端发起的请求（审批等）、服务端通知（事件流）。
const ROOTS = ["ClientRequest", "ServerRequest", "ServerNotification"];
const REQUIRED_SCHEMA_FILES = ROOTS.map((name) => `${name}.json`);

const checkMode = process.argv.includes("--check");

const problems = [];
const fail = (message) => {
  problems.push(message);
  console.error(`✗ ${message}`);
};
const ok = (message) => console.log(`✓ ${message}`);

async function runCodex(args, env) {
  const { stdout } = await exec(process.execPath, [CODEX_BIN, ...args], {
    env,
    cwd: ROOT,
    maxBuffer: 16 * 1024 * 1024,
  });
  return stdout;
}

function banner(pin) {
  return `/**
 * 本文件由 scripts/codex-schema.mjs 自动生成，请勿手改。
 * 来源：codex-cli ${pin} \`app-server generate-json-schema\`。
 * 重新生成：\`pnpm codex:schema\`；漂移校验：\`pnpm codex:schema:check\`。
 */
`;
}

async function generateSchema(pin, stagingDir) {
  const codexHome = path.join(stagingDir, "home");
  const schemaDir = path.join(stagingDir, "schema");
  await mkdir(codexHome, { recursive: true });
  await mkdir(schemaDir, { recursive: true });

  const env = { ...process.env, CODEX_HOME: codexHome };
  const version = (await runCodex(["--version"], env)).trim();
  const expected = `codex-cli ${pin}`;
  if (version !== expected) {
    throw new Error(`codex 版本不符：期望 ${expected}，实际 ${version}。检查 @openai/codex 是否锁在 ${pin}。`);
  }
  ok(`codex 版本 ${version}`);

  await runCodex(["app-server", "generate-json-schema", "--out", schemaDir], env);

  for (const file of REQUIRED_SCHEMA_FILES) {
    if (!existsSync(path.join(schemaDir, file))) {
      throw new Error(`schema 生成缺少必需产物 ${file}`);
    }
  }
  ok(`schema 生成完成（${(await readdir(schemaDir)).length} 个文件）`);
  return schemaDir;
}

async function compareOrWriteSchema(schemaDir) {
  const produced = (await readdir(schemaDir)).filter((name) => name.endsWith(".json")).sort();
  const existing = existsSync(SCHEMA_DIR)
    ? (await readdir(SCHEMA_DIR)).filter((name) => name.endsWith(".json")).sort()
    : [];

  if (checkMode) {
    for (const name of produced) {
      const expected = await readFile(path.join(schemaDir, name));
      const actualPath = path.join(SCHEMA_DIR, name);
      if (!existsSync(actualPath)) {
        fail(`schema 缺少仓库产物 ${name}`);
        continue;
      }
      if (!expected.equals(await readFile(actualPath))) {
        fail(`schema 与 pin 版本不一致：${name}`);
      }
    }
    for (const name of existing) {
      if (!produced.includes(name)) fail(`schema 残留过期产物 ${name}`);
    }
    return;
  }

  await mkdir(SCHEMA_DIR, { recursive: true });
  for (const name of produced) {
    await copyFile(path.join(schemaDir, name), path.join(SCHEMA_DIR, name));
  }
  for (const name of existing) {
    if (!produced.includes(name)) {
      await rm(path.join(SCHEMA_DIR, name));
      console.log(`  清理过期产物 ${name}`);
    }
  }
  ok(`schema 已写入 ${path.relative(ROOT, SCHEMA_DIR)}`);
}

async function generateBindings(pin, schemaDir) {
  const outputs = new Map();
  for (const name of ROOTS) {
    const schema = JSON.parse(await readFile(path.join(schemaDir, `${name}.json`), "utf8"));
    const types = await compile(schema, name, {
      bannerComment: banner(pin),
      additionalProperties: false,
      declareExternallyReferenced: true,
      enableConstEnums: false,
      style: { singleQuote: false },
    });
    outputs.set(`${name}.ts`, types);
  }

  if (checkMode) {
    for (const [file, expected] of outputs) {
      const target = path.join(GENERATED_DIR, file);
      if (!existsSync(target)) {
        fail(`TS 绑定缺少仓库产物 ${file}`);
        continue;
      }
      if ((await readFile(target, "utf8")) !== expected) {
        fail(`TS 绑定与 schema 不一致：${file}`);
      }
    }
    return;
  }

  await mkdir(GENERATED_DIR, { recursive: true });
  for (const [file, content] of outputs) {
    await writeFile(path.join(GENERATED_DIR, file), content, "utf8");
  }
  ok(`TS 绑定已写入 ${path.relative(ROOT, GENERATED_DIR)}`);
}

async function main() {
  if (!existsSync(CODEX_BIN)) {
    throw new Error(`未找到 ${path.relative(ROOT, CODEX_BIN)}，请先执行 pnpm install。`);
  }
  const pin = (await readFile(PIN_FILE, "utf8")).trim();
  if (!/^\d+\.\d+\.\d+$/.test(pin)) {
    throw new Error(`codex-version.txt 内容不是合法版本号：${JSON.stringify(pin)}`);
  }

  const stagingDir = await mkdtemp(path.join(os.tmpdir(), "codex-schema-"));
  try {
    const schemaDir = await generateSchema(pin, stagingDir);
    await compareOrWriteSchema(schemaDir);
    await generateBindings(pin, schemaDir);
  } finally {
    await rm(stagingDir, { recursive: true, force: true });
  }

  if (problems.length > 0) {
    console.error(`\n${problems.length} 处漂移：请执行 pnpm codex:schema 重新生成并提交。`);
    process.exitCode = 1;
    return;
  }
  if (checkMode) ok(`协议绑定与 codex-cli ${pin} 一致`);
}

main().catch((error) => {
  console.error(`✗ ${error.message}`);
  process.exitCode = 1;
});
