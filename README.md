targetcli-fb
============

A command shell for managing the Linux LIO kernel target
--------------------------------------------------------
targetcli-fb is a command-line interface for configuring the LIO generic
SCSI target, present in 3.x Linux kernel versions.

Compatible with both Python 2.7 and 3.x by using the python-six library.

targetcli-fb development
------------------------
targetcli-fb is licensed under the Apache 2.0 license. Contributions are welcome.

 * Mailing list: [targetcli-fb-devel](https://lists.fedorahosted.org/mailman/listinfo/targetcli-fb-devel)
 * Source repo: [GitHub](https://github.com/agrover/targetcli-fb)
 * Bugs: [GitHub](https://github.com/agrover/targetcli-fb/issues) or [Trac](https://fedorahosted.org/targetcli-fb/)
 * Tarballs: [fedorahosted](https://fedorahosted.org/releases/t/a/targetcli-fb/)
 * Playlist of instructional screencast videos: [YouTube](https://www.youtube.com/playlist?list=PLC2C75481A3ABB067)

In-repo packaging
-----------------
Packaging scripts for RPM and DEB are included, but these are to make end-user
custom packaging easier -- distributions tend to maintain their own packaging
scripts separately. If you run into issues with packaging, start with opening
a bug on your distro's bug reporting system.

Some people do use these scripts, so we want to keep them around. Fixes for
any breakage you encounter are welcome.

"fb" -- "free branch"
---------------------

targetcli-fb is a fork of the "targetcli" code written by RisingTide Systems.
The "-fb" differentiates between the original and this version.
Please ensure to use either all "fb" versions of the targetcli components --
targetcli, rtslib, and configshell, or stick with all non-fb versions, since
they are no longer strictly compatible.
