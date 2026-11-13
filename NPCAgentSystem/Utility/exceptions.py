class StateTransitionException(Exception):
    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        msg = f"Invalid state transition from [{from_state}] to [{to_state}]"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.from_state = from_state
        self.to_state = to_state


class StrategyExecutionException(Exception):
    def __init__(self, strategy_name: str, inner_ex: Exception = None):
        msg = f"Strategy [{strategy_name}] execution failed"
        super().__init__(msg, inner_ex) if inner_ex else super().__init__(msg)
        self.strategy_name = strategy_name


class CommandExecutionException(Exception):
    def __init__(self, command_name: str, inner_ex: Exception = None):
        msg = f"Command [{command_name}] execution failed"
        super().__init__(msg, inner_ex) if inner_ex else super().__init__(msg)
        self.command_name = command_name


class NPCException(Exception):
    def __init__(self, npc_id: str, message: str):
        super().__init__(f"NPC [{npc_id}]: {message}")
        self.npc_id = npc_id
