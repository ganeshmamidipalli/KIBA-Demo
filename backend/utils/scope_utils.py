"""
Scope utilities for KPA One-Flow.
Handles scope normalization and merging with follow-up answers.
"""

from typing import Dict, List, Any

def merge_scope_with_answers(scope_text: str, answers: Dict[str, str]) -> str:
    """
    Merge original scope with follow-up answers.
    
    Args:
        scope_text: Original scope text
        answers: Dictionary of question -> answer pairs
        
    Returns:
        Merged scope text
    """
    out = [scope_text.strip()] if scope_text else []
    
    for question, answer in answers.items():
        if question and answer and answer.strip():
            out.append(f"Q: {question}\nA: {answer.strip()}")
    
    return "\n\n".join(out)

def normalize_scope(
    scope_text: str, 
    uploaded_summaries: List[str], 
    project_ctx: Dict[str, Any], 
    vendors: List[str]
) -> str:
    """
    Normalize and structure scope information from multiple sources.
    
    Args:
        scope_text: User-provided scope text
        uploaded_summaries: Extracted text from uploaded files
        project_ctx: Project context information
        vendors: Preferred vendors list
        
    Returns:
        Normalized scope text
    """
    blocks = []
    
    # Project context
    if project_ctx:
        ctx_parts = []
        if project_ctx.get("project_name"):
            ctx_parts.append(f"Project: {project_ctx['project_name']}")
        if project_ctx.get("procurement_type"):
            ctx_parts.append(f"Type: {project_ctx['procurement_type']}")
        if project_ctx.get("service_program"):
            ctx_parts.append(f"Program: {project_ctx['service_program']}")
        if project_ctx.get("technical_poc"):
            ctx_parts.append(f"POC: {project_ctx['technical_poc']}")
        
        if ctx_parts:
            blocks.append(f"PROJECT_CONTEXT:\n" + "\n".join(ctx_parts))
    
    # Preferred vendors
    if vendors:
        vendor_list = ", ".join([v.strip() for v in vendors if v.strip()])
        if vendor_list:
            blocks.append(f"PREFERRED_VENDORS: {vendor_list}")
    
    # Uploaded summaries
    if uploaded_summaries:
        clean_summaries = [s.strip() for s in uploaded_summaries if s.strip()]
        if clean_summaries:
            blocks.append("UPLOADED_SUMMARIES:\n- " + "\n- ".join(clean_summaries))
    
    # User scope
    if scope_text and scope_text.strip():
        blocks.append(f"USER_SCOPE:\n{scope_text.strip()}")
    
    return "\n\n".join(blocks) if blocks else "No additional scope provided."
