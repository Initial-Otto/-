from abc import ABC, abstractmethod
from typing import List
from Core.vector import Vector2
from Utility.exceptions import CommandExecutionException
from Utility.Logger.logger import game_logger


# ========== Command Pattern ==========

class ICommand(ABC):
    @property
    @abstractmethod
    def command_name(self) -> str:
        pass

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        pass


class MoveCommand(ICommand):
    def __init__(self, npc_id: str, target: Vector2):
        self._npc_id = npc_id
        self._target = target
        self._previous_position = Vector2.zero()

    @property
    def command_name(self) -> str:
        return "Move"

    def execute(self):
        game_logger.debug(f"[{self._npc_id}] MoveCommand: Moving to {self._target.x}, {self._target.y}")

    def undo(self):
        game_logger.debug(f"[{self._npc_id}] MoveCommand: Undo move")


class AttackCommand(ICommand):
    def __init__(self, npc_id: str, target_id: str):
        self._npc_id = npc_id
        self._target_id = target_id
        self._has_executed = False

    @property
    def command_name(self) -> str:
        return "Attack"

    def execute(self):
        game_logger.info(f"[{self._npc_id}] AttackCommand: Attacking {self._target_id}")
        self._has_executed = True

    def undo(self):
        if self._has_executed:
            game_logger.debug(f"[{self._npc_id}] AttackCommand: Undo attack")
            self._has_executed = False


class SpeakCommand(ICommand):
    def __init__(self, npc_id: str, dialogue_id: str):
        self._npc_id = npc_id
        self._dialogue_id = dialogue_id

    @property
    def command_name(self) -> str:
        return "Speak"

    def execute(self):
        game_logger.info(f"[{self._npc_id}] SpeakCommand: Playing dialogue {self._dialogue_id}")

    def undo(self):
        game_logger.debug(f"[{self._npc_id}] SpeakCommand: Stop dialogue")


class UseSkillCommand(ICommand):
    def __init__(self, npc_id: str, skill_id: int):
        self._npc_id = npc_id
        self._skill_id = skill_id

    @property
    def command_name(self) -> str:
        return "UseSkill"

    def execute(self):
        game_logger.info(f"[{self._npc_id}] UseSkillCommand: Using skill {self._skill_id}")

    def undo(self):
        game_logger.debug(f"[{self._npc_id}] UseSkillCommand: Cancel skill")


# ========== Command Queue ==========

class CommandQueue:
    def __init__(self, max_history_size: int = 50):
        self._commands: List[ICommand] = []
        self._undo_history: List[ICommand] = []
        self._max_history_size = max_history_size

    @property
    def command_count(self) -> int:
        return len(self._commands)

    @property
    def can_undo(self) -> bool:
        return len(self._undo_history) > 0

    def enqueue(self, command: ICommand):
        self._commands.append(command)
        game_logger.debug(f"Command [{command.command_name}] enqueued. Queue size: {len(self._commands)}")

    def execute(self):
        if not self._commands:
            return

        command = self._commands.pop(0)
        try:
            command.execute()
            self._undo_history.append(command)
            if len(self._undo_history) > self._max_history_size:
                self._undo_history.pop(0)
        except Exception as ex:
            game_logger.error(f"Command [{command.command_name}] execution failed: {ex}", ex)
            raise CommandExecutionException(command.command_name, ex)

    def execute_all(self):
        while self._commands:
            self.execute()

    def undo(self):
        if not self.can_undo:
            game_logger.warn("Cannot undo: no history")
            return

        command = self._undo_history.pop()
        try:
            command.undo()
            game_logger.debug(f"Command [{command.command_name}] undone")
        except Exception as ex:
            game_logger.error(f"Command [{command.command_name}] undo failed: {ex}", ex)

    def clear(self):
        self._commands.clear()
        self._undo_history.clear()


# ========== Action Executor ==========

class IActionExecutor(ABC):
    @abstractmethod
    def execute_command(self, command: ICommand):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def get_command_queue(self) -> CommandQueue:
        pass


class ActionExecutor(IActionExecutor):
    def __init__(self):
        self._command_queue = CommandQueue()

    def execute_command(self, command: ICommand):
        self._command_queue.enqueue(command)

    def update(self):
        self._command_queue.execute()

    def get_command_queue(self) -> CommandQueue:
        return self._command_queue
