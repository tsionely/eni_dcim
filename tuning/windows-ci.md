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
