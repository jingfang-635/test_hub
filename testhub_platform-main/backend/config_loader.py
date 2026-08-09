# -*- coding: utf-8 -*-
"""
统一配置加载器
优先级：环境变量(Vercel/生产) > config.yaml(本地) > 默认值
兼容 python-decouple 的 config(key, default, cast) 签名，settings.py 可无缝替换
"""
import os
import yaml
from pathlib import Path

# config.yaml 位于项目根目录（backend 的父目录）
_YAML_PATH = Path(__file__).resolve().parent.parent / 'config.yaml'
_YAML_CFG = None
_YAML_MTIME = None


def _load_yaml():
    """加载 config.yaml；文件变更后自动重新读取（避免改配置不重启仍读到旧值）"""
    global _YAML_CFG, _YAML_MTIME
    try:
        mtime = _YAML_PATH.stat().st_mtime if _YAML_PATH.exists() else None
    except OSError:
        mtime = None
    if _YAML_CFG is not None and mtime == _YAML_MTIME:
        return _YAML_CFG
    try:
        if _YAML_PATH.exists():
            with open(_YAML_PATH, 'r', encoding='utf-8') as f:
                _YAML_CFG = yaml.safe_load(f) or {}
        else:
            _YAML_CFG = {}
    except Exception:
        _YAML_CFG = {}
    _YAML_MTIME = mtime
    return _YAML_CFG


def _cast_value(val, cast):
    """按 cast 类型转换值"""
    if cast is None:
        return val
    if cast is bool:
        if isinstance(val, bool):
            return val
        return str(val).lower() in ('true', '1', 'yes', 'on')
    if cast is int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return val
    if callable(cast):
        try:
            return cast(val)
        except Exception:
            return val
    return val


def cfg(key, default=None, cast=None, **kwargs):
    """
    获取配置：环境变量 > config.yaml > 默认值
    兼容 decouple.config 签名
    """
    # 1. 环境变量（Vercel 等 Serverless 环境通过环境变量注入配置）
    # 空字符串视为未设置，避免 FEISHU_APP_ID= 这类空值盖住 config.yaml
    env_val = os.environ.get(key)
    if env_val is not None and str(env_val).strip() != '':
        return _cast_value(env_val, cast)
    # 2. config.yaml（本地开发环境）
    yaml_cfg = _load_yaml()
    if key in yaml_cfg and yaml_cfg[key] is not None and str(yaml_cfg[key]).strip() != '':
        return _cast_value(yaml_cfg[key], cast)
    # 3. 默认值
    return default
