from abc import ABC, abstractmethod


class BaseKiller(ABC):
    @abstractmethod
    def list_environments(self) -> list:
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def remove_environment(self, env_to_delete: str):
        raise NotImplementedError("Subclasses must implement this method")
