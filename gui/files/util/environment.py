from dataclasses import dataclass, field, asdict
from typing import Optional

@dataclass
class Environment:
    """実行環境設定オブジェクト。
    不変（frozen）として定義し、テストやGUIからの注入に適するようにする。
    """
    register_num: int = 8
    register_bit: int = 16
    memory_length: int = 65536
    cpu_impl: Optional[object] = None
    window_impl: Optional[object] = None

    def to_dict(self):
        return asdict(self)


# モジュールレベルの現在の環境（互換用シングルトン・フォールバック）
_current_env: Environment = Environment()


def create_default_environment(register_num: int = 8, register_bit: int = 16, memory_length: int = 65536) -> Environment:
    """デフォルトの Environment を作成して返す（テストや起動箇所で使用）。"""
    return Environment(register_num=register_num, register_bit=register_bit, memory_length=memory_length)


def get_current_environment() -> Environment:
    return _current_env


def set_current_environment(env: Environment) -> None:
    """現在の環境を差し替える。グローバルな副作用を許容するアプリでのみ使用すること。"""
    global _current_env
    _current_env = env
