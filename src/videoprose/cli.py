"""
VideoProse 命令行界面
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="VideoProse - 将长视频转化为深度长文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # process 命令
    process_parser = subparsers.add_parser("process", help="处理视频")
    process_parser.add_argument("url", help="视频 URL (B站/YouTube)")
    process_parser.add_argument(
        "-o", "--output",
        help="输出文件路径",
        default=None,
    )
    process_parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "deepseek"],
        default="anthropic",
        help="LLM 提供商",
    )
    process_parser.add_argument(
        "--model",
        help="模型名称",
        default=None,
    )
    
    # web 命令
    web_parser = subparsers.add_parser("web", help="启动 Web 界面")
    web_parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="端口号",
    )
    
    # glossary 命令
    glossary_parser = subparsers.add_parser("glossary", help="管理术语表")
    glossary_parser.add_argument(
        "action",
        choices=["export", "import"],
        help="操作类型",
    )
    glossary_parser.add_argument(
        "file",
        help="术语表文件路径",
    )
    
    args = parser.parse_args()
    
    if args.command == "process":
        cmd_process(args)
    elif args.command == "web":
        cmd_web(args)
    elif args.command == "glossary":
        cmd_glossary(args)
    else:
        parser.print_help()


def cmd_process(args):
    """处理视频命令"""
    from videoprose.workflow import process_video
    from videoprose.config import Config, LLMConfig, set_config
    
    console.print(f"[bold blue]VideoProse[/bold blue] - 视频转长文")
    console.print(f"处理视频: {args.url}\n")
    
    # 配置
    model_defaults = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "deepseek": "deepseek-chat",
    }
    
    config = Config(
        llm=LLMConfig(
            provider=args.provider,
            model=args.model or model_defaults.get(args.provider),
        ),
    )
    set_config(config)
    
    # 输出路径
    output_path = args.output
    if not output_path:
        output_path = f"./output/article_{Path(args.url).stem}.md"
    
    # 处理
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("处理中...", total=None)
        
        def on_progress(msg: str):
            progress.update(task, description=msg)
        
        try:
            document = process_video(
                url=args.url,
                output_path=output_path,
                on_progress=on_progress,
            )
            
            progress.update(task, description="✅ 完成!")
            
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            sys.exit(1)
    
    console.print(f"\n[green]文档已保存到: {output_path}[/green]")
    console.print(f"标题: {document.title}")
    console.print(f"字数: {len(document.body)}")


def cmd_web(args):
    """启动 Web 界面"""
    import subprocess
    
    console.print("[bold blue]VideoProse[/bold blue] - 启动 Web 界面")
    console.print(f"访问 http://localhost:{args.port}\n")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(Path(__file__).parent / "app.py"),
        "--server.port", str(args.port),
    ])


def cmd_glossary(args):
    """管理术语表"""
    from videoprose.modules.knowledge_architect import export_glossary, import_glossary
    
    if args.action == "export":
        console.print(f"导出术语表到: {args.file}")
        # 需要先有 knowledge_base
        console.print("[yellow]请先处理视频生成术语表[/yellow]")
    elif args.action == "import":
        console.print(f"从 {args.file} 导入术语表")
        try:
            kb = import_glossary(args.file)
            console.print(f"[green]导入成功: {len(kb.entities)} 个术语[/green]")
        except Exception as e:
            console.print(f"[red]导入失败: {e}[/red]")


if __name__ == "__main__":
    main()
