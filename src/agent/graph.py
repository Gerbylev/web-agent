from langgraph.graph import END, StateGraph

from agent.nodes import decision_maker, execute_click, execute_command, execute_type, execute_wait, fail_node, next_step, should_continue, success_node
from agent.state import AgentState


def create_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("decision_node", decision_maker)
    workflow.add_node("click_node", execute_click)
    workflow.add_node("type_node", execute_type)
    workflow.add_node("command_node", execute_command)
    workflow.add_node("wait_node", execute_wait)
    workflow.add_node("next_step_node", next_step)
    workflow.add_node("success_node", success_node)
    workflow.add_node("fail_node", fail_node)

    workflow.set_entry_point("decision_node")

    workflow.add_conditional_edges(
        "decision_node",
        lambda state: "success_node"
        if state.get("goal_achieved")
        else "fail_node"
        if state.get("goal_failed")
        else "next_step_node"
        if state.get("action_queue")
        else "error_node",
        {"success_node": "success_node", "fail_node": "fail_node", "next_step_node": "next_step_node", "error_node": END},
    )

    workflow.add_conditional_edges(
        "next_step_node",
        should_continue,
        {
            "click_node": "click_node",
            "click_element_node": "click_node",
            "type_node": "type_node",
            "command_node": "command_node",
            "wait_node": "wait_node",
            "decision_node": "decision_node",
            "success_node": "success_node",
            "fail_node": "fail_node",
            "error_node": END,
        },
    )

    workflow.add_edge("click_node", "next_step_node")
    workflow.add_edge("type_node", "next_step_node")
    workflow.add_edge("command_node", "next_step_node")
    workflow.add_edge("wait_node", "next_step_node")

    workflow.add_edge("success_node", END)
    workflow.add_edge("fail_node", END)

    return workflow.compile()
