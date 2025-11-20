#!/usr/bin/env python3
"""
Command-line interface for running GitTaskBench evaluations from RepoMaster
"""
import sys
import argparse
from pathlib import Path

# Add RepoMaster to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gittaskbench.gittaskbench_runner import GitTaskBenchRunner


def main():
    parser = argparse.ArgumentParser(
        description='Run GitTaskBench evaluations using RepoMaster',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single task
  python scripts/run_gittaskbench.py --task Trafilatura_01

  # Run specific tasks
  python scripts/run_gittaskbench.py --tasks Trafilatura_01 AnimeGANv3_01

  # Run all tasks
  python scripts/run_gittaskbench.py --all

  # Run first 5 tasks (testing)
  python scripts/run_gittaskbench.py --all --max-tasks 5

  # List available tasks
  python scripts/run_gittaskbench.py --list

  # Use different API
  python scripts/run_gittaskbench.py --task Trafilatura_01 --api-type openai
        """
    )
    
    # Task selection
    task_group = parser.add_mutually_exclusive_group(required=True)
    task_group.add_argument('--task', help='Run a single task')
    task_group.add_argument('--tasks', nargs='+', help='Run specific tasks')
    task_group.add_argument('--all', action='store_true', help='Run all tasks')
    task_group.add_argument('--list', action='store_true', help='List all available tasks')
    
    # Configuration
    parser.add_argument('--gittaskbench-root', 
                       default='../GitTaskBench',
                       help='Path to GitTaskBench directory (default: ../GitTaskBench)')
    parser.add_argument('--output-dir',
                       default='./gittaskbench_results',
                       help='Output directory (default: ./gittaskbench_results)')
    parser.add_argument('--api-type',
                       default='basic',
                       help='API type to use (default: basic)')
    parser.add_argument('--max-tasks', type=int,
                       help='Maximum number of tasks to run (for testing)')
    parser.add_argument('--grade', action='store_true',
                       help='Also run GitTaskBench grading after execution')
    
    args = parser.parse_args()
    
    # Initialize runner
    try:
        runner = GitTaskBenchRunner(
            gittaskbench_root=args.gittaskbench_root,
            output_root=args.output_dir,
            api_type=args.api_type
        )
    except ValueError as e:
        print(f"❌ Error: {e}")
        print(f"\n💡 Make sure GitTaskBench is in the correct location:")
        print(f"   Expected: {Path(args.gittaskbench_root).absolute()}")
        return 1
    
    # List tasks
    if args.list:
        tasks = runner.get_all_tasks()
        print(f"\n📋 Available tasks ({len(tasks)}):\n")
        for i, task in enumerate(tasks, 1):
            print(f"{i:3}. {task}")
        return 0
    
    # Run tasks
    if args.task:
        # Single task
        result = runner.run_single_task(args.task)
        
        # Optional grading
        if args.grade and result['success']:
            print("\n🎯 Running GitTaskBench grading...")
            grade_result = runner.grade_with_gittaskbench(args.task)
            print(f"Grade result: {grade_result}")
        
        return 0 if result['success'] else 1
    
    elif args.tasks:
        # Specific tasks
        summary = runner.run_batch(task_ids=args.tasks)
        return 0 if summary['failed'] == 0 else 1
    
    elif args.all:
        # All tasks
        summary = runner.run_batch(max_tasks=args.max_tasks)
        return 0 if summary['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())