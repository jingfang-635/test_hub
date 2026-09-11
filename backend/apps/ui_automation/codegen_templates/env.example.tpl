BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8080
TEST_USERNAME=
TEST_PASSWORD=
# 图形验证码：ocr（ddddocr，默认）| manual（有头人工）
CAPTCHA_MODE=ocr
# manual 时：input（终端回车，默认）| pause（Playwright Inspector）
CAPTCHA_MANUAL_WAIT=input
# 仅测试环境固定验证码时填写；动态码用 ocr/manual
TEST_CAPTCHA=
# manual 会强制有头；ocr 时可用 HEADLESS=true
HEADLESS=true
# Trace：pytest.ini 默认 on；可 --tracing=off|retain-on-failure
# 报告：./scripts/open-report.sh；Trace Viewer 依赖下方源
REPORT_ORIGIN=http://127.0.0.1:9323
