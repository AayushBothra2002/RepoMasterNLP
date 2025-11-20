"""
GitTaskBench evaluation integration for RepoMaster
Run GitTaskBench evaluations directly from RepoMaster
"""
import os
import sys
import json
import yaml
from pathlib import Path
from typing import Optional, List, Dict
from tqdm import tqdm
import tempfile
import shutil

# Add GitTaskBench to Python path
GITTASKBENCH_PATH = Path(__file__).parent.parent.parent.parent / "GitTaskBench"
sys.path.insert(0, str(GITTASKBENCH_PATH))

from src.core.agent_scheduler import RepoMasterAgent
from configs.oai_config import get_llm_config


class GitTaskBenchRunner:
    """Run GitTaskBench evaluations using RepoMaster"""
    
    def __init__(self, gittaskbench_root: str=None, output_root: str=None, api_type: str="basic"):
        """
        Initialize runner
        
        Args:
            gittaskbench_root: Path to GitTaskBench (default: ../GitTaskBench)
            output_root: Where to save outputs (default: ./gittaskbench_results)
            api_type: LLM API type to use
        """
        # Set paths
        if gittaskbench_root is None:
            # Assume GitTaskBench is adjacent to RepoMaster
            gittaskbench_root = Path(__file__).parent.parent.parent.parent / "GitTaskBench"
        
        self.gittaskbench_root = Path(gittaskbench_root)
        if not self.gittaskbench_root.exists():
            raise ValueError(f"GitTaskBench not found at: {self.gittaskbench_root}")
        
        self.config_dir = self.gittaskbench_root / "config"
        self.queries_dir = self.gittaskbench_root / "queries"
        self.code_base_dir = self.gittaskbench_root / "code_base"
        
        # Output directory in RepoMaster
        if output_root is None:
            output_root = Path(__file__).parent.parent.parent / "gittaskbench_results"
        self.output_root = Path(output_root)
        self.output_root.mkdir(exist_ok=True, parents=True)
        
        self.api_type = api_type
        
        print(f"✅ GitTaskBench root: {self.gittaskbench_root}")
        print(f"✅ Output directory: {self.output_root}")
    
    def get_all_tasks(self) -> List[str]:
        """Get list of all available task IDs"""
        tasks = []
        for config_path in self.config_dir.glob("*/task_info.yaml"):
            task_id = config_path.parent.name
            tasks.append(task_id)
        return sorted(tasks)
    
    def load_task_config(self, task_id: str) -> Dict:
        """Load task configuration from both task_info.yaml and query.json"""
        # Load task_info.yaml (for evaluation metadata)
        config_path = self.config_dir / task_id / "task_info.yaml"
        if not config_path.exists():
            raise ValueError(f"Task config not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            task_info = yaml.safe_load(f)
        
        # Load query.json (for task description and repository)
        query_path = self.queries_dir / task_id / "query.json"
        if query_path.exists():
            with open(query_path, 'r', encoding='utf-8') as f:
                query_info = json.load(f)
            
            # Merge query info into task_info
            task_info['task_description'] = query_info.get('task_description', '')
            task_info['repositories'] = query_info.get('repositories', [])
            task_info['input_data'] = query_info.get('file_paths', {}).get('input_files', [])
        
        return task_info
    
    def run_single_task(self, task_id: str, verbose: bool = True) -> Dict:
        """
        Run RepoMaster on a single GitTaskBench task
        
        Args:
            task_id: Task identifier (e.g., 'Trafilatura_01')
            verbose: Print progress information
            
        Returns:
            Dict with execution results
        """
        if verbose:
            print(f"\n{'='*70}")
            print(f"📋 Running Task: {task_id}")
            print(f"{'='*70}")
        
        # Load task configuration (now includes query.json data)
        task_info = self.load_task_config(task_id)
        
        # Extract task details
        task_description = task_info.get('task_description', '')
        repositories = task_info.get('repositories', [])
        
        # Get the first repository (GitTaskBench typically uses one repo per task)
        if not repositories:
            raise ValueError(f"No repository found for task {task_id}")
        
        repo_info = repositories[0]
        
        # Determine repository path
        # GitTaskBench uses absolute paths in query.json, convert to relative
        repo_path = repo_info.get('path', '')
        if repo_path.startswith('/GitTaskBench/'):
            # Remove /GitTaskBench/ prefix and use relative to gittaskbench_root
            relative_path = repo_path.replace('/GitTaskBench/', '')
            repository = str(self.gittaskbench_root / relative_path)
        else:
            # Fallback: use code_base directory
            repository = str(self.code_base_dir / repo_info.get('name', ''))
        
        # Process input data
        input_data = task_info.get('input_data', [])
        if input_data:
            # Convert GitTaskBench absolute paths to actual paths
            for data_item in input_data:
                if 'path' in data_item:
                    path = data_item['path']
                    if path.startswith('/GitTaskBench/'):
                        # Convert to actual path
                        relative_path = path.replace('/GitTaskBench/', '')
                        data_item['path'] = str(self.gittaskbench_root / relative_path)
        
        # Create TWO directories:
        # 1. Working directory (temporary, will contain repo copy)
        temp_work_dir = Path(tempfile.mkdtemp(prefix=f"repomaster_{task_id}_"))
        
        # 2. Final output directory (in GitTaskBench/output, clean)
        final_output_dir = self.output_root / task_id
        final_output_dir.mkdir(exist_ok=True, parents=True)
        
        if verbose:
            print(f"📂 Repository: {repository}")
            print(f"📝 Task: {task_description[:100]}...")
            print(f"�� Working directory: {temp_work_dir}")
            print(f"💾 Final output: {final_output_dir}")
        
        try:
            # Initialize RepoMaster agent with TEMP working directory
            from configs.oai_config import get_llm_config
            llm_config = get_llm_config(api_type=self.api_type)
            code_execution_config = {
                "work_dir": str(temp_work_dir),  # Use temp directory
                "use_docker": False
            }
            
            agent = RepoMasterAgent(
                llm_config=llm_config,
                code_execution_config=code_execution_config
            )
            
            # Format input data
            input_data_json = json.dumps(input_data) if input_data else None
            
            if verbose:
                print(f"🤖 Executing with RepoMaster...")
            
            # Run the task
            result = agent.run_repository_agent(
                task_description=task_description,
                repository=repository,
                input_data=input_data_json
            )
            
            # COPY ONLY OUTPUT FILES to final directory
            if verbose:
                print(f"�� Collecting outputs...")
            
            # Copy generated scripts and output files (not the entire repo)
            for item in temp_work_dir.iterdir():
                # Skip the cloned repository directory
                if item.is_dir() and item.name in [Path(repository).name, 'input_dataset']:
                    if verbose:
                        print(f"  ⏭️  Skipping repository copy: {item.name}")
                    continue
                
                # Copy everything else (scripts, results, etc.)
                if item.is_file():
                    shutil.copy2(item, final_output_dir / item.name)
                    if verbose:
                        print(f"  ✅ Copied: {item.name}")
                elif item.is_dir():
                    shutil.copytree(item, final_output_dir / item.name, dirs_exist_ok=True)
                    if verbose:
                        print(f"  ✅ Copied dir: {item.name}/")
            
            # Save execution result
            result_data = {
                'task_id': task_id,
                'success': True,
                'result': result,
                'output_dir': str(final_output_dir),
                'repository': repository,
                'task_description': task_description
            }
            
            result_file = final_output_dir / 'execution_result.json'
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
            
            if verbose:
                print(f"✅ Task completed successfully")
                print(f"📄 Result saved to: {result_file}")
                print(f"🧹 Cleaning up temporary directory...")
            
            # Cleanup temporary directory
            shutil.rmtree(temp_work_dir, ignore_errors=True)
            
            return result_data
            
        except Exception as e:
            import traceback
            error_data = {
                'task_id': task_id,
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc(),
                'output_dir': str(final_output_dir)
            }
            
            # Save error info
            error_file = final_output_dir / 'execution_error.json'
            with open(error_file, 'w') as f:
                json.dump(error_data, f, indent=2)
            
            if verbose:
                print(f"❌ Task failed: {str(e)}")
            
            # Cleanup temporary directory
            shutil.rmtree(temp_work_dir, ignore_errors=True)
            
            return error_data
    
    def run_batch(self, task_ids: Optional[List[str]]=None, max_tasks: Optional[int]=None) -> Dict:
        """
        Run multiple tasks in batch
        
        Args:
            task_ids: Specific task IDs to run (None = all tasks)
            max_tasks: Maximum number of tasks to run
            
        Returns:
            Summary of results
        """
        # Get tasks to run
        if task_ids is None:
            task_ids = self.get_all_tasks()
        
        if max_tasks:
            task_ids = task_ids[:max_tasks]
        
        print(f"\n🚀 Starting batch evaluation")
        print(f"📊 Total tasks: {len(task_ids)}")
        print(f"🤖 Using API: {self.api_type}")
        
        results = []
        successful = 0
        failed = 0
        
        for task_id in tqdm(task_ids, desc="Running tasks"):
            result = self.run_single_task(task_id, verbose=False)
            results.append(result)
            
            if result['success']:
                successful += 1
            else:
                failed += 1
            
            # Save progress after each task
            self._save_progress(results)
        
        # Generate final summary
        summary = self._generate_summary(results, successful, failed)
        
        return summary
    
    def _save_progress(self, results: List[Dict]):
        """Save evaluation progress"""
        progress_file = self.output_root / 'evaluation_progress.json'
        with open(progress_file, 'w') as f:
            json.dump(results, f, indent=2)
    
    def _generate_summary(self, results: List[Dict], successful: int, failed: int) -> Dict:
        """Generate and save evaluation summary"""
        total = len(results)
        
        summary = {
            'total_tasks': total,
            'successful': successful,
            'failed': failed,
            'success_rate': f"{successful/total*100:.2f}%" if total > 0 else "0%",
            'api_type': self.api_type,
            'output_root': str(self.output_root),
            'results': results
        }
        
        # Save summary
        summary_file = self.output_root / 'evaluation_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print(f"\n{'='*70}")
        print("📊 EVALUATION SUMMARY")
        print(f"{'='*70}")
        print(f"Total tasks:    {total}")
        print(f"Successful:     {successful} ✅")
        print(f"Failed:         {failed} ❌")
        print(f"Success rate:   {summary['success_rate']}")
        print(f"\n💾 Detailed results: {summary_file}")
        print(f"📁 All outputs:      {self.output_root}")
        
        return summary
    
    def grade_with_gittaskbench(self, task_id: str) -> Dict:
        """
        Grade a task using GitTaskBench's evaluation framework
        
        Args:
            task_id: Task to grade
            
        Returns:
            Grading results
        """
        try:
            # Import GitTaskBench grading
            from gittaskbench import TaskEvaluator
            
            output_dir = self.output_root / task_id
            
            if not output_dir.exists():
                return {
                    'task_id': task_id,
                    'graded': False,
                    'error': 'Output directory not found. Run task first.'
                }
            
            # Run grading
            evaluator = TaskEvaluator(task_id)
            grade_result = evaluator.grade(output_dir=str(output_dir))
            
            return {
                'task_id': task_id,
                'graded': True,
                'result': grade_result
            }
            
        except ImportError:
            return {
                'task_id': task_id,
                'graded': False,
                'error': 'GitTaskBench grading module not available. Install GitTaskBench properly.'
            }
        except Exception as e:
            return {
                'task_id': task_id,
                'graded': False,
                'error': str(e)
            }