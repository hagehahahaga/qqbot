from abstract.bases.importer import threading, sys
from typing import Optional, Any, Callable, Literal

from abstract.bases.exceptions import CommandCancel


class CustomThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status: Literal['IDLE', 'RUNNING', 'COMPLETED', 'CANCELLING', 'CANCELLED', 'ERROR'] = 'IDLE'
        self._result: Optional[Any] = None
        self._exception: Optional[Exception] = None
        self.callback: set[Callable] = set()

    def _trace(self, frame: Any, event: str, arg: Any) -> Optional[Callable]:
        if self.status == 'CANCELLING':
            raise CommandCancel('用户取消.')
        return self._trace

    def get_result(self, timeout=None) -> Any:
        """
        Wait for the thread to finish and return the result.
        If the thread raises an exception, it will be re-raised here.

        :param timeout: The maximum time to wait for the thread to finish. If None, wait indefinitely.
        :type timeout: Optional[float]
        :return: The result of the thread's target function.
        :rtype: Any
        :raises TimeoutError: If the thread does not finish within the specified timeout.
        :raises Exception: Re-raises any exception raised by the thread's target function.
        """
        self.join(timeout=timeout)
        if self.is_alive():
            raise TimeoutError('Thread did not finish within the specified timeout.')
        if self._exception:
            raise self._exception
        return self._result

    def register_callback(self, function: Callable) -> None:
        """
        Register a callback function to be called when the thread finishes.
        The function should accept two arguments: the result and the exception (if any).

        :param function: The callback function to register.
        :type function: Callable[[Optional[Any], Optional[Exception]]]
        :return: None
        :rtype: None
        """
        self.callback.add(function)

    def stop(self, timeout: Optional[int | float] = 0) -> None:
        assert self.status == 'RUNNING', 'Cannot stop a thread that is not running.'
        self.status = 'CANCELLING'
        self.join(timeout=timeout)

    def run(self) -> None:
        self.status = 'RUNNING'
        try:
            original_trace = sys.gettrace()
            sys.settrace(self._trace)  # 只对当前线程设置跟踪，而不是全局所有线程
            self._result = self._target(*self._args, **self._kwargs)
            self.status = 'COMPLETED'
        except CommandCancel as e:
            self._exception = e  # 正确存储 CommandCancel 异常
            self.status = 'CANCELLED'
        except Exception as e:
            self._exception = e
            self.status = 'ERROR'
        finally:
            sys.settrace(original_trace)
            for func in self.callback:
                try:
                    func(self._result, self._exception)
                except:
                    pass