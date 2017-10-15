
class ArgsSingleton(type):
    """
    A metaclass which permits only a single instance of each derived class
    sharing the same _class_name for any given set of positional 
    arguments.

    Attempts to instantiate a second instance of a derived class, or another
    class with the same _class_name, with the same args will return the
    existing instance.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        key = getattr(cls, '_class_name', cls)
        if key not in cls._instances:
            cls._instances[key] = {}

        if args not in cls._instances[key]:
            cls._instances[key][args] = (
                super(ArgsSingleton, cls).__call__(*args, **kwargs)
            )

        return cls._instances[key][args]


class SmartDeviceSingletonBase(
    ArgsSingleton(str('ArgsSingletonMeta'), (object,), {})
):
    """
    The base class for the Device class.
    """
    pass
