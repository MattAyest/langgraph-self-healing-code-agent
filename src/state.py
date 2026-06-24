from typing import TypedDict, List, Dict, Any


class SwarmState(TypedDict):
    messages: List[Any]
    workspace_dir: str
    file_manifest: Dict[str, str]
    next_node: str
    loop_count: int
    regression_count: int
    replan_count: int           # increments each time error_distiller forces architect; hard ceiling prevents infinite spec loops
    verification_errors: str
    rollback_graveyard: List[str]
    architectural_plan: str
    interface_contract: str     # formal interface spec written by architect, used by test_writer
    contract_check_count: int   # loop guard for contract_verifier → test_writer retries
    architecture_ledger: str    # accumulated across retries; written to disk by archivist_node
