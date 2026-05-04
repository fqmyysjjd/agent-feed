import { join } from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { copyTemplateAssets } from "./template.js";

const currentDir = dirname(fileURLToPath(import.meta.url));
copyTemplateAssets(join(currentDir, ".."));
