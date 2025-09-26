Name:           python-targetcli-fb
Version:        2.1.58
Release:        %autorelease
Summary:        Command shell for managing the Linux LIO kernel target

License:        Apache-2.0
URL:            https://github.com/open-iscsi/targetcli-fb
Source:         %{pypi_source targetcli}

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  hatch
BuildRequires:  python3-hatch-vcs
BuildRequires:  python3-hatchling
BuildRequires:  systemd-rpm-macros

%global _description %{expand:
An administration shell for configuring iSCSI, FCoE, and other SCSI targets,
using the TCM/LIO kernel target subsystem.
}

%description
%{_description}

%package -n targetcli
Summary:        %{summary}
Requires:       python3-configshell
Requires:       python3-rtslib
Requires:       target-restore
Requires:       python3-six
Requires:       python3-dbus
Requires:       python3-gobject-base

%description -n targetcli
%{_description}

%prep
%autosetup -n targetcli-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files targetcli

mkdir -p %{buildroot}%{_sysconfdir}/target/backup
install -d %{buildroot}%{_unitdir}
install -p -m 644 systemd/targetclid.service %{buildroot}%{_unitdir}/
install -p -m 644 systemd/targetclid.socket %{buildroot}%{_unitdir}/
install -d %{buildroot}%{_mandir}/man8
install -p -m 644 targetcli.8 %{buildroot}%{_mandir}/man8/
install -p -m 644 targetclid.8 %{buildroot}%{_mandir}/man8/

%files -n targetcli -f %{pyproject_files}
%license COPYING
%doc README.md THANKS
%{_bindir}/targetcli
%{_bindir}/targetclid
%{_mandir}/man8/targetcli.8*
%{_mandir}/man8/targetclid.8*
%{_unitdir}/targetclid.service
%{_unitdir}/targetclid.socket
%dir %{_sysconfdir}/target
%dir %{_sysconfdir}/target/backup

%changelog
%autochangelog
