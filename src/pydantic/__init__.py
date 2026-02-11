from __future__ import annotations


def Field(default=None, description: str | None = None):
    return default


class BaseModel:
    def __init__(self, **kwargs):
        anns = getattr(self, "__annotations__", {})
        for name in anns:
            if name in kwargs:
                value = kwargs[name]
            else:
                value = getattr(self.__class__, name)
            current = getattr(self.__class__, name, None)
            if isinstance(current, BaseModel) and isinstance(value, dict):
                value = current.__class__.model_validate(value)
            setattr(self, name, value)

    @classmethod
    def model_validate(cls, raw: dict):
        obj = cls()
        for key, value in raw.items():
            current = getattr(obj, key, None)
            if isinstance(current, BaseModel) and isinstance(value, dict):
                setattr(obj, key, current.__class__.model_validate(value))
            else:
                setattr(obj, key, value)
        return obj
