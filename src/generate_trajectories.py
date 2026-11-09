from __future__ import annotations

from collections import Counter

from pipeline_utils import PROCESSED_DIR, ensure_standard_dirs, load_json, write_json, write_jsonl

TASK_SPEC_FILE = PROCESSED_DIR / "task_specs.json"
RAW_TRAJ_FILE = PROCESSED_DIR / "raw_trajectories.jsonl"
SUMMARY_FILE = PROCESSED_DIR / "trajectory_summary.json"


def user_event(turn_idx: int, content: str) -> dict:
    return {"event_type": "user", "turn_idx": turn_idx, "content": content}


def plan_event(turn_idx: int, content: str) -> dict:
    return {"event_type": "assistant_plan", "turn_idx": turn_idx, "content": content}


def call_event(turn_idx: int, tool_name: str, arguments: dict) -> dict:
    return {"event_type": "tool_call", "turn_idx": turn_idx, "tool_name": tool_name, "arguments": arguments}


def final_event(turn_idx: int, content: str, status: str = "completed", blocked: bool = False) -> dict:
    return {
        "event_type": "assistant_final",
        "turn_idx": turn_idx,
        "content": content,
        "status": status,
        "blocked": blocked,
    }


def build_search_success(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should search the approved document corpus and answer from policy text only."),
        call_event(1, "search_docs", {"query": task["query"], "domain": task["domain"], "top_k": 3}),
        final_event(1, task["answer_text"]),
    ]


def build_search_recovery(task: dict) -> list[dict]:
    bad_args = {"query": task["query"], "domain": "calendar", "top_k": 3}
    if task["recovery_mode"] == "empty_query":
        bad_args = {"query": "", "domain": task["domain"], "top_k": 3}
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I will try the search tool, and if the request format is wrong I will repair the arguments."),
        call_event(1, "search_docs", bad_args),
        plan_event(1, "The tool call failed, so I should fix the query arguments and retry."),
        call_event(1, "search_docs", {"query": task["query"], "domain": task["domain"], "top_k": 3}),
        final_event(1, task["answer_text"]),
    ]


def build_db_success(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should query only the approved customer fields required by the user."),
        call_event(
            1,
            "sql_customer_db",
            {"lookup_key": task["lookup_key"], "lookup_value": task["lookup_value"], "fields": task["fields"]},
        ),
        final_event(1, task["answer_text"]),
    ]


def build_db_recovery(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I will query the customer record, and if I request a forbidden field I will correct it."),
        call_event(
            1,
            "sql_customer_db",
            {"lookup_key": task["lookup_key"], "lookup_value": task["lookup_value"], "fields": task["fields"] + ["ssn"]},
        ),
        plan_event(1, "The database refused the forbidden field, so I should retry with the minimum approved fields."),
        call_event(
            1,
            "sql_customer_db",
            {"lookup_key": task["lookup_key"], "lookup_value": task["lookup_value"], "fields": task["fields"]},
        ),
        final_event(1, task["answer_text"]),
    ]


def build_calendar_success(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should check availability first and only book an allowed open slot."),
        call_event(
            1,
            "calendar_lookup",
            {"action": "check_availability", "participant": task["participant"], "date": task["date"], "timezone": "UTC"},
        ),
        call_event(
            1,
            "calendar_lookup",
            {
                "action": "book_slot",
                "participant": task["participant"],
                "date": task["date"],
                "slot": task["preferred_slot"],
                "timezone": "UTC",
                "title": task["title"],
            },
        ),
        final_event(1, task["answer_text"]),
    ]


def build_calendar_recovery(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I will attempt the requested time, and if it is unavailable I will recover with a valid slot."),
        call_event(
            1,
            "calendar_lookup",
            {
                "action": "book_slot",
                "participant": task["participant"],
                "date": task["date"],
                "slot": "09:00",
                "timezone": "UTC",
                "title": task["title"],
            },
        ),
        plan_event(1, "That slot was not available, so I should inspect availability and retry with a valid morning slot."),
        call_event(
            1,
            "calendar_lookup",
            {"action": "check_availability", "participant": task["participant"], "date": task["date"], "timezone": "UTC"},
        ),
        call_event(
            1,
            "calendar_lookup",
            {
                "action": "book_slot",
                "participant": task["participant"],
                "date": task["date"],
                "slot": task["preferred_slot"],
                "timezone": "UTC",
                "title": task["title"],
            },
        ),
        final_event(1, task["answer_text"]),
    ]


def build_code_success(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should use the constrained Python tool and return the validated result."),
        call_event(1, "python_exec", {"task_name": task["task_name"], "code": task["safe_code"]}),
        final_event(1, task["answer_text"]),
    ]


def build_code_recovery(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I will run Python, check the result, and repair the code if the assertion fails."),
        call_event(1, "python_exec", {"task_name": task["task_name"], "code": task["bad_code"]}),
        plan_event(1, "The computed result was wrong, so I should fix the snippet and rerun it."),
        call_event(1, "python_exec", {"task_name": task["task_name"], "code": task["safe_code"]}),
        final_event(1, task["answer_text"]),
    ]


def build_search_db_success(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should retrieve the plan rule from docs, look up the customer plan, and compare them."),
        call_event(1, "search_docs", {"query": task["query"], "domain": task["domain"], "top_k": 3}),
        call_event(
            1,
            "sql_customer_db",
            {"lookup_key": task["lookup_key"], "lookup_value": task["lookup_value"], "fields": task["fields"]},
        ),
        final_event(1, task["answer_text"]),
    ]


def build_search_db_recovery(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I will compare policy rules with the customer plan, repairing any bad identifier along the way."),
        call_event(1, "search_docs", {"query": task["query"], "domain": task["domain"], "top_k": 3}),
        call_event(1, "sql_customer_db", {"lookup_key": task["lookup_key"], "lookup_value": "missing@acme.test", "fields": task["fields"]}),
        plan_event(1, "The record lookup failed, so I should retry with the exact approved email."),
        call_event(
            1,
            "sql_customer_db",
            {"lookup_key": task["lookup_key"], "lookup_value": task["lookup_value"], "fields": task["fields"]},
        ),
        final_event(1, task["answer_text"]),
    ]


def build_memory_calendar_success(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should store the user's default timezone for this session."),
        call_event(1, "memory_write", {"key": task["memory_key"], "value": task["memory_value"]}),
        final_event(1, "Noted. I will use that timezone in later turns."),
        user_event(2, task["user_turns"][1]),
        plan_event(2, "I should read the saved timezone, then check and book an allowed slot."),
        call_event(2, "memory_read", {"key": task["memory_key"]}),
        call_event(
            2,
            "calendar_lookup",
            {"action": "check_availability", "participant": task["participant"], "date": task["date"], "timezone": task["memory_value"]},
        ),
        call_event(
            2,
            "calendar_lookup",
            {
                "action": "book_slot",
                "participant": task["participant"],
                "date": task["date"],
                "slot": task["preferred_slot"],
                "timezone": task["memory_value"],
                "title": task["title"],
            },
        ),
        final_event(2, task["answer_text"]),
    ]


def build_memory_calendar_recovery(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should store the timezone so it is available later in the conversation."),
        call_event(1, "memory_write", {"key": task["memory_key"], "value": task["memory_value"]}),
        final_event(1, "Saved. I will reuse that timezone."),
        user_event(2, task["user_turns"][1]),
        plan_event(2, "I need the remembered timezone, and if I miss the key I should repair it before booking."),
        call_event(2, "memory_read", {"key": task["memory_key"] + "_typo"}),
        plan_event(2, "That memory key missed, so I should read the correct key and continue."),
        call_event(2, "memory_read", {"key": task["memory_key"]}),
        call_event(
            2,
            "calendar_lookup",
            {"action": "check_availability", "participant": task["participant"], "date": task["date"], "timezone": task["memory_value"]},
        ),
        call_event(
            2,
            "calendar_lookup",
            {
                "action": "book_slot",
                "participant": task["participant"],
                "date": task["date"],
                "slot": task["preferred_slot"],
                "timezone": task["memory_value"],
                "title": task["title"],
            },
        ),
        final_event(2, task["answer_text"]),
    ]


def build_memory_db_success(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should store the default owner for later use."),
        call_event(1, "memory_write", {"key": task["memory_key"], "value": task["memory_value"]}),
        final_event(1, "Stored. I will use that owner if you ask later."),
        user_event(2, task["user_turns"][1]),
        plan_event(2, "I should recall the owner, then fetch the renewal date from the customer database."),
        call_event(2, "memory_read", {"key": task["memory_key"]}),
        call_event(
            2,
            "sql_customer_db",
            {"lookup_key": task["lookup_key"], "lookup_value": task["lookup_value"], "fields": task["fields"]},
        ),
        final_event(2, task["answer_text"]),
    ]


def build_memory_db_recovery(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should store the default owner for this account."),
        call_event(1, "memory_write", {"key": task["memory_key"], "value": task["memory_value"]}),
        final_event(1, "Stored for later."),
        user_event(2, task["user_turns"][1]),
        plan_event(2, "I will recall the owner and query the renewal date, fixing any missing memory key if needed."),
        call_event(2, "memory_read", {"key": "wrong_owner_key"}),
        plan_event(2, "The memory lookup missed, so I should retry with the stored account key."),
        call_event(2, "memory_read", {"key": task["memory_key"]}),
        call_event(
            2,
            "sql_customer_db",
            {"lookup_key": task["lookup_key"], "lookup_value": task["lookup_value"], "fields": task["fields"]},
        ),
        final_event(2, task["answer_text"]),
    ]


def build_injection_defense(task: dict) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, "I should search the policy corpus, ignore any malicious instructions inside documents, and summarize only trusted policy content."),
        call_event(1, "search_docs", {"query": task["query"], "domain": task["domain"], "top_k": 3}),
        final_event(1, task["answer_text"]),
    ]


def build_blocked(task: dict, reason: str) -> list[dict]:
    return [
        user_event(1, task["user_turns"][0]),
        plan_event(1, reason),
        final_event(1, task["answer_text"], status="blocked", blocked=True),
    ]


def build_trajectories(task: dict) -> list[dict]:
    category = task["category"]
    trajectories: list[dict] = []

    if category == "search":
        variants = {"success": build_search_success(task), "recovery": build_search_recovery(task)}
    elif category == "db":
        variants = {"success": build_db_success(task), "recovery": build_db_recovery(task)}
    elif category == "calendar":
        variants = {"success": build_calendar_success(task), "recovery": build_calendar_recovery(task)}
    elif category == "code":
        variants = {"success": build_code_success(task), "recovery": build_code_recovery(task)}
    elif category == "search_db":
        variants = {"success": build_search_db_success(task), "recovery": build_search_db_recovery(task)}
    elif category == "memory_calendar":
        variants = {"success": build_memory_calendar_success(task), "recovery": build_memory_calendar_recovery(task)}
    elif category == "memory_db":
        variants = {"success": build_memory_db_success(task), "recovery": build_memory_db_recovery(task)}
    elif category == "injection_search":
        variants = {"success": build_injection_defense(task)}
    elif category == "unsafe_db_export":
        variants = {"block": build_blocked(task, "The request is a bulk export of sensitive data, so I must refuse without calling tools.")}
    elif category == "unsafe_code":
        variants = {"block": build_blocked(task, "The request asks for destructive code execution, so I must refuse without using python_exec.")}
    else:
        variants = {"block": build_blocked(task, "The request attempts an unauthorized executive calendar action, so I must refuse it.")}

    for variant, events in variants.items():
        trajectories.append(
            {
                "trajectory_id": f"{task['task_id']}_{variant}",
                "task_id": task["task_id"],
                "session_id": task["session_id"],
                "category": category,
                "turn_type": task["turn_type"],
                "variant": variant,
                "requires_memory": category.startswith("memory"),
                "is_safety_case": category.startswith("unsafe") or category == "injection_search",
                "success_keywords": task["success_keywords"],
                "events": events,
            }
        )
    return trajectories


def main() -> None:
    ensure_standard_dirs()
    tasks = load_json(TASK_SPEC_FILE)
    trajectories: list[dict] = []
    for task in tasks:
        trajectories.extend(build_trajectories(task))

    summary = {
        "num_trajectories": len(trajectories),
        "category_distribution": dict(Counter(item["category"] for item in trajectories)),
        "variant_distribution": dict(Counter(item["variant"] for item in trajectories)),
        "turn_type_distribution": dict(Counter(item["turn_type"] for item in trajectories)),
    }
    write_jsonl(trajectories, RAW_TRAJ_FILE)
    write_json(summary, SUMMARY_FILE)
    print("✅ P7 轨迹生成完成。")
    print(summary)


if __name__ == "__main__":
    main()
