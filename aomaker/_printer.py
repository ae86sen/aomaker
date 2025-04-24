from emoji import emojize
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich import box
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.style import Style
    from time import sleep
    import threading
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console()

class TestSessionInfo:

    init_env_s = "开始初始化环境", "rocket"
    init_env_e = "环境初始化完成，所有全局配置已加载到config表", "white_check_mark"
    gen_rep_s = "测试结束, AoMaker开始收集报告", "page_with_curl"
    gen_rep_e = "AoMaker已完成测试报告(reports/aomaker-report.html)!", "sparkles"
    clean_env_s = "测试结束，开始清理环境", "broom"
    clean_env_e = "清理环境完成！", "tada"
    
    _progress_tasks = {}
    _live_displays = {}

    @classmethod
    def map(cls, attr):
        def wrapper():
            value = getattr(cls, attr)
            text = emojize(f":{value[1]}: {value[0]}")
            
            if RICH_AVAILABLE:
                if "init_env" in attr:
                    if attr.endswith("_s"):
                        cls._show_start_progress(attr, text)
                    else:
                        cls._show_completion(attr, text)
                elif "gen_rep" in attr:
                    task_type = "gen_rep"
                    if attr.endswith("_s"):
                        cls._start_progress_display(task_type, text)
                    else:
                        cls._complete_progress_display(task_type, text)
                else:
                    if attr.endswith("_s"):
                        cls._show_start_progress(attr, text)
                    else:
                        cls._show_completion(attr, text)
            else:
                if "clean_env" not in attr:
                    print(cls.output(text))

        return wrapper
    
    @classmethod
    def _start_progress_display(cls, task_type, text):
        """开始显示简化的进度条"""
        if "gen_rep" in task_type:
            title = "报告生成"
            border_style = "green"
            steps = [
                "测试结果收集",
                "报告生成",
                "资源释放"
            ]
        else:
            title = "进度"
            border_style = "blue"
            steps = ["处理中"]
        
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style=border_style),
            TextColumn("[{task.percentage:>3.0f}%]"),
            TimeElapsedColumn(),
            console=console
        )
        
        task_ids = []
        for step in steps:
            task_id = progress.add_task(step, total=100)
            task_ids.append(task_id)
        
        def update_progress():
            for i in range(0, 101, 5):
                if task_type not in cls._progress_tasks:
                    break
                
                if i < 50:
                    progress.update(task_ids[0], completed=i*2)
                elif i < 80:
                    progress.update(task_ids[0], completed=100)
                    progress.update(task_ids[1], completed=(i-50)*3)
                else:
                    progress.update(task_ids[0], completed=100)
                    progress.update(task_ids[1], completed=100)
                    progress.update(task_ids[2], completed=(i-80)*5)
                
                sleep(0.1)  # 短暂停顿
        
        console.print(Panel(
            text,
            title=title,
            border_style=border_style,
            box=box.ROUNDED,
            width=120
        ))
        
        live = Live(progress, refresh_per_second=10, console=console)
        live.start()
        
        cls._progress_tasks[task_type] = {
            'progress': progress,
            'tasks': task_ids,
            'thread': threading.Thread(target=update_progress)
        }
        cls._live_displays[task_type] = live
        
        cls._progress_tasks[task_type]['thread'].daemon = True
        cls._progress_tasks[task_type]['thread'].start()
    
    @classmethod
    def _complete_progress_display(cls, task_type, text):
        """完成进度条显示"""
        if task_type in cls._progress_tasks:
            if task_type in cls._live_displays:
                live = cls._live_displays[task_type]
                live.stop()
                del cls._live_displays[task_type]
            
            if task_type in cls._progress_tasks:
                del cls._progress_tasks[task_type]
        
        if "gen_rep" in task_type:
            box_style = box.DOUBLE
            border_style = "green"
        else:
            box_style = box.ROUNDED
            border_style = "green"
        
        console.print(Panel(
            text,
            title="完成",
            border_style=border_style,
            box=box_style,
            width=120
        ))
    
    @classmethod
    def _show_start_progress(cls, attr, text):
        """显示开始进度的面板"""
        if "init_env" in attr:
            title = "开始"
            border_style = "blue"
            box_style = box.ROUNDED
        elif "gen_rep" in attr:
            title = "报告生成"
            border_style = "green"
            box_style = box.ROUNDED
        elif "clean_env" in attr:
            title = "清理"
            border_style = "yellow"
            box_style = box.ROUNDED
        else:
            title = "进行中"
            border_style = "cyan"
            box_style = box.ROUNDED
            
        console.print(Panel(
            text,
            title=title,
            border_style=border_style,
            box=box_style,
            width=120
        ))
        
        task_type = attr.replace("_s", "")
        if task_type == "init_env":
            steps = [
                ("全局配置加载", "🔄 进行中"),
                ("测试环境准备", "⏳ 等待中"),
                ("依赖检查", "⏳ 等待中")
            ]
        elif task_type == "gen_rep":
            steps = [
                ("测试结果收集", "🔄 进行中"),
                ("报告生成", "⏳ 等待中"),
                ("资源释放", "⏳ 等待中")
            ]
        elif task_type == "clean_env":
            steps = [
                ("临时文件清理", "🔄 进行中"),
                ("连接关闭", "⏳ 等待中"),
                ("资源回收", "⏳ 等待中")
            ]
        else:
            steps = [("处理中", "🔄 进行中")]
        
        table = Table(box=box.ROUNDED, border_style=border_style)
        table.add_column("步骤", style="cyan")
        table.add_column("状态", style="magenta")
        table.add_column("详情", style="green")
        
        for step, status in steps:
            if "进行中" in status:
                detail = "正在处理..."
            else:
                detail = "等待开始"
            table.add_row(step, status, detail)
        
        console.print(table)

    @classmethod
    def _show_completion(cls, attr, text):
        """显示完成状态的面板"""
        if "init_env" in attr:
            title = "完成"
            border_style = "green"
            box_style = box.HEAVY
        elif "gen_rep" in attr:
            title = "完成"
            border_style = "green"
            box_style = box.DOUBLE
        else:
            title = "完成"
            border_style = "green"
            box_style = box.ROUNDED
        
        console.print(Panel(
            text,
            title=title,
            border_style=border_style,
            box=box_style,
            width=120
        ))
        

    @classmethod
    def output(cls, text: str, total_len: int = 156):
        """生成传统的分隔符样式输出（当Rich不可用时使用）"""
        text_len = len(text)
        padding_len = (total_len - text_len - 4) // 2
        output = "=" * padding_len + " " + text + " " + "=" * padding_len
        return output


def printer(label:str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            TestSessionInfo.map(label+"_s")()
            func(*args, **kwargs)
            TestSessionInfo.map(label+"_e")()

        return wrapper

    return decorator
