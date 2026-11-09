# P7 Test Report

- Overall status: PASS
- Passed checks: 13/13

## Command Checks

- py_compile: PASS
  - Command: `/usr/bin/python3 -m py_compile /home/nan/projects/data_engineering_book/code/zh/project_7_agent_tooluse/src/build_tooling.py /home/nan/projects/data_engineering_book/code/zh/project_7_agent_tooluse/src/evaluate_tooluse.py /home/nan/projects/data_engineering_book/code/zh/project_7_agent_tooluse/src/generate_trajectories.py /home/nan/projects/data_engineering_book/code/zh/project_7_agent_tooluse/src/pipeline_utils.py /home/nan/projects/data_engineering_book/code/zh/project_7_agent_tooluse/src/prepare_agent_dataset.py /home/nan/projects/data_engineering_book/code/zh/project_7_agent_tooluse/src/run_p7_checks.py /home/nan/projects/data_engineering_book/code/zh/project_7_agent_tooluse/src/simulate_tool_env.py`
- evaluate_tooluse: PASS
  - Command: `/usr/bin/python3 /home/nan/projects/data_engineering_book/code/zh/project_7_agent_tooluse/src/evaluate_tooluse.py`

## Dataset Checks

- required_files_exist: PASS
  - Details: `{}`
- tool_schema_fields_complete: PASS
  - Details: `{'tool_schema_count': 6}`
- templates_cover_single_multi_and_safety: PASS
  - Details: `{'template_ids': ['single_tool_success', 'multi_tool_chain', 'argument_fix_recovery', 'multi_turn_memory', 'safety_refusal']}`
- variant_coverage: PASS
  - Details: `{'variant_distribution': {'success': 10, 'recovery': 9, 'block': 3}}`
- observations_and_decision_chain_present: PASS
  - Details: `{'num_trajectories': 22}`
- memory_cases_succeed: PASS
  - Details: `{'memory_case_count': 4}`
- safety_cases_blocked_without_tools: PASS
  - Details: `{'safety_case_count': 3}`
- train_val_no_overlap: PASS
  - Details: `{'overlap': 0}`
- train_val_no_task_overlap: PASS
  - Details: `{'overlap': [], 'num_train_tasks': 11, 'num_val_tasks': 2}`
- smoke_covers_general_memory_safety: PASS
  - Details: `{'general': True, 'memory': True, 'safety': True}`
- manifest_matches_record_count: PASS
  - Details: `{'num_records': 94, 'num_train_records': 78, 'num_val_records': 16, 'num_smoke_records': 12, 'category_distribution': {'calendar': 9, 'code': 14, 'db': 7, 'memory_db': 15, 'memory_calendar': 17, 'search_db': 9, 'injection_search': 3, 'search': 14, 'unsafe_calendar': 2, 'unsafe_code': 2, 'unsafe_db_export': 2}, 'variant_distribution': {'recovery': 47, 'success': 41, 'block': 6}, 'target_event_distribution': {'assistant_plan': 35, 'tool_call': 33, 'assistant_final': 26}, 'safety_record_count': 9, 'memory_record_count': 32, 'estimated_tokens_total': 5838}`