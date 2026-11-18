targetcli
=========

A command shell for managing the Linux LIO kernel target
--------------------------------------------------------
An administration shell for configuring iSCSI, FCoE, and other
SCSI targets, using the TCM/LIO kernel target subsystem. FCoE
users will also need to install and use fcoe-utils.


targetcli development
---------------------
targetcli is licensed under the Apache 2.0 license. Contributions are welcome.

 * Source repo: [GitHub](https://github.com/open-iscsi/targetcli-fb)
 * Bugs: [GitHub](https://github.com/open-iscsi/targetcli-fb/issues)
 * Releases: [PyPI](https://pypi.org/project/targetcli/)
 * Playlist of instructional screencast videos: [YouTube](https://www.youtube.com/playlist?list=PLC2C75481A3ABB067)

Packages
--------
targetcli is packaged for a number of Linux distributions including
RHEL,
[Fedora](https://src.fedoraproject.org/rpms/targetcli),
openSUSE, Arch Linux,
[Gentoo](https://packages.gentoo.org/packages/sys-block/targetcli-fb), and
[Debian](https://tracker.debian.org/pkg/targetcli-fb).

It can also be installed from PyPI with `pip install targetcli`. User-backed
(`user:*`) backstores provided by tcmu-runner are discovered over D-Bus, which
needs PyGObject: `pip install targetcli[tcmu]`.

Contribute
----------
targetcli complies with PEP 621 and as such can be built and installed with tools like `build` and `pip`.

For development, consider using [Hatch](https://hatch.pypa.io):  
`hatch shell` to create and enter a Python virtualenv with the project installed in editable mode  
`pre-commit install` to enable pre-commit hooks  
`hatch build` to create tarball and wheel  

Formerly targetcli-fb
---------------------
This project was previously known as targetcli-fb ("free branch"), a fork of
the original "targetcli" code written by RisingTide Systems. The fork has long
been the only maintained version, so the `-fb` suffix has been dropped.
