[pytest]
testpaths = tests/specs
pythonpath = .
markers =
    positive: 正向用例
    negative: 负向用例
    boundary: 边界用例
    permission: 权限用例
addopts =
    -v
    --tracing=on
    --screenshot=only-on-failure
    --html=reports/report.html
    --self-contained-html
    --css=assets/report.css
