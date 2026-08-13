"""图形验证码通用 helper：ocr（ddddocr）或 manual（有头人工）。

含验证码时由 Phase 4 生成到 tests/helpers/captcha.py。
定位一律由调用方传入（从录制推导），模板不绑定任何业务文案/页面。

环境变量：
- CAPTCHA_MODE=ocr|manual（默认 ocr）
- CAPTCHA_MANUAL_WAIT=input|pause（manual 时；默认 input）
"""

from __future__ import annotations

import base64
import os
import time

from playwright.sync_api import Locator, Page


def get_captcha_mode() -> str:
    mode = (os.getenv("CAPTCHA_MODE") or "ocr").strip().lower()
    return mode if mode in ("ocr", "manual") else "ocr"


def is_manual_captcha() -> bool:
    return get_captcha_mode() == "manual"


def _decode_image_src(src: str) -> bytes:
    if "," in src:
        src = src.split(",", 1)[1]
    return base64.b64decode(src)


def read_captcha_code(image: Locator) -> str:
    """从验证码图片 Locator 识别文字（仅 ocr）。"""
    import ddddocr

    src = image.get_attribute("src") or ""
    if not src:
        raise RuntimeError("captcha image has empty src")
    ocr = ddddocr.DdddOcr(show_ad=False)
    return ocr.classification(_decode_image_src(src)).strip()


def refresh_captcha(image: Locator) -> None:
    """点击验证码图片刷新（若站点用其它控件刷新，由 Page Object 自行封装）。"""
    image.click()
    time.sleep(0.5)


def solve_captcha_with_retry(image: Locator, max_attempts: int = 8) -> str:
    """OCR 识别；异常时刷新图片后重试。"""
    last_err: Exception | None = None
    for _ in range(max_attempts):
        try:
            code = read_captcha_code(image)
            if code:
                return code
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            refresh_captcha(image)
    raise RuntimeError(f"captcha OCR failed: {last_err}")


def wait_for_manual_captcha(page: Page) -> None:
    """有头暂停：由用户在浏览器完成验证码并提交登录。

    CAPTCHA_MANUAL_WAIT=input（默认）：终端回车继续
    CAPTCHA_MANUAL_WAIT=pause：Playwright Inspector → Resume
    """
    wait = (os.getenv("CAPTCHA_MANUAL_WAIT") or "input").strip().lower()
    print(
        "\n[CAPTCHA manual] Complete captcha in the browser, then continue."
    )
    if wait == "pause":
        page.pause()
    else:
        input("Press Enter here when done… ")
