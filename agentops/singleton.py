ao_instances = {}


def singleton(class_):

    def getinstance(*args, **kwargs):
        if class_ not in ao_instances:
            ao_instances[class_] = class_(*args, **kwargs)
        return ao_instances[class_]

    return getinstance


def conditional_singleton(class_):

    def getinstance(*args, **kwargs):
        use_singleton = kwargs.pop("use_singleton", True)
        if use_singleton:
            if class_ not in ao_instances:
                ao_instances[class_] = class_(*args, **kwargs)
            return ao_instances[class_]
        else:
            return class_(*args, **kwargs)

    return getinstance


def clear_singletons():
    global ao_instances
    ao_instances = {}
