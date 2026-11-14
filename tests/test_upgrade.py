'''Tests for bbctrl.Upgrade: the message shown when a firmware upgrade script
exits without installing.  While bbctrl still runs to see the exit, nothing
was installed, so every exit is reported.
'''

from bbctrl.Upgrade import failure_message, OUTPUT_LINES


def test_no_output_reports_exit_code_only():
    assert failure_message(1, '') == 'Firmware upgrade failed (exit code 1)'


def test_one_line_of_output_is_included():
    msg = failure_message(1, 'SHA-256 check failed, not installing\n')
    assert msg == ('Firmware upgrade failed (exit code 1):\n'
                   'SHA-256 check failed, not installing')


def test_two_lines_keep_their_order():
    out = 'curl: (6) Could not resolve host: api.github.com\n' \
          'Could not reach GitHub to find the latest release.\n'
    assert failure_message(1, out).splitlines()[1:] == [
        'curl: (6) Could not resolve host: api.github.com',
        'Could not reach GitHub to find the latest release.']


def test_long_output_keeps_only_the_last_lines():
    out = '\n'.join('line %d' % i for i in range(20))
    lines = failure_message(1, out).splitlines()[1:]
    assert lines == ['line %d' % i for i in range(20 - OUTPUT_LINES, 20)]


def test_blank_lines_are_dropped():
    assert failure_message(2, '\n  \nAn upgrade is already running\n\n') == \
        'Firmware upgrade failed (exit code 2):\nAn upgrade is already running'


def test_clean_exit_says_nothing_was_installed():
    assert failure_message(0, '') == \
        'Firmware upgrade failed, nothing was installed'


# The Upgrade class, with the process, I/O loop, LCD and log faked at their
# seams.  The fake process writes its output where Popen was told to.

from bbctrl import Upgrade as upgrade_module


class FakeProc:
    def __init__(self, args, stdout, stderr):
        self.args = args
        self.stdout = stdout
        self.returncode = None

    def finish(self, returncode, output):
        self.stdout.write(output)
        self.stdout.flush()
        self.returncode = returncode

    def poll(self): return self.returncode


class FakeCtrl:
    def __init__(self):
        self.pending = []
        self.errors = []
        self.lcd_events = []

        ctrl = self

        class IOLoop:
            def call_later(self, delay, cb): ctrl.pending.append(cb)

        class LCD:
            def goodbye(self, msg): ctrl.lcd_events.append(('goodbye', msg))
            def resume(self): ctrl.lcd_events.append(('resume',))

        class Logger:
            def error(self, msg): ctrl.errors.append(msg)

        class Log:
            def get(self, name): return Logger()

        self.ioloop = IOLoop()
        self.lcd = LCD()
        self.log = Log()

    def run_pending(self):
        pending, self.pending = self.pending, []
        for cb in pending: cb()


def start(monkeypatch, cmd = ['/usr/local/bin/upgrade-bbctrl']):
    procs = []

    def popen(args, stdout, stderr):
        procs.append(FakeProc(args, stdout, stderr))
        return procs[-1]

    monkeypatch.setattr(upgrade_module.subprocess, 'Popen', popen)
    ctrl = FakeCtrl()
    upgrade_module.Upgrade(ctrl, cmd)
    return ctrl, procs[0]


def test_runs_the_script_in_its_own_systemd_scope(monkeypatch):
    ctrl, proc = start(monkeypatch)
    assert proc.args[0] == 'systemd-run'
    assert '--scope' in proc.args
    assert proc.args[-1] == '/usr/local/bin/upgrade-bbctrl'
    assert ctrl.lcd_events == [('goodbye', 'Upgrading firmware')]


def test_nothing_is_reported_while_the_script_runs(monkeypatch):
    ctrl, proc = start(monkeypatch)
    for _ in range(3): ctrl.run_pending()
    assert ctrl.errors == []
    assert len(ctrl.pending) == 1 # Still polling


def test_failed_script_is_reported_with_its_output(monkeypatch):
    ctrl, proc = start(monkeypatch)
    ctrl.run_pending()
    proc.finish(1, 'Download of bbctrl-3.0.1.tar.bz2 failed\n')
    ctrl.run_pending()

    assert ctrl.errors == ['Firmware upgrade failed (exit code 1):\n'
                           'Download of bbctrl-3.0.1.tar.bz2 failed']
    assert ctrl.pending == [] # Stopped polling
    assert ctrl.lcd_events[-1] == ('resume',)
