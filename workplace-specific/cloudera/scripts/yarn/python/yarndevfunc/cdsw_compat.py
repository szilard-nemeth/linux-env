import logging
from argparse import ArgumentParser
from typing import List

LOG = logging.getLogger(__name__)

# https://www.michaelcho.me/article/method-delegation-in-python


class Delegator:
    def __getattr__(self, called_method):
        def __raise_standard_exception():
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, called_method))

        def __invoke_method_action(method_actions, called_method, *args, **kwargs):
            if called_method in method_actions:
                args, kwargs = method_actions[called_method].perform(called_method, *args, **kwargs)
                return args, kwargs
            return args, kwargs

        def wrapper(*args, **kwargs):
            delegation_config = getattr(self, "DELEGATED_METHODS", None)
            if not isinstance(delegation_config, dict):
                __raise_standard_exception()

            method_actions = getattr(self, "DELEGATED_METHOD_ACTIONS", None)
            if not isinstance(method_actions, dict):
                __raise_standard_exception()

            delegate_object_str = None
            for delegate_object_str, delegated_methods in delegation_config.items():
                if called_method in delegated_methods:
                    break
                else:
                    __raise_standard_exception()

            if delegate_object_str:
                delegate_object = getattr(self, delegate_object_str, None)
                __invoke_method_action(method_actions, called_method, *args, **kwargs)
                return getattr(delegate_object, called_method)(*args, **kwargs)
            else:
                default_delegate_obj = getattr(self, "DEFAULT_DELEGATE_OBJ", None)
                if not default_delegate_obj:
                    raise AttributeError("DEFAULT_DELEGATE_OBJ is not defined!")
                args, kwargs = __invoke_method_action(method_actions, called_method, *args, **kwargs)
                return getattr(default_delegate_obj, called_method)(*args, **kwargs)

        return wrapper


class RemoveKwArgDelegatedMethodAction:
    def __init__(self, kwarg_names: List):
        self.kwarg_names = kwarg_names

    def perform(self, method_name, *args, **kwargs):
        for kwarg_name in self.kwarg_names:
            if kwarg_name in kwargs:
                LOG.info(f"Removing {kwarg_name} from kwargs of method call '{method_name}'. kwargs was: {kwargs}")
                del kwargs[kwarg_name]
        return args, kwargs


class DelegatedArgumentParser(Delegator):
    DEFAULT_DELEGATE_OBJ = ArgumentParser()
    DELEGATED_METHODS = {}
    DELEGATED_METHOD_ACTIONS = {"add_subparsers": RemoveKwArgDelegatedMethodAction(["required"])}
