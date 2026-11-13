from abc import ABC, abstractmethod
from typing import List, Callable, Optional
from Core.enums import BTResult
from .state import INPCContext
from Utility.Logger.logger import game_logger


# ========== Behavior Tree Pattern ==========

class IBTNode(ABC):
    @property
    @abstractmethod
    def node_name(self) -> str:
        pass

    @abstractmethod
    def execute(self, context: INPCContext) -> BTResult:
        pass


class IBehaviorTree(ABC):
    @abstractmethod
    def tick(self, context: INPCContext) -> BTResult:
        pass

    @abstractmethod
    def add_child(self, node: IBTNode):
        pass

    @abstractmethod
    def set_root(self, root: IBTNode):
        pass


class BehaviorTree(IBehaviorTree):
    def __init__(self):
        self._root: Optional[IBTNode] = None

    def set_root(self, root: IBTNode):
        self._root = root

    def add_child(self, node: IBTNode):
        pass

    def tick(self, context: INPCContext) -> BTResult:
        if not self._root:
            game_logger.warn("Behavior tree has no root node")
            return BTResult.FAILURE
        return self._root.execute(context)


# ========== Composite Nodes ==========

class BTSelector(IBTNode):
    def __init__(self, name: str = "Selector"):
        self._name = name
        self._children: List[IBTNode] = []

    @property
    def node_name(self) -> str:
        return self._name

    def add_child(self, child: IBTNode):
        self._children.append(child)

    def execute(self, context: INPCContext) -> BTResult:
        for child in self._children:
            result = child.execute(context)
            if result == BTResult.SUCCESS:
                return BTResult.SUCCESS
            if result == BTResult.RUNNING:
                return BTResult.RUNNING
        return BTResult.FAILURE


class BTSequence(IBTNode):
    def __init__(self, name: str = "Sequence"):
        self._name = name
        self._children: List[IBTNode] = []

    @property
    def node_name(self) -> str:
        return self._name

    def add_child(self, child: IBTNode):
        self._children.append(child)

    def execute(self, context: INPCContext) -> BTResult:
        for child in self._children:
            result = child.execute(context)
            if result == BTResult.FAILURE:
                return BTResult.FAILURE
            if result == BTResult.RUNNING:
                return BTResult.RUNNING
        return BTResult.SUCCESS


# ========== Leaf Nodes ==========

class BTCondition(IBTNode):
    def __init__(self, name: str, condition: Callable[[INPCContext], bool]):
        self._name = name
        self._condition = condition

    @property
    def node_name(self) -> str:
        return self._name

    def execute(self, context: INPCContext) -> BTResult:
        result = self._condition(context)
        game_logger.debug(f"[{context.npc_id}] Condition [{self._name}]: {result}")
        return BTResult.SUCCESS if result else BTResult.FAILURE


class BTAction(IBTNode):
    def __init__(self, name: str, action: Callable[[INPCContext], BTResult]):
        self._name = name
        self._action = action

    @property
    def node_name(self) -> str:
        return self._name

    def execute(self, context: INPCContext) -> BTResult:
        game_logger.debug(f"[{context.npc_id}] Action [{self._name}]")
        return self._action(context)


# ========== Behavior Tree Factory ==========

class BehaviorTreeFactory:
    @staticmethod
    def create_standard_npc_tree() -> IBehaviorTree:
        tree = BehaviorTree()
        root = BTSelector("RootSelector")

        combat_sequence = BTSequence("CombatSequence")
        combat_sequence.add_child(BTCondition("IsInDanger", lambda ctx: True))
        combat_sequence.add_child(BTAction("AttackTarget", lambda ctx: BTResult.SUCCESS))

        patrol_sequence = BTSequence("PatrolSequence")
        patrol_sequence.add_child(BTCondition("IsPatrolNeeded", lambda ctx: True))
        patrol_sequence.add_child(BTAction("Patrol", lambda ctx: BTResult.SUCCESS))

        root.add_child(combat_sequence)
        root.add_child(patrol_sequence)
        root.add_child(BTAction("Idle", lambda ctx: BTResult.SUCCESS))

        tree.set_root(root)
        return tree
