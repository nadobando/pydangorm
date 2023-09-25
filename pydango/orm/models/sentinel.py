import dataclasses

# NOT_SET = LazyFetched()


@dataclasses.dataclass
class LazyFetch:
    def __init__(self, session, instance):
        self.instance = instance
        self.session = session
