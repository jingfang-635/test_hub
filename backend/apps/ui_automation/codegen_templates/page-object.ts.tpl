import { Page, Locator } from "@playwright/test";

export class {{PageClassName}} {
  readonly page: Page;
  // TODO: 定义 Locator，优先 getByRole / getByLabel / getByTestId
  // readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    // this.submitButton = page.getByRole("button", { name: "..." });
  }

  async goto() {
    await this.page.goto("{{page_url}}");
  }

  // TODO: 按录制步骤封装方法（勿在模板写死业务字段名）
}
