from abc import ABC, abstractmethod

from app.models.post import Post


class Publisher(ABC):

    @abstractmethod
    def publish(self, post: Post) -> None:
        pass