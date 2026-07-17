# Windows CI Report

## 2026-07-14 11:28:46 +03:00 - commit `f33f5e0125013f44b3907e56a09146e2715f6562`

Role: QA & MOCK-TUNER.

Repository was pulled before this run and was already up to date. The normal `python` / `py` launchers failed on this Windows machine with a logon-session credential error, so the bundled Codex Python runtime was used after installing `requirements.txt`.

Command:

``powershell
& "C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests -q
``

Result: FAIL.

Summary:

- Captured full output in `tuning/pytest-windows-f33f5e0-full.txt`.
- Latest captured suite result: `61 passed, 8 errors`.
- All captured errors are `PermissionError: [WinError 5] Access is denied: 'C:\Users\tsion\AppData\Local\Temp\pytest-of-tsion'` while pytest is preparing `tmp_path` fixtures.
- The first unredirected run after setup also displayed transient FSM failures before the full-output rerun was captured: `2 failed, 59 passed, 8 errors`.

Full pytest output:

``text
EEE.....................................E........E................EEE    [100%]
=================================== ERRORS ====================================
__________________ ERROR at setup of test_hover_flight_clean __________________

cls = <class '_pytest.runner.CallInfo'>
func = <function call_and_report.<locals>.<lambda> at 0x0000022759AA40E0>
when = 'setup'
reraise = (<class '_pytest.outcomes.Exit'>, <class 'KeyboardInterrupt'>)

    @classmethod
    def from_call(
        cls,
        func: Callable[[], TResult],
        when: Literal["collect", "setup", "call", "teardown"],
        reraise: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> CallInfo[TResult]:
        """Call func, wrapping the result in a CallInfo.
    
        :param func:
            The function to call. Called without arguments.
        :type func: Callable[[], _pytest.runner.TResult]
        :param when:
            The phase in which the function is called.
        :param reraise:
            Exception or exceptions that shall propagate if raised by the
            function, instead of being wrapped in the CallInfo.
        """
        excinfo = None
        instant = timing.Instant()
        try:
>           result: TResult | None = func()
                                     ^^^^^^

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:361: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:250: in <lambda>
    lambda: runtest_hook(item=item, **kwds),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\logging.py:858: in pytest_runtest_setup
    yield
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\capture.py:895: in pytest_runtest_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:170: in pytest_runtest_setup
    item.session._setupstate.setup(item)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:536: in setup
    col.setup()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\python.py:1710: in setup
    self._request._fillfixtures()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:806: in _fillfixtures
    item.funcargs[argname] = self.getfixturevalue(argname)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:630: in getfixturevalue
    fixturedef = self._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1181: in execute
    fixturedef = request._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1232: in execute
    result: FixtureValue = ihook.pytest_fixture_setup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\setuponly.py:36: in pytest_fixture_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1328: in pytest_fixture_setup
    result = call_fixture_func(fixturefunc, request, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:998: in call_fixture_func
    fixture_result = next(generator)
                     ^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:300: in tmp_path
    path = _mk_tmp(request, tmp_path_factory)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:287: in _mk_tmp
    return factory.mktemp(name, numbered=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:136: in mktemp
    basename = self._ensure_relative_to_basetemp(basename)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:117: in _ensure_relative_to_basetemp
    if (self.getbasetemp() / basename).resolve().parent != self.getbasetemp():
        ^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:213: in getbasetemp
    basetemp = make_numbered_dir_with_cleanup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:420: in make_numbered_dir_with_cleanup
    raise e
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:401: in make_numbered_dir_with_cleanup
    p = make_numbered_dir(root, prefix, mode)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:228: in make_numbered_dir
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:187: in extract_suffixes
    for entry in iter:
                 ^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

root = WindowsPath('C:/Users/tsion/AppData/Local/Temp/pytest-of-tsion')
prefix = 'pytest-'

    def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:
        """Find all elements in root that begin with the prefix, case-insensitive."""
        l_prefix = prefix.lower()
>       for x in os.scandir(root):
                 ^^^^^^^^^^^^^^^^
E       PermissionError: [WinError 5] Access is denied: 'C:\\Users\\tsion\\AppData\\Local\\Temp\\pytest-of-tsion'

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
___________________ ERROR at setup of test_single_gate_pass ___________________

cls = <class '_pytest.runner.CallInfo'>
func = <function call_and_report.<locals>.<lambda> at 0x0000022759AA7B00>
when = 'setup'
reraise = (<class '_pytest.outcomes.Exit'>, <class 'KeyboardInterrupt'>)

    @classmethod
    def from_call(
        cls,
        func: Callable[[], TResult],
        when: Literal["collect", "setup", "call", "teardown"],
        reraise: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> CallInfo[TResult]:
        """Call func, wrapping the result in a CallInfo.
    
        :param func:
            The function to call. Called without arguments.
        :type func: Callable[[], _pytest.runner.TResult]
        :param when:
            The phase in which the function is called.
        :param reraise:
            Exception or exceptions that shall propagate if raised by the
            function, instead of being wrapped in the CallInfo.
        """
        excinfo = None
        instant = timing.Instant()
        try:
>           result: TResult | None = func()
                                     ^^^^^^

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:361: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:250: in <lambda>
    lambda: runtest_hook(item=item, **kwds),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\logging.py:858: in pytest_runtest_setup
    yield
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\capture.py:895: in pytest_runtest_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:170: in pytest_runtest_setup
    item.session._setupstate.setup(item)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:536: in setup
    col.setup()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\python.py:1710: in setup
    self._request._fillfixtures()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:806: in _fillfixtures
    item.funcargs[argname] = self.getfixturevalue(argname)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:630: in getfixturevalue
    fixturedef = self._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1181: in execute
    fixturedef = request._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1232: in execute
    result: FixtureValue = ihook.pytest_fixture_setup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\setuponly.py:36: in pytest_fixture_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1328: in pytest_fixture_setup
    result = call_fixture_func(fixturefunc, request, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:998: in call_fixture_func
    fixture_result = next(generator)
                     ^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:300: in tmp_path
    path = _mk_tmp(request, tmp_path_factory)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:287: in _mk_tmp
    return factory.mktemp(name, numbered=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:136: in mktemp
    basename = self._ensure_relative_to_basetemp(basename)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:117: in _ensure_relative_to_basetemp
    if (self.getbasetemp() / basename).resolve().parent != self.getbasetemp():
        ^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:213: in getbasetemp
    basetemp = make_numbered_dir_with_cleanup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:420: in make_numbered_dir_with_cleanup
    raise e
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:401: in make_numbered_dir_with_cleanup
    p = make_numbered_dir(root, prefix, mode)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:228: in make_numbered_dir
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:187: in extract_suffixes
    for entry in iter:
                 ^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

root = WindowsPath('C:/Users/tsion/AppData/Local/Temp/pytest-of-tsion')
prefix = 'pytest-'

    def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:
        """Find all elements in root that begin with the prefix, case-insensitive."""
        l_prefix = prefix.lower()
>       for x in os.scandir(root):
                 ^^^^^^^^^^^^^^^^
E       PermissionError: [WinError 5] Access is denied: 'C:\\Users\\tsion\\AppData\\Local\\Temp\\pytest-of-tsion'

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
______________ ERROR at setup of test_campaign_loop_against_mock ______________

cls = <class '_pytest.runner.CallInfo'>
func = <function call_and_report.<locals>.<lambda> at 0x0000022759D48180>
when = 'setup'
reraise = (<class '_pytest.outcomes.Exit'>, <class 'KeyboardInterrupt'>)

    @classmethod
    def from_call(
        cls,
        func: Callable[[], TResult],
        when: Literal["collect", "setup", "call", "teardown"],
        reraise: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> CallInfo[TResult]:
        """Call func, wrapping the result in a CallInfo.
    
        :param func:
            The function to call. Called without arguments.
        :type func: Callable[[], _pytest.runner.TResult]
        :param when:
            The phase in which the function is called.
        :param reraise:
            Exception or exceptions that shall propagate if raised by the
            function, instead of being wrapped in the CallInfo.
        """
        excinfo = None
        instant = timing.Instant()
        try:
>           result: TResult | None = func()
                                     ^^^^^^

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:361: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:250: in <lambda>
    lambda: runtest_hook(item=item, **kwds),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\logging.py:858: in pytest_runtest_setup
    yield
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\capture.py:895: in pytest_runtest_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:170: in pytest_runtest_setup
    item.session._setupstate.setup(item)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:536: in setup
    col.setup()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\python.py:1710: in setup
    self._request._fillfixtures()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:806: in _fillfixtures
    item.funcargs[argname] = self.getfixturevalue(argname)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:630: in getfixturevalue
    fixturedef = self._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1181: in execute
    fixturedef = request._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1232: in execute
    result: FixtureValue = ihook.pytest_fixture_setup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\setuponly.py:36: in pytest_fixture_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1328: in pytest_fixture_setup
    result = call_fixture_func(fixturefunc, request, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:998: in call_fixture_func
    fixture_result = next(generator)
                     ^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:300: in tmp_path
    path = _mk_tmp(request, tmp_path_factory)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:287: in _mk_tmp
    return factory.mktemp(name, numbered=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:136: in mktemp
    basename = self._ensure_relative_to_basetemp(basename)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:117: in _ensure_relative_to_basetemp
    if (self.getbasetemp() / basename).resolve().parent != self.getbasetemp():
        ^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:213: in getbasetemp
    basetemp = make_numbered_dir_with_cleanup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:420: in make_numbered_dir_with_cleanup
    raise e
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:401: in make_numbered_dir_with_cleanup
    p = make_numbered_dir(root, prefix, mode)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:228: in make_numbered_dir
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:187: in extract_suffixes
    for entry in iter:
                 ^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

root = WindowsPath('C:/Users/tsion/AppData/Local/Temp/pytest-of-tsion')
prefix = 'pytest-'

    def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:
        """Find all elements in root that begin with the prefix, case-insensitive."""
        l_prefix = prefix.lower()
>       for x in os.scandir(root):
                 ^^^^^^^^^^^^^^^^
E       PermissionError: [WinError 5] Access is denied: 'C:\\Users\\tsion\\AppData\\Local\\Temp\\pytest-of-tsion'

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
_________________ ERROR at setup of test_results_db_roundtrip _________________

cls = <class '_pytest.runner.CallInfo'>
func = <function call_and_report.<locals>.<lambda> at 0x0000022759AA4040>
when = 'setup'
reraise = (<class '_pytest.outcomes.Exit'>, <class 'KeyboardInterrupt'>)

    @classmethod
    def from_call(
        cls,
        func: Callable[[], TResult],
        when: Literal["collect", "setup", "call", "teardown"],
        reraise: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> CallInfo[TResult]:
        """Call func, wrapping the result in a CallInfo.
    
        :param func:
            The function to call. Called without arguments.
        :type func: Callable[[], _pytest.runner.TResult]
        :param when:
            The phase in which the function is called.
        :param reraise:
            Exception or exceptions that shall propagate if raised by the
            function, instead of being wrapped in the CallInfo.
        """
        excinfo = None
        instant = timing.Instant()
        try:
>           result: TResult | None = func()
                                     ^^^^^^

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:361: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:250: in <lambda>
    lambda: runtest_hook(item=item, **kwds),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\logging.py:858: in pytest_runtest_setup
    yield
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\capture.py:895: in pytest_runtest_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:170: in pytest_runtest_setup
    item.session._setupstate.setup(item)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:536: in setup
    col.setup()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\python.py:1710: in setup
    self._request._fillfixtures()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:806: in _fillfixtures
    item.funcargs[argname] = self.getfixturevalue(argname)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:630: in getfixturevalue
    fixturedef = self._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1232: in execute
    result: FixtureValue = ihook.pytest_fixture_setup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\setuponly.py:36: in pytest_fixture_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1328: in pytest_fixture_setup
    result = call_fixture_func(fixturefunc, request, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:998: in call_fixture_func
    fixture_result = next(generator)
                     ^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:300: in tmp_path
    path = _mk_tmp(request, tmp_path_factory)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:287: in _mk_tmp
    return factory.mktemp(name, numbered=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:136: in mktemp
    basename = self._ensure_relative_to_basetemp(basename)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:117: in _ensure_relative_to_basetemp
    if (self.getbasetemp() / basename).resolve().parent != self.getbasetemp():
        ^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:213: in getbasetemp
    basetemp = make_numbered_dir_with_cleanup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:420: in make_numbered_dir_with_cleanup
    raise e
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:401: in make_numbered_dir_with_cleanup
    p = make_numbered_dir(root, prefix, mode)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:228: in make_numbered_dir
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:187: in extract_suffixes
    for entry in iter:
                 ^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

root = WindowsPath('C:/Users/tsion/AppData/Local/Temp/pytest-of-tsion')
prefix = 'pytest-'

    def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:
        """Find all elements in root that begin with the prefix, case-insensitive."""
        l_prefix = prefix.lower()
>       for x in os.scandir(root):
                 ^^^^^^^^^^^^^^^^
E       PermissionError: [WinError 5] Access is denied: 'C:\\Users\\tsion\\AppData\\Local\\Temp\\pytest-of-tsion'

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
_________________ ERROR at setup of test_save_load_roundtrip __________________

cls = <class '_pytest.runner.CallInfo'>
func = <function call_and_report.<locals>.<lambda> at 0x000002272920FCE0>
when = 'setup'
reraise = (<class '_pytest.outcomes.Exit'>, <class 'KeyboardInterrupt'>)

    @classmethod
    def from_call(
        cls,
        func: Callable[[], TResult],
        when: Literal["collect", "setup", "call", "teardown"],
        reraise: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> CallInfo[TResult]:
        """Call func, wrapping the result in a CallInfo.
    
        :param func:
            The function to call. Called without arguments.
        :type func: Callable[[], _pytest.runner.TResult]
        :param when:
            The phase in which the function is called.
        :param reraise:
            Exception or exceptions that shall propagate if raised by the
            function, instead of being wrapped in the CallInfo.
        """
        excinfo = None
        instant = timing.Instant()
        try:
>           result: TResult | None = func()
                                     ^^^^^^

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:361: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:250: in <lambda>
    lambda: runtest_hook(item=item, **kwds),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\logging.py:858: in pytest_runtest_setup
    yield
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\capture.py:895: in pytest_runtest_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:170: in pytest_runtest_setup
    item.session._setupstate.setup(item)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:536: in setup
    col.setup()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\python.py:1710: in setup
    self._request._fillfixtures()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:806: in _fillfixtures
    item.funcargs[argname] = self.getfixturevalue(argname)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:630: in getfixturevalue
    fixturedef = self._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1232: in execute
    result: FixtureValue = ihook.pytest_fixture_setup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\setuponly.py:36: in pytest_fixture_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1328: in pytest_fixture_setup
    result = call_fixture_func(fixturefunc, request, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:998: in call_fixture_func
    fixture_result = next(generator)
                     ^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:300: in tmp_path
    path = _mk_tmp(request, tmp_path_factory)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:287: in _mk_tmp
    return factory.mktemp(name, numbered=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:136: in mktemp
    basename = self._ensure_relative_to_basetemp(basename)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:117: in _ensure_relative_to_basetemp
    if (self.getbasetemp() / basename).resolve().parent != self.getbasetemp():
        ^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:213: in getbasetemp
    basetemp = make_numbered_dir_with_cleanup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:420: in make_numbered_dir_with_cleanup
    raise e
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:401: in make_numbered_dir_with_cleanup
    p = make_numbered_dir(root, prefix, mode)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:228: in make_numbered_dir
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:187: in extract_suffixes
    for entry in iter:
                 ^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

root = WindowsPath('C:/Users/tsion/AppData/Local/Temp/pytest-of-tsion')
prefix = 'pytest-'

    def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:
        """Find all elements in root that begin with the prefix, case-insensitive."""
        l_prefix = prefix.lower()
>       for x in os.scandir(root):
                 ^^^^^^^^^^^^^^^^
E       PermissionError: [WinError 5] Access is denied: 'C:\\Users\\tsion\\AppData\\Local\\Temp\\pytest-of-tsion'

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
________________ ERROR at setup of test_record_read_roundtrip _________________

cls = <class '_pytest.runner.CallInfo'>
func = <function call_and_report.<locals>.<lambda> at 0x000002275B61BB00>
when = 'setup'
reraise = (<class '_pytest.outcomes.Exit'>, <class 'KeyboardInterrupt'>)

    @classmethod
    def from_call(
        cls,
        func: Callable[[], TResult],
        when: Literal["collect", "setup", "call", "teardown"],
        reraise: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> CallInfo[TResult]:
        """Call func, wrapping the result in a CallInfo.
    
        :param func:
            The function to call. Called without arguments.
        :type func: Callable[[], _pytest.runner.TResult]
        :param when:
            The phase in which the function is called.
        :param reraise:
            Exception or exceptions that shall propagate if raised by the
            function, instead of being wrapped in the CallInfo.
        """
        excinfo = None
        instant = timing.Instant()
        try:
>           result: TResult | None = func()
                                     ^^^^^^

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:361: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:250: in <lambda>
    lambda: runtest_hook(item=item, **kwds),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\logging.py:858: in pytest_runtest_setup
    yield
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\capture.py:895: in pytest_runtest_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:170: in pytest_runtest_setup
    item.session._setupstate.setup(item)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:536: in setup
    col.setup()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\python.py:1710: in setup
    self._request._fillfixtures()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:806: in _fillfixtures
    item.funcargs[argname] = self.getfixturevalue(argname)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:630: in getfixturevalue
    fixturedef = self._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1232: in execute
    result: FixtureValue = ihook.pytest_fixture_setup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\setuponly.py:36: in pytest_fixture_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1328: in pytest_fixture_setup
    result = call_fixture_func(fixturefunc, request, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:998: in call_fixture_func
    fixture_result = next(generator)
                     ^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:300: in tmp_path
    path = _mk_tmp(request, tmp_path_factory)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:287: in _mk_tmp
    return factory.mktemp(name, numbered=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:136: in mktemp
    basename = self._ensure_relative_to_basetemp(basename)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:117: in _ensure_relative_to_basetemp
    if (self.getbasetemp() / basename).resolve().parent != self.getbasetemp():
        ^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:213: in getbasetemp
    basetemp = make_numbered_dir_with_cleanup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:420: in make_numbered_dir_with_cleanup
    raise e
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:401: in make_numbered_dir_with_cleanup
    p = make_numbered_dir(root, prefix, mode)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:228: in make_numbered_dir
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:187: in extract_suffixes
    for entry in iter:
                 ^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

root = WindowsPath('C:/Users/tsion/AppData/Local/Temp/pytest-of-tsion')
prefix = 'pytest-'

    def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:
        """Find all elements in root that begin with the prefix, case-insensitive."""
        l_prefix = prefix.lower()
>       for x in os.scandir(root):
                 ^^^^^^^^^^^^^^^^
E       PermissionError: [WinError 5] Access is denied: 'C:\\Users\\tsion\\AppData\\Local\\Temp\\pytest-of-tsion'

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
_____________________ ERROR at setup of test_sink_binding _____________________

cls = <class '_pytest.runner.CallInfo'>
func = <function call_and_report.<locals>.<lambda> at 0x000002275B009620>
when = 'setup'
reraise = (<class '_pytest.outcomes.Exit'>, <class 'KeyboardInterrupt'>)

    @classmethod
    def from_call(
        cls,
        func: Callable[[], TResult],
        when: Literal["collect", "setup", "call", "teardown"],
        reraise: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> CallInfo[TResult]:
        """Call func, wrapping the result in a CallInfo.
    
        :param func:
            The function to call. Called without arguments.
        :type func: Callable[[], _pytest.runner.TResult]
        :param when:
            The phase in which the function is called.
        :param reraise:
            Exception or exceptions that shall propagate if raised by the
            function, instead of being wrapped in the CallInfo.
        """
        excinfo = None
        instant = timing.Instant()
        try:
>           result: TResult | None = func()
                                     ^^^^^^

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:361: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:250: in <lambda>
    lambda: runtest_hook(item=item, **kwds),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\logging.py:858: in pytest_runtest_setup
    yield
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\capture.py:895: in pytest_runtest_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:170: in pytest_runtest_setup
    item.session._setupstate.setup(item)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:536: in setup
    col.setup()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\python.py:1710: in setup
    self._request._fillfixtures()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:806: in _fillfixtures
    item.funcargs[argname] = self.getfixturevalue(argname)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:630: in getfixturevalue
    fixturedef = self._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1232: in execute
    result: FixtureValue = ihook.pytest_fixture_setup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\setuponly.py:36: in pytest_fixture_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1328: in pytest_fixture_setup
    result = call_fixture_func(fixturefunc, request, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:998: in call_fixture_func
    fixture_result = next(generator)
                     ^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:300: in tmp_path
    path = _mk_tmp(request, tmp_path_factory)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:287: in _mk_tmp
    return factory.mktemp(name, numbered=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:136: in mktemp
    basename = self._ensure_relative_to_basetemp(basename)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:117: in _ensure_relative_to_basetemp
    if (self.getbasetemp() / basename).resolve().parent != self.getbasetemp():
        ^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:213: in getbasetemp
    basetemp = make_numbered_dir_with_cleanup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:420: in make_numbered_dir_with_cleanup
    raise e
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:401: in make_numbered_dir_with_cleanup
    p = make_numbered_dir(root, prefix, mode)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:228: in make_numbered_dir
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:187: in extract_suffixes
    for entry in iter:
                 ^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

root = WindowsPath('C:/Users/tsion/AppData/Local/Temp/pytest-of-tsion')
prefix = 'pytest-'

    def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:
        """Find all elements in root that begin with the prefix, case-insensitive."""
        l_prefix = prefix.lower()
>       for x in os.scandir(root):
                 ^^^^^^^^^^^^^^^^
E       PermissionError: [WinError 5] Access is denied: 'C:\\Users\\tsion\\AppData\\Local\\Temp\\pytest-of-tsion'

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
_____________ ERROR at setup of test_truncated_file_stops_cleanly _____________

cls = <class '_pytest.runner.CallInfo'>
func = <function call_and_report.<locals>.<lambda> at 0x000002275B00A020>
when = 'setup'
reraise = (<class '_pytest.outcomes.Exit'>, <class 'KeyboardInterrupt'>)

    @classmethod
    def from_call(
        cls,
        func: Callable[[], TResult],
        when: Literal["collect", "setup", "call", "teardown"],
        reraise: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> CallInfo[TResult]:
        """Call func, wrapping the result in a CallInfo.
    
        :param func:
            The function to call. Called without arguments.
        :type func: Callable[[], _pytest.runner.TResult]
        :param when:
            The phase in which the function is called.
        :param reraise:
            Exception or exceptions that shall propagate if raised by the
            function, instead of being wrapped in the CallInfo.
        """
        excinfo = None
        instant = timing.Instant()
        try:
>           result: TResult | None = func()
                                     ^^^^^^

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:361: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:250: in <lambda>
    lambda: runtest_hook(item=item, **kwds),
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\logging.py:858: in pytest_runtest_setup
    yield
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\capture.py:895: in pytest_runtest_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:170: in pytest_runtest_setup
    item.session._setupstate.setup(item)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\runner.py:536: in setup
    col.setup()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\python.py:1710: in setup
    self._request._fillfixtures()
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:806: in _fillfixtures
    item.funcargs[argname] = self.getfixturevalue(argname)
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:630: in getfixturevalue
    fixturedef = self._get_active_fixturedef(argname)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:726: in _get_active_fixturedef
    fixturedef.execute(request=subrequest)
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1232: in execute
    result: FixtureValue = ihook.pytest_fixture_setup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_hooks.py:512: in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\pluggy\_manager.py:120: in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\setuponly.py:36: in pytest_fixture_setup
    return (yield)
            ^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:1328: in pytest_fixture_setup
    result = call_fixture_func(fixturefunc, request, kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\fixtures.py:998: in call_fixture_func
    fixture_result = next(generator)
                     ^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:300: in tmp_path
    path = _mk_tmp(request, tmp_path_factory)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:287: in _mk_tmp
    return factory.mktemp(name, numbered=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:136: in mktemp
    basename = self._ensure_relative_to_basetemp(basename)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:117: in _ensure_relative_to_basetemp
    if (self.getbasetemp() / basename).resolve().parent != self.getbasetemp():
        ^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\tmpdir.py:213: in getbasetemp
    basetemp = make_numbered_dir_with_cleanup(
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:420: in make_numbered_dir_with_cleanup
    raise e
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:401: in make_numbered_dir_with_cleanup
    p = make_numbered_dir(root, prefix, mode)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:228: in make_numbered_dir
    max_existing = max(map(parse_num, find_suffixes(root, prefix)), default=-1)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:187: in extract_suffixes
    for entry in iter:
                 ^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

root = WindowsPath('C:/Users/tsion/AppData/Local/Temp/pytest-of-tsion')
prefix = 'pytest-'

    def find_prefixed(root: Path, prefix: str) -> Iterator[os.DirEntry[str]]:
        """Find all elements in root that begin with the prefix, case-insensitive."""
        l_prefix = prefix.lower()
>       for x in os.scandir(root):
                 ^^^^^^^^^^^^^^^^
E       PermissionError: [WinError 5] Access is denied: 'C:\\Users\\tsion\\AppData\\Local\\Temp\\pytest-of-tsion'

..\..\..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\pathlib.py:175: PermissionError
=========================== short test summary info ===========================
ERROR tests/integration/test_mock_closed_loop.py::test_hover_flight_clean - P...
ERROR tests/integration/test_mock_closed_loop.py::test_single_gate_pass - Per...
ERROR tests/integration/test_mock_closed_loop.py::test_campaign_loop_against_mock
ERROR tests/unit/test_metrics_and_db.py::test_results_db_roundtrip - Permissi...
ERROR tests/unit/test_params.py::test_save_load_roundtrip - PermissionError: ...
ERROR tests/unit/test_udp_tap.py::test_record_read_roundtrip - PermissionErro...
ERROR tests/unit/test_udp_tap.py::test_sink_binding - PermissionError: [WinEr...
ERROR tests/unit/test_udp_tap.py::test_truncated_file_stops_cleanly - Permiss...
61 passed, 8 errors in 8.29s

``

## 2026-07-14 12:14:50 +03:00 - commit `1d27315005dd57c21703908c7a8ef3795d9a2a47`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive, per updated QA instructions).

Command requested by runbook, executed with the bundled Python runtime because `python` and `py` still fail on this machine with a logon-session error:

``powershell
& "C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests -q --basetemp=C:\Temp\pytest-eni
``

Result: FAIL.

Summary:

- `66 passed, 3 failed, 2 warnings`.
- The previous `tmp_path` setup errors from OneDrive are gone in the elevated requested-basetemp run.
- A non-elevated rerun could not clean `C:\Temp\pytest-eni` because that directory was created by the elevated runner; a persistent ACL change to `C:\Temp` was not made.
- Failures:
  - `tests/integration/test_mock_closed_loop.py::test_hover_flight_clean`: `overrun_frac` was `0.7435`, expected `< 0.5`.
  - `tests/integration/test_mock_closed_loop.py::test_single_gate_pass`: heartbeat timeout on `udpin:127.0.0.1:24550`.
  - `tests/integration/test_mock_closed_loop.py::test_campaign_loop_against_mock`: heartbeat timeout on `udpin:127.0.0.1:24550`.

Full pytest output:

``text
FFF..................................................................    [100%]
================================== FAILURES ===================================
___________________________ test_hover_flight_clean ___________________________

sim_and_app = <function sim_and_app.<locals>.factory at 0x0000027BE3A4D760>
tmp_path = WindowsPath('C:/Temp/pytest-eni/test_hover_flight_clean0')

    def test_hover_flight_clean(sim_and_app, tmp_path):
        """Phase-0 acceptance: connect -> arm -> takeoff -> hover -> reset,
        no watchdog trips, no crashes, telemetry written."""
        # Far-away gate the drone won't reach while hovering/searching.
        sim, app = sim_and_app([Gate(pos=np.array([50.0, 0.0, -1.5]), travel_yaw=0.0)])
    
        params = base_params().patch({
            "planner.search.yaw_rate_rps": 0.4,
            # Keep the searcher from approaching: make the red mask unsatisfiable.
            "perception.detector.red_sat_min": 256,
        })
        result = app.fly(params, max_duration_s=6.0)
    
        assert result["aborted"]
        assert result["abort_reason"] == "max duration"      # NOT a watchdog/collision
        assert result["gates_passed"] == 0
        assert result["env_hits"] == 0
        assert result["gate_clips"] == 0
        assert result["loop_stats"]["ticks"] > 500
>       assert result["loop_stats"]["overrun_frac"] < 0.5    # generous for CI
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert 0.7435043304463691 < 0.5

tests\integration\test_mock_closed_loop.py:86: AssertionError
---------------------------- Captured stdout call -----------------------------
Waiting for sim heartbeat...
Connected. Starting IO agents...
gyro bias calibrated over 63 samples: [-0.00268941 -0.00274085  0.00105994]
____________________________ test_single_gate_pass ____________________________

sim_and_app = <function sim_and_app.<locals>.factory at 0x0000027BE4A58A40>

    def test_single_gate_pass(sim_and_app):
        """Full chain: detect the gate, approach, commit, pass -> race finished."""
        gate = Gate(pos=np.array([7.0, 0.0, -1.5]), travel_yaw=0.0,
                    width=1.6, height=1.6)
>       sim, app = sim_and_app([gate])
                   ^^^^^^^^^^^^^^^^^^^

tests\integration\test_mock_closed_loop.py:115: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\integration\test_mock_closed_loop.py:57: in factory
    app.connect()
src\aigp\app.py:105: in connect
    self.mavlink.connect(timeout_s=self.cfg.heartbeat_timeout_s)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <aigp.io.mavlink_io.MavlinkIO object at 0x0000027BE3A251F0>
timeout_s = 10.0

    def connect(self, timeout_s: float = 30.0) -> None:
        """Open the UDP endpoint and wait for the sim's heartbeat.
    
        In connect mode we announce ourselves with client heartbeats while
        waiting � the sim only learns our address from our first packet.
        """
        self.conn = mavutil.mavlink_connection(self.endpoint,
                                               source_system=245, source_component=190)
        deadline = time.monotonic() + timeout_s
        while True:
            if self.mode == "connect":
                self.send_client_heartbeat()
            msg = self.conn.wait_heartbeat(timeout=1.0)
            if msg is not None:
                return
            if time.monotonic() > deadline:
>               raise TimeoutError(f"no heartbeat on {self.endpoint} within {timeout_s}s")
E               TimeoutError: no heartbeat on udpin:127.0.0.1:24550 within 10.0s

src\aigp\io\mavlink_io.py:106: TimeoutError
---------------------------- Captured stdout call -----------------------------
Waiting for sim heartbeat...
_______________________ test_campaign_loop_against_mock _______________________

sim_and_app = <function sim_and_app.<locals>.factory at 0x0000027BE4AE89A0>
tmp_path = WindowsPath('C:/Temp/pytest-eni/test_campaign_loop_against_moc0')

    def test_campaign_loop_against_mock(sim_and_app, tmp_path):
        """The flight-to-flight tuning loop end to end: 3 flights, sim reset
        between, results recorded and scored."""
        from aigp.learning.campaign import Campaign
        from aigp.learning.optimizers import RandomSearch
        from aigp.learning.results_db import ResultsDB
    
        gate = Gate(pos=np.array([7.0, 0.0, -1.5]), travel_yaw=0.0,
                    width=1.6, height=1.6)
>       sim, app = sim_and_app([gate])
                   ^^^^^^^^^^^^^^^^^^^

tests\integration\test_mock_closed_loop.py:138: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests\integration\test_mock_closed_loop.py:57: in factory
    app.connect()
src\aigp\app.py:105: in connect
    self.mavlink.connect(timeout_s=self.cfg.heartbeat_timeout_s)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <aigp.io.mavlink_io.MavlinkIO object at 0x0000027BE4AC3500>
timeout_s = 10.0

    def connect(self, timeout_s: float = 30.0) -> None:
        """Open the UDP endpoint and wait for the sim's heartbeat.
    
        In connect mode we announce ourselves with client heartbeats while
        waiting � the sim only learns our address from our first packet.
        """
        self.conn = mavutil.mavlink_connection(self.endpoint,
                                               source_system=245, source_component=190)
        deadline = time.monotonic() + timeout_s
        while True:
            if self.mode == "connect":
                self.send_client_heartbeat()
            msg = self.conn.wait_heartbeat(timeout=1.0)
            if msg is not None:
                return
            if time.monotonic() > deadline:
>               raise TimeoutError(f"no heartbeat on {self.endpoint} within {timeout_s}s")
E               TimeoutError: no heartbeat on udpin:127.0.0.1:24550 within 10.0s

src\aigp\io\mavlink_io.py:106: TimeoutError
---------------------------- Captured stdout call -----------------------------
Waiting for sim heartbeat...
============================== warnings summary ===============================
..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\cacheprovider.py:469
  C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\cacheprovider.py:469: PytestCacheWarning: could not create cache path C:\Users\tsion\Projects\eni_dcim_qa\.pytest_cache\v\cache\nodeids: [WinError 5] Access is denied: 'C:\\Users\\tsion\\Projects\\eni_dcim_qa\\.pytest_cache\\v\\cache'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

..\..\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\cacheprovider.py:423
  C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages\_pytest\cacheprovider.py:423: PytestCacheWarning: could not create cache path C:\Users\tsion\Projects\eni_dcim_qa\.pytest_cache\v\cache\lastfailed: [WinError 5] Access is denied: 'C:\\Users\\tsion\\Projects\\eni_dcim_qa\\.pytest_cache\\v\\cache'
    config.cache.set("cache/lastfailed", self.lastfailed)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/integration/test_mock_closed_loop.py::test_hover_flight_clean - ...
FAILED tests/integration/test_mock_closed_loop.py::test_single_gate_pass - Ti...
FAILED tests/integration/test_mock_closed_loop.py::test_campaign_loop_against_mock
3 failed, 66 passed, 2 warnings in 34.72s

``
## 2026-07-14 17:14:47 +03:00 - commit `2cc8df981f2a804ed8893ad3d1ca3ab5d13e87f9`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).

Command:

```powershell
& "C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pytest tests -q --basetemp=C:\Temp\pytest-eni
```

Result: FAIL.

Summary:

- Captured full output in `tuning/pytest-windows-2cc8df9-basetemp-full.txt`.
- `66 passed, 3 failed, 2 warnings`.
- `test_hover_flight_clean`: `overrun_frac` was `0.7435`, expected `< 0.5`.
- `test_single_gate_pass`: heartbeat timeout on `udpin:127.0.0.1:24550`.
- `test_campaign_loop_against_mock`: heartbeat timeout on `udpin:127.0.0.1:24550`.
- Ran elevated only to use the required `C:\Temp\pytest-eni` basetemp without changing persistent ACLs.

## 2026-07-15 07:20:00 +03:00 - commit `5ec57ee2fc476a496639ea3b882e813c96a68919`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).

Requested command:

```powershell
python -m pytest tests -q --basetemp=C:\Temp\pytest-eni
```

Result: FAIL.

Summary:

- Pre-run guard was clear: no `FlightSim`/`DCGame`, no `C:\Temp\eni_dcim_sim.lock`.
- The bare `python` launcher failed before pytest with the Windows logon-session error, so the bundled Codex Python runtime was used for the actual suite verdict.
- The sandboxed bundled run hit `PermissionError: [WinError 5]` while pytest tried to clean `C:\Temp\pytest-eni`; an elevated rerun was used only for the required basetemp.
- Captured full elevated output in `tuning/pytest-windows-5ec57ee-basetemp-full.txt`.
- `69 passed, 4 failed, 2 warnings in 44.45s`.
- `test_hover_flight_clean`: `overrun_frac` was `0.7435`, expected `< 0.5`.
- `test_single_gate_pass`: heartbeat timeout on `udpin:127.0.0.1:24550`.
- `test_campaign_loop_against_mock`: heartbeat timeout on `udpin:127.0.0.1:24550`.
- `test_first_gate_pass_with_second_gate_visible`: heartbeat timeout on `udpin:127.0.0.1:24550`.
- A focused rerun of these four tests was not executed because the guard later detected `FlightSim` PID `53212`, start time `2026-07-15 07:20:43 +03:00`, with no lock file.

## 2026-07-15 22:46:55 +03:00 - commit `1998e5cc047a25bf1cdf64976ffb9d13b4daf4e2`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).

Requested command:

```powershell
python -m pytest tests -q --basetemp=C:\Temp\pytest-eni
```

Result: FAIL.

Summary:

- Pre-run guard was clear: no `FlightSim`/`DCGame`, no `C:\Temp\eni_dcim_sim.lock`.
- The bare `python` launcher failed before pytest with the Windows logon-session error, so the bundled Codex Python runtime was used for the actual suite verdict.
- The sandboxed bundled run hit `PermissionError: [WinError 5]` while pytest tried to clean `C:\Temp\pytest-eni`; an elevated rerun was used only for the required basetemp.
- Captured full elevated output in `tuning/pytest-windows-1998e5c-basetemp-full.txt`.
- `69 passed, 3 failed, 1 xfailed, 2 warnings in 47.58s`.
- Expected xfail observed: `test_first_gate_pass_with_second_gate_visible` is now xfailed and is not counted as a CI failure.
- `test_hover_flight_clean`: `overrun_frac` was `0.7431438127090301`, expected `< 0.5`.
- `test_single_gate_pass`: heartbeat timeout on `udpin:127.0.0.1:24550`.
- `test_campaign_loop_against_mock`: heartbeat timeout on `udpin:127.0.0.1:24550`.

## 2026-07-16 01:33:32 +03:00 - commit `f5e88659a26056a7f692412004e30fac498dc276`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).

Requested command:

```powershell
python -m pytest tests -q --basetemp=C:\Temp\pytest-eni
```

Result: FAIL.

Summary:

- Pre-run guard was clear: no `FlightSim`/`DCGame`, no `C:\Temp\eni_dcim_sim.lock`.
- The bare `python` launcher still failed before pytest with the Windows logon-session error, so the bundled Codex Python runtime was used for the actual suite verdict.
- Captured full elevated output in `tuning/pytest-windows-f5e8865-basetemp-full.txt`.
- `69 passed, 3 failed, 1 xfailed, 2 warnings in 49.60s`.
- Expected xfail observed: `test_first_gate_pass_with_second_gate_visible` remains xfailed and is not counted as a CI failure.
- Before timer fix: hover `overrun_frac` was `0.7431438127090301` on commit `1998e5cc047a25bf1cdf64976ffb9d13b4daf4e2`; CI also had 2 heartbeat timeouts.
- After timer fix on this Windows machine: CI hover `overrun_frac` was `0.7431254191817572`; the standalone matching hover probe recorded `0.7468099395567495`.
- After timer fix heartbeat timeout count in CI: 2 (`test_single_gate_pass`, `test_campaign_loop_against_mock`).
- `test_hover_flight_clean`: `overrun_frac` was `0.7431254191817572`, expected `< 0.5`.
- `test_single_gate_pass`: heartbeat timeout on `udpin:127.0.0.1:24550`.
- `test_campaign_loop_against_mock`: heartbeat timeout on `udpin:127.0.0.1:24550`.

## 2026-07-16 06:39:42 +03:00 - commit `44f5f741878e3cf51461c4706e40b7aaaee5b523`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).

Requested command:

```powershell
python -m pytest tests -q --basetemp=C:\Temp\pytest-eni
```

Result: FAIL.

Summary:

- Pre-run guard was clear: no `FlightSim`/`DCGame`, no `C:\Temp\eni_dcim_sim.lock`.
- The bare `python` launcher still failed before pytest with the Windows logon-session error, so the bundled Codex Python runtime was used for the actual suite verdict.
- Captured full elevated output in `tuning/pytest-windows-44f5f74-basetemp-full.txt`.
- `68 passed, 4 failed, 1 xfailed, 2 warnings in 48.22s`.
- Expected xfail observed: `test_first_gate_pass_with_second_gate_visible` remains xfailed and is not counted as a CI failure.
- Before v4: v3 CI hover `overrun_frac` was `0.7431254191817572`; v3 standalone hover probe was `0.7468099395567495`; CI had 2 heartbeat timeouts.
- After v4: hover overrun is telemetry-only on Windows; the standalone matching hover probe recorded `0.7471341874578556`.
- After v4 heartbeat timeout count in CI: 2 (`test_single_gate_pass`, `test_campaign_loop_against_mock`).
- New non-overrun failures: `tests/unit/test_fsm.py::test_happy_path` stayed in `THROTTLE_DOWN` instead of `TAKEOFF`; `tests/unit/test_fsm.py::test_env_collision_aborts` did not mark the manager done.

## 2026-07-16 17:37:37 +03:00 - commit `8d792a93fb4090760b83b94e7c4506a1131076b7`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).

Requested command:

```powershell
python -m pytest tests -q --basetemp=C:\Temp\pytest-eni
```

Result: FAIL.

Summary:

- Pre-run guard was clear for FSM isolation, full CI, and the campaign start: no `FlightSim`/`DCGame`, no `C:\Temp\eni_dcim_sim.lock`.
- HEAD contains requested base `74d93d1`; actual tested HEAD was `8d792a93fb4090760b83b94e7c4506a1131076b7`.
- FSM isolation first, `tests/unit/test_fsm.py -q` x5 with `AIGP_NOSLEEP=1`: runs 1-2 passed; runs 3-5 failed. This is flaky, not deterministic, so I did not paste full `-vv` context as a deterministic Windows bug.
- FSM failure mix: run 3 failed `test_env_collision_aborts` and `test_gate_clips_tolerated_up_to_budget`; run 4 failed `test_happy_path` and `test_env_collision_aborts`; run 5 failed `test_happy_path`.
- Captured FSM outputs in `tuning/pytest-fsm-8d792a9-run1.txt` through `tuning/pytest-fsm-8d792a9-run5.txt`.
- The first full CI attempt hit `PermissionError: [WinError 5]` while pytest tried to clean `C:\Temp\pytest-eni`; an elevated rerun was used only for the required basetemp.
- Captured full elevated CI output in `tuning/pytest-windows-8d792a9-basetemp-full.txt`.
- CI result: `70 passed, 2 failed, 1 xfailed, 2 warnings in 49.82s`.
- Expected xfail observed: `test_first_gate_pass_with_second_gate_visible` remains xfailed and is not counted as a CI failure.
- CI failures: `tests/integration/test_mock_closed_loop.py::test_single_gate_pass` and `tests/integration/test_mock_closed_loop.py::test_campaign_loop_against_mock`, both heartbeat timeouts on `udpin:127.0.0.1:24550`.
- Before v5: v4 standalone hover probe `overrun_frac` was `0.7471341874578556`.
- After v5: standalone hover probe with `AIGP_NOSLEEP=1` recorded `overrun_frac=0.7435043304463691` over 1501 ticks. This is slightly lower but still Windows-tick high; now reported as telemetry.
- Campaign 40 with guard completed before the SIM OPERATOR lock appeared: 40/40 flights, stale-IMU `0/40` (`0.0%`), so no `--low-load` fallback was needed.
- Campaign result: 2 finishes, 10 total gates, max 2 gates, best score `188.67200000000003`.
- Best flight: `20260716T141808-fa6abf10`, 2 gates, finished true, no abort, no gate clips, no env hits, lap time `11.327999999999975`.
- Best parameters for the next Sakana/mock starting point:
  `control.att_rate.vz_i=0.4282407486549845`,
  `control.att_rate.vz_p=0.5997127390752905`,
  `estimation.vision_vel_blend=0.1752711783794073`,
  `planner.approach.aim_up_m=0.5155244016963784`,
  `planner.commit.distance_m=1.5729619093978944`,
  `planner.commit.duration_s=1.1792217758917576`.
- The helper script then began its extra default verification pass and was stopped by the guard after 10/20 default-verification flights because the SIM OPERATOR lock appeared: `phase4b-r2training-chain`. I did not run anything further under the lock.

## 2026-07-16 21:18:40 +03:00 - commit `9fe370237fa1cd57548aadb49f9f20f943b58311`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).

Requested command:

```powershell
python -m pytest tests -q --basetemp=C:\Temp\pytest-eni
```

Result: FAIL.

Summary:

- `git pull --rebase` fast-forwarded to `9fe370237fa1cd57548aadb49f9f20f943b58311`, which is the requested `9fe3702` baseline.
- Pre-run guard was clear for Windows CI, the hover telemetry probe, and the reflight matrix: no `FlightSim`/`DCGame`, no `C:\Temp\eni_dcim_sim.lock`.
- Captured full CI output in `tuning/pytest-windows-9fe3702-basetemp-full.txt`.
- CI result: `71 passed, 3 failed, 1 xfailed, 2 warnings in 51.00s`.
- Expected xfail observed: `test_first_gate_pass_with_second_gate_visible` remains xfailed and is not counted as a CI failure.
- CI chain-correctness failures: `tests/integration/test_mock_closed_loop.py::test_single_gate_pass` and `tests/integration/test_mock_closed_loop.py::test_campaign_loop_against_mock`, both heartbeat timeouts on `udpin:127.0.0.1:24550`; `tests/unit/test_fsm.py::test_env_collision_aborts` still did not mark the manager done.
- Hover overrun is telemetry on Windows. The isolated mock hover probe recorded `overrun_frac=0.7426075268817204`, `ticks=1488`, `overruns=1105`, `max_late_us=27000`; captured in `tuning/phase5-hover-9fe3702/hover-overrun-telemetry.json`.
- Reflight matrix completed offline across all 56 committed `.aigprec` slices and builds `fd9d419`, `54a75a1`, `80c6d44`, and `HEAD`.
- Reflight pairing: 45 runnable slices per build, 11 skipped per build because no unique committed `*-flight.jsonl` could be paired, 0 errors.
- Reflight result was byte-for-byte equivalent at the coverage level across all four builds: 12,356 fixes, 11,950 accepted fixes, 0 fixes below 5m, 12,356 fixes at `>=5m`.
- The table is in `tuning/phase5-reflight-9fe3702/fix-coverage-vs-range.md`; full CSV/JSON are alongside it.
- Interpretation: the current committed slices confirm the Phase 5 concern. The offline suite sees no close-range detector fixes below 5m on any recent build, so planner tuning cannot address the close-range blind stretch by itself.
- Pre-push rebase later advanced HEAD to `5e3ada6d11203226c23f40d899871f39f298aea7`; the only intervening file was `docs/thinktank/BRIEF.md`, so code, fixtures, scripts, and the measured reflight inputs remained unchanged from `9fe3702`.

## 2026-07-17 - commit `34d4f6b6b4476162dff0a9d7ee1f798528fe90e0`

Role: QA & MOCK-TUNER.

Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).

Requested command:

```powershell
python -m pytest tests -q --basetemp=C:\Temp\pytest-eni
```

Result: FAIL.

Summary:

- `git pull --ff-only` advanced the checkout to `34d4f6b6b4476162dff0a9d7ee1f798528fe90e0` (`terminal ownership`).
- The SIM lock was clear at bootstrap. Later operator locks appeared during the work; QA runs were paused while the lock and/or `FlightSim` were live.
- The bare `python` and `py` launchers failed with the Windows logon-session error, so the bundled Codex Python runtime was used.
- First sandboxed CI attempt reached `106 passed, 1 xfailed` but failed during pytest cleanup of `C:\Temp\pytest-eni` with `PermissionError: [WinError 5]`.
- Elevated CI rerun output is in `tuning/pytest-windows-34d4f6b-basetemp-full.txt`.
- Elevated CI result: `2 failed, 112 passed, 1 xfailed, 2 warnings in 50.42s`.
- CI failures: `tests/integration/test_mock_closed_loop.py::test_single_gate_pass` and `tests/integration/test_mock_closed_loop.py::test_campaign_loop_against_mock`, both heartbeat timeouts on `udpin:127.0.0.1:24550`.
- Solo reruns both passed: `test_single_gate_pass` in `8.09s`, `test_campaign_loop_against_mock` in `53.38s`.
- Closed-loop arbitration, solo 3x per test: `single_gate` was `1/3` on HEAD and `1/3` on `116b27e`; `first_gate_with_second_visible` was pytest-green `3/3` on both builds, with xfail/xpass details in per-run logs.
- Reflight matrix with current harness: `9fe3702` had `2706/3233` fixes (`0.837`) and `2407` accepted; HEAD had `2842/3233` fixes (`0.879`) and `2676` accepted. HEAD close tracker contributed `11` fixes.
- The three full-approach phase5b-confirm slices were included. HEAD accepted counts were `212`, `233`, and `72`; close-tracker fixes were `0`, `7`, and `3`.
- Hover overrun telemetry on HEAD: `overrun_frac=0.7435043304463691`, `ticks=1501`, `overruns=1116`, `max_late_us=11000`. This is not a material improvement from the prior ~0.74 Windows baseline.
- Consolidated report: `tuning/phase5b-qa-34d4f6b-summary.md`.
