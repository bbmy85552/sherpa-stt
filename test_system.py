#!/usr/bin/env python3
"""
系统测试脚本
验证各个组件是否正常工作
"""
import os
import sys
from pathlib import Path

def test_model_files():
    """测试模型文件是否存在"""
    print("🔍 测试模型文件...")
    model_dir = Path("models")
    required_files = [
        "model.int8.onnx",
        "tokens.txt",
        "silero_vad.onnx"
    ]

    for file_name in required_files:
        file_path = model_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size / (1024 * 1024)  # MB
            print(f"✅ {file_name} ({size:.1f} MB)")
        else:
            print(f"❌ {file_name} 不存在")
            return False

    return True

def test_imports():
    """测试必要的包是否可以导入"""
    print("\n📦 测试包导入...")

    try:
        import fastapi
        print("✅ FastAPI")
    except ImportError as e:
        print(f"❌ FastAPI: {e}")
        return False

    try:
        import uvicorn
        print("✅ Uvicorn")
    except ImportError as e:
        print(f"❌ Uvicorn: {e}")
        return False

    try:
        import websockets
        print("✅ WebSockets")
    except ImportError as e:
        print(f"❌ WebSockets: {e}")
        return False

    try:
        import numpy
        print("✅ NumPy")
    except ImportError as e:
        print(f"❌ NumPy: {e}")
        return False

    try:
        import sherpa_onnx
        print("✅ Sherpa-ONNX")
    except ImportError as e:
        print(f"❌ Sherpa-ONNX: {e}")
        return False

    return True

def test_sense_voice_service():
    """测试 SenseVoice 服务类"""
    print("\n🎤 测试 SenseVoice 服务...")

    try:
        from main import SenseVoiceService
        service = SenseVoiceService()
        print("✅ SenseVoice 服务初始化成功")
        return True
    except Exception as e:
        print(f"❌ SenseVoice 服务初始化失败: {e}")
        return False

def test_static_files():
    """测试前端静态文件"""
    print("\n🌐 测试前端文件...")

    static_dir = Path("static")
    required_files = [
        "index.html",
        "app.js",
        "style.css"
    ]

    for file_name in required_files:
        file_path = static_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name}")
        else:
            print(f"❌ {file_name} 不存在")
            return False

    return True

def test_port_availability():
    """测试端口是否可用"""
    print("\n🔌 测试端口可用性...")

    import socket

    port = 8000
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
        print(f"✅ 端口 {port} 可用")
        return True
    except OSError:
        print(f"⚠️  端口 {port} 已被占用")
        return False

def main():
    """主测试函数"""
    print("🧪 SenseVoice 系统测试开始...\n")

    tests = [
        ("模型文件", test_model_files),
        ("包导入", test_imports),
        ("SenseVoice 服务", test_sense_voice_service),
        ("前端文件", test_static_files),
        ("端口可用性", test_port_availability)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试失败: {e}")
            results.append((test_name, False))

    # 输出测试结果
    print("\n" + "="*50)
    print("📊 测试结果汇总:")
    print("="*50)

    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:15} {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 项测试通过")

    if passed == len(results):
        print("\n🎉 所有测试通过！系统可以正常启动。")
        print("\n启动命令:")
        print("  ./start_server.sh    # 生产模式")
        print("  ./start_dev.sh       # 开发模式")
        return 0
    else:
        print(f"\n⚠️  有 {len(results) - passed} 项测试失败，请检查问题后重试。")
        return 1

if __name__ == "__main__":
    sys.exit(main())