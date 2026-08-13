/**
 * {{FeatureName}} UI 自动化用例。
 * 本文件仅对应单一功能模块；多模块勿写入同一 .spec.ts。
 */
import { test, expect } from "@playwright/test";
import { {{PageClassName}} } from "../pages/{{pageModule}}";
import { create{{EntityClassName}} } from "../data/{{dataModule}}";

test.describe("{{FeatureName}}", () => {
  test("TC-001 {{caseName}} @positive", async ({ page }) => {
    const {{pageVar}} = new {{PageClassName}}(page);
    const data = create{{EntityClassName}}();
    // TODO: 步骤与断言
  });

  test("TC-002 {{caseName}} @negative", async ({ page }) => {
    // TODO
  });
});
