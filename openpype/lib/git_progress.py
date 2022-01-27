import git
from tqdm import tqdm


class _GitProgress(git.remote.RemoteProgress):
    """ Class handling displaying progress during git operations.

        This is using **tqdm** for showing progress bars. As **GitPython**
        is parsing progress directly from git command, it is somehow unreliable
        as in some operations it is difficult to get total count of iterations
        to display meaningful progress bar.

    """
    _t = None
    _code = 0
    _current_status = ''
    _current_max = ''

    _description = {
        256: "Checking out files",
        4: "Counting objects",
        128: "Finding sources",
        32: "Receiving objects",
        64: "Resolving deltas",
        16: "Writing objects"
    }

    def __init__(self):
        super().__init__()

    def __del__(self):
        if self._t is not None:
            self._t.close()

    def _detroy_tqdm(self):
        """ Used to close tqdm when operation ended.

        """
        if self._t is not None:
            self._t.close()
            self._t = None

    def _check_mask(self, opcode: int) -> bool:
        """" Add meaningful description to **GitPython** opcodes.

            :param opcode: OP_MASK opcode
            :type opcode: int
            :return: String description of opcode
            :rtype: str

            .. seealso:: For opcodes look at :class:`git.RemoteProgress`

        """
        if opcode & self.COUNTING:
            return self._description.get(self.COUNTING)
        elif opcode & self.CHECKING_OUT:
            return self._description.get(self.CHECKING_OUT)
        elif opcode & self.WRITING:
            return self._description.get(self.WRITING)
        elif opcode & self.RECEIVING:
            return self._description.get(self.RECEIVING)
        elif opcode & self.RESOLVING:
            return self._description.get(self.RESOLVING)
        elif opcode & self.FINDING_SOURCES:
            return self._description.get(self.FINDING_SOURCES)
        else:
            return "Processing"

    def update(self, op_code, cur_count, max_count=None, message=''):
        """ Called when git operation update progress.

        .. seealso:: For more details see
                     :func:`git.objects.submodule.base.Submodule.update`
                     `Documentation <https://gitpython.readthedocs.io/en/\
stable/reference.html#git.objects.submodule.base.Submodule.update>`_

        """
        code = self._check_mask(op_code)
        if self._current_status != code or self._current_max != max_count:
            self._current_max = max_count
            self._current_status = code
            self._detroy_tqdm()
            self._t = tqdm(total=max_count)
            self._t.set_description("  . {}".format(code))

        self._t.update(cur_count)
