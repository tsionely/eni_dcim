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
