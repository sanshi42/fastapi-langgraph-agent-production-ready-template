#!/usr/bin/env python3
"""运行评测的命令行界面."""

import argparse
import asyncio
import os
import sys
from typing import (
    Any,
    Dict,
    Optional,
)

import colorama
from colorama import (
    Fore,
    Style,
)

# 修正 app 模块导入路径。
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.core.logging import logger
from evals.evaluator import Evaluator

# 默认配置。
DEFAULT_CONFIG = {
    "generate_report": True,
    "model": settings.EVALUATION_LLM,
    "api_base": settings.EVALUATION_BASE_URL,
}


def print_title(title: str) -> None:
    """打印带颜色的格式化标题.

    Args:
        title: 要打印的标题文本。
    """
    print("\n" + "=" * 60)
    print(f"{Fore.CYAN}{Style.BRIGHT}{title.center(60)}{Style.RESET_ALL}")
    print("=" * 60 + "\n")


def print_info(message: str) -> None:
    """打印带颜色的信息消息.

    Args:
        message: 要打印的消息。
    """
    print(f"{Fore.GREEN}• {message}{Style.RESET_ALL}")


def print_warning(message: str) -> None:
    """打印带颜色的警告消息.

    Args:
        message: 要打印的消息。
    """
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")


def print_error(message: str) -> None:
    """打印带颜色的错误消息.

    Args:
        message: 要打印的消息。
    """
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")


def print_success(message: str) -> None:
    """打印带颜色的成功消息.

    Args:
        message: 要打印的消息。
    """
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def get_user_input(prompt: str, default: Optional[str] = None) -> Optional[str]:
    """使用带颜色的 prompt 获取用户输入.

    Args:
        prompt: 要展示的 prompt。
        default: 用户直接回车时使用的默认值。

    Returns:
        用户输入或默认值；没有默认值时可能为 None。
    """
    default_text = f" [{default}]" if default else ""
    user_input = input(f"{Fore.BLUE}{prompt}{default_text}: {Style.RESET_ALL}")
    return user_input if user_input else default


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """获取用户 yes/no 回答.

    Args:
        prompt: 要展示的 prompt。
        default: 用户直接回车时使用的默认值。

    Returns:
        yes 返回 True，no 返回 False。
    """
    default_value = "Y/n" if default else "y/N"
    response = get_user_input(f"{prompt} {default_value}")

    if not response:
        return default

    return response.lower() in ("y", "yes")


def display_summary(report: Dict[str, Any]) -> None:
    """展示评测结果摘要.

    Args:
        report: 评测报告。
    """
    print_title("评测摘要")

    print(f"{Fore.CYAN}模型:{Style.RESET_ALL} {report['model']}")
    print(f"{Fore.CYAN}耗时:{Style.RESET_ALL} {report['duration_seconds']} 秒")
    print(f"{Fore.CYAN}Trace 总数:{Style.RESET_ALL} {report['total_traces']}")

    success_rate = 0
    if report["total_traces"] > 0:
        success_rate = (report["successful_traces"] / report["total_traces"]) * 100

    if success_rate > 80:
        status_color = Fore.GREEN
    elif success_rate > 50:
        status_color = Fore.YELLOW
    else:
        status_color = Fore.RED

    print(
        f"{Fore.CYAN}成功率:{Style.RESET_ALL} {status_color}{success_rate:.1f}%{Style.RESET_ALL} ({report['successful_traces']}/{report['total_traces']})"
    )

    print("\n" + f"{Fore.CYAN}指标摘要:{Style.RESET_ALL}")
    for metric_name, data in report["metrics_summary"].items():
        total = data["success_count"] + data["failure_count"]
        success_percent = 0
        if total > 0:
            success_percent = (data["success_count"] / total) * 100

        if success_percent > 80:
            status_color = Fore.GREEN
        elif success_percent > 50:
            status_color = Fore.YELLOW
        else:
            status_color = Fore.RED

        print(
            f"  • {metric_name}: {status_color}{success_percent:.1f}%{Style.RESET_ALL} 成功，平均分: {data['avg_score']:.2f}"
        )

    if report["generate_report_path"]:
        print(f"\n{Fore.CYAN}报告生成位置:{Style.RESET_ALL} {report['generate_report_path']}")


async def run_evaluation(generate_report: bool = True) -> None:
    """运行评测流程.

    Args:
        generate_report: 是否生成 JSON 报告。
    """
    print_title("开始评测")
    print_info(f"使用模型: {settings.EVALUATION_LLM}")
    print_info(f"报告生成: {'启用' if generate_report else '禁用'}")

    try:
        evaluator = Evaluator()
        await evaluator.run(generate_report_file=generate_report)

        print_success("评测完成。")

        # 展示结果摘要。
        display_summary(evaluator.report)

    except Exception as e:
        print_error(f"评测失败: {str(e)}")
        logger.error("evaluation_failed", error=str(e))
        sys.exit(1)


def display_configuration(config: Dict[str, Any]) -> None:
    """展示当前配置.

    Args:
        config: 配置字典。
    """
    print_title("配置")
    print_info(f"模型: {config['model']}")
    print_info(f"API Base: {config['api_base']}")
    print_info(f"生成报告: {'是' if config['generate_report'] else '否'}")


def interactive_mode() -> None:
    """以交互模式运行评测器."""
    colorama.init()

    # 使用默认值创建配置。
    config = DEFAULT_CONFIG.copy()

    print_title("评测运行器")
    print_info("欢迎使用评测运行器。")
    print_info("按 Enter 接受默认值，或输入自定义值。")

    # 展示当前配置。
    display_configuration(config)

    print("\n" + f"{Fore.CYAN}配置选项（按 Enter 接受默认值）:{Style.RESET_ALL}")

    # 允许用户修改配置或接受默认值。
    change_config = get_yes_no("是否修改默认配置？", default=False)

    if change_config:
        config["generate_report"] = get_yes_no("是否生成 JSON 报告？", default=config["generate_report"])

    print("\n")
    confirm = get_yes_no("是否使用这些设置开始评测？", default=True)

    if confirm:
        asyncio.run(run_evaluation(generate_report=config["generate_report"]))
    else:
        print_warning("评测已取消。")


def quick_mode() -> None:
    """使用全部默认设置运行评测器."""
    colorama.init()
    print_title("快速评测")
    print_info("正在使用默认设置运行评测...")
    print_info("按 Ctrl+C 取消")

    # 展示默认配置。
    display_configuration(DEFAULT_CONFIG)

    try:
        asyncio.run(run_evaluation(generate_report=DEFAULT_CONFIG["generate_report"]))
    except KeyboardInterrupt:
        print_warning("\n用户已取消评测。")
        sys.exit(0)


def main() -> None:
    """命令行界面主入口."""
    parser = argparse.ArgumentParser(description="对模型输出运行评测")
    parser.add_argument("--no-report", action="store_true", help="不生成 JSON 报告")
    parser.add_argument("--interactive", action="store_true", help="以交互模式运行")
    parser.add_argument("--quick", action="store_true", help="使用全部默认设置运行，不显示 prompt")

    args = parser.parse_args()

    if args.quick:
        quick_mode()
    elif args.interactive:
        interactive_mode()
    else:
        # 使用命令行参数运行。
        asyncio.run(run_evaluation(generate_report=not args.no_report))


if __name__ == "__main__":
    main()
