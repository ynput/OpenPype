import collections
import inspect


def get_available_traits_ids() -> set:
    """
    Get the list of available trait ids.

    Returns:
        set: set of trait ids
    """

    import openpype.pipeline.traits.generated as traits

    queue = collections.deque()
    queue.append(traits)
    traits = set()
    while queue:
        item = queue.popleft()
        for name in dir(item):
            value = getattr(item, name)
            if inspect.ismodule(value):
                queue.append(value)
                continue
            if inspect.isclass(value) and hasattr(value, "kId"):
                traits.add(value.kId)

    return traits
