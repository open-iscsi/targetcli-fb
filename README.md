targetcli-fb
============

A command shell for managing the Linux LIO kernel target
--------------------------------------------------------
An administration shell for configuring iSCSI, FCoE, and other
SCSI targets, using the TCM/LIO kernel target subsystem. FCoE
users will also need to install and use fcoe-utils.


targetcli-fb development
------------------------
targetcli-fb is licensed under the Apache 2.0 license. Contributions are welcome.

 * Mailing list: [targetcli-fb-devel](https://lists.fedorahosted.org/mailman/listinfo/targetcli-fb-devel)
 * Source repo: [GitHub](https://github.com/open-iscsi/targetcli-fb)
 * Bugs: [GitHub](https://github.com/open-iscsi/targetcli-fb/issues) or [Trac](https://fedorahosted.org/targetcli-fb/)
 * Tarballs: [fedorahosted](https://fedorahosted.org/releases/t/a/targetcli-fb/)
 * Playlist of instructional screencast videos: [YouTube](https://www.youtube.com/playlist?list=PLC2C75481A3ABB067)

Packages
--------
targetcli-fb is packaged for a number of Linux distributions including
RHEL,
[Fedora](https://apps.fedoraproject.org/packages/targetcli),
openSUSE, Arch Linux,
[Gentoo](https://packages.gentoo.org/packages/sys-block/targetcli-fb), and
[Debian](https://tracker.debian.org/pkg/targetcli-fb).

Contribute
----------
targetcli complies with PEP 621 and as such can be built and installed with tools like `build` and `pip`.

For development, consider using [Hatch](https://hatch.pypa.io):  
`hatch shell` to create and enter a Python virtualenv with the project installed in editable mode  
`pre-commit install` to enable pre-commit hooks  
`hatch build` to create tarball and wheel  

"fb" -- "free branch"
---------------------

targetcli-fb is a fork of the "targetcli" code written by RisingTide Systems.
The "-fb" differentiates between the original and this version.
Please ensure to use either all "fb" versions of the targetcli components --
targetcli, rtslib, and configshell, or stick with all non-fb versions, since
they are no longer strictly compatible.
