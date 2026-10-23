from app.agents.state import AgentState
from app.agents.executor import executor_node


def coder_node(state: AgentState) -> AgentState:
    """
    Coder node (delegates to enhanced executor node for safe tool operations and code synthesis).
    Maintains full backwards compatibility with existing graph topologies and unit tests.
    """
    return executor_node(state)
