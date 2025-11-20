# from dotenv import load_dotenv
# from pathlib import Path

# # Load environment variables FIRST (before importing anything else)
# env_path = Path(__file__).parent / 'configs' / '.env'
# load_dotenv(env_path, override=True)
from dotenv import load_dotenv
load_dotenv('configs/.env', override=True)


# In any RepoMaster script
from src.gittaskbench.gittaskbench_runner import GitTaskBenchRunner

# Initialize
runner = GitTaskBenchRunner(
    gittaskbench_root='../GitTaskBench',
    output_root='./gittaskbench_output',
    api_type='gemini'
)

# Run single task
result = runner.run_single_task('AnimeGANv3_01')
print(f"Success: {result['success']}")

# # Run batch
# summary = runner.run_batch(task_ids=['Trafilatura_01', 'Trafilatura_02'])
# print(f"Success rate: {summary['success_rate']}")

# # List all tasks
# all_tasks = runner.get_all_tasks()
# print(f"Total tasks: {len(all_tasks)}")