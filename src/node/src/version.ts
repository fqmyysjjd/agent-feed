import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

type PackageJson = {
  version?: unknown;
};

function readVersion(): string {
  const currentDir = dirname(fileURLToPath(import.meta.url));
  const packageJsonPath = join(currentDir, "..", "..", "package.json");
  const content = JSON.parse(readFileSync(packageJsonPath, "utf8")) as PackageJson;
  if (typeof content.version !== "string" || content.version.length === 0) {
    throw new Error(`Missing version in ${packageJsonPath}`);
  }
  return content.version;
}

export const VERSION = readVersion();
