import { faker } from "@faker-js/faker";

export interface {{EntityClassName}} {
  // TODO: 按录制/计划定义字段
  [key: string]: unknown;
}

export function create{{EntityClassName}}(
  overrides?: Partial<{{EntityClassName}}>
): {{EntityClassName}} {
  return {
    // TODO: 按实体填默认值
    name: `item_${Date.now()}`,
    ...overrides,
  };
}
