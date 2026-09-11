# -*- coding: utf-8 -*-
"""
接口测试套件执行器 - pytest + allure-pytest 驱动
"""
import glob
import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class ApiSuiteExecutor:
    """接口测试套件执行器，封装 pytest + allure-pytest 执行逻辑"""

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            self.base_path = Path(settings.BASE_DIR)
        else:
            self.base_path = Path(base_path)

        if not self.base_path.exists():
            raise ValueError(f"项目路径不存在: {self.base_path}")

        self.backend_path = self.base_path / 'backend'
        if not self.backend_path.exists():
            # 兼容以 backend 为 BASE_DIR 的部署方式
            self.backend_path = self.base_path

        self._current_process: Optional[subprocess.Popen] = None
        logger.info(f"初始化 ApiSuiteExecutor，项目根目录: {self.base_path}")

    def run_suite(
        self,
        suite_id: int,
        execution_id: int,
        environment_id: Optional[int] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """运行接口测试套件并生成 Allure 报告"""
        logger.info(
            f"开始执行接口套件: suite_id={suite_id}, execution_id={execution_id}"
        )

        original_cwd = os.getcwd()
        try:
            os.chdir(self.backend_path)

            env = os.environ.copy()
            env['PYTHONPATH'] = self._build_pythonpath()
            env['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
            env['PYTHONUTF8'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'

            env['API_SUITE_ID'] = str(suite_id)
            env['API_EXECUTION_ID'] = str(execution_id)
            if environment_id is not None:
                env['API_ENVIRONMENT_ID'] = str(environment_id)
            if username:
                env['API_USERNAME'] = username

            allure_results_dir = self._get_allure_results_dir(execution_id)
            os.makedirs(allure_results_dir, exist_ok=True)

            # 清理旧结果，避免混入历史数据
            for old_file in glob.glob(os.path.join(allure_results_dir, '*')):
                try:
                    if os.path.isfile(old_file):
                        os.remove(old_file)
                except OSError:
                    pass

            pytest_args = [
                sys.executable, '-m', 'pytest',
                'apps/api_testing/tests/',
                '-s', '-v',
                '--alluredir', allure_results_dir,
                '--tb=short',
                '-p', 'no:cacheprovider',
            ]

            logger.info(f"执行命令: {' '.join(pytest_args)}")
            logger.info(f"工作目录: {os.getcwd()}")

            process = subprocess.Popen(
                pytest_args,
                cwd=str(self.backend_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1,
                env=env,
            )
            self._current_process = process

            log_file_path = self._get_log_file_path(username or 'unknown')
            output_lines = []
            important_patterns = [
                'PASSED', 'FAILED', 'ERROR', 'SKIPPED',
                'collected', 'passed', 'failed',
            ]

            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n{'=' * 80}\n")
                log_file.write(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"执行记录 ID: {execution_id}, 套件 ID: {suite_id}\n"
                )
                log_file.write(f"{'=' * 80}\n")

                if process.stdout:
                    for line in process.stdout:
                        line = line.rstrip()
                        if line:
                            output_lines.append(line)
                            log_file.write(line + '\n')
                            if any(p in line for p in important_patterns):
                                logger.info(f"[pytest] {line}")

                log_file.write("\n[执行完毕]\n")

            exit_code = process.wait()
            self._current_process = None
            logger.info(f"pytest 执行完成，退出码: {exit_code}")

            test_results = self._parse_allure_results(allure_results_dir)
            report_path = self._generate_allure_report(execution_id)

            # pytest: 0=成功, 1=有失败用例, 5=未收集到用例 —— 均视为流程已跑完
            success = exit_code in (0, 1, 5)
            return {
                'success': success,
                'exit_code': exit_code,
                'report_path': report_path,
                'report_url': (
                    f'/media/api-testing/allure-reports/execution_{execution_id}/index.html'
                    if report_path else None
                ),
                'test_results': test_results,
                'output': '\n'.join(output_lines[-50:]),
            }
        except Exception as e:
            logger.error(f"执行接口套件失败: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            os.chdir(original_cwd)

    def _get_log_file_path(self, username: str) -> str:
        today = datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(str(self.base_path), 'logs', 'api_testing', username)
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, f'{today}.log')

    def _build_pythonpath(self) -> str:
        parts = [
            str(self.base_path),
            str(self.backend_path),
            str(self.backend_path / 'apps'),
        ]
        for p in sys.path:
            if p and os.path.exists(str(p)) and str(p) not in parts:
                p_str = str(p)
                if 'site-packages' in p_str or not p_str.endswith('.exe'):
                    parts.append(p_str)
        return os.pathsep.join(parts)

    def _get_allure_results_dir(self, execution_id: Optional[int] = None) -> str:
        base_dir = os.path.join(settings.MEDIA_ROOT, 'api-testing', 'allure-results')
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_allure_report_dir(self, execution_id: Optional[int] = None) -> str:
        base_dir = os.path.join(settings.MEDIA_ROOT, 'api-testing', 'allure-reports')
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _generate_allure_report(self, execution_id: Optional[int] = None) -> Optional[str]:
        try:
            allure_results_dir = self._get_allure_results_dir(execution_id)
            report_dir = self._get_allure_report_dir(execution_id)
            os.makedirs(report_dir, exist_ok=True)

            allure_path = self._find_allure_command()
            if not allure_path:
                logger.warning("未找到 Allure 命令，跳过报告生成")
                return None

            cmd = [allure_path, 'generate', allure_results_dir, '-o', report_dir, '--clean']
            logger.info(f"生成 Allure 报告: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                logger.info(f"Allure 报告生成成功: {report_dir}")
                return report_dir

            logger.error(f"Allure 报告生成失败: {result.stderr}")
            return None
        except subprocess.TimeoutExpired:
            logger.error("Allure 报告生成超时")
            return None
        except Exception as e:
            logger.error(f"生成 Allure 报告失败: {e}", exc_info=True)
            return None

    def _find_allure_command(self) -> Optional[str]:
        if platform.system() == 'Windows':
            builtin = self.base_path / 'allure' / 'bin' / 'allure.bat'
        else:
            builtin = self.base_path / 'allure' / 'bin' / 'allure'

        if builtin.exists():
            logger.info(f"使用项目内置 Allure: {builtin}")
            return str(builtin)

        # 兼容 BASE_DIR 指向 backend 的情况
        alt = Path(settings.BASE_DIR).parent / 'allure' / 'bin' / (
            'allure.bat' if platform.system() == 'Windows' else 'allure'
        )
        if alt.exists():
            return str(alt)

        logger.warning("未找到项目内置 Allure，请确认 allure 目录存在")
        return None

    def _parse_allure_results(self, results_dir: str) -> Dict[str, Any]:
        try:
            result_files = glob.glob(os.path.join(results_dir, '*-result.json'))
            total = passed = failed = skipped = 0
            for result_file in result_files:
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    status = (data.get('status') or '').lower()
                    total += 1
                    if status == 'passed':
                        passed += 1
                    elif status == 'failed':
                        failed += 1
                    elif status == 'skipped':
                        skipped += 1
                except Exception as e:
                    logger.warning(f"解析结果文件失败: {result_file}, 错误: {e}")

            return {
                'total': total,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
            }
        except Exception as e:
            logger.error(f"解析 Allure 结果失败: {e}", exc_info=True)
            return {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0}

    def stop(self):
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._current_process.kill()
            finally:
                self._current_process = None
