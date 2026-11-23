# The Fedora package is built from this spec file. Packit copies it to
# Fedora dist-git with every release (propose_downstream in .packit.yaml),
# so change the packaging here rather than in dist-git.

Name:           targetcli
License:        Apache-2.0
Summary:        An administration shell for storage targets
# Not a version: the version comes from the git tag (hatch-vcs). Packit
# fills it in for pull request builds and releases, so build this spec
# with Packit, e.g. "packit srpm" or "packit build".
Version:        0.0.0
Release:        %autorelease
URL:            https://github.com/open-iscsi/targetcli-fb
Source:         %{pypi_source targetcli}
BuildArch:      noarch
BuildRequires:  python3-devel, systemd-rpm-macros
Requires:       target-restore
# Discovery of tcmu-runner handlers (user:* backstores) over D-Bus, the
# optional "tcmu" extra upstream. Without it, user:* backstores are not
# shown, everything else works.
Recommends:     targetcli+tcmu = %{version}-%{release}


%description
An administration shell for configuring iSCSI, FCoE, and other
SCSI targets, using the TCM/LIO kernel target subsystem. FCoE
users will also need to install and use fcoe-utils.

%pyproject_extras_subpkg -n targetcli tcmu

%prep
%autosetup -n targetcli-%{version}

%generate_buildrequires
%pyproject_buildrequires -x tcmu

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l targetcli
mkdir -p %{buildroot}%{_sysconfdir}/target/backup
mkdir -p %{buildroot}%{_mandir}/man8/
install -m 644 targetcli*.8 %{buildroot}%{_mandir}/man8/
mkdir -p %{buildroot}%{_unitdir}/
install -m 644 systemd/* %{buildroot}%{_unitdir}/

%check
%pyproject_check_import

%post
%systemd_post targetclid.service targetclid.socket

%preun
%systemd_preun targetclid.service targetclid.socket

%postun
%systemd_postun_with_restart targetclid.service targetclid.socket

%files -f %{pyproject_files}
%doc README.md
%{_bindir}/targetcli
%{_bindir}/targetclid
%{_mandir}/man8/targetcli*.8*
%{_unitdir}/targetclid.service
%{_unitdir}/targetclid.socket
%dir %{_sysconfdir}/target
%dir %{_sysconfdir}/target/backup

%changelog
%autochangelog
