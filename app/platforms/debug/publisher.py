from app.core.publisher import Publisher
from app.models.post import Post


class DebugPublisher(Publisher):

    def publish(self, post: Post) -> None:
        print("=== Publishing post ===")
        print(f"Title: {post.title}")
        print(f"Text: {post.text}")
        print(f"Media type: {post.media_type.value}")
        print(f"Media path: {post.media_path}")
        print("=======================")