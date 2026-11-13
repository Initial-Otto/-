from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Callable
from Utility.Logger.logger import game_logger


class DialogueNode:
    def __init__(self, node_id: str, text: str):
        self.node_id = node_id
        self.text = text
        self.options: List['DialogueOption'] = []
        self.next_node_id: Optional[str] = None


class DialogueOption:
    def __init__(self, option_text: str, next_node_id: str, on_select: Callable = None):
        self.option_text = option_text
        self.next_node_id = next_node_id
        self.on_select = on_select


class DialogueData:
    def __init__(self, dialogue_id: str, npc_id: str):
        self.dialogue_id = dialogue_id
        self.npc_id = npc_id
        self.nodes: List[DialogueNode] = []


class DialogueTree:
    def __init__(self, data: DialogueData):
        self.data = data
        self.current_node: Optional[DialogueNode] = None
        if data.nodes:
            self.current_node = data.nodes[0]

    def go_to_node(self, node_id: str):
        for node in self.data.nodes:
            if node.node_id == node_id:
                self.current_node = node
                return
        game_logger.warn(f"Dialogue node [{node_id}] not found")

    def select_option(self, option_index: int):
        if not self.current_node or option_index >= len(self.current_node.options):
            return
        option = self.current_node.options[option_index]
        if option.on_select:
            option.on_select()
        self.go_to_node(option.next_node_id)


class IDialogueManager(ABC):
    @abstractmethod
    def register_dialogue(self, dialogue: DialogueData):
        pass

    @abstractmethod
    def get_dialogue(self, dialogue_id: str) -> Optional[DialogueTree]:
        pass

    @abstractmethod
    def start_dialogue(self, npc_id: str, dialogue_id: str):
        pass

    @abstractmethod
    def end_dialogue(self):
        pass


class DialogueManager(IDialogueManager):
    def __init__(self):
        self._dialogues: Dict[str, DialogueData] = {}
        self._current_dialogue: Optional[DialogueTree] = None

    def register_dialogue(self, dialogue: DialogueData):
        self._dialogues[dialogue.dialogue_id] = dialogue
        game_logger.debug(
            f"Dialogue [{dialogue.dialogue_id}] registered for NPC [{dialogue.npc_id}]"
        )

    def get_dialogue(self, dialogue_id: str) -> Optional[DialogueTree]:
        data = self._dialogues.get(dialogue_id)
        return DialogueTree(data) if data else None

    def start_dialogue(self, npc_id: str, dialogue_id: str):
        data = self._dialogues.get(dialogue_id)
        if data:
            self._current_dialogue = DialogueTree(data)
            game_logger.info(f"Dialogue [{dialogue_id}] started with NPC [{npc_id}]")
        else:
            game_logger.warn(f"Dialogue [{dialogue_id}] not found")

    def end_dialogue(self):
        if self._current_dialogue:
            game_logger.info("Dialogue ended")
            self._current_dialogue = None


class DialogueFactory:
    @staticmethod
    def create_merchant_dialogue(npc_id: str) -> DialogueData:
        data = DialogueData("merchant_greeting", npc_id)

        node_hello = DialogueNode("hello", "欢迎光临！冒险者，需要买点什么吗？")
        node_buy = DialogueNode("buy", "我们这里有各种药水和装备，你想看哪一类？")
        node_sell = DialogueNode("sell", "你有什么好东西要卖给我吗？我可以给你一个公道的价格。")
        node_potion = DialogueNode("potion", "红药水恢复生命，蓝药水恢复法力，都是 20 金币一瓶。要来几瓶？")
        node_equipment = DialogueNode("equipment", "这里有铁剑和皮甲，都是上好的货色，价格也很实惠。")
        node_quest = DialogueNode("quest", "说到任务...最近塔里的怪物越来越多了，如果你能帮我清理一些，我可以给你报酬。")
        node_bye = DialogueNode("bye", "好的，祝你冒险顺利！欢迎下次再来。")

        node_hello.options.append(DialogueOption("我想买点东西", "buy"))
        node_hello.options.append(DialogueOption("我想卖点东西", "sell"))
        node_hello.options.append(DialogueOption("有什么任务吗？", "quest"))
        node_hello.options.append(DialogueOption("只是路过，再见", "bye"))

        node_buy.options.append(DialogueOption("看看药水", "potion"))
        node_buy.options.append(DialogueOption("看看装备", "equipment"))
        node_buy.options.append(DialogueOption("不了，谢谢", "bye"))

        node_sell.options.append(DialogueOption("（拿出背包里的物品）", "bye"))
        node_sell.options.append(DialogueOption("算了，不卖了", "bye"))

        node_potion.options.append(DialogueOption("好的，来一瓶红药水", "bye"))
        node_potion.options.append(DialogueOption("我再想想", "buy"))

        node_equipment.options.append(DialogueOption("铁剑多少钱？", "bye"))
        node_equipment.options.append(DialogueOption("我再考虑考虑", "buy"))

        node_quest.options.append(DialogueOption("没问题，我接受！", "bye"))
        node_quest.options.append(DialogueOption("太危险了，我不去", "bye"))

        data.nodes = [node_hello, node_buy, node_sell, node_potion, node_equipment, node_quest, node_bye]
        return data

    @staticmethod
    def create_guard_dialogue(npc_id: str) -> DialogueData:
        data = DialogueData("guard_greeting", npc_id)

        node_hello = DialogueNode("hello", "站住！这里是守卫区域，你有什么事？")
        node_info = DialogueNode("info", "这座塔里到处都是危险的怪物，你最好小心点。最近上层区域似乎有什么东西在骚动...")
        node_bye = DialogueNode("bye", "去吧，勇敢的冒险者。")

        node_hello.options.append(DialogueOption("请问这里是什么地方？", "info"))
        node_hello.options.append(DialogueOption("我只是路过", "bye"))

        node_info.options.append(DialogueOption("谢谢提醒", "bye"))

        data.nodes = [node_hello, node_info, node_bye]
        return data
