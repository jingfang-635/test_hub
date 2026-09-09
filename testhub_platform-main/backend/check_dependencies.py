"""
检查 AI 浏览器自动化所需的依赖是否已安装
"""
import sys

def check_package(name, import_name=None):
    """检查包是否已安装"""
    if import_name is None:
        import_name = name
    
    try:
        __import__(import_name)
        print(f"✅ {name} 已安装")
        return True
    except ImportError as e:
        print(f"❌ {name} 未安装：{e}")
        return False

def main():
    print("=" * 60)
    print("AI 浏览器自动化依赖检查")
    print("=" * 60)
    print(f"Python 版本：{sys.version}")
    print()
    
    # 核心依赖
    packages = [
        ("langchain_openai", "langchain_openai"),
        ("browser_use", "browser_use"),
        ("pydantic_settings", "pydantic_settings"),
        ("pydantic", "pydantic"),
    ]
    
    results = []
    for name, import_name in packages:
        results.append(check_package(name, import_name))
    
    print()
    print("=" * 60)
    if all(results):
        print("✅ 所有依赖都已安装！")
        return 0
    else:
        print("❌ 部分依赖未安装")
        print()
        print("请运行以下命令安装缺失的依赖：")
        print("  pip install langchain-openai browser-use pydantic-settings")
        print()
        print("如果遇到权限问题，请：")
        print("  1. 以管理员身份运行命令行")
        print("  2. 或者使用：pip install --user <包名>")
        return 1

if __name__ == "__main__":
    sys.exit(main())
